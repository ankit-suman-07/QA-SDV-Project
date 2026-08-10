import { apiRequest } from "./api-client.js";
import { CONFIG } from "./config.js";

// Section 12: POST /api/v1/diagnostics/actions — CONFIRMED LIVE (2026-08-10).
// Section 13: GET .../{actionId} — CONFIRMED LIVE (2026-08-10), but the
// backend does not currently transition actions past ACCEPTED to
// COMPLETED. Frontend polls for CONFIG.ACTION_TIMEOUT_MS then settles
// into a calm "Accepted (completion pending)" state rather than erroring.
// Known limitation, not a frontend bug — see frontend/README.md.
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
