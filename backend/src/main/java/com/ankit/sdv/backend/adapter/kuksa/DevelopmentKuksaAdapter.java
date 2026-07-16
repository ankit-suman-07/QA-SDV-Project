package com.ankit.sdv.backend.adapter.kuksa;

import com.ankit.sdv.backend.model.VehicleState;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.time.Instant;

@Component
@ConditionalOnProperty(
        name = "sdv.kuksa.mode",
        havingValue = "development",
        matchIfMissing = true
)
public class DevelopmentKuksaAdapter implements KuksaAdapter {

    private static final double DEVELOPMENT_TEMPERATURE_CELSIUS =
            85.0;

    @Override
    public VehicleState readCurrentState(String vehicleId) {
        return new VehicleState(
                vehicleId,
                Instant.now(),
                DEVELOPMENT_TEMPERATURE_CELSIUS
        );
    }
}