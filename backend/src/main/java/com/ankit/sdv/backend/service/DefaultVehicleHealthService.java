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
    public VehicleHealthResponse getCurrentHealth(
            String vehicleId
    ) {
        validateVehicleId(vehicleId);

        VehicleState state =
                vehicleStateProvider.getCurrentState(vehicleId);

        if (state == null) {
            throw new IllegalArgumentException(
                    "Vehicle state not found: " + vehicleId
            );
        }

        HealthResult result =
                vehicleHealthEngine.evaluate(state);

        return new VehicleHealthResponse(
                state.vehicleId(),
                result.status()
        );
    }

    private void validateVehicleId(String vehicleId) {
        if (vehicleId == null || vehicleId.isBlank()) {
            throw new IllegalArgumentException(
                    "Vehicle ID must not be blank"
            );
        }
    }
}