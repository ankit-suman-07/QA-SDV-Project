package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.adapter.ditto.HttpVehicleTwinReader;
import com.ankit.sdv.backend.dto.V2VehicleResponse;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.List;

@Service
public class V2VehicleService {
    private static final List<String> VEHICLES = List.of("vehicle-001", "vehicle-002", "vehicle-003");
    private final HttpVehicleTwinReader reader;
    private final Clock clock;

    public V2VehicleService(HttpVehicleTwinReader reader, Clock clock) {
        this.reader = reader;
        this.clock = clock;
    }

    public List<String> vehicleIds() { return VEHICLES; }

    public V2VehicleResponse readAt(String vehicle, Instant evaluation) {
        if (!VEHICLES.contains(vehicle)) throw new IllegalArgumentException("Unknown V2 vehicle ID");
        String thing = "sdv:" + vehicle;
        var snapshot = reader.readV2(vehicle, thing);
        if (snapshot.isEmpty()) return unavailable(vehicle);

        var s = snapshot.get();
        String availability = V1VehicleService.availability(evaluation == null ? clock.instant() : evaluation,
                s.sourceEpochSeconds(), Duration.ofSeconds(5), Duration.ofSeconds(30));
        if (availability == null) return unavailable(vehicle);

        var state = s.state();
        return new V2VehicleResponse(vehicle, thing, state.healthStatus(), availability, state.activeFaults(),
                state.lidar(), state.sourceTimestamp(), state.lastEventId(), state.sessionId(),
                state.sessionGeneration(), state.sequence(), state.frame(), state.recoveryState(),
                state.recoveryStartedAt(), state.sourceSilent());
    }

    V2VehicleResponse unavailable(String vehicle) {
        return V2VehicleResponse.unavailable(vehicle, "sdv:" + vehicle);
    }
}
