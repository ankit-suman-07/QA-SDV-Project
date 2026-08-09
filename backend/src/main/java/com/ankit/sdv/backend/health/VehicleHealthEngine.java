package com.ankit.sdv.backend.health;

import com.ankit.sdv.backend.model.HealthResult;
import com.ankit.sdv.backend.model.HealthStatus;
import com.ankit.sdv.backend.model.VehicleState;
import org.springframework.stereotype.Service;

import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class VehicleHealthEngine {

    static final String COOLING_SYSTEM_FAILURE =
            "COOLING_SYSTEM_FAILURE";

    private static final double ACTIVATION_TEMPERATURE_CELSIUS =
            105.0;

    private static final double ACTIVATION_COOLANT_PRESSURE_KPA =
            150.0;

    private static final double RECOVERY_TEMPERATURE_CELSIUS =
            100.0;

    private static final double RECOVERY_COOLANT_PRESSURE_KPA =
            180.0;

    private final Set<String> vehiclesWithActiveCoolingFault =
            ConcurrentHashMap.newKeySet();

    public HealthResult evaluate(VehicleState state) {
        String vehicleId = state.vehicleId();

        boolean faultActive =
                vehiclesWithActiveCoolingFault.contains(vehicleId);

        if (!faultActive && shouldActivateFault(state)) {
            vehiclesWithActiveCoolingFault.add(vehicleId);
            faultActive = true;
        } else if (faultActive && shouldClearFault(state)) {
            vehiclesWithActiveCoolingFault.remove(vehicleId);
            faultActive = false;
        }

        if (faultActive) {
            return new HealthResult(
                    HealthStatus.CRITICAL,
                    Set.of(COOLING_SYSTEM_FAILURE)
            );
        }

        if (hasOneAbnormalCoolingSignal(state)) {
            return new HealthResult(
                    HealthStatus.WARNING,
                    Set.of()
            );
        }

        return new HealthResult(
                HealthStatus.HEALTHY,
                Set.of()
        );
    }

    private boolean shouldActivateFault(VehicleState state) {
        return state.temperatureCelsius()
                >= ACTIVATION_TEMPERATURE_CELSIUS
                && state.coolantPressureKpa()
                <= ACTIVATION_COOLANT_PRESSURE_KPA;
    }

    private boolean shouldClearFault(VehicleState state) {
        return state.temperatureCelsius()
                <= RECOVERY_TEMPERATURE_CELSIUS
                && state.coolantPressureKpa()
                >= RECOVERY_COOLANT_PRESSURE_KPA;
    }

    private boolean hasOneAbnormalCoolingSignal(
            VehicleState state
    ) {
        boolean highTemperature =
                state.temperatureCelsius()
                        >= ACTIVATION_TEMPERATURE_CELSIUS;

        boolean lowCoolantPressure =
                state.coolantPressureKpa()
                        <= ACTIVATION_COOLANT_PRESSURE_KPA;

        return highTemperature || lowCoolantPressure;
    }
}