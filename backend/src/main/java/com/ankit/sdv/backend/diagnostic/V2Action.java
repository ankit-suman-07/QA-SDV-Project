package com.ankit.sdv.backend.diagnostic;

import java.time.Instant;

public final class V2Action {
    private V2Action() {}

    public enum Command { INJECT_SCENARIO, CLEAR_SCENARIO, RESTART_APP }
    public enum Status { DISPATCHING, ACCEPTED, EXECUTING, SUCCEEDED, FAILED, TIMED_OUT }

    public record Request(String vehicleId, String actionId, String traceId, Command action, String scenario) {}

    public record RestartEvidence(Instant stoppedAt, Instant startRequestedAt, Instant startedAt,
            String observationEventId, String observationSessionId, Instant observationSourceTimestamp) {}

    public record Result(String vehicleId, String actionId, String traceId, Status status, Instant executionStartedAt, RestartEvidence restart) {}

    public record Entry(String vehicleId, String actionId, String traceId, Command action, String scenario,
            Status status, Instant requestedAt, Instant deadline, Instant updatedAt, String outcome,
            boolean executionUncertain, String priorSourceTimestamp, Result executionEvidence, Result lateResult) {
        Request request() { return new Request(vehicleId, actionId, traceId, action, scenario); }

        boolean terminal() {
            return status == Status.SUCCEEDED || status == Status.FAILED || status == Status.TIMED_OUT;
        }

        Entry transition(Status next, Instant now, String reason, boolean uncertain, Result evidence) {
            return new Entry(vehicleId, actionId, traceId, action, scenario, next, requestedAt, deadline,
                    now, reason, uncertain, priorSourceTimestamp, evidence, lateResult);
        }

        Entry withLateResult(Result result) {
            return new Entry(vehicleId, actionId, traceId, action, scenario, status, requestedAt, deadline,
                    updatedAt, outcome, executionUncertain, priorSourceTimestamp, executionEvidence, result);
        }
    }
}
