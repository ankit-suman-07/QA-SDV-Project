package com.ankit.sdv.backend.registry;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Objects;

@Component
public class VehicleRegistry {

    private final List<String> vehicleIds;

    public VehicleRegistry(
            @Value("${sdv.vehicles.ids:vehicle-001}")
            List<String> configuredVehicleIds
    ) {
        Objects.requireNonNull(
                configuredVehicleIds,
                "Configured vehicle IDs cannot be null"
        );

        this.vehicleIds = configuredVehicleIds.stream()
                .filter(Objects::nonNull)
                .map(String::trim)
                .filter(vehicleId -> !vehicleId.isBlank())
                .distinct()
                .toList();

        if (vehicleIds.isEmpty()) {
            throw new IllegalArgumentException(
                    "At least one vehicle ID must be configured"
            );
        }
    }

    public List<String> vehicleIds() {
        return vehicleIds;
    }

    public boolean contains(String vehicleId) {
        return vehicleId != null
                && vehicleIds.contains(vehicleId.trim());
    }

    public void requireRegistered(String vehicleId) {
        if (!contains(vehicleId)) {
            throw new IllegalArgumentException(
                    "Unsupported vehicle ID: " + vehicleId
            );
        }
    }
}