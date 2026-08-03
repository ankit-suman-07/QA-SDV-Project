package com.ankit.sdv.backend.dto;

import com.ankit.sdv.backend.model.DiagnosticAction;
import com.ankit.sdv.backend.model.DiagnosticScenario;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record DiagnosticActionRequest(

        @NotBlank(message = "Vehicle ID is required")
        String vehicleId,

        @NotNull(message = "Diagnostic action is required")
        DiagnosticAction action,

        @NotNull(message = "Diagnostic scenario is required")
        DiagnosticScenario scenario
) {
}