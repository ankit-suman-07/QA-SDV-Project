package com.ankit.sdv.backend.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.web.client.RestClient;
import tools.jackson.databind.json.JsonMapper;

import java.net.URI;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

/** Sole in-process fleet writer. Run one enabled backend replica per fleet Thing. */
public final class FleetMaterializer implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(FleetMaterializer.class);
    private final FleetService fleet;
    private final RestClient client;
    private final URI target;
    private final Duration timeout;
    private final Clock clock;
    private final ExecutorService writes = Executors.newVirtualThreadPerTaskExecutor();
    private final AtomicBoolean running = new AtomicBoolean();
    private final AtomicLong failures = new AtomicLong();
    private volatile Instant lastSuccess;
    private final JsonMapper json = JsonMapper.builder().build();

    public FleetMaterializer(FleetService fleet, RestClient client, URI baseUrl, Duration timeout, Clock clock) {
        this.fleet = fleet; this.client = client; this.timeout = timeout; this.clock = clock;
        this.target = URI.create(baseUrl.toString().replaceAll("/+$", "") + "/api/2/things/sdv:fleet-v1/features/summary/properties");
    }

    @Scheduled(fixedDelayString = "${sdv.v1.fleet.interval:2s}", initialDelayString = "${sdv.v1.fleet.initial-delay:2s}")
    public void update() {
        if (!running.compareAndSet(false, true)) return;
        Future<Boolean> pending = null;
        try {
            // Recompute from individual observations on every attempt, never replay a stale cached summary.
            byte[] body = json.writeValueAsBytes(fleet.read());
            pending = writes.submit(() -> client.put().uri(target).contentType(MediaType.APPLICATION_JSON)
                    .contentLength(body.length).body(body).exchange((request, response) -> {
                        int status = response.getStatusCode().value();
                        if (status == 401 || status == 403) LOG.error("fleet_write_failed code=AUTH_CONFIGURATION status={}", status);
                        else if (status < 200 || status >= 300) LOG.warn("fleet_write_failed code=HTTP_STATUS status={}", status);
                        return status == 200 || status == 201 || status == 204;
                    }));
            if (pending.get(timeout.toNanos(), TimeUnit.NANOSECONDS)) {
                lastSuccess = clock.instant();
                LOG.info("fleet_write_succeeded thing=sdv:fleet-v1");
            } else failed("HTTP_STATUS");
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt(); failed("INTERRUPTED");
        } catch (TimeoutException timeoutError) {
            failed("TIMEOUT");
        } catch (ExecutionException | RuntimeException error) {
            // Do not leak credential-bearing exception text or response bodies.
            failed("TRANSPORT_OR_SERIALIZATION");
        } finally {
            if (pending != null && !pending.isDone()) pending.cancel(true);
            running.set(false);
        }
    }

    private void failed(String code) { failures.incrementAndGet(); LOG.warn("fleet_write_failed code={} retry=NEXT_INTERVAL", code); }
    public long failureCount() { return failures.get(); }
    public Instant lastSuccess() { return lastSuccess; }
    @Override public void close() { writes.shutdownNow(); }
}
