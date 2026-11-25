package com.ankit.sdv.backend.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import java.math.BigInteger;
import java.util.List;

@JsonInclude(JsonInclude.Include.ALWAYS)
public record V2VehicleResponse(String vehicleId, String thingId, String healthStatus,
        String availability, List<String> activeFaults, V1VehicleResponse.Lidar lidar,
        String sourceTimestamp, String lastEventId, String sessionId, BigInteger sessionGeneration,
        BigInteger sequence, BigInteger frame, String recoveryState, String recoveryStartedAt,
        Boolean sourceSilent) implements VehicleProjection {

    public static V2VehicleResponse unavailable(String vehicleId, String thingId) {
        return new V2VehicleResponse(vehicleId, thingId, null, "UNAVAILABLE", null, null, null,
                null, null, null, null, null, null, null, null);
    }
}
