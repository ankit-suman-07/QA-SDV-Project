package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.adapter.ditto.HttpVehicleTwinReader;
import com.ankit.sdv.backend.config.V1DittoProperties;
import com.ankit.sdv.backend.dto.V1VehicleResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.List;

@Service
public class V1VehicleService {
    private static final Logger LOG = LoggerFactory.getLogger(V1VehicleService.class);
    private final HttpVehicleTwinReader reader;
    private final V1DittoProperties config;
    private final Clock clock;

    public V1VehicleService(HttpVehicleTwinReader reader, V1DittoProperties config, Clock clock) {
        this.reader = reader;
        this.config = config;
        this.clock = clock;
    }

    public List<String> vehicleIds() { return config.vehicleIds(); }

    public V1VehicleResponse read(String vehicleId) {
        String thingId = config.things().get(vehicleId); // Exact identity: never trim or consult legacy registry.
        if (thingId == null) throw new IllegalArgumentException("Unknown V1 vehicle ID");
        var unavailable = V1VehicleResponse.unavailable(vehicleId, thingId);
        var snapshot = reader.read(vehicleId, thingId);
        if (snapshot.isEmpty()) return unavailable;
        Instant evaluation = clock.instant();
        BigDecimal now = BigDecimal.valueOf(evaluation.getEpochSecond())
                .add(BigDecimal.valueOf(evaluation.getNano(), 9));
        var state = snapshot.get();
        BigDecimal age = now.subtract(state.sourceEpochSeconds());
        if (age.compareTo(BigDecimal.ONE.negate()) < 0) {
            LOG.warn("ditto_read_failed vehicle={} code=FUTURE_SOURCE_TIMESTAMP", vehicleId);
            return unavailable;
        }
        String availability = age.compareTo(seconds(config.unavailableAfter())) > 0 ? "UNAVAILABLE"
                : age.compareTo(seconds(config.staleAfter())) > 0 ? "STALE" : "AVAILABLE";
        return new V1VehicleResponse(vehicleId, thingId, state.health(), availability, state.faults(),
                state.lidar(), state.sourceTimestamp(), state.lastEventId());
    }

    private static BigDecimal seconds(Duration duration) {
        return BigDecimal.valueOf(duration.getSeconds()).add(BigDecimal.valueOf(duration.getNano(), 9));
    }
}
