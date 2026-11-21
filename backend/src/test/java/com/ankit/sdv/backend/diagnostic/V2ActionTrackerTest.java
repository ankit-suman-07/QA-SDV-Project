package com.ankit.sdv.backend.diagnostic;

import com.ankit.sdv.backend.dto.V2VehicleResponse;
import com.ankit.sdv.backend.service.V2VehicleService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.json.JsonMapper;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.*;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static com.ankit.sdv.backend.diagnostic.V2Action.*;
import static com.ankit.sdv.backend.diagnostic.V2Action.Status.*;
import static org.assertj.core.api.Assertions.*;
import org.assertj.core.api.ThrowableAssert.ThrowingCallable;
import static org.mockito.Mockito.*;

class V2ActionTrackerTest {
    private static final Instant EPOCH = Instant.parse("2026-01-01T00:00:00Z");
    private final JsonMapper json = JsonMapper.builder().build();
    private final Clock clock = mock(Clock.class);
    private final ActionExecution executor = mock(ActionExecution.class);
    private final V2VehicleService vehicles = mock(V2VehicleService.class);
    @TempDir Path directory;
    private Request request;
    private Instant now;

    @BeforeEach void setup() throws Exception {
        now = EPOCH;
        when(clock.instant()).thenAnswer(call -> now);
        when(vehicles.vehicleIds()).thenReturn(List.of("vehicle-001", "vehicle-002", "vehicle-003"));
        var fixture = json.readTree(Files.readAllBytes(Path.of("../tests/fixtures/v2/diagnostics/cases.json")));
        request = json.treeToValue(fixture.get("request"), Request.class);
    }

    private V2ActionTracker open() throws Exception {
        return new V2ActionTracker(new ActionJournal(directory.resolve("actions.json"), json), executor, vehicles, clock);
    }

    @Test void durableDispatchIdempotencyCorrelationAndTerminalResults() throws Exception {
        try (var tracker = open()) {
            assertThat(tracker.create(request).status()).isEqualTo(ACCEPTED);
            assertThat(tracker.create(request).status()).isEqualTo(ACCEPTED);
            verify(executor).dispatch(request);
            status(HttpStatus.CONFLICT, () -> tracker.create(new Request(request.vehicleId(), request.actionId(),
                    "other", request.action(), request.scenario())));
            status(HttpStatus.CONFLICT, () -> tracker.apply(new Result("vehicle-002", request.actionId(),
                    request.traceId(), EXECUTING, null, null), request));
            assertThat(tracker.apply(result(EXECUTING), request).status()).isEqualTo(EXECUTING);
        }
        try (var tracker = open()) {
            assertThat(tracker.read(request.actionId()).status()).isEqualTo(EXECUTING);
            var succeeded = tracker.apply(result(SUCCEEDED), request);
            assertThat(tracker.apply(result(FAILED), request)).isEqualTo(succeeded);
            assertThat(tracker.history(request.vehicleId())).containsExactly(succeeded);
            assertThat(tracker.history("vehicle-001")).isEmpty();
        }
    }

    @Test void exactDeadlineLateResultAndExpiry() throws Exception {
        try (var tracker = open()) {
            tracker.create(request);
            now = EPOCH.plusSeconds(10).minusNanos(1);
            assertThat(tracker.read(request.actionId()).status()).isEqualTo(ACCEPTED);
            now = EPOCH.plusSeconds(10);
            var terminal = tracker.read(request.actionId());
            assertThat(terminal.status()).isEqualTo(TIMED_OUT);
            assertThat(terminal.executionUncertain()).isTrue();
            when(executor.result(request)).thenReturn(Optional.of(result(SUCCEEDED)));
            assertThat(tracker.read(request.actionId()).lateResult()).isEqualTo(result(SUCCEEDED));
            assertThat(tracker.read(request.actionId()).status()).isEqualTo(TIMED_OUT);
            now = EPOCH.plus(Duration.ofDays(7));
            assertThat(tracker.history(request.vehicleId())).isEmpty();
            status(HttpStatus.NOT_FOUND, () -> tracker.read(request.actionId()));
        }
    }

    @Test void rejectionUnavailableAndUncertainDispatchAreDurable() throws Exception {
        try (var tracker = open()) {
            for (var code : List.of(HttpStatus.CONFLICT, HttpStatus.SERVICE_UNAVAILABLE, HttpStatus.GATEWAY_TIMEOUT)) {
                var id = "dispatch-" + code.value();
                var action = new Request(request.vehicleId(), id, request.traceId(), request.action(), request.scenario());
                doThrow(new ResponseStatusException(code, "controlled failure")).when(executor).dispatch(action);
                status(code, () -> tracker.create(action));
                var record = tracker.create(action);
                assertThat(record.status()).isEqualTo(code == HttpStatus.GATEWAY_TIMEOUT ? TIMED_OUT : FAILED);
                assertThat(record.executionUncertain()).isEqualTo(code == HttpStatus.GATEWAY_TIMEOUT);
                verify(executor).dispatch(action);
            }
        }
    }

    @Test void restartNeedsCorrelatedLifecycleAndFreshTwinEvidence() throws Exception {
        var restart = new Request(request.vehicleId(), "restart-id", request.traceId(), Command.RESTART_APP, null);
        when(vehicles.readAt(request.vehicleId(), null)).thenReturn(V2VehicleResponse.unavailable(request.vehicleId(), "sdv:vehicle-003"));
        try (var tracker = open()) {
            assertThat(tracker.create(restart).deadline()).isEqualTo(EPOCH.plusSeconds(30));
            tracker.apply(new Result(restart.vehicleId(), restart.actionId(), restart.traceId(), EXECUTING, null, null), restart);
            status(HttpStatus.CONFLICT, () -> tracker.apply(new Result(restart.vehicleId(), restart.actionId(),
                    restart.traceId(), SUCCEEDED, null, null), restart));
            now = EPOCH.plusSeconds(4);
            var proof = new RestartEvidence(EPOCH.plusSeconds(1), EPOCH.plusSeconds(2), EPOCH.plusSeconds(3),
                    "new-event", "new-session", now);
            var completed = new Result(restart.vehicleId(), restart.actionId(), restart.traceId(), SUCCEEDED, null, proof);
            status(HttpStatus.CONFLICT, () -> tracker.apply(completed, restart));
            var twin = mock(V2VehicleResponse.class);
            when(twin.availability()).thenReturn("AVAILABLE");
            when(twin.sourceTimestamp()).thenReturn(now.toString());
            when(twin.lastEventId()).thenReturn("new-event");
            when(twin.sessionId()).thenReturn("new-session");
            when(vehicles.readAt(request.vehicleId(), null)).thenReturn(twin);
            assertThat(tracker.apply(completed, restart).status()).isEqualTo(SUCCEEDED);
        }
    }

    @Test void periodicPollTracksExecutionAndInterruptedReservationDoesNotRedispatch() throws Exception {
        try (var tracker = open()) {
            tracker.create(request);
            when(executor.result(request)).thenReturn(Optional.of(result(EXECUTING)));
            tracker.pollActive();
            verify(executor, timeout(2000)).result(request);
            assertThat(tracker.read(request.actionId()).status()).isEqualTo(EXECUTING);
        }
        String reserved = "reservation";
        try (var journal = new ActionJournal(directory.resolve("actions.json"), json)) {
            var entry = new Entry(request.vehicleId(), reserved, request.traceId(), request.action(), request.scenario(),
                    DISPATCHING, now, now.plusSeconds(10), now, null, false, null, null, null);
            journal.save(Map.of(reserved, entry));
        }
        try (var tracker = open()) {
            var outcome = tracker.read(reserved);
            assertThat(outcome.status()).isEqualTo(TIMED_OUT);
            assertThat(outcome.executionUncertain()).isTrue();
            verify(executor, times(1)).dispatch(any());
        }
    }

    @Test void persistenceFailureDoesNotDispatchOrAdvance() throws Exception {
        var journal = mock(ActionJournal.class);
        when(journal.loaded()).thenReturn(Map.of());
        var tracker = new V2ActionTracker(journal, executor, vehicles, clock);
        doThrow(new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE)).when(journal).save(anyMap());
        status(HttpStatus.SERVICE_UNAVAILABLE, () -> tracker.create(request));
        verifyNoInteractions(executor);
        doNothing().when(journal).save(anyMap());
        tracker.create(request);
        doThrow(new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE)).when(journal).save(anyMap());
        status(HttpStatus.SERVICE_UNAVAILABLE, () -> tracker.apply(result(EXECUTING), request));
        assertThat(tracker.read(request.actionId()).status()).isEqualTo(ACCEPTED);
    }

    @Test void oldestTerminalIsEvictedAtCapacityForItsVehicleOnly() throws Exception {
        try (var tracker = open()) {
            for (int i = 0; i <= 100; i++) {
                now = EPOCH.plusSeconds(i);
                var action = new Request(request.vehicleId(), "history-" + i, request.traceId(), request.action(), request.scenario());
                tracker.create(action);
                tracker.apply(new Result(action.vehicleId(), action.actionId(), action.traceId(), FAILED, null, null), action);
            }
            assertThat(tracker.history(request.vehicleId())).hasSize(100);
            status(HttpStatus.NOT_FOUND, () -> tracker.read("history-0"));
        }
    }

    private Result result(Status status) {
        return new Result(request.vehicleId(), request.actionId(), request.traceId(), status, null, null);
    }

    private static void status(HttpStatus status, ThrowingCallable call) {
        assertThatExceptionOfType(ResponseStatusException.class).isThrownBy(call)
                .satisfies(failure -> assertThat(failure.getStatusCode()).isEqualTo(status));
    }
}
