package com.ankit.sdv.backend.controller;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import com.ankit.sdv.backend.service.FleetMaterializer;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.convention.TestBean;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.ObjectMapper;

import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class FleetMaterializationTest {
    static HttpServer ditto;
    static ExecutorService executor;
    static final AtomicInteger status = new AtomicInteger(204);
    static final AtomicInteger writes = new AtomicInteger();
    static volatile String body, auth, method;
    static volatile CountDownLatch entered, release;
    @Autowired FleetMaterializer writer;
    @Autowired MockMvc mvc;
    @Autowired ObjectMapper json;
    @TestBean(methodName = "fixedClock") Clock systemClock;
    static Clock fixedClock() { return Clock.fixed(Instant.parse("2026-01-01T00:00:04Z"), ZoneOffset.UTC); }

    @DynamicPropertySource static void configure(DynamicPropertyRegistry props) throws Exception {
        ditto = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        executor = Executors.newVirtualThreadPerTaskExecutor();
        ditto.setExecutor(executor);
        ditto.createContext("/api/2/things/", exchange -> {
            String path = exchange.getRequestURI().getPath();
            if (path.equals("/api/2/things/sdv:fleet-v1/features/summary/properties")) {
                writes.incrementAndGet();
                method = exchange.getRequestMethod();
                auth = exchange.getRequestHeaders().getFirst("Authorization");
                body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
                if (entered != null) { entered.countDown(); try { release.await(3, TimeUnit.SECONDS); }
                    catch (InterruptedException e) { Thread.currentThread().interrupt(); } }
                exchange.sendResponseHeaders(status.get(), -1);
            } else {
                String vehicle = path.substring("/api/2/things/sdv:".length());
                byte[] fixture = Files.readAllBytes(Path.of("../tests/fixtures/v1/ditto-" + vehicle + ".json"));
                exchange.getResponseHeaders().set("Content-Type", "application/json");
                exchange.sendResponseHeaders(200, fixture.length);
                exchange.getResponseBody().write(fixture);
            }
            exchange.close();
        });
        ditto.start();
        props.add("sdv.v1.ditto.base-url", () -> "http://127.0.0.1:" + ditto.getAddress().getPort());
        props.add("sdv.v1.fleet.enabled", () -> "true");
        props.add("sdv.v1.fleet.username", () -> "fleet-service");
        props.add("sdv.v1.fleet.password", () -> "test-only-password");
        props.add("sdv.v1.fleet.initial-delay", () -> "1h");
        props.add("sdv.v1.fleet.interval", () -> "1h");
        props.add("sdv.v1.fleet.write-timeout", () -> "300ms");
    }
    @AfterAll static void stop() { ditto.stop(0); executor.shutdownNow(); }
    @BeforeEach void reset() { writes.set(0); status.set(204); body = null; entered = null; release = null; }
    void update() { writer.update(); }
    String fleet() throws Exception { return mvc.perform(get("/api/v1/fleet")).andExpect(status().isOk())
            .andReturn().getResponse().getContentAsString(); }

    @ParameterizedTest @ValueSource(ints = {200, 201, 204})
    void writesExactApiProjectionWithServiceAuthentication(int code) throws Exception {
        status.set(code); update();
        assertThat(writes).hasValue(1);
        assertThat(method).isEqualTo("PUT");
        assertThat(auth).isEqualTo("Basic " + java.util.Base64.getEncoder().encodeToString("fleet-service:test-only-password".getBytes(StandardCharsets.UTF_8)));
        assertThat(json.readTree(body)).isEqualTo(json.readTree(fleet()));
    }
    @ParameterizedTest @ValueSource(ints = {401, 403, 500, 503})
    void failurePreservesApiAndNextScheduledAttemptCanRecover(int code) throws Exception {
        status.set(code); update();
        assertThat(writes).hasValue(1); // no immediate retry
        assertThat(json.readTree(fleet()).path("healthyVehicles").asInt()).isEqualTo(2);
        assertThat(writer.failureCount()).isGreaterThan(0);
        status.set(204); update();
        assertThat(writes).hasValue(2);
        assertThat(writer.lastSuccess()).isEqualTo(fixedClock().instant());
    }
    @Test void concurrentTriggersDoNotOverlapAndStalledWriteIsBounded() throws Exception {
        entered = new CountDownLatch(1); release = new CountDownLatch(1);
        try (var callers = Executors.newVirtualThreadPerTaskExecutor()) {
            long start = System.nanoTime();
            var first = callers.submit(() -> { update(); return null; });
            assertThat(entered.await(2, TimeUnit.SECONDS)).isTrue();
            update();
            first.get(2, TimeUnit.SECONDS);
            assertThat(Duration.ofNanos(System.nanoTime() - start)).isLessThan(Duration.ofSeconds(2));
            assertThat(writes).hasValue(1);
            assertThat(writer.failureCount()).isGreaterThan(0);
        } finally { release.countDown(); }
    }
}
