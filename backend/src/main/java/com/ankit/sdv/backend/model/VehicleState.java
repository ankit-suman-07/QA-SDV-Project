package com.ankit.sdv.backend.model;

import java.time.Instant;

public record VehicleState(
        String vehicleId,
        Instant sourceTimestamp,
        double temperatureCelsius,
        double coolantPressureKpa
) {
}