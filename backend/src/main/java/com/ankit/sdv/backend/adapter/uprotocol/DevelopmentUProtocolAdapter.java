package com.ankit.sdv.backend.adapter.uprotocol;

import com.ankit.sdv.backend.model.VehicleState;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.util.concurrent.atomic.AtomicReference;

@Component
@ConditionalOnProperty(
        name = "sdv.uprotocol.mode",
        havingValue = "development",
        matchIfMissing = true
)
public class DevelopmentUProtocolAdapter
        implements UProtocolAdapter {

    private final AtomicReference<VehicleState> lastPublishedState =
            new AtomicReference<>();

    @Override
    public void publishVehicleStatus(
            VehicleState vehicleState
    ) {
        lastPublishedState.set(vehicleState);
    }

    public VehicleState getLastPublishedState() {
        return lastPublishedState.get();
    }
}