package com.ankit.sdv.backend.adapter.uprotocol;

import com.ankit.sdv.backend.model.VehicleState;

public interface UProtocolAdapter {

    void publishVehicleStatus(VehicleState vehicleState);
}