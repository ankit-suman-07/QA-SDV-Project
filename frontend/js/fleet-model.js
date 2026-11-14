// Selection and request versions prevent obsolete successes/errors from changing the view.
export class FleetDashboard {
  constructor(api, diagnostics, onChange = () => {}) {
    this.api = api;
    this.diagnostics = diagnostics;
    this.onChange = onChange;
    this.selectionVersion = 0;
    this.vehicleVersion = 0;
    this.fleetVersion = 0;
    this.state = {
      fleet: null, fleetLoading: true, fleetError: null,
      selectedId: null, vehicle: null, vehicleLoading: true, vehicleError: null,
      action: null, actionError: null, submitting: false,
    };
  }

  changed() { this.onChange(this.state); }

  async refreshFleet() {
    const version = ++this.fleetVersion;
    this.state.fleetLoading = true;
    this.changed();
    try {
      const fleet = await this.api.getFleet();
      if (version !== this.fleetVersion) return;
      if (!fleet || !Array.isArray(fleet.vehicles)) throw new Error('Invalid fleet response');
      this.state.fleet = fleet;
      this.state.fleetError = null;
      if (!this.state.selectedId && fleet.vehicles.length) await this.selectVehicle(fleet.vehicles[0].vehicleId);
    } catch (error) {
      if (version === this.fleetVersion) this.state.fleetError = error.message;
    } finally {
      if (version === this.fleetVersion) { this.state.fleetLoading = false; this.changed(); }
    }
  }

  async selectVehicle(id) {
    ++this.selectionVersion;
    this.state.selectedId = id;
    this.state.vehicle = null;
    this.state.vehicleError = null;
    this.state.action = null;
    this.state.actionError = null;
    await this.refreshVehicle();
  }

  async refreshVehicle() {
    const id = this.state.selectedId;
    if (!id) return;
    const version = ++this.vehicleVersion;
    this.state.vehicleLoading = true;
    this.changed();
    try {
      const vehicle = await this.api.getState(id);
      if (version !== this.vehicleVersion) return;
      if (!vehicle || vehicle.vehicleId !== id) throw new Error('Vehicle response identity mismatch');
      this.state.vehicle = vehicle;
      this.state.vehicleError = null;
    } catch (error) {
      if (version === this.vehicleVersion) this.state.vehicleError = error.message;
    } finally {
      if (version === this.vehicleVersion) { this.state.vehicleLoading = false; this.changed(); }
    }
  }

  async submit(action) {
    if (this.state.submitting || !this.state.selectedId) return;
    const version = this.selectionVersion;
    const vehicleId = this.state.selectedId;
    this.state.submitting = true;
    this.state.action = null;
    this.state.actionError = null;
    this.changed();
    try {
      const acknowledgement = await this.diagnostics.submitAction({ vehicleId, action, scenario: 'LIDAR_OBSTRUCTION' });
      if (version === this.selectionVersion) this.state.action = acknowledgement;
      // The next observation poll establishes health. An acknowledgement never changes it.
    } catch (error) {
      if (version === this.selectionVersion) {
        const details = error.apiError;
        this.state.actionError = [details?.code, details?.dispatchStatus, details?.actionId, error.message].filter(Boolean).join(' · ');
      }
    } finally {
      this.state.submitting = false;
      this.changed();
    }
  }
}
