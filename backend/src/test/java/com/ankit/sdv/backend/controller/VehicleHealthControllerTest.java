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

    @Test
    void shouldReturnNotFoundForUnsupportedVehicleId()
            throws Exception {

        when(vehicleHealthService.getCurrentHealth("vehicle-999"))
                .thenThrow(
                        new IllegalArgumentException(
                                "Unsupported vehicle ID: vehicle-999"
                        )
                );

        mockMvc.perform(
                        get("/api/vehicles/vehicle-999/health")
                )
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code")
                        .value("VEHICLE_NOT_FOUND"))
                .andExpect(jsonPath("$.message")
                        .value(
                                "Unsupported vehicle ID: vehicle-999"
                        ))
                .andExpect(jsonPath("$.path")
                        .value(
                                "/api/vehicles/vehicle-999/health"
                        ));
    }
}