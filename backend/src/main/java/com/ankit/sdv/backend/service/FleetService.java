package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.config.V1DittoProperties;
import com.ankit.sdv.backend.dto.FleetResponse;
import com.ankit.sdv.backend.dto.V1VehicleResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.util.ArrayList;
import java.util.concurrent.*;

@Service
public class FleetService implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(FleetService.class);
    private final V1VehicleService vehicles;
    private final V1DittoProperties config;
    private final Clock clock;
    private final ExecutorService reads = Executors.newVirtualThreadPerTaskExecutor();

    public FleetService(V1VehicleService vehicles, V1DittoProperties config, Clock clock) {
        this.vehicles = vehicles;
        this.config = config;
        this.clock = clock;
    }

    public FleetResponse read() {
        var evaluation = clock.instant();
        var ids = vehicles.vehicleIds().stream().distinct().sorted().toList();
        // Submit both reads before waiting. One deadline includes headers, body and parsing.
        long deadline = System.nanoTime() + config.readTimeout().toNanos();
        var pending = ids.stream().map(id -> reads.submit(() -> vehicles.readAt(id, evaluation))).toList();
        var views = new ArrayList<V1VehicleResponse>();
        try {
            for (int i = 0; i < ids.size(); i++) {
                var task = pending.get(i);
                V1VehicleResponse view;
                try {
                    // Completed independent reads survive even if a previous read exhausted the budget.
                    view = task.isDone() ? task.get() : task.get(Math.max(0, deadline - System.nanoTime()), TimeUnit.NANOSECONDS);
                } catch (TimeoutException | ExecutionException error) {
                    task.cancel(true);
                    LOG.warn("fleet_read_failed vehicle={} code=UNAVAILABLE", ids.get(i));
                    view = V1VehicleResponse.unavailable(ids.get(i), config.things().get(ids.get(i)));
                } catch (InterruptedException error) {
                    Thread.currentThread().interrupt();
                    task.cancel(true);
                    view = V1VehicleResponse.unavailable(ids.get(i), config.things().get(ids.get(i)));
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
        return new FleetResponse(evaluation, views.size(), available, stale, unavailable, healthy, warning, critical, views);
    }

    @Override public void close() { reads.shutdownNow(); }
}
