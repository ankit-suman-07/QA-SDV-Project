package com.ankit.sdv.backend.adapter.ditto;

import com.ankit.sdv.backend.model.VehicleState;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.util.concurrent.atomic.AtomicReference;

@Component
@ConditionalOnProperty(
        name = "sdv.ditto.mode",
        havingValue = "development",
        matchIfMissing = true
)
public class DevelopmentDittoAdapter
        implements DittoAdapter {

    private final AtomicReference<VehicleState> lastUpdatedState =
            new AtomicReference<>();

    @Override
    public void updateVehicleState(VehicleState vehicleState) {
        lastUpdatedState.set(vehicleState);
    }

    public VehicleState getLastUpdatedState() {
        return lastUpdatedState.get();
    }
}