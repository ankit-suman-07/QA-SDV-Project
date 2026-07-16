package com.ankit.sdv.backend.adapter.ditto;

import com.ankit.sdv.backend.model.VehicleState;

public interface DittoAdapter {

    void updateVehicleState(VehicleState vehicleState);
}