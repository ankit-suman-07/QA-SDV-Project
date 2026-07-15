const DEFAULT_API_BASE_URL = "http://localhost:8080";
const DEFAULT_VEHICLE_ID = "vehicle-001";

export async function getVehicleState({ mode = "mock", state = "healthy", fetchImpl = fetch } = {}) {
  const url = mode === "api"
    ? `${DEFAULT_API_BASE_URL}/api/vehicles/${DEFAULT_VEHICLE_ID}`
    : `./mocks/${state}.json`;

  const response = await fetchImpl(url, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`Vehicle state request failed with HTTP ${response.status}`);
  return response.json();
}
