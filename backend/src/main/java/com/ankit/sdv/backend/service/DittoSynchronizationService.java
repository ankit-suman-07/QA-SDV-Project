package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.adapter.ditto.DittoAdapter;
import com.ankit.sdv.backend.model.VehicleState;
import org.springframework.stereotype.Service;

@Service
public class DittoSynchronizationService {

    private final DittoAdapter dittoAdapter;

    public DittoSynchronizationService(
            DittoAdapter dittoAdapter
    ) {
        this.dittoAdapter = dittoAdapter;
    }

    public void synchronize(VehicleState vehicleState) {
        dittoAdapter.updateVehicleState(vehicleState);
    }
}