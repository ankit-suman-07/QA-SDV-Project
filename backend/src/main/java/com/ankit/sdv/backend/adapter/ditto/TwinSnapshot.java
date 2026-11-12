package com.ankit.sdv.backend.adapter.ditto;

import com.ankit.sdv.backend.dto.V1VehicleResponse.Lidar;
import java.math.BigDecimal;
import java.util.List;

/** Validated observation with original timestamp text and exact fractional time. */
public record TwinSnapshot(String health, List<String> faults, Lidar lidar,
        String sourceTimestamp, String lastEventId, BigDecimal sourceEpochSeconds) {}
