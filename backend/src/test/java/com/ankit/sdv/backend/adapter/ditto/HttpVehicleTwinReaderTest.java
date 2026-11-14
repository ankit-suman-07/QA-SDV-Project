package com.ankit.sdv.backend.adapter.ditto;

import com.ankit.sdv.backend.config.V1DittoProperties;
import com.ankit.sdv.backend.service.V1VehicleService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

import java.net.URI;
import java.net.SocketTimeoutException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.*;
import static org.springframework.test.web.client.response.MockRestResponseCreators.*;

@ExtendWith(OutputCaptureExtension.class)
class HttpVehicleTwinReaderTest {
    final RestClient.Builder builder = RestClient.builder();
    final MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    final HttpVehicleTwinReader reader = new HttpVehicleTwinReader(builder.build(), URI.create("http://ditto.example/prefix"));

    String fixture() throws Exception {
        return Files.readString(Path.of("../tests/fixtures/v1/ditto-vehicle-002.json"));
    }
    void responds(String body) {
        server.expect(requestTo("http://ditto.example/prefix/api/2/things/sdv:vehicle-002"))
                .andExpect(method(org.springframework.http.HttpMethod.GET))
                .andExpect(header("Accept", "application/json"))
                .andRespond(withSuccess(body, MediaType.APPLICATION_JSON));
    }
    @Test void readsWholeThingAtConfiguredPrefixAndPreservesSourceAndEvent() throws Exception {
        responds(fixture());
        var snapshot = reader.read("vehicle-002", "sdv:vehicle-002").orElseThrow();
        assertThat(snapshot.sourceTimestamp()).isEqualTo("2026-01-01T00:00:00Z");
        assertThat(snapshot.lastEventId()).isEqualTo("vehicle-002-event-000");
        server.verify();
    }
    @Test void configuredThresholdsAndFutureToleranceUseTheInjectedClock() throws Exception {
        var config = new V1DittoProperties("mock", URI.create("http://ditto.example/prefix"),
                Duration.ofSeconds(2), Duration.ofSeconds(2), Duration.ofSeconds(2), Duration.ofSeconds(8), null, null, null);
        responds(fixture());
        var service = new V1VehicleService(reader, config,
                Clock.fixed(Instant.parse("2026-01-01T00:00:04Z"), ZoneOffset.UTC));
        assertThat(service.read("vehicle-002").availability()).isEqualTo("STALE");
        server.verify();
    }
    @Test void subnanosecondFutureExcessIsNotRoundedIntoTheTolerance() throws Exception {
        responds(fixture().replace("2026-01-01T00:00:00Z", "2026-01-01T00:00:05.000000000001Z"));
        var config = new V1DittoProperties("live", URI.create("http://ditto.example/prefix"),
                Duration.ofSeconds(2), Duration.ofSeconds(2), Duration.ofSeconds(5), Duration.ofSeconds(30), null, null, null);
        var service = new V1VehicleService(reader, config,
                Clock.fixed(Instant.parse("2026-01-01T00:00:04Z"), ZoneOffset.UTC));
        var result = service.read("vehicle-002");
        assertThat(result.availability()).isEqualTo("UNAVAILABLE");
        assertThat(result.sourceTimestamp()).isNull();
        server.verify();
    }
    @Test void timeoutIsUnavailableWithoutLeakingDependencyDetails(CapturedOutput output) {
        server.expect(anything()).andRespond(withException(new SocketTimeoutException("credential-must-not-leak")));
        assertThat(reader.read("vehicle-002", "sdv:vehicle-002")).isEmpty();
        assertThat(output).contains("TRANSPORT_UNAVAILABLE").doesNotContain("credential-must-not-leak");
        server.verify();
    }
    @ParameterizedTest @ValueSource(ints = {401, 403})
    void authenticationFailuresAreObservableAndRedacted(int status, CapturedOutput output) {
        server.expect(anything()).andRespond(withStatus(HttpStatus.valueOf(status)).body("credential-must-not-leak"));
        assertThat(reader.read("vehicle-002", "sdv:vehicle-002")).isEmpty();
        assertThat(output).contains("AUTH_CONFIGURATION", "status=" + status).doesNotContain("credential-must-not-leak");
        server.verify();
    }
    @Test void responseSizeIsBoundedBeforeParsing() {
        responds(" ".repeat(1024 * 1024 + 1));
        assertThat(reader.read("vehicle-002", "sdv:vehicle-002")).isEmpty();
        server.verify();
    }
    @Test void nestedExtensionsRespectParserLimitsWithoutCrashingAndUnicodePairsAreValid() throws Exception {
        String extension = "[".repeat(100) + "0" + "]".repeat(100);
        responds(fixture().replace("\"schemaVersion\"", "\"extension\":" + extension + ",\"schemaVersion\""));
        assertThat(reader.read("vehicle-002", "sdv:vehicle-002")).isPresent();
        server.verify();
        server.reset();
        String deep = "[".repeat(600) + "0" + "]".repeat(600);
        responds(fixture().replace("\"schemaVersion\"", "\"extension\":" + deep + ",\"schemaVersion\""));
        assertThat(reader.read("vehicle-002", "sdv:vehicle-002")).isEmpty();
        server.verify();
        server.reset();
        responds(fixture().replace("\"schemaVersion\"", "\"extension\":\"\\ud83d\\ude80\",\"schemaVersion\""));
        assertThat(reader.read("vehicle-002", "sdv:vehicle-002")).isPresent();
        server.verify();
    }
    @ParameterizedTest @ValueSource(strings = {"2026-02-30T00:00:00Z", "2026-01-01T24:00:00Z", "2026-01-01T00:00:60Z"})
    void invalidCalendarValuesCannotBecomeSnapshots(String timestamp) throws Exception {
        responds(fixture().replace("2026-01-01T00:00:00Z", timestamp));
        assertThat(reader.read("vehicle-002", "sdv:vehicle-002")).isEmpty();
        server.verify();
    }
}
