package com.ankit.sdv.backend.controller;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc

class FleetControllerTest {
    static final Instant NOW = Instant.parse("2026-01-01T00:00:04Z");
    static final Map<String, Reply> replies = new ConcurrentHashMap<>();
    static final AtomicInteger requests = new AtomicInteger();
    static HttpServer ditto;
    static java.util.concurrent.ExecutorService executor;
    @org.springframework.test.context.bean.override.convention.TestBean(methodName = "fleetClock") Clock systemClock;
    static Clock fleetClock() { return Clock.fixed(NOW, ZoneOffset.UTC); }
    @Autowired MockMvc mvc;
    @Autowired ObjectMapper json;

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry properties) throws Exception {
        ditto = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        executor = java.util.concurrent.Executors.newVirtualThreadPerTaskExecutor();
        ditto.setExecutor(executor);
        ditto.createContext("/api/2/things/", exchange -> {
            requests.incrementAndGet();
            assertThat(exchange.getRequestMethod()).isEqualTo("GET");
            assertThat(exchange.getRequestHeaders().getFirst("Accept")).isEqualTo("application/json");
            assertThat(exchange.getRequestHeaders().getFirst("Authorization")).isEqualTo("Basic " +
                    java.util.Base64.getEncoder().encodeToString("review-user:test-only-pass".getBytes(StandardCharsets.UTF_8)));
            String id = exchange.getRequestURI().getPath().substring("/api/2/things/sdv:".length());
            Reply reply = replies.getOrDefault(id, new Reply(404, "{}"));
            if (reply.status() == 599) {
                exchange.sendResponseHeaders(200, 1000);
                try { Thread.sleep(1500); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
                exchange.close(); return;
            }
            byte[] bytes = reply.body().getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().set("Content-Type", "application/json");
            exchange.sendResponseHeaders(reply.status(), bytes.length);
            try (var out = exchange.getResponseBody()) { out.write(bytes); }
            exchange.close();
        });
        ditto.start();
        properties.add("sdv.v1.ditto.read-timeout", () -> "200ms");
        properties.add("sdv.v1.ditto.mode", () -> "mock");
        properties.add("sdv.v1.ditto.username", () -> "review-user");
        properties.add("sdv.v1.ditto.password", () -> "test-only-pass");
        properties.add("sdv.v1.ditto.base-url", () -> "http://127.0.0.1:" + ditto.getAddress().getPort());
    }

    @AfterAll static void stop() { ditto.stop(0); executor.shutdownNow(); }
    @BeforeEach void reset() throws Exception {
        requests.set(0);
        for (String id : new String[]{"vehicle-001", "vehicle-002"}) {
            replies.put(id, new Reply(200, fixture(id)));
        }
    }
    static String fixture(String id) throws Exception {
        return Files.readString(Path.of("../tests/fixtures/v1/ditto-" + id + ".json"));
    }
    JsonNode read(String id, String endpoint) throws Exception {
        String body = mvc.perform(get("/api/v1/vehicles/{id}/{endpoint}", id, endpoint))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        return json.readTree(body);
    }
    void assertNoSnapshot(JsonNode response) {
        assertThat(response.path("availability").asText()).isEqualTo("UNAVAILABLE");
        for (String key : new String[]{"healthStatus", "activeFaults", "lidar", "sourceTimestamp", "lastEventId"}) {
            assertThat(response.has(key)).as(key + " must be explicitly null").isTrue();
            assertThat(response.get(key).isNull()).as(key).isTrue();
        }
    }

    JsonNode fleet() throws Exception {
        String body = mvc.perform(get("/api/v1/fleet")).andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();
        JsonNode view = json.readTree(body);
        assertThat(view.path("generatedAt").asText()).isEqualTo(NOW.toString());
        assertThat(view.path("totalVehicles").asInt()).isEqualTo(2);
        assertThat(view.path("availableVehicles").asInt() + view.path("staleVehicles").asInt()
                + view.path("unavailableVehicles").asInt()).isEqualTo(2);
        assertThat(view.path("healthyVehicles").asInt() + view.path("warningVehicles").asInt()
                + view.path("criticalVehicles").asInt()).isEqualTo(view.path("availableVehicles").asInt());
        assertThat(view.at("/vehicles/0/vehicleId").asText()).isEqualTo("vehicle-001");
        assertThat(view.at("/vehicles/1/vehicleId").asText()).isEqualTo("vehicle-002");
        return view;
    }
    @Test void canonicalHealthyFleetProjection() throws Exception {
        assertThat(fleet()).isEqualTo(json.readTree(Files.readString(Path.of("../tests/fixtures/v1/fleet-summary.json"))));
        assertThat(requests).hasValue(2);
    }
    @ParameterizedTest @CsvSource({"HEALTHY,35,healthyVehicles", "WARNING,8,warningVehicles", "CRITICAL,3,criticalVehicles"})
    void faultWarningAndRecoveryCountOnlyCurrentHealth(String health, int distance, String counter) throws Exception {
        String body = fixture("vehicle-002").replace("\"HEALTHY\"", "\"" + health + "\"")
                .replace("35.0", Integer.toString(distance));
        if (!health.equals("HEALTHY")) body = body.replace("\"faults\": []", "\"faults\": [\"LIDAR_OBSTRUCTION\"]");
        replies.put("vehicle-002", new Reply(200, body));
        var result = fleet();
        assertThat(result.path(counter).asInt()).isEqualTo(health.equals("HEALTHY") ? 2 : 1);
        assertThat(result.at("/vehicles/1/healthStatus").asText()).isEqualTo(health);
    }
    @ParameterizedTest @CsvSource({"-1000000001,UNAVAILABLE", "-1000000000,AVAILABLE", "5000000000,AVAILABLE",
            "5000000001,STALE", "30000000000,STALE", "30000000001,UNAVAILABLE"})
    void boundariesExcludeStaleAndUnavailableFromHealthCounts(long age, String availability) throws Exception {
        replies.put("vehicle-002", new Reply(200, fixture("vehicle-002").replace("2026-01-01T00:00:00Z", NOW.minusNanos(age).toString())));
        var result = fleet();
        assertThat(result.at("/vehicles/1/availability").asText()).isEqualTo(availability);
        assertThat(result.path("healthyVehicles").asInt()).isEqualTo(availability.equals("AVAILABLE") ? 2 : 1);
        if (availability.equals("STALE")) assertThat(result.at("/vehicles/1/healthStatus").asText()).isEqualTo("HEALTHY");
        if (age < -1_000_000_000L) assertNoSnapshot(result.at("/vehicles/1"));
    }
    @ParameterizedTest @ValueSource(ints = {404, 503, 599})
    void missingFailedOrStalledBodyDoesNotSuppressOtherVehicle(int status) throws Exception {
        replies.put("vehicle-001", new Reply(status, "{}"));
        long start = System.nanoTime();
        var result = fleet();
        assertThat(Duration.ofNanos(System.nanoTime() - start)).isLessThan(Duration.ofSeconds(1));
        assertNoSnapshot(result.at("/vehicles/0"));
        assertThat(result.at("/vehicles/1/availability").asText()).isEqualTo("AVAILABLE");
        assertThat(result.path("healthyVehicles").asInt()).isEqualTo(1);
    }
    record Reply(int status, String body) {}
}
