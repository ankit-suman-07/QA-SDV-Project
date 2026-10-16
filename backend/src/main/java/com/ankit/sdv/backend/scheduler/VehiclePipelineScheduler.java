package com.ankit.sdv.backend.scheduler;

import com.ankit.sdv.backend.registry.VehicleRegistry;
import com.ankit.sdv.backend.service.VehicleIntegrationService;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class VehiclePipelineScheduler {

    private final VehicleIntegrationService integrationService;
    private final VehicleRegistry vehicleRegistry;

    public VehiclePipelineScheduler(
            VehicleIntegrationService integrationService,
            VehicleRegistry vehicleRegistry
    ) {
        this.integrationService = integrationService;
        this.vehicleRegistry = vehicleRegistry;
    }

    @Scheduled(
            fixedDelayString =
                    "${sdv.pipeline.interval-ms:1000}",
            initialDelayString =
                    "${sdv.pipeline.initial-delay-ms:2000}"
    )
    public void synchronizeVehicles() {
        for (String vehicleId : vehicleRegistry.vehicleIds()) {
            integrationService.synchronizeVehicleState(vehicleId);
        }
    }
}