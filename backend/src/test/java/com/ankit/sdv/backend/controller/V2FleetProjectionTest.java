package com.ankit.sdv.backend.controller;

import com.ankit.sdv.backend.service.FleetMaterializer;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.convention.TestBean;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ObjectNode;

import java.net.InetSocketAddress;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.*;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = {
        "sdv.v1.fleet.enabled=true", "sdv.v1.fleet.version=v2",
        "sdv.v1.fleet.username=writer", "sdv.v1.fleet.password=test-only",
        "sdv.v1.fleet.initial-delay=1h"
})
@AutoConfigureMockMvc
class V2FleetProjectionTest {
    private static final List<String> VEHICLES = List.of("vehicle-001", "vehicle-002", "vehicle-003");
    private static final String THINGS = "/api/2/things/sdv:";
    private static final String TARGET = THINGS + "fleet-v2/features/summary/properties";
    private static final Instant SOURCE = Instant.parse("2026-01-01T00:00:00Z");
    private static final Path FIXTURES = Path.of("../tests/fixtures/v2");
    private static final AtomicReference<Instant> now = new AtomicReference<>(SOURCE);
    private static final Map<String, byte[]> twins = new ConcurrentHashMap<>();
    private static final Map<String, Integer> statuses = new ConcurrentHashMap<>();
    private static final AtomicReference<String> unexpectedWrite = new AtomicReference<>();
    private static volatile byte[] written;
    private static HttpServer ditto;
    private static ExecutorService executor;

    @Autowired ObjectMapper json;
    @Autowired MockMvc mvc;
    @Autowired FleetMaterializer writer;
    @TestBean(methodName = "testClock") Clock systemClock;

    static Clock testClock() {
        return ((InstantSource) now::get).withZone(ZoneOffset.UTC);
    }

    @DynamicPropertySource
    static void configure(DynamicPropertyRegistry props) throws Exception {
        ditto = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        executor = Executors.newVirtualThreadPerTaskExecutor();
        ditto.setExecutor(executor);
        ditto.createContext("/api/2/things/", request -> {
            try (request) {
                String path = request.getRequestURI().getPath();
                if ("PUT".equals(request.getRequestMethod())) {
                    if (!TARGET.equals(path)) unexpectedWrite.set(path);
                    written = request.getRequestBody().readAllBytes();
                    request.sendResponseHeaders(statuses.getOrDefault(path, 204), -1);
                    return;
                }
                byte[] body = twins.get(path);
                int code = statuses.getOrDefault(path, body == null ? 404 : 200);
                request.sendResponseHeaders(code, code == 200 ? body.length : -1);
                if (code == 200) request.getResponseBody().write(body);
            }
        });
        ditto.start();
        props.add("sdv.v1.ditto.base-url", () -> "http://127.0.0.1:" + ditto.getAddress().getPort());
    }

    @BeforeEach
    void fixtures() throws Exception {
        twins.clear();
        statuses.clear();
        unexpectedWrite.set(null);
        written = null;
        now.set(SOURCE);
        for (String id : VEHICLES) twins.put(THINGS + id, Files.readAllBytes(FIXTURES.resolve("twins/" + id + ".json")));
    }

    @AfterAll
    static void stop() {
        ditto.stop(0);
        executor.shutdownNow();
    }

    @Test
    void listsExactlyThreeAndPreservesIdentityAndRecovery() throws Exception {
        assertThat(read("/api/v2/vehicles").get("vehicleIds")).isEqualTo(json.valueToTree(VEHICLES));
        for (String id : VEHICLES) {
            var state = state(id);
            assertThat(state.get("vehicleId").asText()).isEqualTo(id);
            assertThat(state.get("thingId").asText()).isEqualTo("sdv:" + id);
            assertThat(state.get("lastEventId").asText()).isEqualTo(id + "-s1-0");
        }
        mvc.perform(get("/api/v2/vehicles/vehicle-004/state")).andExpect(status().isNotFound());
        var thing = thing("vehicle-002");
        var recovered = (ObjectNode) json.readTree(Files.readAllBytes(FIXTURES.resolve("health-events/recovery-sensor-failure.json")));
        recovered.set("lastEventId", recovered.remove("eventId"));
        ((ObjectNode) thing.at("/features/v2")).set("properties", recovered);
        save("vehicle-002", thing);
        var state = state("vehicle-002");
        assertThat(state.get("healthStatus").asText()).isEqualTo("CRITICAL");
        assertThat(state.get("recoveryState").asText()).isEqualTo("IN_PROGRESS");
        assertThat(state.get("activeFaults").get(0).asText()).isEqualTo("LIDAR_SENSOR_FAILURE");
        assertThat(state.at("/lidar/sensorAvailable").booleanValue()).isTrue();
        assertThat(state.get("sessionGeneration").asInt()).isEqualTo(1);
        assertThat(state.get("frame").asInt()).isEqualTo(100);
        var silent = thing("vehicle-003");
        ((ObjectNode) silent.at("/features/v2/properties")).put("sourceSilent", true);
        save("vehicle-003", silent);
        writer.update();
        var fleet = read("/api/v2/fleet");
        assertThat(fleet.get("availableVehicles").asInt()).isEqualTo(3);
        assertThat(fleet.get("criticalVehicles").asInt()).isEqualTo(1);
        assertThat(fleet.at("/vehicles/2/sourceSilent").booleanValue()).isTrue();
    }

    @Test
    void preservesLastAcceptedObservationAndCriticalFaultAfterRecoveryReset() throws Exception {
        fault("vehicle-002", 20, "CRITICAL");

        var state = state("vehicle-002");
        assertThat(state.get("availability").asText()).isEqualTo("AVAILABLE");
        assertThat(state.get("healthStatus").asText()).isEqualTo("CRITICAL");
        assertThat(state.get("activeFaults")).isEqualTo(json.valueToTree(List.of("LIDAR_OBSTRUCTION")));
        assertThat(state.get("recoveryState").asText()).isEqualTo("NONE");
        assertThat(state.get("recoveryStartedAt").isNull()).isTrue();
        assertThat(state.at("/lidar/distanceMeters").asInt()).isEqualTo(20);
        assertThat(state.get("lastEventId").asText()).isEqualTo("vehicle-002-s1-0");
        assertThat(state.get("sourceTimestamp").asText()).isEqualTo("2026-01-01T00:00:00.000Z");
    }

    @ParameterizedTest
    @CsvSource({
            "warning-stale, WARNING, LIDAR_OBSTRUCTION",
            "warning-future, WARNING, LIDAR_OBSTRUCTION",
            "sensor-stale, CRITICAL, LIDAR_SENSOR_FAILURE",
            "sensor-future, CRITICAL, LIDAR_SENSOR_FAILURE"
    })
    void projectsProducerSnapshotsAfterClockRejection(String scenario, String severity,
                                                     String faultCode) throws Exception {
        var snapshots = json.readTree(Files.readAllBytes(FIXTURES.resolve("twins/retained-fault-resets.json")))
                .get(scenario);
        var thing = thing("vehicle-002");
        var feature = (ObjectNode) thing.at("/features/v2");
        for (int stage = 0; stage < 3; stage++) {
            var props = snapshots.get(stage);
            feature.set("properties", props);
            save("vehicle-002", thing);
            now.set(Instant.parse(props.get("sourceTimestamp").asText()));
            var state = state("vehicle-002");
            assertThat(state.get("availability").asText()).as("stage %d", stage).isEqualTo("AVAILABLE");
            assertThat(state.get("healthStatus").asText()).isEqualTo(stage == 2 ? "HEALTHY" : severity);
            assertThat(state.get("activeFaults"))
                    .isEqualTo(json.valueToTree(stage == 2 ? List.of() : List.of(faultCode)));
            assertThat(state.get("recoveryState").asText()).isEqualTo(stage == 1 ? "IN_PROGRESS" : "NONE");
            assertThat(state.get("recoveryStartedAt")).isEqualTo(props.get("recoveryStartedAt"));
            assertThat(state.at("/lidar/distanceMeters").asInt()).isEqualTo(20);
            for (String field : List.of("lastEventId", "sourceTimestamp", "sessionId", "sessionGeneration",
                    "sequence", "frame")) {
                assertThat(state.get(field)).as(field).isEqualTo(props.get(field));
            }
        }
    }

    @ParameterizedTest
    @CsvSource({
            "20, HEALTHY, LIDAR_OBSTRUCTION,",
            "20, CRITICAL, LIDAR_OBSTRUCTION, 2026-01-01T00:00:00Z",
            "20, WARNING, LIDAR_SENSOR_FAILURE,",
            "20, WARNING, UNKNOWN_FAULT,",
            "8, CRITICAL, LIDAR_SENSOR_FAILURE,",
            "20, CRITICAL, UNKNOWN_FAULT,",
            "8, CRITICAL, LIDAR_OBSTRUCTION,"
    })
    void rejectsInvalidRecoveryResetSnapshots(int distance, String health, String faultCode,
                                              String recoveryStartedAt) throws Exception {
        fault("vehicle-002", distance, health);
        var thing = thing("vehicle-002");
        var props = (ObjectNode) thing.at("/features/v2/properties");
        props.putArray("faults").add(faultCode);
        props.put("recoveryStartedAt", recoveryStartedAt);
        save("vehicle-002", thing);

        var state = state("vehicle-002");
        assertThat(state.get("availability").asText()).isEqualTo("UNAVAILABLE");
        assertThat(state.get("healthStatus").isNull()).isTrue();
    }

    @Test
    void freshnessIsDerivedAtExactBoundaries() throws Exception {
        assertAvailability(SOURCE.minusSeconds(1), "AVAILABLE", false);
        assertAvailability(SOURCE.minusSeconds(1).minusNanos(1), "UNAVAILABLE", true);
        assertAvailability(SOURCE.plusSeconds(5), "AVAILABLE", false);
        assertAvailability(SOURCE.plusSeconds(5).plusNanos(1), "STALE", false);
        assertAvailability(SOURCE.plusSeconds(30), "STALE", false);
        assertAvailability(SOURCE.plusSeconds(30).plusNanos(1), "UNAVAILABLE", false);
    }

    @Test
    void malformedMissingAndFailedReadAreIsolated() throws Exception {
        var thing = thing("vehicle-001");
        ((ObjectNode) thing.at("/features/v2/properties")).put("vehicleId", "vehicle-002");
        save("vehicle-001", thing);
        statuses.put(THINGS + "vehicle-002", 403);
        twins.remove(THINGS + "vehicle-003");
        for (String id : VEHICLES) {
            var state = state(id);
            assertThat(state.get("availability").asText()).isEqualTo("UNAVAILABLE");
            for (String field : List.of("lastEventId", "sourceTimestamp", "lidar", "healthStatus",
                    "sessionId", "sourceSilent", "recoveryState", "activeFaults")) {
                assertThat(state.get(field).isNull()).as(field).isTrue();
            }
        }
        writer.update();
        assertCounts(read("/api/v2/fleet"), 2);
    }

    @Test
    void materializesOneSnapshotAndKeepsReadsOnFailure() throws Exception {
        fault("vehicle-002", 8, "WARNING");
        fault("vehicle-003", 3, "CRITICAL");
        writer.update();
        JsonNode first = json.readTree(written);
        now.set(SOURCE.plusSeconds(6));
        assertThat(read("/api/v2/fleet")).isEqualTo(first);
        assertCounts(first, 0);
        assertThat(first.get("vehicles").valueStream().map(v -> v.get("vehicleId").asText()).toList())
                .containsExactlyElementsOf(VEHICLES);

        var fresh = thing("vehicle-001");
        ((ObjectNode) fresh.at("/features/v2/properties")).put("sourceTimestamp", now.get().toString());
        save("vehicle-001", fresh);
        fault("vehicle-002", 20, "HEALTHY");
        var stale = thing("vehicle-002");
        ((ObjectNode) stale.at("/features/v2/properties")).putArray("faults");
        save("vehicle-002", stale);
        var aged = thing("vehicle-003");
        ((ObjectNode) aged.at("/features/v2/properties")).put("sourceTimestamp", SOURCE.minusSeconds(30).toString());
        save("vehicle-003", aged);
        statuses.put(TARGET, 503);
        var failures = writer.failureCount();
        writer.update();
        assertThat(writer.failureCount()).isEqualTo(failures + 1);
        var next = read("/api/v2/fleet");
        assertThat(next).isEqualTo(json.readTree(written));
        assertCounts(next, 1);
        assertThat(state("vehicle-001").get("availability").asText()).isEqualTo("AVAILABLE");
        assertThat(state("vehicle-003").get("healthStatus").asText()).isEqualTo("CRITICAL");
        assertThat(unexpectedWrite.get()).isNull();
    }

    private void assertAvailability(Instant evaluation, String expected, boolean noTrustedState) throws Exception {
        now.set(evaluation);
        var state = state("vehicle-001");
        assertThat(state.get("availability").asText()).isEqualTo(expected);
        assertThat(state.get("sourceTimestamp").isNull()).isEqualTo(noTrustedState);
    }

    private void assertCounts(JsonNode fleet, int index) throws Exception {
        var counts = json.readTree(Files.readAllBytes(FIXTURES.resolve("twins/fleet-cases.json")))
                .get("cases").get(index).get("expected");
        List<String> fields = List.of("totalVehicles", "availableVehicles", "staleVehicles",
                "unavailableVehicles", "healthyVehicles", "warningVehicles", "criticalVehicles");
        for (int i = 0; i < fields.size(); i++) assertThat(fleet.get(fields.get(i))).isEqualTo(counts.get(i));
    }

    private void fault(String vehicle, int distance, String health) throws Exception {
        var thing = thing(vehicle);
        ObjectNode props = (ObjectNode) thing.at("/features/v2/properties");
        props.put("health", health).putArray("faults").add("LIDAR_OBSTRUCTION");
        ((ObjectNode) props.get("lidar")).put("distanceMeters", distance);
        save(vehicle, thing);
    }

    private ObjectNode thing(String id) { return (ObjectNode) json.readTree(twins.get(THINGS + id)); }
    private void save(String id, ObjectNode thing) { twins.put(THINGS + id, json.writeValueAsBytes(thing)); }
    private JsonNode state(String id) throws Exception { return read("/api/v2/vehicles/" + id + "/state"); }
    private JsonNode read(String route) throws Exception {
        return json.readTree(mvc.perform(get(route)).andExpect(status().isOk()).andReturn().getResponse().getContentAsByteArray());
    }
}
