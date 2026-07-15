package com.ankit.sdv.backend.controller;

import com.ankit.sdv.backend.dto.VehicleHealthResponse;
import com.ankit.sdv.backend.model.HealthStatus;
import com.ankit.sdv.backend.service.VehicleHealthService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(VehicleHealthController.class)
class VehicleHealthControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private VehicleHealthService vehicleHealthService;

    @Test
    void shouldReturnCurrentVehicleHealth() throws Exception {
        when(vehicleHealthService.getCurrentHealth("vehicle-001"))
                .thenReturn(
                        new VehicleHealthResponse(
                                "vehicle-001",
                                HealthStatus.HEALTHY
                        )
                );

        mockMvc.perform(
                        get("/api/vehicles/vehicle-001/health")
                )
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.vehicleId")
                        .value("vehicle-001"))
                .andExpect(jsonPath("$.healthStatus")
                        .value("HEALTHY"));
    }
}