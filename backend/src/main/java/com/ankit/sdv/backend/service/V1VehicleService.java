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
        return readAt(vehicleId, null);
    }

    /** Fleet callers supply one captured time; single-vehicle reads keep evaluating after I/O. */
    public V1VehicleResponse readAt(String vehicleId, Instant evaluationTime) {
        String thingId = config.things().get(vehicleId); // Exact identity: never trim or consult legacy registry.
        if (thingId == null) throw new IllegalArgumentException("Unknown V1 vehicle ID");
        var unavailable = V1VehicleResponse.unavailable(vehicleId, thingId);
        var snapshot = reader.read(vehicleId, thingId);
        if (snapshot.isEmpty()) return unavailable;
        Instant evaluation = evaluationTime == null ? clock.instant() : evaluationTime;
        var state = snapshot.get();
        String availability = availability(evaluation, state.sourceEpochSeconds(), config.staleAfter(), config.unavailableAfter());
        if (availability == null) {
            LOG.warn("ditto_read_failed vehicle={} code=FUTURE_SOURCE_TIMESTAMP", vehicleId);
            return unavailable;
        }
        return new V1VehicleResponse(vehicleId, thingId, state.health(), availability, state.faults(),
                state.lidar(), state.sourceTimestamp(), state.lastEventId());
    }

    static String availability(Instant now, BigDecimal source, Duration stale, Duration unavailable) {
        BigDecimal age = BigDecimal.valueOf(now.getEpochSecond())
                .add(BigDecimal.valueOf(now.getNano(), 9)).subtract(source);
        if (age.compareTo(BigDecimal.ONE.negate()) < 0) return null;
        return age.compareTo(seconds(unavailable)) > 0 ? "UNAVAILABLE"
                : age.compareTo(seconds(stale)) > 0 ? "STALE" : "AVAILABLE";
    }

    private static BigDecimal seconds(Duration duration) {
        return BigDecimal.valueOf(duration.getSeconds()).add(BigDecimal.valueOf(duration.getNano(), 9));
    }
}
