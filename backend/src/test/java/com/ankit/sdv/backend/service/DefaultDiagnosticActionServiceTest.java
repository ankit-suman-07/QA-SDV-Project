package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.adapter.simulator.SimulatorControlAdapter;
import com.ankit.sdv.backend.dto.DiagnosticActionRequest;
import com.ankit.sdv.backend.dto.DiagnosticActionResponse;
import com.ankit.sdv.backend.model.DiagnosticAction;
import com.ankit.sdv.backend.model.DiagnosticActionStatus;
import com.ankit.sdv.backend.model.DiagnosticScenario;
import com.ankit.sdv.backend.support.ActionIdGenerator;
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
            mock(SimulatorControlAdapter.class);

    private final ActionIdGenerator actionIdGenerator =
            () -> "action-001";

    private final Clock clock = Clock.fixed(
            Instant.parse("2026-08-03T17:00:00Z"),
            ZoneOffset.UTC
    );

    private final DefaultDiagnosticActionService service =
            new DefaultDiagnosticActionService(
                    simulatorControlAdapter,
                    actionIdGenerator,
                    clock
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


}