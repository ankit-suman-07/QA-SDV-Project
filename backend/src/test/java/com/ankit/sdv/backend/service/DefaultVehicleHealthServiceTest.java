package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.dto.VehicleHealthResponse;
import com.ankit.sdv.backend.health.VehicleHealthEngine;
import com.ankit.sdv.backend.model.HealthResult;
import com.ankit.sdv.backend.model.HealthStatus;
import com.ankit.sdv.backend.model.VehicleState;
import com.ankit.sdv.backend.provider.VehicleStateProvider;
import org.junit.jupiter.api.Test;

import java.time.Instant;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

class DefaultVehicleHealthServiceTest {

    @Test
    void shouldReturnHealthForSpecifiedVehicle() {
        VehicleState state = new VehicleState(
                "vehicle-002",
                Instant.parse("2026-07-15T16:00:00Z"),
                95.0,
                200.0
        );

        HealthResult healthResult =
                new HealthResult(HealthStatus.WARNING);

        VehicleHealthEngine vehicleHealthEngine =
                mock(VehicleHealthEngine.class);

        VehicleStateProvider vehicleStateProvider =
                mock(VehicleStateProvider.class);

        when(vehicleStateProvider.getCurrentState("vehicle-002"))
                .thenReturn(state);

        when(vehicleHealthEngine.evaluate(state))
                .thenReturn(healthResult);

        DefaultVehicleHealthService vehicleHealthService =
                new DefaultVehicleHealthService(
                        vehicleHealthEngine,
                        vehicleStateProvider
                );

        VehicleHealthResponse response =
                vehicleHealthService.getCurrentHealth(
                        "vehicle-002"
                );

        assertEquals(
                "vehicle-002",
                response.vehicleId()
        );
        assertEquals(
                HealthStatus.WARNING,
                response.healthStatus()
        );

        verify(vehicleHealthEngine).evaluate(state);
    }

    @Test
    void shouldRejectVehicleWithoutStoredState() {
        VehicleHealthEngine vehicleHealthEngine =
                mock(VehicleHealthEngine.class);

        VehicleStateProvider vehicleStateProvider =
                mock(VehicleStateProvider.class);

        when(vehicleStateProvider.getCurrentState("vehicle-999"))
                .thenReturn(null);

        DefaultVehicleHealthService vehicleHealthService =
                new DefaultVehicleHealthService(
                        vehicleHealthEngine,
                        vehicleStateProvider
                );

        IllegalArgumentException exception =
                assertThrows(
                        IllegalArgumentException.class,
                        () -> vehicleHealthService.getCurrentHealth(
                                "vehicle-999"
                        )
                );

        assertEquals(
                "Vehicle state not found: vehicle-999",
                exception.getMessage()
        );

        verifyNoInteractions(vehicleHealthEngine);
    }
}