import { CONFIG } from './config.js';
import { createHttpFleetApi } from './fleet-api.js';
import { createHttpDiagnosticApi } from './diagnostic-api.js';
import { FleetDashboard } from './fleet-model.js';
import { createV2FleetApi } from './v2-fleet-api.js';
import { V2FleetDashboard, V2_VEHICLES } from './v2-fleet-model.js';

const v2 = typeof CONFIG.V2_API_BASE_URL === 'string';
const preview = CONFIG.FLEET_PREVIEW || (!v2 && /:19082\/?$/.test(CONFIG.API_BASE_URL));

const element = id => document.getElementById(id);
const text = (id, value) => { element(id).textContent = value ?? '—'; };
function errorText(id, value) { text(id, value); element(id).hidden = !value; }
const counters = [
  ['totalVehicles', 'Total vehicles'], ['availableVehicles', 'Available'],
  ['staleVehicles', 'Stale'], ['unavailableVehicles', 'Unavailable'],
  ['healthyVehicles', 'Healthy now'], ['warningVehicles', 'Warning now'], ['criticalVehicles', 'Critical now'],
];
for (const [key, label] of counters) {
  const card = document.createElement('div'); card.className = 'metric-card';
  const title = document.createElement('span'); title.className = 'metric-card__label'; title.textContent = label;
  const value = document.createElement('div'); value.className = 'metric-card__value'; value.id = key; value.textContent = '—';
  card.append(title, value); element('fleet-counts').append(card);
}
let optionsKey;
function render(state) {
  const fleet = state.fleet;
  text('fleet-status', state.fleetError ? 'Request failed — counts below are last known, not current.'
    : !fleet ? 'Loading fleet…' : `${state.fleetLoading ? 'Refreshing… ' : ''}Evaluated at ${fleet.generatedAt}`);
  errorText('fleet-error', state.fleetError);
  for (const [key] of counters) text(key, fleet?.[key]);
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
  text('vehicle-health', health ? `${health}${state.vehicleError || vehicle.availability !== 'AVAILABLE' ? ' (last known)' : ''}` : 'Unknown');
  text('vehicle-availability', state.vehicleError ? 'Request error — current availability unknown' : vehicle?.availability);
  text('vehicle-faults', vehicle?.activeFaults == null ? 'Unknown' : vehicle.activeFaults.join(', ') || 'None');
  text('lidar-distance', vehicle?.lidar?.distanceMeters == null ? 'Unknown' : `${vehicle.lidar.distanceMeters} m`);
  text('lidar-sensor', vehicle?.lidar == null ? 'Unknown' : vehicle.lidar.sensorAvailable ? 'Yes' : 'No');
  text('source-timestamp', vehicle?.sourceTimestamp);
  text('last-event', vehicle?.lastEventId);
  for (const id of ['inject', 'clear', 'restart']) {
    element(id).disabled = !state.selectedId || state.submitting || Boolean(state.actionActive);
  }
  const action = state.action;
  text('action-status', state.submitting ? (v2 ? 'Submitting action…' : 'Submitting scenario…') : v2
    ? describeAction(action, state.pendingActionId) : action
      ? `${action.status} / ${action.dispatchStatus ?? 'dispatch unconfirmed'} · action ${action.actionId} · trace ${action.traceId}. Observe health separately.` : '');
  errorText('action-error', state.actionError);
  if (v2) {
    element('preview-label').hidden = !(preview || fleet?.mock === true || vehicle?.mock === true);
    renderV2(state);
  }
}

function describeAction(action, pendingId) {
  if (!action) return pendingId ? `Action ${pendingId}` : '';
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

function renderV2(state) {
  const vehicle = state.vehicle;
  const lastKnown = vehicle && (state.vehicleError || vehicle.availability !== 'AVAILABLE');
  const observed = value => value == null ? 'Unknown' : `${value}${lastKnown ? ' (last known)' : ''}`;
  renderList('fleet-vehicles', V2_VEHICLES.map(id => {
    const view = state.fleet?.vehicles.find(entry => entry.vehicleId === id);
    return `${id} · ${view?.availability ?? (state.fleetError ? 'Unknown' : 'Loading')}`;
  }));
  text('vehicle-faults', observed(vehicle?.activeFaults ? vehicle.activeFaults.join(', ') || 'None' : null));
  text('lidar-distance', observed(vehicle?.lidar?.distanceMeters == null ? null : `${vehicle.lidar.distanceMeters} m`));
  text('lidar-sensor', observed(vehicle?.lidar?.sensorAvailable == null ? null : vehicle.lidar.sensorAvailable ? 'Yes' : 'No'));
  text('vehicle-recovery', observed(vehicle?.recoveryState));
  text('recovery-started', vehicle?.recoveryStartedAt);
  text('source-silent', observed(vehicle?.sourceSilent == null ? null : vehicle.sourceSilent ? 'Yes' : 'No'));
  text('source-session', vehicle?.sessionId ? `${vehicle.sessionId} / ${vehicle.sessionGeneration ?? '—'}` : null);
  text('source-frame', vehicle?.sequence == null ? null : `${vehicle.sequence} / ${vehicle.frame ?? '—'}`);
  text('source-provenance', vehicle?.provenance ?? (vehicle?.lastEventId && (preview || vehicle.mock) ? 'SYNTHETIC' : 'Unknown'));
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
element('fleet-vehicles').hidden = !v2;
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
element('menu-toggle').addEventListener('click', event => {
  const open = element('sidebar').classList.toggle('is-open'); event.currentTarget.setAttribute('aria-expanded', String(open));
});
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
