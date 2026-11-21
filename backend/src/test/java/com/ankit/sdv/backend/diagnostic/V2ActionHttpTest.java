package com.ankit.sdv.backend.diagnostic;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import java.net.InetSocketAddress;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest(properties = {"sdv.v2.actions.enabled=true", "sdv.v2.actions.poll-initial-delay=1h"})
@AutoConfigureMockMvc
class V2ActionHttpTest {
    private static final String ROOT = "/api/v2/diagnostics";
    private static final String TOKEN = "Bearer component-test";
    @TempDir static Path directory;
    private static HttpServer mock;
    private static final AtomicInteger scenarioWrites = new AtomicInteger();
    private static final AtomicInteger lifecycleWrites = new AtomicInteger();
    private static volatile int providerStatus = 200;
    private static volatile String executorResult;

    @Autowired MockMvc mvc;

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry registry) throws Exception {
        mock = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        mock.createContext("/", request -> {
            try (request) {
                var path = request.getRequestURI().getPath();
                request.getResponseHeaders().add("X-SDV-Mock", "true");
                if (path.equals("/api/v1/scenarios/actions")) {
                    scenarioWrites.incrementAndGet();
                    var input = HttpActionExecution.JSON.readTree(request.getRequestBody());
                    var ack = HttpActionExecution.JSON.createObjectNode();
                    for (var field : input.propertyNames()) ack.set(field, input.get(field));
                    ack.put("active", true);
                    var bytes = HttpActionExecution.JSON.writeValueAsBytes(ack);
                    request.sendResponseHeaders(providerStatus, bytes.length);
                    request.getResponseBody().write(bytes);
                } else if (path.equals(ROOT + "/actions") && request.getRequestMethod().equals("POST")) {
                    lifecycleWrites.incrementAndGet();
                    var input = HttpActionExecution.JSON.readTree(request.getRequestBody());
                    var ack = HttpActionExecution.JSON.createObjectNode();
                    for (var field : input.propertyNames()) ack.set(field, input.get(field));
                    ack.put("status", "ACCEPTED");
                    var bytes = HttpActionExecution.JSON.writeValueAsBytes(ack);
                    request.sendResponseHeaders(202, bytes.length);
                    request.getResponseBody().write(bytes);
                } else if (path.equals(ROOT + "/actions/action-003") && executorResult != null) {
                    var bytes = executorResult.getBytes(java.nio.charset.StandardCharsets.UTF_8);
                    request.sendResponseHeaders(200, bytes.length);
                    request.getResponseBody().write(bytes);
                } else if (path.equals("/mock/v2/diagnostics/vehicle-003/faults")
                        || path.equals("/mock/v2/diagnostics/vehicle-003/health")) {
                    var bytes = HttpActionExecution.JSON.writeValueAsBytes(
                            HttpActionExecution.JSON.createObjectNode().put("vehicleId", "vehicle-003")
                                    .put("boundary", "PROJECT_MOCK_NOT_NATIVE_PROTOCOL"));
                    request.sendResponseHeaders(200, bytes.length);
                    request.getResponseBody().write(bytes);
                } else request.sendResponseHeaders(404, -1);
            }
        });
        mock.start();
        registry.add("sdv.v2.actions.journal", () -> directory.resolve("actions.json").toString());
        registry.add("sdv.v2.actions.token", () -> "component-test");
        registry.add("sdv.v2.actions.scenario-providers[vehicle-003]", V2ActionHttpTest::url);
        registry.add("sdv.v2.actions.fixture-base", V2ActionHttpTest::url);
    }

    private static String url() { return "http://127.0.0.1:" + mock.getAddress().getPort(); }

    @AfterAll static void stop() { mock.stop(0); }

    @Test void routesAndAuthorizesWithoutStartingAnyRealExecutor() throws Exception {
        var fixture = HttpActionExecution.JSON.readTree(Files.readAllBytes(
                Path.of("../tests/fixtures/v2/diagnostics/cases.json"))).get("request");
        var body = HttpActionExecution.JSON.writeValueAsString(fixture);
        mvc.perform(post(ROOT + "/actions").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isUnauthorized());
        send(body.replace("\"vehicle-003\"", "\"vehicle-004\"")).andExpect(status().isNotFound());
        send(body.replace("\"vehicle-003\"", "42")).andExpect(status().isBadRequest());
        send(body.replace("\"INJECT_SCENARIO\"", "0")).andExpect(status().isBadRequest());
        send(body).andExpect(status().isAccepted()).andExpect(jsonPath("$.status").value("ACCEPTED"));
        send(body).andExpect(status().isAccepted());
        send(body.replace("trace-003", "other")).andExpect(status().isConflict());
        assertThat(scenarioWrites).hasValue(1);
        assertThat(lifecycleWrites).hasValue(0);

        executorResult = """
                {"vehicleId":"vehicle-002","actionId":"action-003","traceId":"trace-003","status":"EXECUTING"}
                """;
        mvc.perform(get(ROOT + "/actions/action-003").header("Authorization", TOKEN)).andExpect(status().isConflict());
        executorResult = executorResult.replace("vehicle-002", "vehicle-003");
        mvc.perform(get(ROOT + "/actions/action-003").header("Authorization", TOKEN))
                .andExpect(status().isOk()).andExpect(jsonPath("$.status").value("EXECUTING"));
        executorResult = executorResult.replace("EXECUTING", "SUCCEEDED");
        mvc.perform(get(ROOT + "/actions/action-003").header("Authorization", TOKEN))
                .andExpect(status().isOk()).andExpect(jsonPath("$.status").value("SUCCEEDED"));

        var restart = fixture.deepCopy();
        if (restart instanceof tools.jackson.databind.node.ObjectNode restartBody) {
            restartBody.put("actionId", "restart-test").put("action", "RESTART_APP").remove("scenario");
        }
        send(HttpActionExecution.JSON.writeValueAsString(restart)).andExpect(status().isAccepted());
        assertThat(lifecycleWrites).hasValue(1);
        assertThat(scenarioWrites).hasValue(1);

        for (int code : new int[]{409, 503, 504}) {
            providerStatus = code;
            send(body.replace("action-003", "provider-" + code)).andExpect(status().is(code));
        }
        mvc.perform(get(ROOT + "/actions/provider-504").header("Authorization", TOKEN))
                .andExpect(status().isOk()).andExpect(jsonPath("$.status").value("TIMED_OUT"))
                .andExpect(jsonPath("$.executionUncertain").value(true));
        mvc.perform(get(ROOT + "/vehicles/vehicle-003/actions").header("Authorization", TOKEN))
                .andExpect(status().isOk()).andExpect(jsonPath("$[0].vehicleId").value("vehicle-003"));
        for (String kind : new String[]{"health", "faults"}) {
            mvc.perform(get(ROOT + "/vehicles/vehicle-003/" + kind).header("Authorization", TOKEN))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.boundary").value("PROJECT_MOCK_NOT_NATIVE_PROTOCOL"));
        }
    }

    private org.springframework.test.web.servlet.ResultActions send(String body) throws Exception {
        return mvc.perform(post(ROOT + "/actions").header("Authorization", TOKEN)
                .contentType(MediaType.APPLICATION_JSON).content(body));
    }
}
