package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.config.V1DittoProperties;
import com.ankit.sdv.backend.dto.FleetResponse;
import com.ankit.sdv.backend.dto.V1VehicleResponse;
import com.ankit.sdv.backend.dto.V2VehicleResponse;
import com.ankit.sdv.backend.dto.VehicleProjection;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.function.BiFunction;
import java.util.function.Function;
import java.util.ArrayList;
import java.util.concurrent.*;

@Service
public class FleetService implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(FleetService.class);
    private final V1VehicleService vehicles;
    private final V1DittoProperties config;
    private final V2VehicleService v2;
    private volatile FleetResponse<V2VehicleResponse> latestV2;
    private final Clock clock;
    private final ExecutorService reads = Executors.newVirtualThreadPerTaskExecutor();

    public FleetService(V1VehicleService vehicles, V1DittoProperties config, Clock clock, V2VehicleService v2) {
        this.vehicles = vehicles;
        this.config = config;
        this.clock = clock;
        this.v2 = v2;
    }

    public FleetResponse<V1VehicleResponse> read() {
        return read(vehicles.vehicleIds().stream().distinct().sorted().toList(), vehicles::readAt,
                id -> V1VehicleResponse.unavailable(id, config.things().get(id)));
    }

    public FleetResponse<V2VehicleResponse> readV2() {
        var latest = latestV2;
        return latest == null ? read(v2.vehicleIds(), v2::readAt, v2::unavailable) : latest;
    }

    /** The sole writer publishes and exposes the same immutable projection, even on write failure. */
    FleetResponse<V2VehicleResponse> refreshV2() {
        var snapshot = read(v2.vehicleIds(), v2::readAt, v2::unavailable);
        latestV2 = snapshot;
        return snapshot;
    }

    private <T extends VehicleProjection> FleetResponse<T> read(List<String> ids,
            BiFunction<String, Instant, T> readVehicle, Function<String, T> unavailableVehicle) {
        var evaluation = clock.instant();
        long deadline = System.nanoTime() + config.readTimeout().toNanos();
        var pending = ids.stream().map(id -> reads.submit(() -> readVehicle.apply(id, evaluation))).toList();
        var views = new ArrayList<T>();
        try {
            for (int i = 0; i < ids.size(); i++) {
                var task = pending.get(i);
                T view;
                try {
                    // Completed independent reads survive even if a previous read exhausted the budget.
                    view = task.isDone() ? task.get() : task.get(Math.max(0, deadline - System.nanoTime()), TimeUnit.NANOSECONDS);
                } catch (TimeoutException | ExecutionException error) {
                    task.cancel(true);
                    LOG.warn("fleet_read_failed vehicle={} code=UNAVAILABLE", ids.get(i));
                    view = unavailableVehicle.apply(ids.get(i));
                } catch (InterruptedException error) {
                    Thread.currentThread().interrupt();
                    task.cancel(true);
                    view = unavailableVehicle.apply(ids.get(i));
                }
                views.add(view);
            }
        } finally {
            pending.forEach(task -> { if (!task.isDone()) task.cancel(true); });
        }
        int available = 0, stale = 0, unavailable = 0, healthy = 0, warning = 0, critical = 0;
        for (var view : views) {
            switch (view.availability()) {
                case "AVAILABLE" -> {
                    available++;
                    switch (view.healthStatus()) {
                        case "HEALTHY" -> healthy++;
                        case "WARNING" -> warning++;
                        case "CRITICAL" -> critical++;
                        default -> throw new IllegalStateException("Invalid trusted health");
                    }
                }
                case "STALE" -> stale++;
                case "UNAVAILABLE" -> unavailable++;
                default -> throw new IllegalStateException("Invalid trusted availability");
            }
        }
        return new FleetResponse<>(evaluation, views.size(), available, stale, unavailable, healthy, warning, critical, views);
    }

    @Override public void close() { reads.shutdownNow(); }
}
