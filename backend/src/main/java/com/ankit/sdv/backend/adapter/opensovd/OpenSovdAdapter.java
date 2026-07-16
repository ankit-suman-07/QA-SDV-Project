package com.ankit.sdv.backend.adapter.opensovd;

import com.ankit.sdv.backend.model.HealthResult;
import com.ankit.sdv.backend.model.VehicleState;

public interface OpenSovdAdapter {

    void updateDiagnosticState(
            VehicleState vehicleState,
            HealthResult healthResult
    );
}