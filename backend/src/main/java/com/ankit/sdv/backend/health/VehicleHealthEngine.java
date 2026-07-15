package com.ankit.sdv.backend.health;

import com.ankit.sdv.backend.model.HealthResult;
import com.ankit.sdv.backend.model.HealthStatus;
import com.ankit.sdv.backend.model.VehicleState;
import org.springframework.stereotype.Service;

@Service
public class VehicleHealthEngine {

    private static final double CRITICAL_TEMPERATURE_CELSIUS = 105.0;

    public HealthResult evaluate(VehicleState state) {
        if (state.temperatureCelsius()
                >= CRITICAL_TEMPERATURE_CELSIUS) {
            return new HealthResult(HealthStatus.CRITICAL);
        }

        return new HealthResult(HealthStatus.HEALTHY);
    }
}