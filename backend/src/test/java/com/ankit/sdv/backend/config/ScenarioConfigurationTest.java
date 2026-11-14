package com.ankit.sdv.backend.config;

import com.ankit.sdv.backend.adapter.simulator.DevelopmentSimulatorControlAdapter;
import com.ankit.sdv.backend.adapter.simulator.HttpSimulatorControlAdapter;
import com.ankit.sdv.backend.adapter.simulator.SimulatorControlAdapter;
import com.ankit.sdv.backend.dto.DiagnosticActionRequest;
import com.ankit.sdv.backend.exception.ProviderDispatchException;
import com.ankit.sdv.backend.model.DiagnosticAction;
import com.ankit.sdv.backend.model.DiagnosticScenario;
import com.ankit.sdv.backend.registry.VehicleRegistry;
import com.ankit.sdv.backend.service.DefaultDiagnosticActionService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import tools.jackson.databind.json.JsonMapper;

import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.URI;
import java.time.Clock;
import java.time.Duration;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.*;

class ScenarioConfigurationTest {
    final ApplicationContextRunner context = new ApplicationContextRunner()
            .withUserConfiguration(SimulatorControlConfiguration.class, DevelopmentSimulatorControlAdapter.class)
            .withPropertyValues("sdv.simulator.providers[vehicle-001]=http://127.0.0.1:8091",
                    "sdv.simulator.providers[vehicle-002]=http://127.0.0.1:8092");

    @ParameterizedTest @ValueSource(strings = {"sdv.simulator.mode=other", "sdv.simulator.connect-timeout=0s", "sdv.simulator.read-timeout=-1s",
            "sdv.simulator.providers[vehicle-002]=", "sdv.simulator.providers[vehicle-999]=http://127.0.0.1:8099",
            "sdv.simulator.providers[vehicle-001]=http://user:private@localhost",
            "sdv.simulator.providers[vehicle-001]=http://localhost?token=private",
            "sdv.simulator.providers[vehicle-001]=http://localhost#fragment",
            "sdv.simulator.providers[vehicle-001]=ftp://localhost"})
    void invalidConfigurationFailsStartup(String value) {
        context.withPropertyValues("sdv.simulator.mode=http", value).run(result -> assertThat(result).hasFailed());
    }
    @ParameterizedTest @ValueSource(strings = {"http", "development"})
    void modeSelectsOneAdapterWithNoImplicitFallback(String mode) {
        context.withPropertyValues("sdv.simulator.mode=" + mode).run(result -> {
            assertThat(result).hasNotFailed().hasSingleBean(SimulatorControlAdapter.class);
            assertThat(result.getBean(SimulatorControlAdapter.class)).isInstanceOf(
                    mode.equals("http") ? HttpSimulatorControlAdapter.class : DevelopmentSimulatorControlAdapter.class);
        });
    }
    @Test void realRefusedConnectionIsRetainedWithoutAcceptedState() throws Exception {
        int port;
        try (var socket = new ServerSocket(0, 1, InetAddress.getLoopbackAddress())) { port = socket.getLocalPort(); }
        var config = new SimulatorProperties("http", Map.of("vehicle-001", URI.create("http://127.0.0.1:8091"),
                "vehicle-002", URI.create("http://127.0.0.1:" + port)), Duration.ofMillis(100), Duration.ofSeconds(2));
        try (var adapter = new SimulatorControlConfiguration().httpSimulatorControlAdapter(config)) {
            var service = new DefaultDiagnosticActionService(adapter, () -> "refused-action", Clock.systemUTC(),
                    new VehicleRegistry(List.of("vehicle-001", "vehicle-002")));
            var error = catchThrowableOfType(ProviderDispatchException.class, () -> service.submit(new DiagnosticActionRequest(
                    "vehicle-002", DiagnosticAction.INJECT_SCENARIO, DiagnosticScenario.LIDAR_OBSTRUCTION)));
            assertThat(error.reason()).isEqualTo(ProviderDispatchException.Reason.UNAVAILABLE);
            assertThat(error.action().actionId()).isEqualTo("refused-action");
            assertThat(service.getById("refused-action").status().name()).isEqualTo("FAILED");
            assertThat(service.getById("refused-action").dispatchStatus().name()).isEqualTo("FAILED");
        }
    }
    @Test void explicitDevelopmentCoolingKeepsLegacyResponseWithoutClaimingDispatch() {
        var service = new DefaultDiagnosticActionService(new DevelopmentSimulatorControlAdapter(), () -> "dev-action", Clock.systemUTC(),
                new VehicleRegistry(List.of("vehicle-001", "vehicle-002", "vehicle-003")));
        var response = service.submit(new DiagnosticActionRequest("vehicle-003", DiagnosticAction.INJECT_SCENARIO,
                DiagnosticScenario.COOLING_SYSTEM_FAILURE));
        var body = JsonMapper.builder().build().valueToTree(response);
        assertThat(body.size()).isEqualTo(7);
        assertThat(body.path("status").asText()).isEqualTo("ACCEPTED");
        assertThat(body.has("dispatchStatus")).isFalse();
        assertThat(service.getById("dev-action")).isEqualTo(response);
    }
}
