package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.health.VehicleHealthEngine;
import org.junit.jupiter.api.Test;
import com.ankit.sdv.backend.model.VehicleState;
import com.ankit.sdv.backend.provider.VehicleStateProvider;

import java.time.Instant;

import static org.junit.jupiter.api.Assertions.assertThrows;

class DefaultVehicleHealthServiceTest {

    private final VehicleHealthEngine vehicleHealthEngine =
            new VehicleHealthEngine();

    private final VehicleStateProvider vehicleStateProvider =
            vehicleId -> new VehicleState(
                    "vehicle-001",
                    Instant.parse("2026-07-15T16:00:00Z"),
                    85.0,
                    200.0
            );

    private final DefaultVehicleHealthService vehicleHealthService =
            new DefaultVehicleHealthService(
                    vehicleHealthEngine,
                    vehicleStateProvider
            );

    @Test
    void shouldRejectUnsupportedVehicleId() {
        assertThrows(
                IllegalArgumentException.class,
                () -> vehicleHealthService.getCurrentHealth(
                        "vehicle-999"
                )
        );
    }
}