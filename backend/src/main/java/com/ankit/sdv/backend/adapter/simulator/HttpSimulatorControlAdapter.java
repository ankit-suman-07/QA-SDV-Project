package com.ankit.sdv.backend.adapter.simulator;

import com.ankit.sdv.backend.model.DiagnosticAction;
import com.ankit.sdv.backend.model.DiagnosticScenario;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition
        .ConditionalOnProperty;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
@ConditionalOnProperty(
        name = "sdv.simulator.mode",
        havingValue = "http"
)
public class HttpSimulatorControlAdapter
        implements SimulatorControlAdapter {

    private static final String ACTION_PATH =
            "/api/v1/scenarios/actions";

    private final RestClient restClient;

    public HttpSimulatorControlAdapter(
            RestClient.Builder restClientBuilder,
            @Value(
                    "${sdv.simulator.base-url:"
                            + "http://localhost:8090}"
            )
            String simulatorBaseUrl
    ) {
        this.restClient = restClientBuilder
                .baseUrl(simulatorBaseUrl)
                .build();
    }

    @Override
    public void executeAction(
            String vehicleId,
            DiagnosticAction action,
            DiagnosticScenario scenario,
            String actionId,
            String traceId
    ) {
        SimulatorActionRequest request =
                new SimulatorActionRequest(
                        vehicleId,
                        action,
                        scenario,
                        actionId,
                        traceId
                );

        restClient.post()
                .uri(ACTION_PATH)
                .contentType(MediaType.APPLICATION_JSON)
                .body(request)
                .retrieve()
                .toBodilessEntity();
    }

    private record SimulatorActionRequest(
            String vehicleId,
            DiagnosticAction action,
            DiagnosticScenario scenario,
            String actionId,
            String traceId
    ) {
    }
}