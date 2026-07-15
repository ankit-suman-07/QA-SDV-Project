package com.ankit.sdv.backend;

import com.ankit.sdv.backend.service.DittoSynchronizationService;
import com.ankit.sdv.backend.service.VehicleIntegrationService;
import com.ankit.sdv.backend.service.UProtocolEventService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import static org.junit.jupiter.api.Assertions.assertNotNull;

@SpringBootTest
class BackendApplicationTests {

    @Autowired
    private VehicleIntegrationService vehicleIntegrationService;

    @Autowired
    private DittoSynchronizationService dittoSynchronizationService;

    @Autowired
    private UProtocolEventService uProtocolEventService;

    @Test
    void contextLoads() {
        assertNotNull(vehicleIntegrationService);
        assertNotNull(dittoSynchronizationService);
        assertNotNull(uProtocolEventService);
    }
}