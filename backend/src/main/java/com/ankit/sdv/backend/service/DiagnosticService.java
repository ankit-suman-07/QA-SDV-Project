package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.adapter.opensovd.OpenSovdAdapter;
import com.ankit.sdv.backend.model.HealthResult;
import com.ankit.sdv.backend.model.VehicleState;
import org.springframework.stereotype.Service;

@Service
public class DiagnosticService {

    private final OpenSovdAdapter openSovdAdapter;

    public DiagnosticService(
            OpenSovdAdapter openSovdAdapter
    ) {
        this.openSovdAdapter = openSovdAdapter;
    }

    public void updateDiagnostics(
            VehicleState vehicleState,
            HealthResult healthResult
    ) {
        openSovdAdapter.updateDiagnosticState(
                vehicleState,
                healthResult
        );
    }
}