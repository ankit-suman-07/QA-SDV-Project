package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.adapter.uprotocol.UProtocolAdapter;
import com.ankit.sdv.backend.model.VehicleState;
import org.junit.jupiter.api.Test;

import java.time.Instant;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

class UProtocolEventServiceTest {

    @Test
    void shouldPublishVehicleStatusThroughUProtocolAdapter() {
        UProtocolAdapter uProtocolAdapter =
                mock(UProtocolAdapter.class);

        UProtocolEventService eventService =
                new UProtocolEventService(uProtocolAdapter);

        VehicleState vehicleState = new VehicleState(
                "vehicle-001",
                Instant.parse("2026-07-15T16:00:00Z"),
                95.0,
                200.0
        );

        eventService.publishVehicleStatus(vehicleState);

        verify(uProtocolAdapter)
                .publishVehicleStatus(vehicleState);
    }
}