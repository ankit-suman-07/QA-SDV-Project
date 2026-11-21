package com.ankit.sdv.backend.diagnostic;

import com.ankit.sdv.backend.adapter.simulator.HttpSimulatorControlAdapter;
import com.ankit.sdv.backend.exception.ProviderDispatchException;
import com.ankit.sdv.backend.model.DiagnosticAction;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.client.RestClient;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.core.JacksonException;
import tools.jackson.core.StreamReadFeature;
import tools.jackson.databind.DeserializationFeature;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.net.URI;
import java.time.Duration;
import java.util.Optional;
import java.util.concurrent.*;

import static com.ankit.sdv.backend.diagnostic.V2Action.*;
import static com.ankit.sdv.backend.diagnostic.V2ActionTracker.error;

final class HttpActionExecution implements ActionExecution, AutoCloseable {
    private static final int MAX_BYTES = 65536;
    private static final String ACTIONS = "/api/v2/diagnostics/actions";
    private final ActionSettings settings;
    private final RestClient http;
    private final HttpSimulatorControlAdapter scenarios;
    private final ExecutorService calls = Executors.newVirtualThreadPerTaskExecutor();

    static final JsonMapper JSON = JsonMapper.builder()
            .enable(StreamReadFeature.STRICT_DUPLICATE_DETECTION)
            .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
            .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS).build();

    HttpActionExecution(ActionSettings settings, RestClient http) {
        this.settings = settings;
        this.http = http;
        scenarios = new HttpSimulatorControlAdapter(http, settings.scenarioProviders(), Duration.ofSeconds(2));
    }

    @Override public void dispatch(Request request) {
        if (request.action() != Command.RESTART_APP) {
            if (!scenarios.supportsVehicle(request.vehicleId())) throw unavailable();
            try {
                scenarios.executeV2(request.vehicleId(), DiagnosticAction.valueOf(request.action().name()),
                        request.actionId(), request.traceId());
            } catch (ProviderDispatchException failure) {
                throw switch (failure.reason()) {
                    case REJECTED -> error(HttpStatus.CONFLICT, "Scenario provider rejected action");
                    case TIMEOUT, BAD_RESPONSE -> timeout();
                    case UNAVAILABLE -> unavailable();
                };
            }
            return;
        }
        URI base = settings.fixtureBase() != null ? settings.fixtureBase() : settings.lifecycleExecutors().get(request.vehicleId());
        if (base == null) throw unavailable();
        String path = settings.fixtureBase() != null ? ACTIONS : "/actions";
        var ack = exchange(base, path, request, 202);
        if (!correlates(ack, request) || !matches(ack, "status", "ACCEPTED")) throw timeout();
    }

    @Override public Optional<Result> result(Request request) {
        URI base = settings.fixtureBase() != null ? settings.fixtureBase() : settings.results().get(request.vehicleId());
        if (base == null) return Optional.empty();
        String prefix = settings.fixtureBase() != null ? ACTIONS : "/actions";
        JsonNode result;
        try {
            result = exchange(base, prefix + "/" + request.actionId(), null, 200);
        } catch (ResponseStatusException failure) {
            return Optional.empty(); // Read-side outage never turns an action into a success or a rejection.
        }
        if (!correlates(result, request)) {
            throw error(HttpStatus.CONFLICT, "CORRELATION_MISMATCH");
        }
        var status = result.path("status").asText();
        if ("ACCEPTED".equals(status) || "TIMED_OUT".equals(status)) return Optional.empty();
        if (!result.path("status").isTextual()) throw error(HttpStatus.CONFLICT, "Invalid executor status");
        try {
            return Optional.of(JSON.treeToValue(result, Result.class));
        } catch (JacksonException malformed) {
            throw error(HttpStatus.CONFLICT, "Invalid executor result");
        }
    }

    private static boolean correlates(JsonNode response, Request request) {
        return matches(response, "vehicleId", request.vehicleId())
                && matches(response, "actionId", request.actionId())
                && matches(response, "traceId", request.traceId());
    }

    private static boolean matches(JsonNode response, String field, String expected) {
        var value = response.path(field);
        return value.isTextual() && expected.equals(value.asText());
    }

    enum Diagnostic { HEALTH, FAULTS }

    /** Callable project projection while Bayan's native bindings are pending. */
    JsonNode diagnostic(String vehicle, Diagnostic kind) {
        if (!vehicle.matches("vehicle-00[123]")) throw error(HttpStatus.NOT_FOUND, "Unknown vehicle ID");
        URI base = settings.fixtureBase();
        if (base == null) throw unavailable();
        var result = exchange(base, "/mock/v2/diagnostics/" + vehicle
                + (kind == Diagnostic.HEALTH ? "/health" : "/faults"), null, 200);
        if (!matches(result, "vehicleId", vehicle)
                || !matches(result, "boundary", "PROJECT_MOCK_NOT_NATIVE_PROTOCOL")) throw unavailable();
        return result;
    }

    private JsonNode exchange(URI base, String path, Request body, int expected) {
        URI url = URI.create(base.toString().replaceAll("/+$", "") + path);
        Future<JsonNode> work = calls.submit(() -> {
            var spec = body == null ? http.get().uri(url)
                    : http.post().uri(url).contentType(MediaType.APPLICATION_JSON).body(JSON.writeValueAsBytes(body));
            return spec.accept(MediaType.APPLICATION_JSON).exchange((request, response) -> {
                int code = response.getStatusCode().value();
                if (code == 504) throw timeout();
                if (code == 409 || (body != null && code == 422)) throw error(HttpStatus.CONFLICT, "Executor rejected action");
                if (code != expected) throw unavailable();
                if (settings.fixtureBase() != null && !response.getHeaders().containsHeader("X-SDV-Mock")) throw unavailable();
                byte[] bytes = response.getBody().readNBytes(MAX_BYTES + 1);
                if (bytes.length > MAX_BYTES) throw body == null ? unavailable() : timeout();
                var result = JSON.readTree(bytes);
                if (result == null || !result.isObject()) throw body == null ? unavailable() : timeout();
                return result;
            });
        });
        try {
            return work.get(2, TimeUnit.SECONDS);
        } catch (TimeoutException failure) {
            throw timeout();
        } catch (InterruptedException failure) {
            Thread.currentThread().interrupt();
            throw body == null ? unavailable() : timeout();
        } catch (ExecutionException failure) {
            if (failure.getCause() instanceof ResponseStatusException classified) throw classified;
            if (failure.getCause() instanceof JacksonException && body != null) throw timeout();
            throw unavailable();
        } finally {
            if (!work.isDone()) work.cancel(true);
        }
    }

    private static ResponseStatusException unavailable() { return error(HttpStatus.SERVICE_UNAVAILABLE, "Executor unavailable"); }
    private static ResponseStatusException timeout() { return error(HttpStatus.GATEWAY_TIMEOUT, "Executor acknowledgement uncertain"); }

    @Override public void close() {
        calls.shutdownNow();
        scenarios.close();
    }
}
