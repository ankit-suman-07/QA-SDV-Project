package com.ankit.sdv.backend.provider;

import com.ankit.sdv.backend.model.VehicleState;
import org.springframework.stereotype.Component;

import java.time.Instant;

@Component
public class InMemoryVehicleStateProvider
        implements VehicleStateProvider {

    private volatile VehicleState currentState =
            new VehicleState(
                    "vehicle-001",
                    Instant.now(),
                    85.0,
                    200.0
            );

    @Override
    public VehicleState getCurrentState(String vehicleId) {
        return currentState;
    }

    public void updateState(VehicleState vehicleState) {
        this.currentState = vehicleState;
    }
}