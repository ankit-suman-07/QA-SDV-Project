package com.ankit.sdv.backend.controller;

import com.ankit.sdv.backend.dto.FleetResponse;
import com.ankit.sdv.backend.service.FleetService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class FleetController {
    private final FleetService fleet;
    public FleetController(FleetService fleet) { this.fleet = fleet; }
    @GetMapping("/api/v1/fleet") public FleetResponse read() { return fleet.read(); }
}
