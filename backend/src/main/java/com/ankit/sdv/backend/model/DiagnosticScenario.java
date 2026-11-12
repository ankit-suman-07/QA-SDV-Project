package com.ankit.sdv.backend.model;

import com.fasterxml.jackson.annotation.JsonCreator;
import tools.jackson.databind.JsonNode;

public enum DiagnosticScenario {
    COOLING_SYSTEM_FAILURE, LIDAR_OBSTRUCTION;

    @JsonCreator(mode = JsonCreator.Mode.DELEGATING)
    public static DiagnosticScenario fromJson(JsonNode value) {
        if (!value.isTextual()) throw new IllegalArgumentException("Diagnostic scenario must be a string");
        return valueOf(value.asText());
    }
}
