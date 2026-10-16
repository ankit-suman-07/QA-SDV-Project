package com.ankit.sdv.backend.scheduler;

import com.ankit.sdv.backend.service.VehicleIntegrationService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class VehiclePipelineScheduler {

    private final VehicleIntegrationService integrationService;
    private final List<String> vehicleIds;

    public VehiclePipelineScheduler(
            VehicleIntegrationService integrationService,
            @Value("${sdv.vehicles.ids:vehicle-001}")
            List<String> vehicleIds
    ) {
        this.integrationService = integrationService;
        this.vehicleIds = normalizeVehicleIds(vehicleIds);
    }

    @Scheduled(
            fixedDelayString = "${sdv.pipeline.interval-ms:1000}",
            initialDelayString = "${sdv.pipeline.initial-delay-ms:2000}"
    )
    public void synchronizeVehicles() {
        vehicleIds.forEach(
                integrationService::synchronizeVehicleState
        );
    }

    private List<String> normalizeVehicleIds(
            List<String> configuredVehicleIds
    ) {
        List<String> normalizedVehicleIds =
                configuredVehicleIds.stream()
                        .map(String::trim)
                        .filter(vehicleId -> !vehicleId.isBlank())
                        .distinct()
                        .toList();

        if (normalizedVehicleIds.isEmpty()) {
            throw new IllegalArgumentException(
                    "At least one vehicle ID must be configured"
            );
        }

        return normalizedVehicleIds;
    }
}