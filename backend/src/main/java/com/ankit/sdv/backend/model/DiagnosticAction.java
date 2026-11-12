package com.ankit.sdv.backend.model;

import com.fasterxml.jackson.annotation.JsonCreator;
import tools.jackson.databind.JsonNode;

public enum DiagnosticAction {
    INJECT_SCENARIO, CLEAR_SCENARIO;

    @JsonCreator(mode = JsonCreator.Mode.DELEGATING)
    public static DiagnosticAction fromJson(JsonNode value) {
        if (!value.isTextual()) throw new IllegalArgumentException("Diagnostic action must be a string");
        return valueOf(value.asText());
    }
}
