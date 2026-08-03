package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.adapter.simulator.SimulatorControlAdapter;
import com.ankit.sdv.backend.dto.DiagnosticActionRequest;
import com.ankit.sdv.backend.dto.DiagnosticActionResponse;
import com.ankit.sdv.backend.model.DiagnosticActionStatus;
import com.ankit.sdv.backend.support.ActionIdGenerator;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.Instant;
import java.util.Objects;

@Service
public class DefaultDiagnosticActionService
        implements DiagnosticActionService {

    private static final String SUPPORTED_VEHICLE_ID =
            "vehicle-001";

    private final SimulatorControlAdapter simulatorControlAdapter;
    private final ActionIdGenerator actionIdGenerator;
    private final Clock clock;

    public DefaultDiagnosticActionService(
            SimulatorControlAdapter simulatorControlAdapter,
            ActionIdGenerator actionIdGenerator,
            Clock clock
    ) {
        this.simulatorControlAdapter =
                simulatorControlAdapter;
        this.actionIdGenerator =
                actionIdGenerator;
        this.clock = clock;
    }

    @Override
    public DiagnosticActionResponse submit(
            DiagnosticActionRequest request
    ) {
        Objects.requireNonNull(
                request,
                "Diagnostic action request cannot be null"
        );

        validateVehicleId(request.vehicleId());

        String actionId = actionIdGenerator.generate();
        String traceId = actionId;
        Instant requestedAt = clock.instant();

        DiagnosticActionResponse response =
                new DiagnosticActionResponse(
                        actionId,
                        traceId,
                        request.vehicleId(),
                        request.action(),
                        request.scenario(),
                        DiagnosticActionStatus.ACCEPTED,
                        requestedAt
                );

        simulatorControlAdapter.executeAction(
                request.vehicleId(),
                request.action(),
                request.scenario(),
                actionId,
                traceId
        );

        return response;
    }

    private void validateVehicleId(String vehicleId) {
        if (!SUPPORTED_VEHICLE_ID.equals(vehicleId)) {
            throw new IllegalArgumentException(
                    "Unsupported vehicle ID: " + vehicleId
            );
        }
    }
}