package com.ankit.sdv.backend.health;

import com.ankit.sdv.backend.model.HealthResult;
import com.ankit.sdv.backend.model.HealthStatus;
import com.ankit.sdv.backend.model.VehicleState;
import org.junit.jupiter.api.Test;

import java.time.Instant;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class VehicleHealthEngineCorrelationTest {

    private static final Instant SOURCE_TIMESTAMP =
            Instant.parse("2026-08-03T16:00:00Z");

    private final VehicleHealthEngine healthEngine =
            new VehicleHealthEngine();

    @Test
    void shouldActivateCoolingSystemFailureWhenTemperatureIsHighAndPressureIsLow() {
        VehicleState state = vehicleState(108.0, 140.0);

        HealthResult result = healthEngine.evaluate(state);

        assertEquals(HealthStatus.CRITICAL, result.status());
        assertTrue(
                result.activeFaults()
                        .contains("COOLING_SYSTEM_FAILURE")
        );
    }

    @Test
    void shouldNotActivateCorrelatedFaultWhenOnlyTemperatureIsHigh() {
        VehicleState state = vehicleState(108.0, 220.0);

        HealthResult result = healthEngine.evaluate(state);

        assertEquals(HealthStatus.WARNING, result.status());
        assertFalse(
                result.activeFaults()
                        .contains("COOLING_SYSTEM_FAILURE")
        );
    }

    @Test
    void shouldNotActivateCorrelatedFaultWhenOnlyCoolantPressureIsLow() {
        VehicleState state = vehicleState(85.0, 140.0);

        HealthResult result = healthEngine.evaluate(state);

        assertEquals(HealthStatus.WARNING, result.status());
        assertFalse(
                result.activeFaults()
                        .contains("COOLING_SYSTEM_FAILURE")
        );
    }

    @Test
    void shouldKeepFaultActiveUntilBothRecoveryConditionsAreSatisfied() {
        healthEngine.evaluate(vehicleState(108.0, 140.0));

        HealthResult result =
                healthEngine.evaluate(vehicleState(103.0, 165.0));

        assertEquals(HealthStatus.CRITICAL, result.status());
        assertTrue(
                result.activeFaults()
                        .contains("COOLING_SYSTEM_FAILURE")
        );
    }

    @Test
    void shouldClearFaultWhenTemperatureAndPressureRecover() {
        healthEngine.evaluate(vehicleState(108.0, 140.0));

        HealthResult result =
                healthEngine.evaluate(vehicleState(99.0, 190.0));

        assertEquals(HealthStatus.HEALTHY, result.status());
        assertFalse(
                result.activeFaults()
                        .contains("COOLING_SYSTEM_FAILURE")
        );
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