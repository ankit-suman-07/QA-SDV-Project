package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.adapter.kuksa.KuksaAdapter;
import com.ankit.sdv.backend.health.VehicleHealthEngine;
import com.ankit.sdv.backend.model.HealthResult;
import com.ankit.sdv.backend.model.VehicleState;
import com.ankit.sdv.backend.provider.InMemoryVehicleStateProvider;
import org.springframework.stereotype.Service;

@Service
public class VehicleIntegrationService {

    private static final String VEHICLE_ID = "vehicle-001";

    private final KuksaAdapter kuksaAdapter;
    private final InMemoryVehicleStateProvider stateProvider;
    private final VehicleHealthEngine vehicleHealthEngine;
    private final DittoSynchronizationService dittoSynchronizationService;
    private final UProtocolEventService uProtocolEventService;
    private final DiagnosticService diagnosticService;

    public VehicleIntegrationService(
            KuksaAdapter kuksaAdapter,
            InMemoryVehicleStateProvider stateProvider,
            VehicleHealthEngine vehicleHealthEngine,
            DittoSynchronizationService dittoSynchronizationService,
            UProtocolEventService uProtocolEventService,
            DiagnosticService diagnosticService
    ) {
        this.kuksaAdapter = kuksaAdapter;
        this.stateProvider = stateProvider;
        this.vehicleHealthEngine = vehicleHealthEngine;
        this.dittoSynchronizationService =
                dittoSynchronizationService;
        this.uProtocolEventService = uProtocolEventService;
        this.diagnosticService = diagnosticService;
    }

    public void synchronizeVehicleState() {
        VehicleState state =
                kuksaAdapter.readCurrentState(VEHICLE_ID);

        validateState(state);

        HealthResult healthResult =
                vehicleHealthEngine.evaluate(state);

        stateProvider.updateState(state);
        dittoSynchronizationService.synchronize(state);
        uProtocolEventService.publishVehicleStatus(state);

        diagnosticService.updateDiagnostics(
                state,
                healthResult
        );
    }

    private void validateState(VehicleState state) {
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
    }
}