package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.adapter.ditto.DittoAdapter;
import com.ankit.sdv.backend.model.VehicleState;
import org.junit.jupiter.api.Test;

import java.time.Instant;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

class DittoSynchronizationServiceTest {

    @Test
    void shouldSendVehicleStateToDittoAdapter() {
        DittoAdapter dittoAdapter =
                mock(DittoAdapter.class);

        DittoSynchronizationService synchronizationService =
                new DittoSynchronizationService(dittoAdapter);

        VehicleState vehicleState = new VehicleState(
                "vehicle-001",
                Instant.parse("2026-07-15T16:00:00Z"),
                90.0,
                200.0
        );

        synchronizationService.synchronize(vehicleState);

        verify(dittoAdapter)
                .updateVehicleState(vehicleState);
    }
}