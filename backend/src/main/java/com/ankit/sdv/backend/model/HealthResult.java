package com.ankit.sdv.backend.model;

import java.util.Objects;
import java.util.Set;

public record HealthResult(
        HealthStatus status,
        Set<String> activeFaults
) {

    public HealthResult {
        Objects.requireNonNull(
                status,
                "Health status cannot be null"
        );

        activeFaults = Set.copyOf(
                Objects.requireNonNull(
                        activeFaults,
                        "Active faults cannot be null"
                )
        );
    }

    public HealthResult(HealthStatus status) {
        this(status, Set.of());
    }
}