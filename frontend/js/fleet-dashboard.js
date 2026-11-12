import { CONFIG } from './config.js';
import { createHttpFleetApi } from './fleet-api.js';
import { createHttpDiagnosticApi } from './diagnostic-api.js';
import { FleetDashboard } from './fleet-model.js';

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
  const ids = fleet?.vehicles.map(vehicle => vehicle.vehicleId) ?? [];
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
          : 'AVAILABLE — trusted observation at the backend evaluation time.');
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
  for (const id of ['inject', 'clear']) element(id).disabled = !state.selectedId || state.submitting;
  const action = state.action;
  text('action-status', state.submitting ? 'Submitting scenario…' : action
    ? `${action.status} / ${action.dispatchStatus ?? 'dispatch unconfirmed'} · action ${action.actionId} · trace ${action.traceId}. Observe health separately.` : '');
  errorText('action-error', state.actionError);
}
const model = new FleetDashboard(createHttpFleetApi(), createHttpDiagnosticApi(), render);
element('preview-label').hidden = !(CONFIG.FLEET_PREVIEW || /:19082\/?$/.test(CONFIG.API_BASE_URL));
element('vehicle-select').addEventListener('change', event => model.selectVehicle(event.target.value));
element('inject').addEventListener('click', () => model.submit('INJECT_SCENARIO'));
element('clear').addEventListener('click', () => model.submit('CLEAR_SCENARIO'));
async function refresh() { await Promise.all([model.refreshFleet(), model.refreshVehicle()]); }
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
