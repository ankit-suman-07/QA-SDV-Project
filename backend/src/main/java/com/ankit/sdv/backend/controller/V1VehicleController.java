package com.ankit.sdv.backend.controller;

import com.ankit.sdv.backend.dto.V1VehicleResponse;
import com.ankit.sdv.backend.service.V1VehicleService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/vehicles")
public class V1VehicleController {
    private final V1VehicleService vehicles;

    public V1VehicleController(V1VehicleService vehicles) { this.vehicles = vehicles; }

    @GetMapping
    public VehicleIds list() { return new VehicleIds(vehicles.vehicleIds()); }

    @GetMapping({"/{vehicleId}/state", "/{vehicleId}/health"})
    public V1VehicleResponse read(@PathVariable String vehicleId) { return vehicles.read(vehicleId); }

    public record VehicleIds(List<String> vehicleIds) {}
}
