// Central place to switch between mock and real API, and tune timing.
// Section 10-15 of the handoff guide.
export const CONFIG = {
  USE_MOCK_API: false,
  API_BASE_URL: globalThis.SDV_CONFIG?.API_BASE_URL ?? "http://localhost:8082",
  V2_API_BASE_URL: globalThis.SDV_CONFIG?.V2_API_BASE_URL,
  FLEET_PREVIEW: globalThis.SDV_CONFIG?.FLEET_PREVIEW === true,
  POLL_INTERVAL_MS: 2000,
  STALE_AFTER_MS: 5000,
  ACTION_POLL_MS: 1000,
  ACTION_TIMEOUT_MS: 20000,
  VEHICLE_ID: "vehicle-001", // Section 10: only supported value
};
