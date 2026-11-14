import test from 'node:test';
import assert from 'node:assert/strict';
import { createHttpFleetApi } from '../js/fleet-api.js';
import { createHttpDiagnosticApi } from '../js/diagnostic-api.js';

test('fleet client uses v1 paths and encodes a selected identity', async () => {
  const original = globalThis.fetch; const urls = [];
  globalThis.fetch = async url => { urls.push(url); return { ok: true, status: 200, json: async () => ({}) }; };
  try {
    const api = createHttpFleetApi('http://backend');
    await api.getFleet(); await api.getState('vehicle-002'); await api.getState('bad/id');
    assert.deepEqual(urls, ['http://backend/api/v1/fleet', 'http://backend/api/v1/vehicles/vehicle-002/state', 'http://backend/api/v1/vehicles/bad%2Fid/state']);
  } finally { globalThis.fetch = original; }
});

test('scenario timeout preserves correlated UNKNOWN error and never retries POST', async () => {
  const original = globalThis.fetch; let calls = 0;
  globalThis.fetch = async (url, options) => {
    calls++;
    assert.equal(options.method, 'POST');
    assert.equal(JSON.parse(options.body).vehicleId, 'vehicle-002');
    return { ok: false, status: 504, json: async () => ({ code: 'PROVIDER_TIMEOUT', message: 'Unknown execution', actionId: 'a', traceId: 't', dispatchStatus: 'UNKNOWN' }) };
  };
  try {
    await assert.rejects(createHttpDiagnosticApi('http://backend').submitAction({ vehicleId: 'vehicle-002', action: 'INJECT_SCENARIO', scenario: 'LIDAR_OBSTRUCTION' }), error => {
      assert.equal(error.apiError.actionId, 'a'); assert.equal(error.apiError.traceId, 't');
      assert.equal(error.apiError.dispatchStatus, 'UNKNOWN'); return true;
    });
    assert.equal(calls, 1);
  } finally { globalThis.fetch = original; }
});
