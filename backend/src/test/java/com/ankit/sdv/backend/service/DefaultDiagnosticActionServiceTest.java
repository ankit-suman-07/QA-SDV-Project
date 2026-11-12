package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.adapter.simulator.SimulatorControlAdapter;
import com.ankit.sdv.backend.dto.DiagnosticActionRequest;
import com.ankit.sdv.backend.dto.DiagnosticActionResponse;
import com.ankit.sdv.backend.model.DiagnosticAction;
import com.ankit.sdv.backend.model.DiagnosticActionStatus;
import com.ankit.sdv.backend.model.DiagnosticScenario;
import com.ankit.sdv.backend.support.ActionIdGenerator;
import com.ankit.sdv.backend.registry.VehicleRegistry;
import java.util.List;
import org.junit.jupiter.api.Test;

import java.util.NoSuchElementException;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

class DefaultDiagnosticActionServiceTest {

    private final SimulatorControlAdapter simulatorControlAdapter =
            mock(SimulatorControlAdapter.class, org.mockito.Mockito.CALLS_REAL_METHODS);

    private final ActionIdGenerator actionIdGenerator =
            () -> "action-001";

    private final Clock clock = Clock.fixed(
            Instant.parse("2026-08-03T17:00:00Z"),
            ZoneOffset.UTC
    );

    private final VehicleRegistry vehicleRegistry =
        new VehicleRegistry(
                List.of(
                        "vehicle-001",
                        "vehicle-002",
                        "vehicle-003"
                )
        );

        private final DefaultDiagnosticActionService service =
        new DefaultDiagnosticActionService(
                simulatorControlAdapter,
                actionIdGenerator,
                clock,
                vehicleRegistry
        );

    @Test
    void shouldAcceptAndForwardCoolingFailureInjection() {
        DiagnosticActionRequest request =
                new DiagnosticActionRequest(
                        "vehicle-001",
                        DiagnosticAction.INJECT_SCENARIO,
                        DiagnosticScenario.COOLING_SYSTEM_FAILURE
                );

        DiagnosticActionResponse response =
                service.submit(request);

        assertEquals("action-001", response.actionId());
        assertEquals("action-001", response.traceId());
        assertEquals(
                "vehicle-001",
                response.vehicleId()
        );
        assertEquals(
                DiagnosticAction.INJECT_SCENARIO,
                response.action()
        );
        assertEquals(
                DiagnosticScenario.COOLING_SYSTEM_FAILURE,
                response.scenario()
        );
        assertEquals(
                DiagnosticActionStatus.ACCEPTED,
                response.status()
        );
        assertEquals(
                Instant.parse("2026-08-03T17:00:00Z"),
                response.requestedAt()
        );

        verify(simulatorControlAdapter)
                .executeAction(
                        "vehicle-001",
                        DiagnosticAction.INJECT_SCENARIO,
                        DiagnosticScenario.COOLING_SYSTEM_FAILURE,
                        "action-001",
                        "action-001"
                );
    }

    @Test
    void shouldStoreAndRetrieveSubmittedActionById() {
        DiagnosticActionRequest request =
                new DiagnosticActionRequest(
                        "vehicle-001",
                        DiagnosticAction.INJECT_SCENARIO,
                        DiagnosticScenario.COOLING_SYSTEM_FAILURE
                );

        DiagnosticActionResponse submitted =
                service.submit(request);

        DiagnosticActionResponse retrieved =
                service.getById("action-001");

        assertEquals(submitted, retrieved);
        assertEquals(
                DiagnosticActionStatus.ACCEPTED,
                retrieved.status()
        );
    }

    @Test
    void shouldRejectUnknownActionId() {
        NoSuchElementException exception =
                assertThrows(
                        NoSuchElementException.class,
                        () -> service.getById("action-999")
                );

        assertEquals(
                "Diagnostic action not found: action-999",
                exception.getMessage()
        );
    }

    @Test
    void shouldTransitionAcceptedActionToInProgress() {
        DiagnosticActionRequest request =
                new DiagnosticActionRequest(
                        "vehicle-001",
                        DiagnosticAction.INJECT_SCENARIO,
                        DiagnosticScenario.COOLING_SYSTEM_FAILURE
                );

        service.submit(request);

        DiagnosticActionResponse updated =
                service.updateStatus(
                        "action-001",
                        DiagnosticActionStatus.IN_PROGRESS
                );

        assertEquals(
                DiagnosticActionStatus.IN_PROGRESS,
                updated.status()
        );

        assertEquals(
                DiagnosticActionStatus.IN_PROGRESS,
                service.getById("action-001").status()
        );
    }

    @Test
    void shouldRejectTransitionFromAcceptedDirectlyToCompleted() {
        DiagnosticActionRequest request =
                new DiagnosticActionRequest(
                        "vehicle-001",
                        DiagnosticAction.INJECT_SCENARIO,
                        DiagnosticScenario.COOLING_SYSTEM_FAILURE
                );

        service.submit(request);

        IllegalStateException exception =
                assertThrows(
                        IllegalStateException.class,
                        () -> service.updateStatus(
                                "action-001",
                                DiagnosticActionStatus.COMPLETED
                        )
                );

        assertEquals(
                "Invalid diagnostic action status transition: "
                        + "ACCEPTED -> COMPLETED",
                exception.getMessage()
        );

        assertEquals(
                DiagnosticActionStatus.ACCEPTED,
                service.getById("action-001").status()
        );
    }

    @Test
    void shouldTransitionInProgressActionToCompleted() {
        DiagnosticActionRequest request =
                new DiagnosticActionRequest(
                        "vehicle-001",
                        DiagnosticAction.INJECT_SCENARIO,
                        DiagnosticScenario.COOLING_SYSTEM_FAILURE
                );

        service.submit(request);

        service.updateStatus(
                "action-001",
                DiagnosticActionStatus.IN_PROGRESS
        );

        DiagnosticActionResponse completed =
                service.updateStatus(
                        "action-001",
                        DiagnosticActionStatus.COMPLETED
                );

        assertEquals(
                DiagnosticActionStatus.COMPLETED,
                completed.status()
        );

        assertEquals(
                DiagnosticActionStatus.COMPLETED,
                service.getById("action-001").status()
        );
    }

    @Test
    void shouldTransitionInProgressActionToFailed() {
        DiagnosticActionRequest request =
                new DiagnosticActionRequest(
                        "vehicle-001",
                        DiagnosticAction.INJECT_SCENARIO,
                        DiagnosticScenario.COOLING_SYSTEM_FAILURE
                );

        service.submit(request);

        service.updateStatus(
                "action-001",
                DiagnosticActionStatus.IN_PROGRESS
        );

        DiagnosticActionResponse failed =
                service.updateStatus(
                        "action-001",
                        DiagnosticActionStatus.FAILED
                );

        assertEquals(
                DiagnosticActionStatus.FAILED,
                failed.status()
        );

        assertEquals(
                DiagnosticActionStatus.FAILED,
                service.getById("action-001").status()
        );
    }

    @Test
    void shouldRejectTransitionFromCompletedBackToInProgress() {
        DiagnosticActionRequest request =
                new DiagnosticActionRequest(
                        "vehicle-001",
                        DiagnosticAction.INJECT_SCENARIO,
                        DiagnosticScenario.COOLING_SYSTEM_FAILURE
                );

        service.submit(request);

        service.updateStatus(
                "action-001",
                DiagnosticActionStatus.IN_PROGRESS
        );

        service.updateStatus(
                "action-001",
                DiagnosticActionStatus.COMPLETED
        );

        IllegalStateException exception =
                assertThrows(
                        IllegalStateException.class,
                        () -> service.updateStatus(
                                "action-001",
                                DiagnosticActionStatus.IN_PROGRESS
                        )
                );

        assertEquals(
                "Invalid diagnostic action status transition: "
                        + "COMPLETED -> IN_PROGRESS",
                exception.getMessage()
        );

        assertEquals(
                DiagnosticActionStatus.COMPLETED,
                service.getById("action-001").status()
        );
    }

    @Test
void shouldAcceptActionForAnotherConfiguredVehicle() {
    DiagnosticActionRequest request =
            new DiagnosticActionRequest(
                    "vehicle-002",
                    DiagnosticAction.INJECT_SCENARIO,
                    DiagnosticScenario.COOLING_SYSTEM_FAILURE
            );

    DiagnosticActionResponse response =
            service.submit(request);

    assertEquals(
            "vehicle-002",
            response.vehicleId()
    );

    assertEquals(
            DiagnosticActionStatus.ACCEPTED,
            response.status()
    );

    verify(simulatorControlAdapter)
            .executeAction(
                    "vehicle-002",
                    DiagnosticAction.INJECT_SCENARIO,
                    DiagnosticScenario.COOLING_SYSTEM_FAILURE,
                    "action-001",
                    "action-001"
            );
}
}