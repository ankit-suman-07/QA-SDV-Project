package com.ankit.sdv.backend.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import java.util.List;
import java.math.BigDecimal;

/** C7 projection. Untrusted reads always serialize all five data fields as null. */
@JsonInclude(JsonInclude.Include.ALWAYS)
public record V1VehicleResponse(String vehicleId, String thingId, String healthStatus,
        String availability, List<String> activeFaults, Lidar lidar,
        String sourceTimestamp, String lastEventId) implements VehicleProjection {
    public record Lidar(BigDecimal distanceMeters, boolean sensorAvailable) {}

    public static V1VehicleResponse unavailable(String vehicleId, String thingId) {
        return new V1VehicleResponse(vehicleId, thingId, null, "UNAVAILABLE", null, null, null, null);
    }
}
