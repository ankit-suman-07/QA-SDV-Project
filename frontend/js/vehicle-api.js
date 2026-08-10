import { apiRequest } from "./api-client.js";
import { CONFIG } from "./config.js";

/** Section 11: GET /api/vehicles/{vehicleId}/state and /health — READY. */
export function createHttpVehicleApi(baseUrl = CONFIG.API_BASE_URL) {
  return {
    async getState(vehicleId) {
      return apiRequest(baseUrl, `/api/vehicles/${vehicleId}/state`);
    },
    async getHealth(vehicleId) {
      return apiRequest(baseUrl, `/api/vehicles/${vehicleId}/health`);
    },
  };
}

/** options.fixture = { state, health, ... } loaded from mocks/*.json.
 * options.simulateDisconnected = true throws to exercise the disconnected UI. */
export function createMockVehicleApi(options = {}) {
  const delayMs = options.delayMs ?? 250; // Section 15: 150-400ms artificial delay
  const fixture = options.fixture;

  const delay = () => new Promise((resolve) => setTimeout(resolve, delayMs));

  return {
    async getState(vehicleId) {
      await delay();
      if (options.simulateDisconnected)
        throw new Error("simulated network failure");
      return { ...fixture.state, vehicleId };
    },
    async getHealth(vehicleId) {
      await delay();
      if (options.simulateDisconnected)
        throw new Error("simulated network failure");
      return { ...fixture.health, vehicleId };
    },
  };
}

/** Loads a named fixture JSON file (normal | warning | cooling-critical | recovered). */
export async function loadFixture(name) {
  const response = await fetch(`mocks/${name}.json`);
  return response.json();
}
