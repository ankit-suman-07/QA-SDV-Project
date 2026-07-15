package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.dto.VehicleHealthResponse;
import com.ankit.sdv.backend.health.VehicleHealthEngine;
import com.ankit.sdv.backend.model.HealthResult;
import com.ankit.sdv.backend.model.VehicleState;
import org.springframework.stereotype.Service;

import java.time.Instant;

@Service
public class DefaultVehicleHealthService
        implements VehicleHealthService {

    private static final double BASELINE_TEMPERATURE_CELSIUS = 85.0;

    private final VehicleHealthEngine vehicleHealthEngine;

    public DefaultVehicleHealthService(
            VehicleHealthEngine vehicleHealthEngine
    ) {
        this.vehicleHealthEngine = vehicleHealthEngine;
    }

    @Override
    public VehicleHealthResponse getCurrentHealth(String vehicleId) {
        VehicleState baselineState = new VehicleState(
                vehicleId,
                Instant.now(),
                BASELINE_TEMPERATURE_CELSIUS
        );

        HealthResult result =
                vehicleHealthEngine.evaluate(baselineState);

        return new VehicleHealthResponse(
                vehicleId,
                result.status()
        );
    }
}