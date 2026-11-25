import { FleetDashboard } from './fleet-model.js';

export const V2_VEHICLES = Object.freeze(['vehicle-001', 'vehicle-002', 'vehicle-003']);
const TERMINAL = new Set(['SUCCEEDED', 'FAILED', 'TIMED_OUT']);
const ACTIVE = new Set(['ACCEPTED', 'EXECUTING']);
const COUNTS = ['totalVehicles', 'availableVehicles', 'staleVehicles', 'unavailableVehicles',
  'healthyVehicles', 'warningVehicles', 'criticalVehicles'];

function correlate(result, request) {
  if (!result || ['vehicleId', 'actionId', 'traceId', 'action'].some(key => result[key] !== request[key])
    || (!ACTIVE.has(result.status) && !TERMINAL.has(result.status))) {
    throw new Error('Invalid action response or correlation mismatch.');
  }
  return result;
}

function actionError(error) {
  switch (error.apiError?.httpStatus) {
    case 401:
    case 403: return 'Diagnostics authorization required. Open the dashboard through the authorized gateway.';
    case 409: return 'Action rejected or correlation conflict.';
    case 503: return 'Diagnostic service or executor unavailable.';
    case 0:
    case 408:
    case 504: return 'Dispatch could not be confirmed. Execution is unknown.';
    default: return error.message;
  }
}

export class V2FleetDashboard extends FleetDashboard {
  constructor(api, onChange, newId = () => crypto.randomUUID()) {
    super(api, api, onChange);
    this.newId = newId;
    this.actions = new Map();
    this.state.selectedId = V2_VEHICLES[0];
    this.state.history = null;
    this.state.historyError = null;
    this.historyVersion = 0;
  }

  async refreshFleet() {
    const version = ++this.fleetVersion;
    this.state.fleetLoading = true;
    this.changed();
    try {
      const fleet = await this.api.getFleet();
      if (version !== this.fleetVersion) return;
      const generated = Date.parse(fleet?.generatedAt);
      if (!Number.isFinite(generated) || fleet?.totalVehicles !== V2_VEHICLES.length
          || !Array.isArray(fleet.vehicles)
          || fleet.vehicles.map(vehicle => vehicle?.vehicleId).join('|') !== V2_VEHICLES.join('|')
          || COUNTS.some(key => !Number.isInteger(fleet[key]) || fleet[key] < 0)) {
        throw new Error('Invalid V2 fleet response.');
      }
      if (this.state.fleet && generated < Date.parse(this.state.fleet.generatedAt)) {
        throw new Error('Older fleet snapshot received.');
      }
      this.state.fleet = fleet;
      this.state.fleetError = null;
    } catch (error) {
      if (version === this.fleetVersion) this.state.fleetError = error.message;
    } finally {
      if (version === this.fleetVersion) { this.state.fleetLoading = false; this.changed(); }
    }
  }

  async selectVehicle(id) {
    if (!V2_VEHICLES.includes(id)) return;
    ++this.selectionVersion;
    this.state.selectedId = id;
    this.state.vehicle = null;
    this.state.vehicleError = null;
    this.state.history = null;
    this.state.historyError = null;
    this.syncAction();
    await Promise.all([this.refreshVehicle(), this.refreshHistory(), this.refreshAction()]);
  }

  syncAction() {
    const current = this.actions.get(this.state.selectedId);
    this.state.action = current?.record ?? null;
    this.state.actionError = current?.error ?? null;
    this.state.pendingActionId = current?.request.actionId ?? null;
    this.state.submitting = current?.sending ?? false;
    this.state.actionActive = Boolean(current?.uncertain || ACTIVE.has(current?.record?.status));
    this.changed();
  }

  async submit(action) {
    const vehicleId = this.state.selectedId;
    if (this.state.submitting || this.state.actionActive || !V2_VEHICLES.includes(vehicleId)) return;
    const request = { vehicleId, action, actionId: this.newId(), traceId: this.newId() };
    if (action !== 'RESTART_APP') request.scenario = 'LIDAR_OBSTRUCTION';
    const current = { request, sending: true, record: null, error: null, uncertain: false };
    this.actions.set(vehicleId, current);
    this.syncAction();
    try {
      current.record = correlate(await this.api.submitAction(request), request);
    } catch (error) {
      current.error = actionError(error);
      current.uncertain = [0, 408, 504].includes(error.apiError?.httpStatus) || !error.apiError;
    } finally {
      current.sending = false;
      this.syncAction();
    }
  }

  async refreshAction() {
    const current = this.actions.get(this.state.selectedId);
    if (!current || current.sending || current.reading || !(current.uncertain || ACTIVE.has(current.record?.status))) return;
    current.reading = true;
    try {
      const record = correlate(await this.api.getAction(current.request.actionId), current.request);
      if (current.record?.status === 'EXECUTING' && record.status === 'ACCEPTED') return;
      current.record = record;
      current.error = null;
      current.uncertain = false;
    } catch (error) {
      // A missing record after an uncertain submission still cannot prove safety to re-submit.
      current.error = `Action status could not be confirmed. ${actionError(error)}`;
    } finally {
      current.reading = false;
      this.syncAction();
    }
  }

  async refreshHistory() {
    const vehicleId = this.state.selectedId;
    const selected = this.selectionVersion;
    const version = ++this.historyVersion;
    const current = () => selected === this.selectionVersion && version === this.historyVersion;
    try {
      const history = await this.api.getHistory(vehicleId);
      if (!current()) return;
      if (!Array.isArray(history) || history.some(entry => entry?.vehicleId !== vehicleId || !entry.actionId
          || !entry.traceId || (!TERMINAL.has(entry.status) && !ACTIVE.has(entry.status)))) {
        throw new Error('Invalid vehicle action history.');
      }
      this.state.history = history;
      this.state.historyError = null;
    } catch (error) {
      if (current()) this.state.historyError = actionError(error);
    } finally {
      if (current()) this.changed();
    }
  }
}
