package com.ankit.sdv.backend.adapter.kuksa;

import com.ankit.sdv.backend.model.VehicleState;

public interface KuksaAdapter {

    VehicleState readCurrentState(String vehicleId);
}