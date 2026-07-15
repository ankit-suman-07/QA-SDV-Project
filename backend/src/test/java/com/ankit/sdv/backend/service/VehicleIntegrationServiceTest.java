package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.adapter.kuksa.KuksaAdapter;
import com.ankit.sdv.backend.model.VehicleState;
import com.ankit.sdv.backend.provider.InMemoryVehicleStateProvider;
import org.junit.jupiter.api.Test;

import java.time.Instant;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class VehicleIntegrationServiceTest {

    @Test
    void shouldSynchronizeKuksaStateWithCurrentStateProvider() {
        VehicleState kuksaState = new VehicleState(
                "vehicle-001",
                Instant.parse("2026-07-15T16:00:00Z"),
                95.0
        );

        KuksaAdapter kuksaAdapter =
                mock(KuksaAdapter.class);

        when(kuksaAdapter.readCurrentState("vehicle-001"))
                .thenReturn(kuksaState);

        InMemoryVehicleStateProvider stateProvider =
                new InMemoryVehicleStateProvider();

        VehicleIntegrationService integrationService =
                new VehicleIntegrationService(
                        kuksaAdapter,
                        stateProvider
                );

        integrationService.synchronizeVehicleState();

        VehicleState synchronizedState =
                stateProvider.getCurrentState("vehicle-001");

        assertEquals(kuksaState, synchronizedState);

        verify(kuksaAdapter)
                .readCurrentState("vehicle-001");
    }
}