package com.ankit.sdv.backend.adapter.simulator;

import com.ankit.sdv.backend.model.DiagnosticAction;
import com.ankit.sdv.backend.model.DiagnosticScenario;

public interface SimulatorControlAdapter {

    void executeAction(
            String vehicleId,
            DiagnosticAction action,
            DiagnosticScenario scenario,
            String actionId,
            String traceId
    );
}