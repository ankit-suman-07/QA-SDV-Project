package com.ankit.sdv.backend.health;

import com.ankit.sdv.backend.model.HealthResult;
import com.ankit.sdv.backend.model.HealthStatus;
import com.ankit.sdv.backend.model.VehicleState;
import org.springframework.stereotype.Service;

@Service
public class VehicleHealthEngine {

    private static final double WARNING_TEMPERATURE_CELSIUS = 90.0;
    private static final double CRITICAL_TEMPERATURE_CELSIUS = 105.0;

    public HealthResult evaluate(VehicleState state) {
        if (state.temperatureCelsius()
                >= CRITICAL_TEMPERATURE_CELSIUS) {
            return new HealthResult(HealthStatus.CRITICAL);
        }

        if (state.temperatureCelsius()
                >= WARNING_TEMPERATURE_CELSIUS) {
            return new HealthResult(HealthStatus.WARNING);
        }

        return new HealthResult(HealthStatus.HEALTHY);
    }
}