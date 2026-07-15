package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.adapter.kuksa.KuksaAdapter;
import com.ankit.sdv.backend.model.VehicleState;
import com.ankit.sdv.backend.provider.InMemoryVehicleStateProvider;

public class VehicleIntegrationService {

    private static final String VEHICLE_ID = "vehicle-001";

    private final KuksaAdapter kuksaAdapter;
    private final InMemoryVehicleStateProvider stateProvider;

    public VehicleIntegrationService(
            KuksaAdapter kuksaAdapter,
            InMemoryVehicleStateProvider stateProvider
    ) {
        this.kuksaAdapter = kuksaAdapter;
        this.stateProvider = stateProvider;
    }

    public void synchronizeVehicleState() {
        VehicleState state =
                kuksaAdapter.readCurrentState(VEHICLE_ID);

        stateProvider.updateState(state);
    }
}