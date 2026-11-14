package com.ankit.sdv.backend.adapter.simulator;

import com.ankit.sdv.backend.model.DiagnosticAction;
import com.ankit.sdv.backend.model.DiagnosticScenario;

public interface SimulatorControlAdapter {

    /** Legacy/development adapters do not provide real provider acknowledgement evidence. */
    default boolean dispatchAcknowledged() { return false; }

    default boolean supportsVehicle(String vehicleId) { return true; }


    void executeAction(
            String vehicleId,
            DiagnosticAction action,
            DiagnosticScenario scenario,
            String actionId,
            String traceId
    );
}