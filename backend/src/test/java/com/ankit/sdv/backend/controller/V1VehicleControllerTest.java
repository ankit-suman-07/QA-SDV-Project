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
@Import(V1VehicleControllerTest.FixedClock.class)
class V1VehicleControllerTest {
    static final Instant NOW = Instant.parse("2026-01-01T00:00:04Z");
    static final Map<String, Reply> replies = new ConcurrentHashMap<>();
    static final AtomicInteger requests = new AtomicInteger();
    static HttpServer ditto;
    @Autowired MockMvc mvc;
    @Autowired ObjectMapper json;

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry properties) throws Exception {
        ditto = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        ditto.createContext("/api/2/things/", exchange -> {
            requests.incrementAndGet();
            assertThat(exchange.getRequestMethod()).isEqualTo("GET");
            assertThat(exchange.getRequestHeaders().getFirst("Accept")).isEqualTo("application/json");
            String id = exchange.getRequestURI().getPath().substring("/api/2/things/sdv:".length());
            Reply reply = replies.getOrDefault(id, new Reply(404, "{}"));
            byte[] bytes = reply.body().getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().set("Content-Type", "application/json");
            exchange.sendResponseHeaders(reply.status(), bytes.length);
            try (var out = exchange.getResponseBody()) { out.write(bytes); }
            exchange.close();
        });
        ditto.start();
        properties.add("sdv.v1.ditto.mode", () -> "mock");
        properties.add("sdv.v1.ditto.base-url", () -> "http://127.0.0.1:" + ditto.getAddress().getPort());
    }

    @AfterAll static void stop() { ditto.stop(0); }
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

    @Test void listsOnlyTheTwoV1VehiclesWithoutReadingDitto() throws Exception {
        mvc.perform(get("/api/v1/vehicles")).andExpect(status().isOk())
                .andExpect(content().json("{\"vehicleIds\":[\"vehicle-001\",\"vehicle-002\"]}"));
        assertThat(requests).hasValue(0);
    }
    @ParameterizedTest @ValueSource(strings = {"vehicle-001", "vehicle-002"})
    void stateAndHealthUseTheSameTrustedProjection(String id) throws Exception {
        JsonNode state = read(id, "state");
        assertThat(state).isEqualTo(read(id, "health"));
        assertThat(state.path("vehicleId").asText()).isEqualTo(id);
        assertThat(state.path("thingId").asText()).isEqualTo("sdv:" + id);
        assertThat(state.path("sourceTimestamp").asText()).isEqualTo("2026-01-01T00:00:00Z");
        assertThat(state.path("lastEventId").asText()).isEqualTo(id + "-event-000");
        assertThat(state.path("healthStatus").asText()).isEqualTo("HEALTHY");
        assertThat(state.path("availability").asText()).isEqualTo("AVAILABLE");
        assertThat(state.path("activeFaults").isArray()).isTrue();
        assertThat(state.path("activeFaults").size()).isZero();
        assertThat(state.path("lidar").path("distanceMeters").asDouble()).isEqualTo(35);
    }
    @ParameterizedTest @ValueSource(strings = {"vehicle-999", "vehicle-003", " vehicle-001", "vehicle-001 "})
    void unknownIdsDoNotReadOrUseLegacyRegistry(String id) throws Exception {
        mvc.perform(get("/api/v1/vehicles/{id}/state", id)).andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/vehicles/{id}/health", id)).andExpect(status().isNotFound());
        assertThat(requests).hasValue(0);
    }
    @ParameterizedTest
    @CsvSource({"-1000000001,UNAVAILABLE", "-1000000000,AVAILABLE", "0,AVAILABLE",
            "5000000000,AVAILABLE", "5000000001,STALE", "30000000000,STALE", "30000000001,UNAVAILABLE"})
    void exactSourceAgeBoundaries(long ageNanos, String availability) throws Exception {
        String timestamp = NOW.minusNanos(ageNanos).toString();
        replies.put("vehicle-002", new Reply(200, fixture("vehicle-002").replace("2026-01-01T00:00:00Z", timestamp)));
        JsonNode state = read("vehicle-002", "state");
        assertThat(state.path("availability").asText()).isEqualTo(availability);
        if (ageNanos < -1_000_000_000L) assertNoSnapshot(state);
        else { // A valid old snapshot remains trustworthy last-known data, even past 30 seconds.
            assertThat(state.path("sourceTimestamp").asText()).isEqualTo(timestamp);
            assertThat(state.path("healthStatus").asText()).isEqualTo("HEALTHY");
        }
    }
    @ParameterizedTest @ValueSource(ints = {201, 204, 301, 400, 401, 403, 404, 408, 429, 500, 502, 503})
    void unsuccessfulReadCannotReturnGeneratedHealth(int status) throws Exception {
        replies.put("vehicle-002", new Reply(status, "{\"password\":\"must-not-leak\"}"));
        assertNoSnapshot(read("vehicle-002", "state"));
        assertThat(read("vehicle-001", "state").path("availability").asText()).isEqualTo("AVAILABLE");
    }
    @ParameterizedTest @ValueSource(strings = {"{", "[]", "null", "{}", "{\"thingId\":\"wrong\"}"})
    void malformedSnapshotsHaveExplicitNullFields(String body) throws Exception {
        replies.put("vehicle-002", new Reply(200, body));
        assertNoSnapshot(read("vehicle-002", "state"));
    }
    @Test void faultsAndRecoveryAreIsolatedAndSensorFailureIsStillAvailable() throws Exception {
        for (String name : new String[]{"vehicle-002-fault", "vehicle-002-recovered"}) {
            String event = Files.readString(Path.of("../tests/fixtures/v1/" + name + ".json"));
            JsonNode props = json.readTree(event);
            var mutable = (tools.jackson.databind.node.ObjectNode) props;
            mutable.set("lastEventId", mutable.remove("eventId"));
            String thing = "{\"thingId\":\"sdv:vehicle-002\",\"attributes\":{\"vehicleId\":\"vehicle-002\"},\"features\":{\"v1\":{\"properties\":" + props + "}}}";
            replies.put("vehicle-002", new Reply(200, thing));
            assertThat(read("vehicle-002", "state").path("healthStatus").asText()).isEqualTo(props.path("health").asText());
            assertThat(read("vehicle-001", "state").path("healthStatus").asText()).isEqualTo("HEALTHY");
        }
        String failure = fixture("vehicle-002").replace("\"HEALTHY\"", "\"CRITICAL\"")
                .replace("\"faults\": []", "\"faults\": [\"LIDAR_SENSOR_FAILURE\"]")
                .replace("\"distanceMeters\": 35.0", "\"distanceMeters\": null")
                .replace("\"sensorAvailable\": true", "\"sensorAvailable\": false");
        replies.put("vehicle-002", new Reply(200, failure));
        JsonNode state = read("vehicle-002", "health");
        assertThat(state.path("availability").asText()).isEqualTo("AVAILABLE");
        assertThat(state.path("healthStatus").asText()).isEqualTo("CRITICAL");
    }
    record Reply(int status, String body) {}
    @TestConfiguration static class FixedClock {
        @Bean @Primary Clock v1TestClock() { return Clock.fixed(NOW, ZoneOffset.UTC); }
    }
}
