package com.ankit.sdv.backend.scheduler;

import com.ankit.sdv.backend.service.VehicleIntegrationService;
import org.junit.jupiter.api.Test;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

class VehiclePipelineSchedulerTest {

    @Test
    void shouldExecuteVehicleIntegrationPipeline() {
        VehicleIntegrationService integrationService =
                mock(VehicleIntegrationService.class);

        VehiclePipelineScheduler scheduler =
                new VehiclePipelineScheduler(
                        integrationService
                );

        scheduler.synchronizeVehicle();

        verify(integrationService)
                .synchronizeVehicleState();
    }
}