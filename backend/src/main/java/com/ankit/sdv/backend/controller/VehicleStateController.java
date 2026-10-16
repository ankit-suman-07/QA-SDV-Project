package com.ankit.sdv.backend.controller;

import com.ankit.sdv.backend.model.VehicleState;
import com.ankit.sdv.backend.provider.VehicleStateProvider;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/vehicles")
public class VehicleStateController {

    // private static final String SUPPORTED_VEHICLE_ID =
    //         "vehicle-001";

    private final VehicleStateProvider vehicleStateProvider;

    public VehicleStateController(
            VehicleStateProvider vehicleStateProvider
    ) {
        this.vehicleStateProvider = vehicleStateProvider;
    }

    @GetMapping("/{vehicleId}/state")
public VehicleState getVehicleState(
        @PathVariable("vehicleId") String vehicleId
) {
    VehicleState state =
            vehicleStateProvider.getCurrentState(vehicleId);

    if (state == null) {
        throw new IllegalArgumentException(
                "Vehicle state not found: " + vehicleId
        );
    }

    return state;
}

    // private void validateVehicleId(String vehicleId) {
    //     if (!SUPPORTED_VEHICLE_ID.equals(vehicleId)) {
    //         throw new IllegalArgumentException(
    //                 "Unsupported vehicle ID: " + vehicleId
    //         );
    //     }
    // }
}