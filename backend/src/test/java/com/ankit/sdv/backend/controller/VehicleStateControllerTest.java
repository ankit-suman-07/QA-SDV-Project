package com.ankit.sdv.backend.controller;

import com.ankit.sdv.backend.model.VehicleState;
import com.ankit.sdv.backend.provider.VehicleStateProvider;
import com.ankit.sdv.backend.service.VehicleHealthService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Instant;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(VehicleStateController.class)
class VehicleStateControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private VehicleStateProvider vehicleStateProvider;

    @Test
    void shouldReturnCurrentVehicleState() throws Exception {
        VehicleState state = new VehicleState(
                "vehicle-001",
                Instant.parse("2026-07-15T16:00:00Z"),
                85.0,
                200.0
        );
        when(vehicleStateProvider.getCurrentState("vehicle-001"))
                .thenReturn(state);

        mockMvc.perform(
                        get("/api/vehicles/vehicle-001/state")
                )
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.vehicleId")
                        .value("vehicle-001"))
                .andExpect(jsonPath("$.sourceTimestamp")
                        .value("2026-07-15T16:00:00Z"))
                .andExpect(jsonPath("$.temperatureCelsius")
                        .value(85.0));
    }

    @Test
void shouldReturnStateForVehicle002() throws Exception {
    VehicleState state = new VehicleState(
            "vehicle-002",
            Instant.parse("2026-07-15T16:05:00Z"),
            90.0,
            180.0
    );

    when(vehicleStateProvider.getCurrentState("vehicle-002"))
            .thenReturn(state);

    mockMvc.perform(
                    get("/api/vehicles/vehicle-002/state")
            )
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.vehicleId")
                    .value("vehicle-002"))
            .andExpect(jsonPath("$.sourceTimestamp")
                    .value("2026-07-15T16:05:00Z"))
            .andExpect(jsonPath("$.temperatureCelsius")
                    .value(90.0));
}
        @Test
void shouldReturnNotFoundWhenVehicleStateDoesNotExist()
        throws Exception {

    when(vehicleStateProvider.getCurrentState("vehicle-999"))
            .thenReturn(null);

    mockMvc.perform(
                    get("/api/vehicles/vehicle-999/state")
            )
            .andExpect(status().isNotFound())
            .andExpect(jsonPath("$.code")
                    .value("VEHICLE_NOT_FOUND"))
            .andExpect(jsonPath("$.message")
                    .value("Vehicle state not found: vehicle-999"));
}
}