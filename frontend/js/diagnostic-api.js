import { apiRequest } from "./api-client.js";
import { CONFIG } from "./config.js";

/** Section 12: POST /api/v1/diagnostics/actions — READY, returns 202.
 * Section 13: GET .../{actionId} — IN PROGRESS. Calling it here is
 * optimistic; until the backend confirms it's live, use
 * createMockDiagnosticApi's getAction instead (see diagnostics.js). */
export function createHttpDiagnosticApi(baseUrl = CONFIG.API_BASE_URL) {
  return {
    async submitAction(request) {
      return apiRequest(baseUrl, "/api/v1/diagnostics/actions", {
        method: "POST",
        body: request,
        allowOneRetry: false, // Section 10: never auto-retry POST actions
      });
    },
    async getAction(actionId) {
      return apiRequest(baseUrl, `/api/v1/diagnostics/actions/${actionId}`);
    },
  };
}

export function createMockDiagnosticApi(options = {}) {
  const delayMs = options.delayMs ?? 300;
  const completeAfterMs = options.completeAfterMs ?? 3000; // Section 15: predictable clock
  const submittedAt = new Map();
  const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  return {
    async submitAction(request) {
      await delay(delayMs);
      if (options.simulateValidationError) {
        const err = new Error("vehicleId: must not be blank");
        err.apiError = {
          httpStatus: 400,
          code: "VALIDATION_ERROR",
          message: "vehicleId: must not be blank",
          path: "/api/v1/diagnostics/actions",
          retryable: false,
        };
        throw err;
      }
      const actionId = `action-${Date.now()}`;
      const response = {
        actionId,
        traceId: actionId,
        vehicleId: request.vehicleId,
        action: request.action,
        scenario: request.scenario,
        status: "ACCEPTED",
        requestedAt: new Date().toISOString(),
      };
      submittedAt.set(actionId, Date.now());
      return response;
    },
    async getAction(actionId) {
      await delay(150);
      const startedAt =
        submittedAt.get(actionId) ?? Date.now() - completeAfterMs;
      const elapsed = Date.now() - startedAt;
      const status = elapsed >= completeAfterMs ? "COMPLETED" : "IN_PROGRESS";
      return {
        actionId,
        traceId: actionId,
        vehicleId: CONFIG.VEHICLE_ID,
        action: "INJECT_SCENARIO",
        scenario: "COOLING_SYSTEM_FAILURE",
        status,
        requestedAt: new Date(startedAt).toISOString(),
      };
    },
  };
}
