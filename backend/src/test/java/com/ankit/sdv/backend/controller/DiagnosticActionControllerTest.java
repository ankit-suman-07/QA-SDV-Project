package com.ankit.sdv.backend.controller;

import com.ankit.sdv.backend.dto.DiagnosticActionRequest;
import com.ankit.sdv.backend.dto.DiagnosticActionResponse;
import com.ankit.sdv.backend.model.DiagnosticAction;
import com.ankit.sdv.backend.model.DiagnosticActionStatus;
import com.ankit.sdv.backend.model.DiagnosticScenario;
import com.ankit.sdv.backend.service.DiagnosticActionService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Instant;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(DiagnosticActionController.class)
class DiagnosticActionControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private DiagnosticActionService diagnosticActionService;

    @Test
    void shouldAcceptCoolingSystemFailureInjection()
            throws Exception {

        Instant requestedAt =
                Instant.parse("2026-08-03T17:00:00Z");

        when(diagnosticActionService.submit(
                any(DiagnosticActionRequest.class)
        )).thenReturn(
                new DiagnosticActionResponse(
                        "action-001",
                        "action-001",
                        "vehicle-001",
                        DiagnosticAction.INJECT_SCENARIO,
                        DiagnosticScenario.COOLING_SYSTEM_FAILURE,
                        DiagnosticActionStatus.ACCEPTED,
                        requestedAt
                )
        );

        mockMvc.perform(
                        post("/api/v1/diagnostics/actions")
                                .contentType(
                                        MediaType.APPLICATION_JSON
                                )
                                .content("""
                                        {
                                          "vehicleId": "vehicle-001",
                                          "action": "INJECT_SCENARIO",
                                          "scenario": "COOLING_SYSTEM_FAILURE"
                                        }
                                        """)
                )
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.actionId")
                        .value("action-001"))
                .andExpect(jsonPath("$.traceId")
                        .value("action-001"))
                .andExpect(jsonPath("$.vehicleId")
                        .value("vehicle-001"))
                .andExpect(jsonPath("$.action")
                        .value("INJECT_SCENARIO"))
                .andExpect(jsonPath("$.scenario")
                        .value("COOLING_SYSTEM_FAILURE"))
                .andExpect(jsonPath("$.status")
                        .value("ACCEPTED"))
                .andExpect(jsonPath("$.requestedAt")
                        .value("2026-08-03T17:00:00Z"));
    }
}