package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.dto.VehicleHealthResponse;
import com.ankit.sdv.backend.health.VehicleHealthEngine;
import com.ankit.sdv.backend.model.HealthResult;
import com.ankit.sdv.backend.model.VehicleState;
import com.ankit.sdv.backend.provider.VehicleStateProvider;
import org.springframework.stereotype.Service;

@Service
public class DefaultVehicleHealthService
        implements VehicleHealthService {

    private static final String SUPPORTED_VEHICLE_ID =
            "vehicle-001";

    private final VehicleHealthEngine vehicleHealthEngine;
    private final VehicleStateProvider vehicleStateProvider;

    public DefaultVehicleHealthService(
            VehicleHealthEngine vehicleHealthEngine,
            VehicleStateProvider vehicleStateProvider
    ) {
        this.vehicleHealthEngine = vehicleHealthEngine;
        this.vehicleStateProvider = vehicleStateProvider;
    }

    @Override
    public VehicleHealthResponse getCurrentHealth(String vehicleId) {
        validateVehicleId(vehicleId);

        VehicleState state =
                vehicleStateProvider.getCurrentState(vehicleId);

        HealthResult result =
                vehicleHealthEngine.evaluate(state);

        return new VehicleHealthResponse(
                vehicleId,
                result.status()
        );
    }

    private void validateVehicleId(String vehicleId) {
        if (!SUPPORTED_VEHICLE_ID.equals(vehicleId)) {
            throw new IllegalArgumentException(
                    "Unsupported vehicle ID: " + vehicleId
            );
        }
    }
}