package com.ankit.sdv.backend.scheduler;

import com.ankit.sdv.backend.service.VehicleIntegrationService;
import com.ankit.sdv.backend.registry.VehicleRegistry;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

class VehiclePipelineSchedulerTest {

    @Test
    void shouldExecutePipelineForEveryConfiguredVehicle() {
        VehicleIntegrationService integrationService =
                mock(VehicleIntegrationService.class);

        VehicleRegistry vehicleRegistry =
                new VehicleRegistry(
                        List.of(
                                "vehicle-001",
                                "vehicle-002",
                                "vehicle-003"
                        )
                );

        VehiclePipelineScheduler scheduler =
                new VehiclePipelineScheduler(
                        integrationService,
                        vehicleRegistry
                );



        scheduler.synchronizeVehicles();

        verify(integrationService)
                .synchronizeVehicleState("vehicle-001");
        verify(integrationService)
                .synchronizeVehicleState("vehicle-002");
        verify(integrationService)
                .synchronizeVehicleState("vehicle-003");
    }
}