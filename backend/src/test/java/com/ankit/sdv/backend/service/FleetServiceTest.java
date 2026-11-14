package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.config.V1DittoProperties;
import com.ankit.sdv.backend.dto.V1VehicleResponse;
import org.junit.jupiter.api.Test;

import java.net.URI;
import java.time.*;
import java.util.List;
import java.util.concurrent.*;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class FleetServiceTest {
    @Test void capturesClockOnceAndReadsBothVehiclesIndependentlyAtThatTime() throws Exception {
        var vehicles = mock(V1VehicleService.class);
        var clock = mock(Clock.class);
        var now = Instant.parse("2026-01-01T00:00:04Z");
        when(clock.instant()).thenReturn(now, now.plusSeconds(60));
        when(vehicles.vehicleIds()).thenReturn(List.of("vehicle-002", "vehicle-001", "vehicle-002"));
        var entered = new CountDownLatch(2);
        when(vehicles.readAt(anyString(), eq(now))).thenAnswer(call -> {
            entered.countDown();
            if (!entered.await(1, TimeUnit.SECONDS)) throw new AssertionError("reads must start independently");
            String id = call.getArgument(0);
            return new V1VehicleResponse(id, "sdv:" + id, "HEALTHY", "AVAILABLE", List.of(), null, now.toString(), "event");
        });
        var properties = new V1DittoProperties("mock", URI.create("http://localhost:8080"), Duration.ofSeconds(2),
                Duration.ofSeconds(2), Duration.ofSeconds(5), Duration.ofSeconds(30), null, null, null);
        try (var fleet = new FleetService(vehicles, properties, clock)) {
            var result = fleet.read();
            assertThat(result.generatedAt()).isEqualTo(now);
            assertThat(result.totalVehicles()).isEqualTo(2);
            assertThat(result.healthyVehicles()).isEqualTo(2);
            assertThat(result.vehicles()).extracting(V1VehicleResponse::vehicleId).containsExactly("vehicle-001", "vehicle-002");
        }
        verify(clock, times(1)).instant();
        verify(vehicles, times(1)).readAt("vehicle-001", now);
        verify(vehicles, times(1)).readAt("vehicle-002", now);
    }
}
