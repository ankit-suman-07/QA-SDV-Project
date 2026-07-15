package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.adapter.kuksa.KuksaAdapter;
import com.ankit.sdv.backend.model.VehicleState;
import com.ankit.sdv.backend.provider.InMemoryVehicleStateProvider;
import org.junit.jupiter.api.Test;

import java.time.Instant;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

class VehicleIntegrationServiceTest {

    @Test
    void shouldSynchronizeKuksaStateWithProviderDittoAndUProtocol() {
        VehicleState kuksaState = new VehicleState(
                "vehicle-001",
                Instant.parse("2026-07-15T16:00:00Z"),
                95.0
        );

        KuksaAdapter kuksaAdapter =
                mock(KuksaAdapter.class);

        DittoSynchronizationService dittoService =
                mock(DittoSynchronizationService.class);

        UProtocolEventService uProtocolEventService =
                mock(UProtocolEventService.class);

        when(kuksaAdapter.readCurrentState("vehicle-001"))
                .thenReturn(kuksaState);

        InMemoryVehicleStateProvider stateProvider =
                new InMemoryVehicleStateProvider();

        VehicleIntegrationService integrationService =
                new VehicleIntegrationService(
                        kuksaAdapter,
                        stateProvider,
                        dittoService,
                        uProtocolEventService
                );

        integrationService.synchronizeVehicleState();

        VehicleState synchronizedState =
                stateProvider.getCurrentState("vehicle-001");

        assertEquals(kuksaState, synchronizedState);

        verify(kuksaAdapter)
                .readCurrentState("vehicle-001");

        verify(dittoService)
                .synchronize(kuksaState);

        verify(uProtocolEventService)
                .publishVehicleStatus(kuksaState);
    }

    @Test
    void shouldRejectMissingKuksaStateWithoutOverwritingCurrentState() {
        KuksaAdapter kuksaAdapter =
                mock(KuksaAdapter.class);

        DittoSynchronizationService dittoService =
                mock(DittoSynchronizationService.class);

        UProtocolEventService uProtocolEventService =
                mock(UProtocolEventService.class);

        when(kuksaAdapter.readCurrentState("vehicle-001"))
                .thenReturn(null);

        InMemoryVehicleStateProvider stateProvider =
                new InMemoryVehicleStateProvider();

        VehicleState existingState =
                stateProvider.getCurrentState("vehicle-001");

        VehicleIntegrationService integrationService =
                new VehicleIntegrationService(
                        kuksaAdapter,
                        stateProvider,
                        dittoService,
                        uProtocolEventService
                );

        assertThrows(
                IllegalStateException.class,
                integrationService::synchronizeVehicleState
        );

        VehicleState stateAfterFailure =
                stateProvider.getCurrentState("vehicle-001");

        assertEquals(existingState, stateAfterFailure);

        verify(kuksaAdapter)
                .readCurrentState("vehicle-001");

        verifyNoInteractions(dittoService);
        verifyNoInteractions(uProtocolEventService);
    }

    @Test
    void shouldRejectStateForDifferentVehicle() {
        VehicleState incorrectState = new VehicleState(
                "vehicle-999",
                Instant.parse("2026-07-15T16:00:00Z"),
                85.0
        );

        KuksaAdapter kuksaAdapter =
                mock(KuksaAdapter.class);

        DittoSynchronizationService dittoService =
                mock(DittoSynchronizationService.class);

        UProtocolEventService uProtocolEventService =
                mock(UProtocolEventService.class);

        when(kuksaAdapter.readCurrentState("vehicle-001"))
                .thenReturn(incorrectState);

        InMemoryVehicleStateProvider stateProvider =
                new InMemoryVehicleStateProvider();

        VehicleState existingState =
                stateProvider.getCurrentState("vehicle-001");

        VehicleIntegrationService integrationService =
                new VehicleIntegrationService(
                        kuksaAdapter,
                        stateProvider,
                        dittoService,
                        uProtocolEventService
                );

        assertThrows(
                IllegalStateException.class,
                integrationService::synchronizeVehicleState
        );

        VehicleState stateAfterFailure =
                stateProvider.getCurrentState("vehicle-001");

        assertEquals(existingState, stateAfterFailure);

        verify(kuksaAdapter)
                .readCurrentState("vehicle-001");

        verifyNoInteractions(dittoService);
        verifyNoInteractions(uProtocolEventService);
    }
}