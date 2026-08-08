package com.ankit.sdv.backend.health;

import com.ankit.sdv.backend.model.HealthResult;
import com.ankit.sdv.backend.model.HealthStatus;
import com.ankit.sdv.backend.model.VehicleState;
import org.junit.jupiter.api.Test;

import java.time.Instant;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class VehicleHealthEngineTest {

    private static final Instant SOURCE_TIMESTAMP =
            Instant.parse("2026-08-03T16:00:00Z");

    private final VehicleHealthEngine healthEngine =
            new VehicleHealthEngine();

    @Test
    void shouldReturnWarningWhenOnlyTemperatureThresholdIsReached() {
        VehicleState state = vehicleState(105.0, 200.0);

        HealthResult result = healthEngine.evaluate(state);

        assertEquals(HealthStatus.WARNING, result.status());
        assertTrue(result.activeFaults().isEmpty());
    }

    @Test
    void shouldReturnWarningWhenOnlyPressureThresholdIsReached() {
        VehicleState state = vehicleState(85.0, 150.0);

        HealthResult result = healthEngine.evaluate(state);

        assertEquals(HealthStatus.WARNING, result.status());
        assertTrue(result.activeFaults().isEmpty());
    }

    @Test
    void shouldReturnHealthyWhenBothSignalsAreNormal() {
        VehicleState state = vehicleState(104.9, 150.1);

        HealthResult result = healthEngine.evaluate(state);

        assertEquals(HealthStatus.HEALTHY, result.status());
        assertTrue(result.activeFaults().isEmpty());
    }

    private VehicleState vehicleState(
            double temperatureCelsius,
            double coolantPressureKpa
    ) {
        return new VehicleState(
                "vehicle-001",
                SOURCE_TIMESTAMP,
                temperatureCelsius,
                coolantPressureKpa
        );
    }
}