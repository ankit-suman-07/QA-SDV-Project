package com.ankit.sdv.backend.dto;

import java.time.Instant;
import java.util.List;

/** Exact C7 projection, derived only from individually validated observations. */
public record FleetResponse(Instant generatedAt, int totalVehicles, int availableVehicles,
        int staleVehicles, int unavailableVehicles, int healthyVehicles, int warningVehicles,
        int criticalVehicles, List<V1VehicleResponse> vehicles) {
    public FleetResponse { vehicles = List.copyOf(vehicles); }
}
