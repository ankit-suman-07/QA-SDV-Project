package com.ankit.sdv.backend.provider;

import com.ankit.sdv.backend.model.VehicleState;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import static org.junit.jupiter.api.Assertions.assertNull;

import static org.junit.jupiter.api.Assertions.assertEquals;

class InMemoryVehicleStateProviderTest {

    @Test
    void shouldStoreVehicleStatesIndependently() {
        InMemoryVehicleStateProvider provider =
                new InMemoryVehicleStateProvider();

        VehicleState vehicle001 = new VehicleState(
                "vehicle-001",
                Instant.parse("2026-07-15T16:00:00Z"),
                85.0,
                200.0
        );

        VehicleState vehicle002 = new VehicleState(
                "vehicle-002",
                Instant.parse("2026-07-15T16:05:00Z"),
                90.0,
                180.0
        );

        provider.updateState(vehicle001);
        provider.updateState(vehicle002);

        assertEquals(
                vehicle001,
                provider.getCurrentState("vehicle-001")
        );
        assertEquals(
                vehicle002,
                provider.getCurrentState("vehicle-002")
        );
    }

    @Test
void shouldStartWithoutFabricatedVehicleState() {
    InMemoryVehicleStateProvider provider =
            new InMemoryVehicleStateProvider();

    assertNull(
            provider.getCurrentState("vehicle-001")
    );

    assertNull(
            provider.getCurrentState("vehicle-002")
    );
}
}