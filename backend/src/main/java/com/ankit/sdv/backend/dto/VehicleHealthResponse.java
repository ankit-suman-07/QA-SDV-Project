package com.ankit.sdv.backend.dto;

import com.ankit.sdv.backend.model.HealthStatus;

public record VehicleHealthResponse(
        String vehicleId,
        HealthStatus healthStatus
) {
}