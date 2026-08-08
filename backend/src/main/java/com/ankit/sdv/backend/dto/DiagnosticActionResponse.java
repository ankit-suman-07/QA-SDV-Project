package com.ankit.sdv.backend.dto;

import com.ankit.sdv.backend.model.DiagnosticAction;
import com.ankit.sdv.backend.model.DiagnosticActionStatus;
import com.ankit.sdv.backend.model.DiagnosticScenario;

import java.time.Instant;

public record DiagnosticActionResponse(
        String actionId,
        String traceId,
        String vehicleId,
        DiagnosticAction action,
        DiagnosticScenario scenario,
        DiagnosticActionStatus status,
        Instant requestedAt
) {
}