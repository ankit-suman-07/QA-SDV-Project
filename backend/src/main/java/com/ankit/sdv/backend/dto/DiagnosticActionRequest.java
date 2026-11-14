package com.ankit.sdv.backend.dto;

import com.ankit.sdv.backend.model.DiagnosticAction;
import com.ankit.sdv.backend.model.DiagnosticScenario;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import tools.jackson.databind.annotation.JsonDeserialize;
import tools.jackson.databind.ValueDeserializer;
import tools.jackson.databind.DeserializationContext;
import tools.jackson.core.JsonParser;
import tools.jackson.core.JsonToken;

public record DiagnosticActionRequest(

        @NotBlank(message = "Vehicle ID is required")
        @JsonDeserialize(using = VehicleIdDeserializer.class)
        String vehicleId,

        @NotNull(message = "Diagnostic action is required")
        DiagnosticAction action,

        @NotNull(message = "Diagnostic scenario is required")
        DiagnosticScenario scenario
) {
    public static class VehicleIdDeserializer extends ValueDeserializer<String> {
        @Override public String deserialize(JsonParser parser, DeserializationContext context) {
            if (parser.currentToken() != JsonToken.VALUE_STRING) {
                return context.reportInputMismatch(String.class, "Vehicle ID must be a string");
            }
            return parser.getString();
        }
    }
}