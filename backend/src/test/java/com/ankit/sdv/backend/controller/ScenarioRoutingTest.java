package com.ankit.sdv.backend.controller;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.convention.TestBean;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;
import tools.jackson.databind.node.ObjectNode;

import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class ScenarioRoutingTest {
    static final String ROUTE = "/api/v1/diagnostics/actions";
    static final Map<String, HttpServer> servers = new HashMap<>();
    static final Map<String, AtomicInteger> counts = new ConcurrentHashMap<>();
    static final Map<String, String> modes = new ConcurrentHashMap<>();
    static final Map<String, JsonNode> received = new ConcurrentHashMap<>();
    static final ExecutorService executor = Executors.newCachedThreadPool();
    static final JsonMapper json = JsonMapper.builder().build();
    static volatile CountDownLatch release = new CountDownLatch(1);
    @Autowired MockMvc mvc;
    @TestBean(name = "systemClock", methodName = "fixedClock") Clock testClock;
    static Clock fixedClock() { return Clock.fixed(Instant.parse("2026-01-01T00:00:04Z"), ZoneOffset.UTC); }

    @DynamicPropertySource static void properties(DynamicPropertyRegistry props) throws Exception {
        for (String vehicle : List.of("vehicle-001", "vehicle-002")) {
            counts.put(vehicle, new AtomicInteger());
            var server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            server.setExecutor(executor);
            server.createContext("/edge/api/v1/scenarios/actions", exchange -> {
                counts.get(vehicle).incrementAndGet();
                JsonNode request = json.readTree(exchange.getRequestBody().readAllBytes());
                received.put(vehicle, request);
                String mode = modes.getOrDefault(vehicle, "ok");
                try {
                    if (mode.equals("reset")) return;
                    if (mode.equals("timeout")) release.await(3, TimeUnit.SECONDS);
                    ObjectNode ack = (ObjectNode) request.deepCopy();
                    ack.put("active", request.path("action").asText().equals("INJECT_SCENARIO"));
                    switch (mode) {
                        case "vehicleId" -> ack.put("vehicleId", "vehicle-999");
                        case "action" -> ack.put("action", "WRONG");
                        case "scenario" -> ack.put("scenario", "WRONG");
                        case "actionId" -> ack.put("actionId", "wrong");
                        case "traceId" -> ack.put("traceId", "wrong");
                        case "active" -> ack.put("active", !ack.get("active").asBoolean());
                        case "activeType" -> ack.put("active", "true");
                        case "missing" -> ack.remove("vehicleId");
                        default -> { }
                    }
                    String body = mode.equals("malformed") ? "{private-provider-secret" : mode.equals("array") ? "[]"
                            : mode.equals("null") ? "null" : mode.equals("trailing") ? ack + " {}"
                            : mode.equals("duplicate") ? ack.toString().replace("\"active\":", "\"active\":false,\"active\":") : ack.toString();
                    int code = mode.equals("reject") ? 409 : mode.equals("unauthorized") ? 401
                            : mode.equals("serverError") ? 503 : mode.equals("gatewayTimeout") ? 504
                            : mode.equals("redirect") ? 307 : 200;
                    byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
                    exchange.getResponseHeaders().set("Content-Type", "application/json");
                    exchange.sendResponseHeaders(code, bytes.length);
                    if (mode.equals("bodyTimeout")) {
                        exchange.getResponseBody().write(bytes, 0, 1);
                        exchange.getResponseBody().flush();
                        release.await(3, TimeUnit.SECONDS);
                    } else exchange.getResponseBody().write(bytes);
                } catch (InterruptedException error) { Thread.currentThread().interrupt(); }
                catch (java.io.IOException ignored) { /* Client timed out/closed this test response. */ }
                finally { exchange.close(); }
            });
            server.start();
            servers.put(vehicle, server);
            String url = "http://127.0.0.1:" + server.getAddress().getPort() + "/edge";
            props.add("sdv.simulator.providers[" + vehicle + "]", () -> url);
            if (vehicle.equals("vehicle-001")) props.add("sdv.simulator.base-url", () -> url);
        }
        props.add("sdv.simulator.mode", () -> "http");
        props.add("sdv.simulator.connect-timeout", () -> "2s");
        props.add("sdv.simulator.read-timeout", () -> "500ms");
    }
    @BeforeEach void reset() { counts.values().forEach(n -> n.set(0)); received.clear(); modes.clear(); release = new CountDownLatch(1); }
    @AfterEach void release() { release.countDown(); }
    @AfterAll static void stop() { servers.values().forEach(s -> s.stop(0)); executor.shutdownNow(); }

    JsonNode submit(String body, int status) throws Exception {
        var result = mvc.perform(post(ROUTE).contentType("application/json").content(body))
                .andExpect(status().is(status)).andReturn();
        return json.readTree(result.getResponse().getContentAsString());
    }
    String request(String vehicle, String action, String scenario) {
        return "{\"vehicleId\":\"" + vehicle + "\",\"action\":\"" + action + "\",\"scenario\":\"" + scenario + "\"}";
    }
    JsonNode lookup(String id) throws Exception {
        return json.readTree(mvc.perform(get(ROUTE + "/{id}", id)).andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString());
    }

    @ParameterizedTest @CsvSource({"vehicle-001,INJECT_SCENARIO,LIDAR_OBSTRUCTION", "vehicle-002,INJECT_SCENARIO,LIDAR_OBSTRUCTION",
            "vehicle-001,CLEAR_SCENARIO,LIDAR_OBSTRUCTION", "vehicle-002,CLEAR_SCENARIO,LIDAR_OBSTRUCTION",
            "vehicle-001,INJECT_SCENARIO,COOLING_SYSTEM_FAILURE", "vehicle-002,CLEAR_SCENARIO,COOLING_SYSTEM_FAILURE"})
    void routesOnlyToSelectedProviderAndStoresAcknowledgement(String vehicle, String action, String scenario) throws Exception {
        var response = submit(request(vehicle, action, scenario), 202);
        assertThat(response.path("status").asText()).isEqualTo("ACCEPTED");
        assertThat(response.path("dispatchStatus").asText()).isEqualTo("DISPATCHED");
        assertThat(response.path("requestedAt").asText()).isEqualTo("2026-01-01T00:00:04Z");
        assertThat(UUID.fromString(response.path("actionId").asText())).isNotNull();
        assertThat(response.path("traceId").asText()).isEqualTo(response.path("actionId").asText());
        assertThat(lookup(response.path("actionId").asText())).isEqualTo(response);
        JsonNode wire = received.get(vehicle);
        assertThat(wire.size()).isEqualTo(5);
        for (String field : List.of("vehicleId", "action", "scenario", "actionId", "traceId")) assertThat(wire.get(field)).isEqualTo(response.get(field));
        assertThat(counts.get(vehicle)).hasValue(1);
        assertThat(counts.get(vehicle.equals("vehicle-001") ? "vehicle-002" : "vehicle-001")).hasValue(0);
    }

    @ParameterizedTest @ValueSource(strings = {"{}", "{", "null",
            "{\"vehicleId\":\"vehicle-001 \",\"action\":\"INJECT_SCENARIO\",\"scenario\":\"COOLING_SYSTEM_FAILURE\"}",
            "{\"vehicleId\":\"vehicle-001\",\"action\":null,\"scenario\":\"COOLING_SYSTEM_FAILURE\"}",
            "{\"vehicleId\":\"vehicle-001\",\"action\":\"INJECT_SCENARIO\",\"scenario\":null}",
            "{\"vehicleId\":false,\"action\":\"INJECT_SCENARIO\",\"scenario\":\"COOLING_SYSTEM_FAILURE\"}",
            "{\"vehicleId\":\"\",\"action\":\"INJECT_SCENARIO\",\"scenario\":\"COOLING_SYSTEM_FAILURE\"}",
            "{\"vehicleId\":\" vehicle-001\",\"action\":\"INJECT_SCENARIO\",\"scenario\":\"COOLING_SYSTEM_FAILURE\"}",
            "{\"vehicleId\":123,\"action\":\"INJECT_SCENARIO\",\"scenario\":\"COOLING_SYSTEM_FAILURE\"}",
            "{\"vehicleId\":\"vehicle-001\",\"action\":\"OTHER\",\"scenario\":\"COOLING_SYSTEM_FAILURE\"}",
            "{\"vehicleId\":\"vehicle-001\",\"action\":0,\"scenario\":\"COOLING_SYSTEM_FAILURE\"}",
            "{\"vehicleId\":\"vehicle-001\",\"action\":\"INJECT_SCENARIO\",\"scenario\":0}",
            "{\"vehicleId\":\"vehicle-001\",\"action\":\"INJECT_SCENARIO\",\"scenario\":\"OTHER\"}"})
    void invalidRequestsAre400WithNoDispatch(String body) throws Exception {
        var error = submit(body, 400);
        assertThat(error.path("code").asText()).isEqualTo("VALIDATION_ERROR");
        assertThat(error.path("path").asText()).isEqualTo(ROUTE);
        assertThat(error.has("actionId")).isFalse();
        assertThat(error.has("timestamp")).isTrue();
        assertThat(counts.values().stream().mapToInt(AtomicInteger::get).sum()).isZero();
    }
    @ParameterizedTest @ValueSource(strings = {"vehicle-999", "vehicle-003", "unknown"})
    void unknownTargetsHaveNoProviderDispatch(String id) throws Exception {
        submit(request(id, "INJECT_SCENARIO", "COOLING_SYSTEM_FAILURE"), 404);
        assertThat(counts.values().stream().mapToInt(AtomicInteger::get).sum()).isZero();
    }
    @ParameterizedTest @CsvSource({"reject,502,PROVIDER_REJECTED,REJECTED,REJECTED", "unauthorized,502,PROVIDER_REJECTED,REJECTED,REJECTED",
            "serverError,502,PROVIDER_BAD_RESPONSE,FAILED,FAILED", "gatewayTimeout,502,PROVIDER_BAD_RESPONSE,FAILED,FAILED",
            "redirect,502,PROVIDER_BAD_RESPONSE,FAILED,FAILED", "reset,503,PROVIDER_UNAVAILABLE,FAILED,FAILED",
            "timeout,504,PROVIDER_TIMEOUT,FAILED,UNKNOWN", "bodyTimeout,504,PROVIDER_TIMEOUT,FAILED,UNKNOWN"})
    void failuresHaveCorrelatedErrorsStoredOutcomesAndNoRetry(String mode, int status, String code, String lifecycle, String dispatch) throws Exception {
        modes.put("vehicle-002", mode);
        var error = submit(request("vehicle-002", "INJECT_SCENARIO", "COOLING_SYSTEM_FAILURE"), status);
        assertThat(error.path("code").asText()).isEqualTo(code);
        assertThat(error.path("dispatchStatus").asText()).isEqualTo(dispatch);
        assertThat(error.path("traceId").asText()).isEqualTo(error.path("actionId").asText());
        assertThat(error.path("message").asText()).doesNotContain("127.0.0.1");
        assertThat(error.path("path").asText()).isEqualTo(ROUTE);
        var stored = lookup(error.path("actionId").asText());
        assertThat(stored.path("status").asText()).isEqualTo(lifecycle);
        assertThat(stored.path("dispatchStatus").asText()).isEqualTo(dispatch);
        assertThat(stored.path("traceId").asText()).isEqualTo(error.path("traceId").asText());
        assertThat(counts.get("vehicle-002")).hasValue(1);
        submit(request("vehicle-001", "CLEAR_SCENARIO", "COOLING_SYSTEM_FAILURE"), 202);
    }
    @ParameterizedTest @ValueSource(strings = {"vehicleId", "action", "scenario", "actionId", "traceId", "active", "activeType", "missing", "malformed", "array", "null", "trailing", "duplicate"})
    void invalidAcknowledgementsNeverBecomeAccepted(String mode) throws Exception {
        modes.put("vehicle-002", mode);
        var error = submit(request("vehicle-002", "CLEAR_SCENARIO", "COOLING_SYSTEM_FAILURE"), 502);
        assertThat(error.path("code").asText()).isEqualTo("PROVIDER_BAD_RESPONSE");
        assertThat(error.toString()).doesNotContain("private-provider-secret");
        assertThat(lookup(error.path("actionId").asText()).path("status").asText()).isEqualTo("FAILED");
        assertThat(counts.get("vehicle-002")).hasValue(1);
    }
    @Test void clientSuppliedTargetAndIdsCannotOverrideBackendRoutingOrCorrelation() throws Exception {
        String body = request("vehicle-002", "INJECT_SCENARIO", "COOLING_SYSTEM_FAILURE").replace("}",
                ",\"providerBaseUrl\":\"http://untrusted.invalid\",\"actionId\":\"supplied\",\"traceId\":\"supplied\"}");
        var first = submit(body, 202);
        var second = submit(body, 202);
        assertThat(first.path("actionId").asText()).isNotEqualTo("supplied").isNotEqualTo(second.path("actionId").asText());
        assertThat(counts.get("vehicle-002")).hasValue(2);
        assertThat(counts.get("vehicle-001")).hasValue(0);
    }
}
