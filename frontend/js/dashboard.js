import { getVehicleState } from "./api.js";
import { renderVehicle, showError, showLoading } from "./ui.js";

const demoState = document.getElementById("demoState");
let previousHealthStatus = null;

export async function updateDashboard(stateName = demoState.value) {
  showLoading();
  try {
    if (stateName === "error") throw new Error("Simulated API failure");
    const state = await getVehicleState({ mode: "mock", state: stateName });
    const recovered = stateName === "recovered" || (previousHealthStatus === "CRITICAL" && state.healthStatus === "HEALTHY");
    renderVehicle(state, { recovered });
    previousHealthStatus = state.healthStatus;
  } catch (error) {
    console.error(error);
    showError("Unable to retrieve vehicle information. Please verify the backend/API connection.");
  }
}

demoState.addEventListener("change", () => updateDashboard());
updateDashboard();
