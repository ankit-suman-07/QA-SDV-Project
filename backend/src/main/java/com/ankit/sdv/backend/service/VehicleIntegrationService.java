package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.adapter.kuksa.KuksaAdapter;
import com.ankit.sdv.backend.model.VehicleState;
import com.ankit.sdv.backend.provider.InMemoryVehicleStateProvider;
import org.springframework.stereotype.Service;

@Service
public class VehicleIntegrationService {

    private static final String VEHICLE_ID = "vehicle-001";

    private final KuksaAdapter kuksaAdapter;
    private final InMemoryVehicleStateProvider stateProvider;
    private final DittoSynchronizationService dittoSynchronizationService;

    public VehicleIntegrationService(
            KuksaAdapter kuksaAdapter,
            InMemoryVehicleStateProvider stateProvider,
            DittoSynchronizationService dittoSynchronizationService
    ) {
        this.kuksaAdapter = kuksaAdapter;
        this.stateProvider = stateProvider;
        this.dittoSynchronizationService =
                dittoSynchronizationService;
    }

    public void synchronizeVehicleState() {
        VehicleState state =
                kuksaAdapter.readCurrentState(VEHICLE_ID);

        if (state == null) {
            throw new IllegalStateException(
                    "Kuksa returned no state for vehicle-001"
            );
        }

        if (!VEHICLE_ID.equals(state.vehicleId())) {
            throw new IllegalStateException(
                    "Kuksa returned state for unexpected vehicle: "
                            + state.vehicleId()
            );
        }

        stateProvider.updateState(state);
        dittoSynchronizationService.synchronize(state);
    }
}