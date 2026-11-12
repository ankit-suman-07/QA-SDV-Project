package com.ankit.sdv.backend.adapter.simulator;

import com.ankit.sdv.backend.exception.ProviderDispatchException;
import com.ankit.sdv.backend.model.DiagnosticAction;
import com.ankit.sdv.backend.model.DiagnosticScenario;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import tools.jackson.core.JacksonException;
import tools.jackson.core.StreamReadFeature;
import tools.jackson.databind.DeserializationFeature;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.net.URI;
import java.net.SocketTimeoutException;
import java.net.http.HttpTimeoutException;
import java.util.Map;
import java.time.Duration;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import static com.ankit.sdv.backend.exception.ProviderDispatchException.Reason.*;

/** Exactly one POST to the configured vehicle target; success requires a matching acknowledgement. */
public final class HttpSimulatorControlAdapter implements SimulatorControlAdapter, AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(HttpSimulatorControlAdapter.class);
    private static final int MAX_ACK_BYTES = 64 * 1024;
    private final RestClient client;
    private final Map<String, URI> providers;
    private final Duration responseTimeout;
    private final ExecutorService requests = Executors.newVirtualThreadPerTaskExecutor();
    private final JsonMapper json = JsonMapper.builder().enable(StreamReadFeature.STRICT_DUPLICATE_DETECTION)
            .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS).build();

    public HttpSimulatorControlAdapter(RestClient client, Map<String, URI> providers, Duration responseTimeout) {
        this.client = client; this.providers = Map.copyOf(providers); this.responseTimeout = responseTimeout;
    }
    @Override public boolean supportsVehicle(String vehicleId) { return providers.containsKey(vehicleId); }
    @Override public boolean dispatchAcknowledged() { return true; }

    @Override public void executeAction(String vehicleId, DiagnosticAction action, DiagnosticScenario scenario, String actionId, String traceId) {
        if (!supportsVehicle(vehicleId)) throw new IllegalArgumentException("Unsupported provider vehicle ID");
        // A deadline covers both headers and body. Cancellation interrupts the owned virtual thread,
        // causing the HTTP exchange/body stream to close; it cannot undo provider execution.
        var pending = requests.submit(() -> post(vehicleId, action, scenario, actionId, traceId));
        ProviderDispatchException failure;
        try {
            pending.get(responseTimeout.toNanos(), TimeUnit.NANOSECONDS);
            return;
        } catch (TimeoutException error) {
            pending.cancel(true);
            failure = new ProviderDispatchException(TIMEOUT);
        } catch (InterruptedException error) {
            pending.cancel(true);
            Thread.currentThread().interrupt();
            failure = new ProviderDispatchException(UNAVAILABLE);
        } catch (ExecutionException error) {
            Throwable cause = error.getCause();
            if (cause instanceof ProviderDispatchException classified) failure = classified;
            else if (cause instanceof RestClientException) failure = new ProviderDispatchException(timeout(cause) ? TIMEOUT : UNAVAILABLE);
            else if (cause instanceof RuntimeException unexpected) throw unexpected;
            else failure = new ProviderDispatchException(UNAVAILABLE);
        }
        LOG.warn("provider_dispatch_failed vehicle={} actionId={} code={}", vehicleId, actionId, failure.reason().code);
        throw failure;
    }

    @Override public void close() { requests.shutdownNow(); }

    private void post(String vehicleId, DiagnosticAction action, DiagnosticScenario scenario, String actionId, String traceId) {
        URI provider = providers.get(vehicleId);
        if (provider == null) throw new IllegalArgumentException("Unsupported provider vehicle ID");
        var body = new SimulatorActionRequest(vehicleId, action, scenario, actionId, traceId);
        URI target = URI.create(provider.toString().replaceAll("/+$", "") + "/api/v1/scenarios/actions");
        client.post().uri(target).contentType(MediaType.APPLICATION_JSON).accept(MediaType.APPLICATION_JSON)
                    .body(body).exchange((request, response) -> {
                        int status = response.getStatusCode().value();
                        if (status >= 400 && status < 500) throw new ProviderDispatchException(REJECTED);
                        if (status < 200 || status >= 300) throw new ProviderDispatchException(BAD_RESPONSE);
                        byte[] bytes = response.getBody().readNBytes(MAX_ACK_BYTES + 1);
                        if (bytes.length > MAX_ACK_BYTES) throw new ProviderDispatchException(BAD_RESPONSE);
                        try {
                            JsonNode ack = json.readTree(bytes);
                            if (ack == null || !ack.isObject() || !matches(ack, "vehicleId", vehicleId)
                                    || !matches(ack, "action", action.name()) || !matches(ack, "scenario", scenario.name())
                                    || !matches(ack, "actionId", actionId) || !matches(ack, "traceId", traceId)
                                    || !ack.path("active").isBoolean()
                                    || ack.get("active").booleanValue() != (action == DiagnosticAction.INJECT_SCENARIO)) {
                                throw new ProviderDispatchException(BAD_RESPONSE);
                            }
                        } catch (JacksonException error) { throw new ProviderDispatchException(BAD_RESPONSE); }
                        return null;
                    });
    }
    private static boolean matches(JsonNode ack, String field, String expected) {
        return ack.path(field).isTextual() && expected.equals(ack.get(field).asText());
    }
    private static boolean timeout(Throwable error) {
        for (Throwable current = error; current != null; current = current.getCause()) {
            if (current instanceof HttpTimeoutException || current instanceof SocketTimeoutException || current instanceof TimeoutException) return true;
        }
        return false;
    }
    private record SimulatorActionRequest(String vehicleId, DiagnosticAction action, DiagnosticScenario scenario, String actionId, String traceId) {}
}
