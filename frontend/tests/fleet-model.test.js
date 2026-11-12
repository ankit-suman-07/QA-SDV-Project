import test from 'node:test';
import assert from 'node:assert/strict';
import { FleetDashboard } from '../js/fleet-model.js';

const deferred = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };
const view = (id, availability = 'AVAILABLE') => ({ vehicleId: id, availability, healthStatus: 'HEALTHY', activeFaults: [], sourceTimestamp: '2026-01-01T00:00:00Z' });
const summary = { vehicles: [view('vehicle-001'), view('vehicle-002')], totalVehicles: 2, healthyVehicles: 2 };

test('fleet loading and errors are distinct from selected vehicle availability', async () => {
  const fleet = deferred();
  const model = new FleetDashboard({ getFleet: () => fleet.promise, getState: async id => view(id) }, {}, () => {});
  const load = model.refreshFleet();
  assert.equal(model.state.fleetLoading, true);
  fleet.resolve(summary); await load;
  assert.equal(model.state.fleet.totalVehicles, 2);
  assert.equal(model.state.selectedId, 'vehicle-001');
  assert.equal(model.state.vehicle.vehicleId, 'vehicle-001');
  model.api.getFleet = async () => { throw new Error('offline'); };
  await model.refreshFleet();
  assert.match(model.state.fleetError, /offline/);
  assert.equal(model.state.fleet, summary); // explicitly labelled last known by the view
});

test('an old selection or error cannot overwrite a newer selection', async () => {
  const old = deferred(), current = deferred();
  const model = new FleetDashboard({ getState: id => id === 'vehicle-001' ? old.promise : current.promise }, {}, () => {});
  const first = model.selectVehicle('vehicle-001');
  const second = model.selectVehicle('vehicle-002');
  assert.equal(model.state.vehicle, null);
  assert.equal(model.state.vehicleLoading, true);
  current.resolve(view('vehicle-002', 'STALE')); await second;
  old.reject(new Error('obsolete error')); await first;
  assert.equal(model.state.vehicle.vehicleId, 'vehicle-002');
  assert.equal(model.state.vehicle.availability, 'STALE');
  assert.equal(model.state.vehicleError, null);
});

test('newer polls win and failed reads preserve labelled last known state', async () => {
  const old = deferred(), current = deferred(); let call = 0;
  const model = new FleetDashboard({ getState: () => ++call === 1 ? old.promise : current.promise }, {}, () => {});
  const first = model.selectVehicle('vehicle-002'); const second = model.refreshVehicle();
  current.resolve(view('vehicle-002', 'UNAVAILABLE')); await second;
  old.resolve(view('vehicle-002')); await first;
  assert.equal(model.state.vehicle.availability, 'UNAVAILABLE');
  model.api.getState = async () => { throw new Error('read failed'); };
  await model.refreshVehicle();
  assert.match(model.state.vehicleError, /read failed/);
  assert.equal(model.state.vehicle.availability, 'UNAVAILABLE');
});

test('dispatch acknowledgement does not change observed health; no automatic POST retry', async () => {
  let submissions = [];
  const model = new FleetDashboard({ getState: async id => view(id) }, { submitAction: async request => {
    submissions.push(request);
    return { ...request, status: 'ACCEPTED', dispatchStatus: 'DISPATCHED', actionId: 'a', traceId: 't' };
  } }, () => {});
  await model.selectVehicle('vehicle-002');
  await model.submit('INJECT_SCENARIO');
  assert.deepEqual(submissions, [{ vehicleId: 'vehicle-002', action: 'INJECT_SCENARIO', scenario: 'LIDAR_OBSTRUCTION' }]);
  assert.equal(model.state.vehicle.healthStatus, 'HEALTHY');
  assert.equal(model.state.action.dispatchStatus, 'DISPATCHED');
  await model.submit('CLEAR_SCENARIO');
  assert.equal(submissions[1].action, 'CLEAR_SCENARIO');
  let attempts = 0;
  model.diagnostics.submitAction = async () => { attempts++; const error = new Error('Delivery unknown'); error.apiError = { code: 'PROVIDER_TIMEOUT', dispatchStatus: 'UNKNOWN' }; throw error; };
  await model.submit('INJECT_SCENARIO');
  assert.equal(attempts, 1);
  assert.match(model.state.actionError, /UNKNOWN/);
  assert.equal(model.state.vehicle.healthStatus, 'HEALTHY');
});

test('switching during an action hides old acknowledgement without allowing duplicate submission', async () => {
  const pending = deferred(); let attempts = 0;
  const model = new FleetDashboard({ getState: async id => view(id) }, { submitAction: () => { attempts++; return pending.promise; } }, () => {});
  await model.selectVehicle('vehicle-001');
  const submit = model.submit('INJECT_SCENARIO');
  await model.selectVehicle('vehicle-002');
  await model.submit('INJECT_SCENARIO');
  assert.equal(attempts, 1);
  pending.resolve({ vehicleId: 'vehicle-001', status: 'ACCEPTED', dispatchStatus: 'DISPATCHED' }); await submit;
  assert.equal(model.state.action, null);
  assert.equal(model.state.submitting, false);
});
