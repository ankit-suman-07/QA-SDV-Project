package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.health.VehicleHealthEngine;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertThrows;

class DefaultVehicleHealthServiceTest {

    private final VehicleHealthEngine vehicleHealthEngine =
            new VehicleHealthEngine();

    private final DefaultVehicleHealthService vehicleHealthService =
            new DefaultVehicleHealthService(vehicleHealthEngine);

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