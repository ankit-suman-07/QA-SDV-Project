package com.ankit.sdv.backend.registry;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class VehicleRegistryTest {

    @Test
    void shouldNormalizeConfiguredVehicleIds() {
        VehicleRegistry registry = new VehicleRegistry(
                List.of(
                        "vehicle-001",
                        " vehicle-002 ",
                        "vehicle-001",
                        "vehicle-003"
                )
        );

        assertEquals(
                List.of(
                        "vehicle-001",
                        "vehicle-002",
                        "vehicle-003"
                ),
                registry.vehicleIds()
        );
    }

    @Test
    void shouldAcceptConfiguredVehicle() {
        VehicleRegistry registry = new VehicleRegistry(
                List.of(
                        "vehicle-001",
                        "vehicle-002",
                        "vehicle-003"
                )
        );

        assertDoesNotThrow(
                () -> registry.requireRegistered("vehicle-002")
        );
    }

    @Test
    void shouldRejectUnconfiguredVehicle() {
        VehicleRegistry registry = new VehicleRegistry(
                List.of(
                        "vehicle-001",
                        "vehicle-002",
                        "vehicle-003"
                )
        );

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> registry.requireRegistered("vehicle-999")
        );

        assertEquals(
                "Unsupported vehicle ID: vehicle-999",
                exception.getMessage()
        );
    }
}