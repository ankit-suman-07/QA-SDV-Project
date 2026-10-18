package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.adapter.simulator.SimulatorControlAdapter;
import com.ankit.sdv.backend.dto.DiagnosticActionRequest;
import com.ankit.sdv.backend.dto.DiagnosticActionResponse;
import com.ankit.sdv.backend.model.DiagnosticActionStatus;
import com.ankit.sdv.backend.support.ActionIdGenerator;
import com.ankit.sdv.backend.registry.VehicleRegistry;
import org.springframework.stereotype.Service;

import java.util.NoSuchElementException;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

import java.time.Clock;
import java.time.Instant;
import java.util.Objects;

@Service
public class DefaultDiagnosticActionService
        implements DiagnosticActionService {

//     private static final String SUPPORTED_VEHICLE_ID =
//             "vehicle-001";

    private final ConcurrentMap<String, DiagnosticActionResponse>
            actionsById = new ConcurrentHashMap<>();




    private final SimulatorControlAdapter simulatorControlAdapter;
    private final VehicleRegistry vehicleRegistry;
    private final ActionIdGenerator actionIdGenerator;
    private final Clock clock;

    public DefaultDiagnosticActionService(
        SimulatorControlAdapter simulatorControlAdapter,
        ActionIdGenerator actionIdGenerator,
        Clock clock,
        VehicleRegistry vehicleRegistry
) {
    this.simulatorControlAdapter =
            simulatorControlAdapter;
    this.actionIdGenerator =
            actionIdGenerator;
    this.clock = clock;
    this.vehicleRegistry = vehicleRegistry;
}


    @Override
    public DiagnosticActionResponse submit(
            DiagnosticActionRequest request
    ) {
        Objects.requireNonNull(
                request,
                "Diagnostic action request cannot be null"
        );

        //validateVehicleId(request.vehicleId());
        vehicleRegistry.requireRegistered(request.vehicleId());

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

        actionsById.put(actionId, response);

        simulatorControlAdapter.executeAction(
                request.vehicleId(),
                request.action(),
                request.scenario(),
                actionId,
                traceId
        );

        return response;
    }

    @Override
    public DiagnosticActionResponse getById(String actionId) {
        Objects.requireNonNull(
                actionId,
                "Diagnostic action ID cannot be null"
        );

        DiagnosticActionResponse response =
                actionsById.get(actionId);

        if (response == null) {
            throw new NoSuchElementException(
                    "Diagnostic action not found: " + actionId
            );
        }

        return response;
    }

    @Override
    public DiagnosticActionResponse updateStatus(
            String actionId,
            DiagnosticActionStatus status
    ) {
        Objects.requireNonNull(
                actionId,
                "Diagnostic action ID cannot be null"
        );

        Objects.requireNonNull(
                status,
                "Diagnostic action status cannot be null"
        );

        DiagnosticActionResponse updated =
                actionsById.computeIfPresent(
                        actionId,
                        (id, current) -> {
                            if (!isValidTransition(
                                    current.status(),
                                    status
                            )) {
                                throw new IllegalStateException(
                                        "Invalid diagnostic action "
                                                + "status transition: "
                                                + current.status()
                                                + " -> "
                                                + status
                                );
                            }

                            return new DiagnosticActionResponse(
                                    current.actionId(),
                                    current.traceId(),
                                    current.vehicleId(),
                                    current.action(),
                                    current.scenario(),
                                    status,
                                    current.requestedAt()
                            );
                        }
                );

        if (updated == null) {
            throw new NoSuchElementException(
                    "Diagnostic action not found: " + actionId
            );
        }

        return updated;
    }

//     private void validateVehicleId(String vehicleId) {
//         if (!SUPPORTED_VEHICLE_ID.equals(vehicleId)) {
//             throw new IllegalArgumentException(
//                     "Unsupported vehicle ID: " + vehicleId
//             );
//         }
//     }

    private boolean isValidTransition(
            DiagnosticActionStatus current,
            DiagnosticActionStatus requested
    ) {
        if (current == requested) {
            return true;
        }

        return switch (current) {
            case ACCEPTED ->
                    requested == DiagnosticActionStatus.IN_PROGRESS
                            || requested
                            == DiagnosticActionStatus.REJECTED;

            case IN_PROGRESS ->
                    requested == DiagnosticActionStatus.COMPLETED
                            || requested
                            == DiagnosticActionStatus.FAILED;

            case COMPLETED, FAILED, REJECTED -> false;
        };
    }

}