package com.ankit.sdv.backend.controller;

import com.ankit.sdv.backend.dto.VehicleHealthResponse;
import com.ankit.sdv.backend.service.VehicleHealthService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/vehicles")
public class VehicleHealthController {

    private final VehicleHealthService vehicleHealthService;

    public VehicleHealthController(
            VehicleHealthService vehicleHealthService
    ) {
        this.vehicleHealthService = vehicleHealthService;
    }

    @GetMapping("/{vehicleId}/health")
    public VehicleHealthResponse getVehicleHealth(
            @PathVariable String vehicleId
    ) {
        return vehicleHealthService.getCurrentHealth(vehicleId);
    }
}