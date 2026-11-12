package com.ankit.sdv.backend.dto;

import com.ankit.sdv.backend.model.DiagnosticAction;
import com.ankit.sdv.backend.model.DiagnosticActionStatus;
import com.ankit.sdv.backend.model.DiagnosticScenario;

import java.time.Instant;
import com.ankit.sdv.backend.model.DispatchStatus;
import com.fasterxml.jackson.annotation.JsonInclude;

public record DiagnosticActionResponse(
        String actionId,
        String traceId,
        String vehicleId,
        DiagnosticAction action,
        DiagnosticScenario scenario,
        DiagnosticActionStatus status,
        Instant requestedAt,
        @JsonInclude(JsonInclude.Include.NON_NULL) DispatchStatus dispatchStatus
) {
    public DiagnosticActionResponse(String actionId, String traceId, String vehicleId, DiagnosticAction action,
            DiagnosticScenario scenario, DiagnosticActionStatus status, Instant requestedAt) {
        this(actionId, traceId, vehicleId, action, scenario, status, requestedAt, null);
    }
}