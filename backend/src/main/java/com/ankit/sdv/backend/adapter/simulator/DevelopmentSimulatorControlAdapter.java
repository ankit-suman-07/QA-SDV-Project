package com.ankit.sdv.backend.adapter.simulator;

import com.ankit.sdv.backend.model.DiagnosticAction;
import com.ankit.sdv.backend.model.DiagnosticScenario;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(
        name = "sdv.simulator.mode",
        havingValue = "development",
        matchIfMissing = true
)
public class DevelopmentSimulatorControlAdapter
        implements SimulatorControlAdapter {

    private static final Logger LOGGER =
            LoggerFactory.getLogger(
                    DevelopmentSimulatorControlAdapter.class
            );

    @Override
    public void executeAction(
            String vehicleId,
            DiagnosticAction action,
            DiagnosticScenario scenario,
            String actionId,
            String traceId
    ) {
        LOGGER.info(
                "Development simulator action: vehicleId={}, "
                        + "action={}, scenario={}, actionId={}, "
                        + "traceId={}",
                vehicleId,
                action,
                scenario,
                actionId,
                traceId
        );
    }
}