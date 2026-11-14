package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.adapter.simulator.SimulatorControlAdapter;
import com.ankit.sdv.backend.dto.DiagnosticActionRequest;
import com.ankit.sdv.backend.dto.DiagnosticActionResponse;
import com.ankit.sdv.backend.exception.InvalidDiagnosticRequestException;
import com.ankit.sdv.backend.exception.ProviderDispatchException;
import com.ankit.sdv.backend.model.DiagnosticActionStatus;
import com.ankit.sdv.backend.model.DiagnosticScenario;
import com.ankit.sdv.backend.model.DispatchStatus;
import com.ankit.sdv.backend.registry.VehicleRegistry;
import com.ankit.sdv.backend.support.ActionIdGenerator;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.Instant;
import java.util.NoSuchElementException;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

@Service
public class DefaultDiagnosticActionService implements DiagnosticActionService {
    private final ConcurrentMap<String, DiagnosticActionResponse> actionsById = new ConcurrentHashMap<>();
    private final SimulatorControlAdapter simulatorControlAdapter;
    private final VehicleRegistry vehicleRegistry;
    private final ActionIdGenerator actionIdGenerator;
    private final Clock clock;

    public DefaultDiagnosticActionService(SimulatorControlAdapter simulatorControlAdapter,
            ActionIdGenerator actionIdGenerator, Clock clock, VehicleRegistry vehicleRegistry) {
        this.simulatorControlAdapter = simulatorControlAdapter;
        this.actionIdGenerator = actionIdGenerator;
        this.clock = clock;
        this.vehicleRegistry = vehicleRegistry;
    }

    @Override public DiagnosticActionResponse submit(DiagnosticActionRequest request) {
        validate(request); // No IDs allocated or provider dispatch on validation failure.
        String actionId = actionIdGenerator.generate();
        String traceId = actionId;
        Instant requestedAt = clock.instant();
        try {
            simulatorControlAdapter.executeAction(request.vehicleId(), request.action(), request.scenario(), actionId, traceId);
        } catch (ProviderDispatchException error) {
            var failed = new DiagnosticActionResponse(actionId, traceId, request.vehicleId(), request.action(),
                    request.scenario(), error.reason().lifecycle, requestedAt, error.reason().dispatch);
            actionsById.put(actionId, failed);
            throw error.correlate(failed);
        }
        // HTTP success has been validated; development mode preserves its old, explicitly simulated response.
        var accepted = new DiagnosticActionResponse(actionId, traceId, request.vehicleId(), request.action(), request.scenario(),
                DiagnosticActionStatus.ACCEPTED, requestedAt,
                simulatorControlAdapter.dispatchAcknowledged() ? DispatchStatus.DISPATCHED : null);
        actionsById.put(actionId, accepted);
        return accepted;
    }

    private void validate(DiagnosticActionRequest request) {
        if (request == null || request.vehicleId() == null || request.vehicleId().isBlank()
                || request.vehicleId().codePoints().anyMatch(c -> Character.isWhitespace(c) || Character.isSpaceChar(c))
                || request.action() == null || request.scenario() == null) {
            throw new InvalidDiagnosticRequestException();
        }
        String id = request.vehicleId();
        if (!vehicleRegistry.vehicleIds().contains(id) || !simulatorControlAdapter.supportsVehicle(id)
                || (request.scenario() == DiagnosticScenario.LIDAR_OBSTRUCTION
                    && !Set.of("vehicle-001", "vehicle-002").contains(id))) {
            throw new IllegalArgumentException("Unsupported vehicle ID");
        }
    }

    @Override public DiagnosticActionResponse getById(String actionId) {
        Objects.requireNonNull(actionId, "Diagnostic action ID cannot be null");
        DiagnosticActionResponse response = actionsById.get(actionId);
        if (response == null) throw new NoSuchElementException("Diagnostic action not found: " + actionId);
        return response;
    }

    @Override public DiagnosticActionResponse updateStatus(String actionId, DiagnosticActionStatus status) {
        Objects.requireNonNull(actionId, "Diagnostic action ID cannot be null");
        Objects.requireNonNull(status, "Diagnostic action status cannot be null");
        var updated = actionsById.computeIfPresent(actionId, (id, current) -> {
            if (!isValidTransition(current.status(), status)) {
                throw new IllegalStateException("Invalid diagnostic action status transition: " + current.status() + " -> " + status);
            }
            return new DiagnosticActionResponse(current.actionId(), current.traceId(), current.vehicleId(), current.action(),
                    current.scenario(), status, current.requestedAt(), current.dispatchStatus());
        });
        if (updated == null) throw new NoSuchElementException("Diagnostic action not found: " + actionId);
        return updated;
    }

    private boolean isValidTransition(DiagnosticActionStatus current, DiagnosticActionStatus requested) {
        if (current == requested) return true;
        return switch (current) {
            case ACCEPTED -> requested == DiagnosticActionStatus.IN_PROGRESS || requested == DiagnosticActionStatus.REJECTED;
            case IN_PROGRESS -> requested == DiagnosticActionStatus.COMPLETED || requested == DiagnosticActionStatus.FAILED;
            case COMPLETED, FAILED, REJECTED -> false;
        };
    }
}
