package com.ankit.sdv.backend.adapter.simulator;

import com.ankit.sdv.backend.model.DiagnosticAction;
import com.ankit.sdv.backend.model.DiagnosticScenario;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

import static org.springframework.test.web.client
        .match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client
        .match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client
        .match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client
        .response.MockRestResponseCreators.withSuccess;

class HttpSimulatorControlAdapterTest {

    @Test
    void shouldSendDiagnosticActionToSimulator() {
        RestClient.Builder builder = RestClient.builder();

        MockRestServiceServer server =
                MockRestServiceServer
                        .bindTo(builder)
                        .build();

        HttpSimulatorControlAdapter adapter =
                new HttpSimulatorControlAdapter(
                        builder.build(),
                        java.util.Map.of("vehicle-001", java.net.URI.create("http://localhost:8090")), java.time.Duration.ofSeconds(2)
                );

        server.expect(
                        requestTo(
                                "http://localhost:8090"
                                        + "/api/v1/scenarios/actions"
                        )
                )
                .andExpect(method(HttpMethod.POST))
                .andExpect(
                        content().contentType(
                                MediaType.APPLICATION_JSON
                        )
                )
                .andExpect(
                        content().json(
                                """
                                {
                                  "vehicleId": "vehicle-001",
                                  "action": "INJECT_SCENARIO",
                                  "scenario": "COOLING_SYSTEM_FAILURE",
                                  "actionId": "action-001",
                                  "traceId": "trace-001"
                                }
                                """
                        )
                )
                .andRespond(
                        withSuccess(
                                """
                                {
                                  "vehicleId": "vehicle-001",
                                  "action": "INJECT_SCENARIO",
                                  "scenario": "COOLING_SYSTEM_FAILURE",
                                  "actionId": "action-001",
                                  "traceId": "trace-001",
                                  "active": true
                                }
                                """,
                                MediaType.APPLICATION_JSON
                        )
                );

        adapter.executeAction(
                "vehicle-001",
                DiagnosticAction.INJECT_SCENARIO,
                DiagnosticScenario.COOLING_SYSTEM_FAILURE,
                "action-001",
                "trace-001"
        );

        server.verify();
        adapter.close();
    }
}