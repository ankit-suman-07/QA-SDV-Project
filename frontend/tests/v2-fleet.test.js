import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { createV2FleetApi } from '../js/v2-fleet-api.js';
import { V2FleetDashboard, V2_VEHICLES } from '../js/v2-fleet-model.js';

const fixture = name => JSON.parse(readFileSync(new URL(`../../tests/fixtures/v2/${name}.json`, import.meta.url)));
const source = fixture('health-events/recovery-sensor-failure');
const recovering = {
  ...source, lastEventId: source.eventId, healthStatus: source.health, activeFaults: source.faults, availability: 'AVAILABLE',
};
const action = fixture('diagnostics/cases').request.action;
const view = vehicleId => vehicleId === source.vehicleId ? recovering : {
  vehicleId, availability: 'UNAVAILABLE', healthStatus: null, lidar: null, lastEventId: null,
};
const counts = fixture('twins/fleet-cases').cases[2].expected;
const summary = {
  generatedAt: '2026-01-01T00:00:04Z', vehicles: V2_VEHICLES.map(vehicleId => ({ ...view(vehicleId), availability: 'UNAVAILABLE' })),
  ...Object.fromEntries(['totalVehicles', 'availableVehicles', 'staleVehicles', 'unavailableVehicles',
    'healthyVehicles', 'warningVehicles', 'criticalVehicles'].map((key, index) => [key, counts[index]])),
};
const create = api => {
  let sequence = 0;
  return new V2FleetDashboard({ getState: async id => view(id), getHistory: async () => [], ...api }, () => {}, () => `id-${++sequence}`);
};
const deferred = () => {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
};

test('retains all three even when missing, and keeps fleet and observation samples independent', async () => {
  const pending = deferred();
  const model = create({ getFleet: () => pending.promise });
  const load = model.refreshFleet();
  assert.equal(model.state.fleetLoading, true);
  assert.equal(model.state.fleet, null);
  pending.resolve(summary);
  await load;
  assert.equal(model.state.fleet.unavailableVehicles, counts[3]);
  assert.deepEqual(model.state.fleet.vehicles.map(row => row.vehicleId), V2_VEHICLES);
  await model.selectVehicle(source.vehicleId);
  assert.equal(model.state.vehicle.recoveryState, 'IN_PROGRESS');
  assert.equal(model.state.vehicle.healthStatus, 'CRITICAL');
  assert.equal(model.state.vehicle.lastEventId, source.eventId);
  assert.equal(model.state.fleet.criticalVehicles, 0);
  model.api.getFleet = async () => ({ ...summary, generatedAt: '2026-01-01T00:00:03Z' });
  await model.refreshFleet();
  assert.match(model.state.fleetError, /Older fleet snapshot/);
  model.api.getFleet = async () => ({ ...summary, vehicles: summary.vehicles.slice(0, 2) });
  await model.refreshFleet();
  assert.match(model.state.fleetError, /Invalid V2 fleet/);
  assert.equal(model.state.fleet, summary);
});

test('rapid selection cannot apply another vehicle’s unread observation, history or action result', async () => {
  const state = deferred(), history = deferred(), dispatched = deferred(), result = deferred();
  let request;
  const model = create({
    getState: id => id === 'vehicle-001' ? state.promise : Promise.resolve(view(id)),
    getHistory: id => id === 'vehicle-001' ? history.promise : Promise.resolve([]),
    submitAction: payload => { request = payload; return dispatched.promise; },
    getAction: () => result.promise,
  });
  const first = model.selectVehicle('vehicle-001');
  const sending = model.submit(action);
  await model.selectVehicle('vehicle-002');
  dispatched.resolve({ ...request, status: 'ACCEPTED' }); await sending;
  state.resolve(view('vehicle-001')); history.resolve([{ vehicleId: 'vehicle-001' }]); await first;
  assert.equal(model.state.action, null);
  assert.deepEqual(model.state.history, []);
  const returning = model.selectVehicle('vehicle-001');
  await model.selectVehicle('vehicle-003');
  result.resolve({ ...request, status: 'EXECUTING' }); await returning;
  assert.equal(model.state.vehicle.vehicleId, 'vehicle-003');
  assert.equal(model.state.action, null);
  assert.deepEqual(model.state.history, []);
});

test('tracks correlated execution, rejects mismatches, and keeps CLEAR separate from recovery', async () => {
  let submitted, result, attempts = 0;
  const model = create({
    submitAction: async request => { attempts++; submitted = request; return { ...request, status: 'ACCEPTED' }; },
    getAction: async () => result,
  });
  await model.selectVehicle(source.vehicleId);
  await model.submit('CLEAR_SCENARIO');
  assert.equal(model.state.action.status, 'ACCEPTED');
  await model.submit('CLEAR_SCENARIO');
  assert.equal(attempts, 1);
  result = { ...submitted, status: 'EXECUTING', traceId: 'other' };
  await model.refreshAction();
  assert.match(model.state.actionError, /correlation/);
  assert.equal(model.state.action.status, 'ACCEPTED');
  result.traceId = submitted.traceId;
  await model.refreshAction();
  assert.equal(model.state.action.status, 'EXECUTING');
  result = { ...submitted, status: 'SUCCEEDED' };
  await model.refreshAction();
  assert.equal(model.state.action.status, 'SUCCEEDED');
  assert.equal(model.state.vehicle.recoveryState, 'IN_PROGRESS');
  await model.submit('RESTART_APP');
  assert.equal(submitted.vehicleId, source.vehicleId);
  assert.equal('scenario' in submitted, false);
});

test('terminal timeout and rejection remain distinct from an unknown dispatch acknowledgement', async () => {
  let submitted, attempts = 0, code = 504;
  const model = create({
    submitAction: async request => {
      attempts++; submitted = request;
      throw Object.assign(new Error('fixture'), { apiError: { httpStatus: code } });
    },
    getAction: async () => ({ ...submitted, status: 'TIMED_OUT', executionUncertain: true }),
  });
  await model.submit(action);
  assert.match(model.state.actionError, /Execution is unknown/);
  assert.ok(model.state.pendingActionId);
  await model.submit(action);
  assert.equal(attempts, 1);
  await model.refreshAction();
  assert.equal(model.state.action.status, 'TIMED_OUT');
  assert.equal(model.state.actionActive, false);
  code = 409;
  await model.submit(action);
  assert.match(model.state.actionError, /rejected/);
  assert.equal(model.state.action, null);
});

test('V2 adapter uses explicit routes and adds no browser bearer credentials', async () => {
  const original = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return new Response('{}');
  };
  try {
    const api = createV2FleetApi('https://example.test/gateway/');
    await api.getFleet();
    await api.getState('vehicle-003');
    await api.submitAction(fixture('diagnostics/cases').request);
    await api.getAction('action-003');
    await api.getHistory('vehicle-003');
    assert.deepEqual(calls.map(call => call.url.replace('https://example.test/gateway', '')), [
      '/api/v2/fleet', '/api/v2/vehicles/vehicle-003/state', '/api/v2/diagnostics/actions',
      '/api/v2/diagnostics/actions/action-003', '/api/v2/diagnostics/vehicles/vehicle-003/actions',
    ]);
    assert.equal(calls[2].options.method, 'POST');
    assert.deepEqual(calls[2].options.headers, { 'Content-Type': 'application/json' });
    assert.equal(calls[3].options.headers, undefined);
  } finally {
    globalThis.fetch = original;
  }
});
