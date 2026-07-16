package com.ankit.sdv.backend.adapter.opensovd;

import com.ankit.sdv.backend.model.HealthResult;
import com.ankit.sdv.backend.model.VehicleState;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.util.concurrent.atomic.AtomicReference;

@Component
@ConditionalOnProperty(
        name = "sdv.opensovd.mode",
        havingValue = "development",
        matchIfMissing = true
)
public class DevelopmentOpenSovdAdapter
        implements OpenSovdAdapter {

    private final AtomicReference<DiagnosticSnapshot>
            lastDiagnostic = new AtomicReference<>();

    @Override
    public void updateDiagnosticState(
            VehicleState vehicleState,
            HealthResult healthResult
    ) {
        lastDiagnostic.set(
                new DiagnosticSnapshot(
                        vehicleState,
                        healthResult
                )
        );
    }

    public DiagnosticSnapshot getLastDiagnostic() {
        return lastDiagnostic.get();
    }

    public record DiagnosticSnapshot(
            VehicleState vehicleState,
            HealthResult healthResult
    ) {
    }
}