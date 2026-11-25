import { CONFIG } from './config.js';
import { createHttpFleetApi } from './fleet-api.js';
import { createHttpDiagnosticApi } from './diagnostic-api.js';
import { FleetDashboard } from './fleet-model.js';
import { createV2FleetApi } from './v2-fleet-api.js';
import { V2FleetDashboard, V2_VEHICLES } from './v2-fleet-model.js';

const v2 = typeof CONFIG.V2_API_BASE_URL === 'string';
const preview = CONFIG.FLEET_PREVIEW || (!v2 && /:19082\/?$/.test(CONFIG.API_BASE_URL));

const element = id => document.getElementById(id);
const text = (id, value) => {
  const field = element(id);
  const next = String(value ?? 'Unavailable');
  if (field.textContent !== next) field.textContent = next;
};
const tones = new Map([
  ['AVAILABLE', 'sage'], ['HEALTHY', 'sage'], ['STALE', 'orange'], ['WARNING', 'orange'],
  ['UNAVAILABLE', 'rose'], ['CRITICAL', 'rose'], ['IN_PROGRESS', 'lavender'],
]);
function status(field, label, status = label) {
  const tone = tones.get(status) ?? 'lavender';
  field.className = `fleet-status-chip fleet-tone--${tone}`;
  if (field.textContent !== label) field.textContent = label;
}
function observed(value, lastKnown) {
  return value == null ? 'Unknown' : `${value}${lastKnown ? ' (last known)' : ''}`;
}

function errorText(id, value) { text(id, value); element(id).hidden = !value; }
const counters = [
  ['totalVehicles', 'Vehicles', 'blue'], ['availableVehicles', 'Available', 'sage'],
  ['staleVehicles', 'Stale', 'orange'], ['unavailableVehicles', 'Unavailable', 'rose'],
  ['healthyVehicles', 'Healthy', 'sage'], ['warningVehicles', 'Warning', 'orange'],
  ['criticalVehicles', 'Critical', 'rose'],
];
for (const [key, label, tone] of counters) {
  const card = document.createElement('div'); card.className = `fleet-count fleet-tone--${tone}`;
  const title = document.createElement('span'); title.textContent = label;
  const value = document.createElement('div'); value.className = 'fleet-count__value'; value.id = key; value.textContent = '—';
  card.append(title, value); element('fleet-counts').append(card);
}
let optionsKey;
function render(state) {
  const fleet = state.fleet;
  text('fleet-status', state.fleetError ? (fleet ? 'Fleet request failed. Showing the last known fleet snapshot.' : 'Fleet snapshot unavailable.')
    : !fleet ? 'Loading fleet…' : `${state.fleetLoading ? 'Refreshing… ' : ''}Evaluated at ${fleet.generatedAt}`);
  errorText('fleet-error', state.fleetError);
  for (const [key] of counters) text(key, fleet?.[key] ?? '—');
  const ids = v2 ? V2_VEHICLES : fleet?.vehicles.map(vehicle => vehicle.vehicleId) ?? [];
  const key = ids.join('|');
  if (key !== optionsKey) {
    optionsKey = key;
    element('vehicle-select').replaceChildren(...ids.map(id => {
      const option = document.createElement('option'); option.value = id; option.textContent = id; return option;
    }));
  }
  element('vehicle-select').disabled = !ids.length;
  element('vehicle-select').value = state.selectedId ?? '';
  const vehicle = state.vehicle;
  text('vehicle-status', state.vehicleError ? 'Request failed — showing last known data where available.'
    : state.vehicleLoading ? 'Loading vehicle…'
      : vehicle?.availability === 'STALE' ? 'STALE — last known observation; excluded from current health counts.'
        : vehicle?.availability === 'UNAVAILABLE' ? 'UNAVAILABLE — no current observation; any retained health is last known.'
          : vehicle?.availability === 'AVAILABLE' ? 'AVAILABLE — trusted observation at the backend evaluation time.'
            : 'Observation unavailable.');
  errorText('vehicle-error', state.vehicleError);
  text('vehicle-id', state.selectedId);
  text('thing-id', vehicle?.thingId);
  const health = vehicle?.healthStatus;
  const lastKnown = state.vehicleError || vehicle?.availability !== 'AVAILABLE';
  status(element('vehicle-health'), observed(health, lastKnown), lastKnown ? null : health);
  status(element('vehicle-availability'), state.vehicleError ? 'Unknown (request failed)' : vehicle?.availability ?? 'Unknown');
  text('vehicle-faults', vehicle?.activeFaults == null ? 'Unknown' : vehicle.activeFaults.join(', ') || 'None');
  text('lidar-distance', vehicle?.lidar?.distanceMeters == null ? 'Unknown' : `${vehicle.lidar.distanceMeters} m`);
  text('lidar-sensor', vehicle?.lidar?.sensorAvailable == null ? 'Unknown' : vehicle.lidar.sensorAvailable ? 'Yes' : 'No');
  text('source-timestamp', observed(vehicle?.sourceTimestamp, lastKnown));
  text('last-event', observed(vehicle?.lastEventId, lastKnown));
  for (const id of ['inject', 'clear', 'restart']) {
    element(id).disabled = !state.selectedId || state.submitting || Boolean(state.actionActive);
  }
  const action = state.action;
  text('action-status', state.submitting ? (v2 ? 'Submitting action…' : 'Submitting scenario…') : v2
    ? describeAction(action, state.pendingActionId) : action
      ? `${action.status} / ${action.dispatchStatus ?? 'dispatch unconfirmed'} · action ${action.actionId} · trace ${action.traceId}. Observe health separately.` : 'No action requested for this selection.');
  errorText('action-error', state.actionError);
  if (v2) {
    element('preview-label').hidden = !(preview || fleet?.mock === true || vehicle?.mock === true);
    renderV2(state);
  }
}

function describeAction(action, pendingId) {
  if (!action) return pendingId ? `Action ${pendingId}` : 'No action requested for this selection.';
  const details = {
    ACCEPTED: 'Dispatch acknowledged.',
    EXECUTING: 'Executor reports progress.',
    SUCCEEDED: action.action === 'CLEAR_SCENARIO' ? 'Obstruction cleared. Check observed recovery separately.'
      : 'Executor completion recorded.',
    FAILED: 'Execution failed.',
    TIMED_OUT: 'Execution outcome unknown.',
  };
  return [action.status, details[action.status], action.outcome, `action ${action.actionId}`,
    `trace ${action.traceId}`, action.lateResult ? `Late result: ${action.lateResult.status}` : null].filter(Boolean).join(' · ');
}

function renderList(id, items) {
  element(id).replaceChildren(...items.map(message => {
    const item = document.createElement('li');
    item.textContent = message;
    return item;
  }));
}

function renderRoster(fleet, selectedId, fleetError) {
  const columns = ['Vehicle ID', 'Health', 'Availability', 'Active faults', 'Source age', 'Thing ID'];
  element('fleet-vehicles').replaceChildren(...V2_VEHICLES.map(id => {
    const entry = fleet?.vehicles.find(vehicle => vehicle.vehicleId === id);
    const lastKnown = fleetError || entry?.availability !== 'AVAILABLE';
    const delta = Date.parse(fleet?.generatedAt) - Date.parse(entry?.sourceTimestamp);
    const row = document.createElement('tr');
    if (id === selectedId) row.className = 'fleet-roster__selected';
    const values = [
      id, observed(entry?.healthStatus, lastKnown), entry?.availability ?? 'Unknown',
      observed(entry?.activeFaults ? entry.activeFaults.join(', ') || 'None' : null, lastKnown),
      Number.isFinite(delta) && delta >= 0 ? `${(delta / 1000).toFixed(1)} s` : 'Unavailable',
      entry?.thingId ?? 'Unavailable',
    ];
    values.forEach((value, index) => {
      const cell = document.createElement(index === 0 ? 'th' : 'td');
      if (index === 0) cell.scope = 'row';
      else cell.dataset.label = columns[index];
      if (index === 1 || index === 2) {
        const chip = document.createElement('span');
        status(chip, value, index === 1 && lastKnown ? null : undefined);
        cell.append(chip);
      } else cell.textContent = value;
      row.append(cell);
    });
    return row;
  }));
}

function renderV2(state) {
  const vehicle = state.vehicle;
  const lastKnown = vehicle && (state.vehicleError || vehicle.availability !== 'AVAILABLE');
  const read = value => observed(value, lastKnown);
  renderRoster(state.fleet, state.selectedId, state.fleetError);
  text('vehicle-faults', read(vehicle?.activeFaults ? vehicle.activeFaults.join(', ') || 'None' : null));
  text('lidar-distance', read(vehicle?.lidar?.distanceMeters == null ? null : `${vehicle.lidar.distanceMeters} m`));
  text('lidar-sensor', read(vehicle?.lidar?.sensorAvailable == null ? null : vehicle.lidar.sensorAvailable ? 'Yes' : 'No'));
  status(element('vehicle-recovery'), read(vehicle?.recoveryState), lastKnown ? null : vehicle?.recoveryState);
  text('recovery-started', read(vehicle?.recoveryStartedAt));
  text('source-silent', read(vehicle?.sourceSilent == null ? null : vehicle.sourceSilent ? 'Yes' : 'No'));
  text('source-session', read(vehicle?.sessionId ? `${vehicle.sessionId} / ${vehicle.sessionGeneration ?? 'Unknown'}` : null));
  text('source-frame', read(vehicle?.sequence == null ? null : `${vehicle.sequence} / ${vehicle.frame ?? 'Unknown'}`));
  text('source-provenance', read(vehicle?.provenance));
  text('history-status', state.historyError
    ? `${state.historyError}${state.history ? ' Showing last known history.' : ''}`
    : !state.history ? 'Loading action history…' : state.history.length ? '' : 'No retained actions.');
  renderList('action-history', [...(state.history ?? [])].reverse().map(entry => [
    entry.requestedAt, entry.action, describeAction(entry),
  ].filter(Boolean).join(' · ')));
}

const model = v2 ? new V2FleetDashboard(createV2FleetApi(CONFIG.V2_API_BASE_URL), render)
  : new FleetDashboard(createHttpFleetApi(), createHttpDiagnosticApi(), render);
element('preview-label').hidden = !preview;
if (!v2) document.body.classList.add('fleet-page--v1');
if (v2) for (const field of document.querySelectorAll('[data-v2]')) field.hidden = false;
element('vehicle-select').addEventListener('change', event => model.selectVehicle(event.target.value));
element('inject').addEventListener('click', () => model.submit('INJECT_SCENARIO'));
element('clear').addEventListener('click', () => model.submit('CLEAR_SCENARIO'));
element('restart').addEventListener('click', () => { if (v2) model.submit('RESTART_APP'); });
async function refresh() {
  await Promise.all([model.refreshFleet(), model.refreshVehicle(),
    ...(v2 ? [model.refreshAction(), model.refreshHistory()] : [])]);
}
element('refresh').addEventListener('click', refresh);
// Poll after completion rather than setInterval: slow requests cannot accumulate.
let timer;
let stopped = false;
let polling = false;
async function poll() {
  if (document.hidden || stopped || polling) return;
  polling = true;
  try { await refresh(); }
  finally {
    polling = false;
    if (!document.hidden && !stopped) timer = setTimeout(poll, CONFIG.POLL_INTERVAL_MS);
  }
}
document.addEventListener('visibilitychange', () => { clearTimeout(timer); if (!document.hidden) poll(); });
window.addEventListener('beforeunload', () => { stopped = true; clearTimeout(timer); });
render(model.state);
poll();
