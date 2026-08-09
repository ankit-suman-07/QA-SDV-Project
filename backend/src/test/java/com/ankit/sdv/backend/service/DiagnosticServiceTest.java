package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.adapter.opensovd.OpenSovdAdapter;
import com.ankit.sdv.backend.model.HealthResult;
import com.ankit.sdv.backend.model.HealthStatus;
import com.ankit.sdv.backend.model.VehicleState;
import org.junit.jupiter.api.Test;

import java.time.Instant;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

class DiagnosticServiceTest {

    @Test
    void shouldSendStateAndHealthToOpenSovdAdapter() {
        OpenSovdAdapter openSovdAdapter =
                mock(OpenSovdAdapter.class);

        DiagnosticService diagnosticService =
                new DiagnosticService(openSovdAdapter);

        VehicleState vehicleState = new VehicleState(
                "vehicle-001",
                Instant.parse("2026-07-15T16:00:00Z"),
                90.0,
                200.0
        );

        HealthResult healthResult =
                new HealthResult(HealthStatus.CRITICAL);

        diagnosticService.updateDiagnostics(
                vehicleState,
                healthResult
        );

        verify(openSovdAdapter)
                .updateDiagnosticState(
                        vehicleState,
                        healthResult
                );
    }
}