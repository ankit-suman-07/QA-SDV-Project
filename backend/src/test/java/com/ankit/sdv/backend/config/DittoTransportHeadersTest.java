package com.ankit.sdv.backend.config;

import com.ankit.sdv.backend.dto.FleetResponse;
import com.ankit.sdv.backend.service.FleetService;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;
import java.io.ByteArrayOutputStream;
import java.net.*;
import java.nio.file.*;
import java.time.*;
import java.util.*;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.zip.GZIPOutputStream;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class DittoTransportHeadersTest {
    @Test void configuredReaderAndFleetWriterSendOneEncodingFieldAndDecodeGzip() throws Exception {
        var fields = new CopyOnWriteArrayList<List<String>>();
        var methods = new CopyOnWriteArrayList<String>();
        var server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", exchange -> {
            fields.add(exchange.getRequestHeaders().get("Accept-Encoding"));
            methods.add(exchange.getRequestMethod());
            if (fields.getLast().size() != 1) {
                exchange.sendResponseHeaders(400, -1);
            } else if (exchange.getRequestMethod().equals("GET")) {
                var body = new ByteArrayOutputStream();
                try (var gzip = new GZIPOutputStream(body)) {
                    gzip.write(Files.readAllBytes(Path.of("../tests/fixtures/v1/ditto-vehicle-002.json")));
                }
                exchange.getResponseHeaders().set("Content-Type", "application/json");
                exchange.getResponseHeaders().set("Content-Encoding", "gzip");
                exchange.sendResponseHeaders(200, body.size());
                exchange.getResponseBody().write(body.toByteArray());
            } else {
                exchange.getRequestBody().readAllBytes();
                exchange.sendResponseHeaders(204, -1);
            }
            exchange.close();
        });
        server.start();
        try {
            var timeout = Duration.ofSeconds(2);
            var properties = new V1DittoProperties("live", URI.create("http://127.0.0.1:" + server.getAddress().getPort()),
                    timeout, timeout, Duration.ofSeconds(5), Duration.ofSeconds(30), "test", "test-only", null);
            var reader = new V1DittoConfiguration().httpVehicleTwinReader(properties);
            var result = reader.read("vehicle-002", "sdv:vehicle-002");
            assertThat(fields.getFirst()).containsExactly("gzip, deflate");
            assertThat(result).isPresent();
            assertThat(result.orElseThrow().lastEventId()).isEqualTo("vehicle-002-event-000");
            var fleet = mock(FleetService.class);
            when(fleet.read()).thenReturn(new FleetResponse(Instant.EPOCH, 0,0,0,0,0,0,0,List.of()));
            var fleetProperties = new FleetProperties(true, timeout, timeout, timeout, "fleet", "test-only");
            try (var writer = new FleetConfiguration().fleetMaterializer(fleet, fleetProperties, properties, Clock.systemUTC())) {
                writer.update();
                assertThat(fields.getLast()).containsExactly("gzip, deflate");
                assertThat(writer.failureCount()).isZero();
                assertThat(writer.lastSuccess()).isNotNull();
            }
            assertThat(methods).containsExactly("GET", "PUT");
        } finally { server.stop(0); }
    }
}
