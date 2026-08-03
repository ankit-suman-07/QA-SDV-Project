package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.adapter.kuksa.KuksaAdapter;
import com.ankit.sdv.backend.health.VehicleHealthEngine;
import com.ankit.sdv.backend.model.HealthResult;
import com.ankit.sdv.backend.model.HealthStatus;
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
    void shouldProcessValidStateThroughCompletePipeline() {
        VehicleState kuksaState = new VehicleState(
                "vehicle-001",
                Instant.parse("2026-07-15T16:00:00Z"),
                95.0,
                200.0
        );

        HealthResult healthResult =
                new HealthResult(HealthStatus.WARNING);

        KuksaAdapter kuksaAdapter =
                mock(KuksaAdapter.class);

        VehicleHealthEngine healthEngine =
                mock(VehicleHealthEngine.class);

        DittoSynchronizationService dittoService =
                mock(DittoSynchronizationService.class);

        UProtocolEventService uProtocolEventService =
                mock(UProtocolEventService.class);

        DiagnosticService diagnosticService =
                mock(DiagnosticService.class);

        when(kuksaAdapter.readCurrentState("vehicle-001"))
                .thenReturn(kuksaState);

        when(healthEngine.evaluate(kuksaState))
                .thenReturn(healthResult);

        InMemoryVehicleStateProvider stateProvider =
                new InMemoryVehicleStateProvider();

        VehicleIntegrationService integrationService =
                new VehicleIntegrationService(
                        kuksaAdapter,
                        stateProvider,
                        healthEngine,
                        dittoService,
                        uProtocolEventService,
                        diagnosticService
                );

        integrationService.synchronizeVehicleState();

        assertEquals(
                kuksaState,
                stateProvider.getCurrentState("vehicle-001")
        );

        verify(kuksaAdapter)
                .readCurrentState("vehicle-001");

        verify(healthEngine)
                .evaluate(kuksaState);

        verify(dittoService)
                .synchronize(kuksaState);

        verify(uProtocolEventService)
                .publishVehicleStatus(kuksaState);

        verify(diagnosticService)
                .updateDiagnostics(
                        kuksaState,
                        healthResult
                );
    }

    @Test
    void shouldRejectMissingKuksaStateWithoutProcessingIt() {
        KuksaAdapter kuksaAdapter =
                mock(KuksaAdapter.class);

        VehicleHealthEngine healthEngine =
                mock(VehicleHealthEngine.class);

        DittoSynchronizationService dittoService =
                mock(DittoSynchronizationService.class);

        UProtocolEventService uProtocolEventService =
                mock(UProtocolEventService.class);

        DiagnosticService diagnosticService =
                mock(DiagnosticService.class);

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
                        healthEngine,
                        dittoService,
                        uProtocolEventService,
                        diagnosticService
                );

        assertThrows(
                IllegalStateException.class,
                integrationService::synchronizeVehicleState
        );

        assertEquals(
                existingState,
                stateProvider.getCurrentState("vehicle-001")
        );

        verifyNoInteractions(
                healthEngine,
                dittoService,
                uProtocolEventService,
                diagnosticService
        );
    }

    @Test
    void shouldRejectStateForDifferentVehicleWithoutProcessingIt() {
        VehicleState incorrectState = new VehicleState(
                "vehicle-999",
                Instant.parse("2026-07-15T16:00:00Z"),
                85.0,
                200.0
        );

        KuksaAdapter kuksaAdapter =
                mock(KuksaAdapter.class);

        VehicleHealthEngine healthEngine =
                mock(VehicleHealthEngine.class);

        DittoSynchronizationService dittoService =
                mock(DittoSynchronizationService.class);

        UProtocolEventService uProtocolEventService =
                mock(UProtocolEventService.class);

        DiagnosticService diagnosticService =
                mock(DiagnosticService.class);

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
                        healthEngine,
                        dittoService,
                        uProtocolEventService,
                        diagnosticService
                );

        assertThrows(
                IllegalStateException.class,
                integrationService::synchronizeVehicleState
        );

        assertEquals(
                existingState,
                stateProvider.getCurrentState("vehicle-001")
        );

        verifyNoInteractions(
                healthEngine,
                dittoService,
                uProtocolEventService,
                diagnosticService
        );
    }
}