package com.ankit.sdv.backend.provider;

import com.ankit.sdv.backend.model.VehicleState;

public interface VehicleStateProvider {

    VehicleState getCurrentState(String vehicleId);
}