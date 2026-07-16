package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.adapter.uprotocol.UProtocolAdapter;
import com.ankit.sdv.backend.model.VehicleState;
import org.springframework.stereotype.Service;

@Service
public class UProtocolEventService {

    private final UProtocolAdapter uProtocolAdapter;

    public UProtocolEventService(
            UProtocolAdapter uProtocolAdapter
    ) {
        this.uProtocolAdapter = uProtocolAdapter;
    }

    public void publishVehicleStatus(VehicleState vehicleState) {
        uProtocolAdapter.publishVehicleStatus(vehicleState);
    }
}