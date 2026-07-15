package com.ankit.sdv.backend.health;

import com.ankit.sdv.backend.model.HealthResult;
import com.ankit.sdv.backend.model.HealthStatus;
import com.ankit.sdv.backend.model.VehicleState;
import org.junit.jupiter.api.Test;

import java.time.Instant;

import static org.junit.jupiter.api.Assertions.assertEquals;

class VehicleHealthEngineTest {

    private final VehicleHealthEngine healthEngine =
            new VehicleHealthEngine();

    @Test
    void shouldReturnCriticalWhenTemperatureIs105Degrees() {
        VehicleState state = new VehicleState(
                "vehicle-001",
                Instant.parse("2026-07-15T16:00:00Z"),
                105.0
        );

        HealthResult result = healthEngine.evaluate(state);

        assertEquals(HealthStatus.CRITICAL, result.status());
    }
}