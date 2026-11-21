package com.ankit.sdv.backend.diagnostic;

import com.ankit.sdv.backend.service.V2VehicleService;
import com.ankit.sdv.backend.dto.V2VehicleResponse;
import org.springframework.http.HttpStatus;
import org.springframework.scheduling.annotation.Scheduled;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.TimeUnit;

import static com.ankit.sdv.backend.diagnostic.V2Action.*;
import static com.ankit.sdv.backend.diagnostic.V2Action.Status.*;

final class V2ActionTracker implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(V2ActionTracker.class);
    private static final int CAPACITY = 100;
    private static final Duration RETENTION = Duration.ofDays(7);

    private final ActionJournal journal;
    private final ActionExecution executor;
    private final V2VehicleService vehicles;
    private final Clock clock;
    private Map<String, Entry> entries;
    private final ExecutorService twinReads = Executors.newVirtualThreadPerTaskExecutor();
    private final ExecutorService polls = Executors.newVirtualThreadPerTaskExecutor();
    private final Set<String> polling = new HashSet<>();
    private final Set<String> dispatching = new HashSet<>();

    V2ActionTracker(ActionJournal journal, ActionExecution executor, V2VehicleService vehicles, Clock clock) {
        this.journal = journal;
        this.executor = executor;
        this.vehicles = vehicles;
        this.clock = clock;
        entries = new LinkedHashMap<>(journal.loaded());
        for (var entry : List.copyOf(entries.values())) {
            if (entry.status() == DISPATCHING) {
                replace(entry.transition(TIMED_OUT, clock.instant(), "DISPATCH_INTERRUPTED", true, null));
            }
        }
    }

    Entry create(Request request) {
        validate(request);
        synchronized (this) {
            var existing = existing(request);
            if (existing != null) return existing;
        }
        var baseline = request.action() == Command.RESTART_APP ? readTwin(request.vehicleId()) : null;
        String priorSource = baseline == null ? null : baseline.sourceTimestamp();
        synchronized (this) {
            var existing = existing(request);
            if (existing != null) return existing;
            var next = new LinkedHashMap<>(entries);
            if (next.values().stream().filter(entry -> entry.vehicleId().equals(request.vehicleId())).count() >= CAPACITY) {
                var oldest = next.values().stream().filter(entry -> entry.vehicleId().equals(request.vehicleId()) && entry.terminal())
                        .min(Comparator.comparing(Entry::requestedAt)).orElseThrow(
                                () -> error(HttpStatus.SERVICE_UNAVAILABLE, "Action history is full"));
                next.remove(oldest.actionId());
            }
            Instant now = clock.instant();
            var entry = new Entry(request.vehicleId(), request.actionId(), request.traceId(), request.action(),
                    request.scenario(), DISPATCHING, now,
                    now.plusSeconds(request.action() == Command.RESTART_APP ? 30 : 10),
                    now, null, false, priorSource, null, null);
            next.put(entry.actionId(), entry);
            save(next);
            dispatching.add(request.actionId());
        }

        try {
            dispatch(request);
            synchronized (this) {
                var entry = entries.get(request.actionId());
                var accepted = entry.transition(ACCEPTED, clock.instant(), null, false, null);
                replace(accepted);
                return accepted;
            }
        } finally {
            synchronized (this) { dispatching.remove(request.actionId()); }
        }
    }

    private void dispatch(Request request) {
        try {
            executor.dispatch(request);
        } catch (ResponseStatusException failure) {
            synchronized (this) {
                var entry = entries.get(request.actionId());
                boolean uncertain = failure.getStatusCode().value() == 504;
                replace(entry.transition(uncertain ? TIMED_OUT : FAILED, clock.instant(),
                        failure.getReason(), uncertain, null));
            }
            throw failure;
        }
    }

    Entry read(String id) {
        Request request;
        synchronized (this) {
            var entry = find(id);
            if (entry.status() == DISPATCHING) throw pending();
            if (entry.terminal() && (entry.status() != TIMED_OUT || entry.lateResult() != null)) return entry;
            request = entry.request();
        }
        // Poll an explicitly configured executor. Read failures cannot erase an action record.
        var result = executor.result(request);
        if (result.isPresent()) return apply(result.get(), request);
        synchronized (this) { return find(id); }
    }

    @Scheduled(fixedDelayString = "${sdv.v2.actions.poll-interval:500ms}",
            initialDelayString = "${sdv.v2.actions.poll-initial-delay:500ms}")
    synchronized void pollActive() {
        maintain();
        for (var entry : entries.values()) {
            if ((entry.status() == ACCEPTED || entry.status() == EXECUTING) && polling.add(entry.actionId())) {
                polls.submit(() -> {
                    try {
                        read(entry.actionId());
                    } catch (ResponseStatusException failure) {
                        LOG.warn("v2_action_poll_failed status={}", failure.getStatusCode().value());
                    } finally {
                        synchronized (this) { polling.remove(entry.actionId()); }
                    }
                });
            }
        }
    }

    synchronized List<Entry> history(String vehicleId) {
        if (!vehicles.vehicleIds().contains(vehicleId)) throw error(HttpStatus.NOT_FOUND, "Unknown vehicle ID");
        maintain();
        return entries.values().stream()
                .filter(entry -> entry.vehicleId().equals(vehicleId) && entry.status() != DISPATCHING).toList();
    }

    Entry apply(Result result, Request expected) {
        if (result == null || !Objects.equals(expected.actionId(), result.actionId())
                || !Objects.equals(expected.vehicleId(), result.vehicleId())
                || !Objects.equals(expected.traceId(), result.traceId())) {
            throw error(HttpStatus.CONFLICT, "CORRELATION_MISMATCH");
        }
        if (result.status() != EXECUTING && result.status() != SUCCEEDED && result.status() != FAILED) {
            throw error(HttpStatus.CONFLICT, "Invalid executor status");
        }
        Entry observed;
        synchronized (this) {
            observed = find(expected.actionId());
            if (!observed.request().equals(expected)) throw error(HttpStatus.CONFLICT, "CORRELATION_MISMATCH");
            if (observed.status() == DISPATCHING) throw error(HttpStatus.CONFLICT, "Dispatch is still pending");
            if (observed.terminal()) return late(observed, result);
        }
        if (result.status() == SUCCEEDED && expected.action() == Command.RESTART_APP) {
            validateRestart(observed, result.restart());
        }
        synchronized (this) {
            var current = find(expected.actionId());
            if (!current.request().equals(expected)) throw error(HttpStatus.CONFLICT, "CORRELATION_MISMATCH");
            if (current.terminal()) return late(current, result);
            if (current.status() == result.status()) return current;
            if (result.status() == SUCCEEDED && current.status() == ACCEPTED) {
                // A poll may miss EXECUTING, but the outcome must carry evidence it occurred.
                var started = result.executionStartedAt();
                if (started == null || started.isBefore(current.requestedAt()) || started.isAfter(clock.instant())) {
                    throw error(HttpStatus.CONFLICT, "Success lacks execution-start evidence");
                }
            }
            var updated = current.transition(result.status(), clock.instant(), null, false, result);
            replace(updated);
            return updated;
        }
    }

    private Entry late(Entry entry, Result result) {
        if (entry.status() != TIMED_OUT || result.status() == EXECUTING || entry.lateResult() != null) return entry;
        var updated = entry.withLateResult(result);
        replace(updated);
        return updated;
    }

    private void validateRestart(Entry entry, RestartEvidence proof) {
        if (proof == null || proof.stoppedAt() == null || proof.startRequestedAt() == null
                || proof.startedAt() == null || proof.observationSourceTimestamp() == null
                || proof.stoppedAt().isBefore(entry.requestedAt())
                || proof.startRequestedAt().isBefore(proof.stoppedAt())
                || proof.startedAt().isBefore(proof.startRequestedAt())
                || proof.startedAt().isAfter(clock.instant())
                || !proof.observationSourceTimestamp().isAfter(proof.startedAt())
                || (entry.priorSourceTimestamp() != null
                    && !proof.observationSourceTimestamp().isAfter(Instant.parse(entry.priorSourceTimestamp())))) {
            throw error(HttpStatus.CONFLICT, "Restart completion lacks lifecycle and post-start observation evidence");
        }
        var state = readTwin(entry.vehicleId());
        if (state == null || !"AVAILABLE".equals(state.availability()) || !Objects.equals(state.lastEventId(), proof.observationEventId())
                || !Objects.equals(state.sessionId(), proof.observationSessionId())
                || !proof.observationSourceTimestamp().equals(Instant.parse(state.sourceTimestamp()))) {
            throw error(HttpStatus.CONFLICT, "Restart observation does not match fresh individual state");
        }
    }

    private V2VehicleResponse readTwin(String vehicle) {
        var pending = twinReads.submit(() -> vehicles.readAt(vehicle, null));
        try {
            return pending.get(2, TimeUnit.SECONDS);
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            return null;
        } catch (ExecutionException | TimeoutException failure) {
            return null;
        } finally {
            if (!pending.isDone()) pending.cancel(true);
        }
    }

    private void validate(Request request) {
        if (request == null || !identifier(request.vehicleId()) || !identifier(request.actionId())
                || !identifier(request.traceId()) || request.action() == null
                || (request.action() == Command.RESTART_APP ? request.scenario() != null
                        : !"LIDAR_OBSTRUCTION".equals(request.scenario()))) {
            throw error(HttpStatus.BAD_REQUEST, "Invalid action request");
        }
        if (!vehicles.vehicleIds().contains(request.vehicleId())) throw error(HttpStatus.NOT_FOUND, "Unknown vehicle ID");
    }

    private static boolean identifier(String value) {
        return value != null && value.matches("[A-Za-z0-9][A-Za-z0-9._-]{0,127}");
    }

    private Entry existing(Request request) {
        maintain();
        var entry = entries.get(request.actionId());
        if (entry != null) {
            if (!entry.request().equals(request)) throw error(HttpStatus.CONFLICT, "Action ID already used");
            if (entry.status() == DISPATCHING) throw pending();
        }
        return entry;
    }

    private Entry find(String id) {
        maintain();
        var entry = entries.get(id);
        if (entry == null) throw error(HttpStatus.NOT_FOUND, "Unknown action ID");
        return entry;
    }

    private void maintain() {
        Instant now = clock.instant();
        var next = new LinkedHashMap<>(entries);
        next.values().removeIf(entry -> entry.terminal() && !now.isBefore(entry.requestedAt().plus(RETENTION)));
        next.replaceAll((id, entry) -> {
            if (entry.status() == DISPATCHING && !dispatching.contains(id)) {
                return entry.transition(TIMED_OUT, now, "DISPATCH_INTERRUPTED", true, null);
            }
            return !entry.terminal() && entry.status() != DISPATCHING && !now.isBefore(entry.deadline())
                    ? entry.transition(TIMED_OUT, now, "EXECUTION_TIMEOUT", true, entry.executionEvidence()) : entry;
        });
        if (!next.equals(entries)) save(next);
    }

    private void replace(Entry entry) {
        var next = new LinkedHashMap<>(entries);
        next.put(entry.actionId(), entry);
        save(next);
    }

    private void save(Map<String, Entry> next) {
        journal.save(next);
        entries = next;
    }

    private static ResponseStatusException pending() {
        return error(HttpStatus.SERVICE_UNAVAILABLE, "Dispatch acknowledgement pending");
    }

    static ResponseStatusException error(HttpStatus status, String message) {
        return new ResponseStatusException(status, message);
    }

    @Override public void close() throws IOException {
        polls.shutdownNow();
        twinReads.shutdownNow();
        journal.close();
    }
}
