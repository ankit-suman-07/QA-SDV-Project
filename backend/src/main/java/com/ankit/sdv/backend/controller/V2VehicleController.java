package com.ankit.sdv.backend.controller;

import com.ankit.sdv.backend.dto.V2VehicleResponse;
import com.ankit.sdv.backend.service.V2VehicleService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v2/vehicles")
public class V2VehicleController {
    private final V2VehicleService vehicles;

    public V2VehicleController(V2VehicleService vehicles) { this.vehicles = vehicles; }

    @GetMapping
    public VehicleIds list() { return new VehicleIds(vehicles.vehicleIds()); }

    @GetMapping("/{vehicleId}/state")
    public V2VehicleResponse read(@PathVariable String vehicleId) { return vehicles.readAt(vehicleId, null); }

    public record VehicleIds(List<String> vehicleIds) {}
}
