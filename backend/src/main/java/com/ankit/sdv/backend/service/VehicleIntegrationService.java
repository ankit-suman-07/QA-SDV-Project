package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.adapter.kuksa.KuksaAdapter;
import com.ankit.sdv.backend.health.VehicleHealthEngine;
import com.ankit.sdv.backend.model.HealthResult;
import com.ankit.sdv.backend.model.VehicleState;
import com.ankit.sdv.backend.provider.InMemoryVehicleStateProvider;
import org.springframework.stereotype.Service;

@Service
public class VehicleIntegrationService {

//     private static final String LEGACY_DEFAULT_VEHICLE_ID =
//             "vehicle-001";

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



    public void synchronizeVehicleState(String vehicleId) {
        validateRequestedVehicleId(vehicleId);

        VehicleState state =
                kuksaAdapter.readCurrentState(vehicleId);

        validateState(vehicleId, state);

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

    private void validateRequestedVehicleId(String vehicleId) {
        if (vehicleId == null || vehicleId.isBlank()) {
            throw new IllegalArgumentException(
                    "Vehicle ID must not be blank"
            );
        }
    }

    private void validateState(
            String requestedVehicleId,
            VehicleState state
    ) {
        if (state == null) {
            throw new IllegalStateException(
                    "Kuksa returned no state for "
                            + requestedVehicleId
            );
        }

        if (!requestedVehicleId.equals(state.vehicleId())) {
            throw new IllegalStateException(
                    "Kuksa returned state for unexpected vehicle: "
                            + state.vehicleId()
                            + "; expected: "
                            + requestedVehicleId
            );
        }
    }
}