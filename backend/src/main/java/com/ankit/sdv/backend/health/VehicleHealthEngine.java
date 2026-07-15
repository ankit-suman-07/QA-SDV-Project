package com.ankit.sdv.backend.health;

import com.ankit.sdv.backend.model.HealthResult;
import com.ankit.sdv.backend.model.VehicleState;
import org.springframework.stereotype.Service;

@Service
public class VehicleHealthEngine {

    public HealthResult evaluate(VehicleState state) {
        throw new UnsupportedOperationException(
                "Health evaluation has not been implemented"
        );
    }
}