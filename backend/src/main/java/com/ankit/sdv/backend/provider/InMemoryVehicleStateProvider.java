package com.ankit.sdv.backend.provider;

import com.ankit.sdv.backend.model.VehicleState;
import org.springframework.stereotype.Component;

//import java.time.Instant;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class InMemoryVehicleStateProvider
        implements VehicleStateProvider {

    private final Map<String, VehicleState> currentStates =
            new ConcurrentHashMap<>();

//     public InMemoryVehicleStateProvider() {
//         updateState(
//                 new VehicleState(
//                         "vehicle-001",
//                         Instant.now(),
//                         85.0,
//                         200.0
//                 )
//         );
//     }

    @Override
    public VehicleState getCurrentState(String vehicleId) {
        return currentStates.get(vehicleId);
    }

    public void updateState(VehicleState vehicleState) {
        Objects.requireNonNull(
                vehicleState,
                "Vehicle state must not be null"
        );
        Objects.requireNonNull(
                vehicleState.vehicleId(),
                "Vehicle ID must not be null"
        );

        currentStates.put(
                vehicleState.vehicleId(),
                vehicleState
        );
    }
}