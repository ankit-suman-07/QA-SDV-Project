package com.ankit.sdv.backend.scheduler;

import com.ankit.sdv.backend.service.VehicleIntegrationService;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class VehiclePipelineScheduler {

    private final VehicleIntegrationService integrationService;

    public VehiclePipelineScheduler(
            VehicleIntegrationService integrationService
    ) {
        this.integrationService = integrationService;
    }

    @Scheduled(
            fixedDelayString = "${sdv.pipeline.interval-ms:1000}",
            initialDelayString = "${sdv.pipeline.initial-delay-ms:2000}"
    )
    public void synchronizeVehicle() {
        integrationService.synchronizeVehicleState();
    }
}