
package com.ankit.sdv.backend.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.messaging.Message;
import org.springframework.stereotype.Service;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.time.Duration;
import java.time.Instant;
import java.util.Arrays;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Service
@ConditionalOnProperty(
        name = "sdv.mqtt.enabled",
        havingValue = "true"
)
public class VehicleEventConsumer {

    private static final Logger logger =
            LoggerFactory.getLogger(VehicleEventConsumer.class);

    private static final Duration MAX_AGE =
            Duration.ofSeconds(30);

    private static final Duration FUTURE_TOLERANCE =
            Duration.ofSeconds(5);

    private static final Duration STALE_TIMEOUT =
            Duration.ofSeconds(10);

    private final ObjectMapper objectMapper;
    private final Set<String> allowedVehicles;

    private final ConcurrentHashMap<String, EventSnapshot>
            latestEvents = new ConcurrentHashMap<>();

    public VehicleEventConsumer(
            ObjectMapper objectMapper,
            @Value("${sdv.vehicles.ids}") String vehicleIds
    ) {
        this.objectMapper = objectMapper;
        this.allowedVehicles = Arrays.stream(
                vehicleIds.split(",")
        ).map(String::trim)
         .filter(id -> !id.isEmpty())
         .collect(Collectors.toUnmodifiableSet());
    }

    public void receive(Message<String> message) {
        String payload = message.getPayload();

        try {
            JsonNode event = objectMapper.readTree(payload);

            if (event == null || !event.isObject()) {
                logger.warn("Rejected non-object MQTT event");
                return;
            }

            JsonNode idNode = event.path("vehicleId");
            JsonNode timeNode = event.path("timestamp");
            JsonNode healthNode = event.path("healthStatus");

            if (!idNode.isTextual()
                    || !timeNode.isTextual()
                    || !healthNode.isTextual()) {
                logger.warn("Rejected event: invalid required fields");
                return;
            }

            String vehicleId = idNode.asText().trim();
            String healthStatus = healthNode.asText().trim();

            if (!allowedVehicles.contains(vehicleId)
                    || healthStatus.isEmpty()) {
                logger.warn(
                        "Rejected unknown vehicle or empty status: {}",
                        vehicleId
                );
                return;
            }

            Instant sourceTime =
                    Instant.parse(timeNode.asText());

            Instant now = Instant.now();

            if (sourceTime.isBefore(now.minus(MAX_AGE))
                    || sourceTime.isAfter(
                            now.plus(FUTURE_TOLERANCE))) {
                logger.warn(
                        "Rejected stale/future event: {}",
                        vehicleId
                );
                return;
            }

            EventSnapshot incoming =
                    new EventSnapshot(sourceTime, payload, now);

            EventSnapshot latest = latestEvents.compute(
                    vehicleId,
                    (id, previous) -> {
                        if (previous == null
                                || sourceTime.isAfter(
                                        previous.timestamp())) {
                            return incoming;
                        }
                        return previous;
                    }
            );

            if (latest != incoming) {
                logger.info(
                        "Ignored duplicate/older event: {}",
                        vehicleId
                );
                return;
            }

            logger.info(
                    "Accepted MQTT event: vehicle={}, health={}",
                    vehicleId,
                    healthStatus
            );

            // TODO: Forward validated events to the
            // agreed backend/twin update service.

        } catch (Exception ex) {
            logger.warn(
                    "Rejected malformed MQTT event: {}",
                    ex.getMessage()
            );
        }
    }

    String latestPayloadFor(String vehicleId) {
        EventSnapshot snapshot = latestEvents.get(vehicleId);
        return snapshot == null ? null : snapshot.payload();
    }

    // Vehicle availability based on last received event
    public enum Availability {
        UNKNOWN,
        LIVE,
        STALE
    }

    public Availability getAvailability(String vehicleId) {
        return availabilityAt(vehicleId, Instant.now());
    }

    Availability availabilityAt(String vehicleId, Instant now) {
        EventSnapshot snapshot = latestEvents.get(vehicleId);

        if (snapshot == null) {
            return Availability.UNKNOWN;
        }

        if (!snapshot.receivedAt().isAfter(
                now.minus(STALE_TIMEOUT))) {
            return Availability.STALE;
        }

        return Availability.LIVE;
    }

    private record EventSnapshot(
            Instant timestamp,
            String payload,
            Instant receivedAt
    ) {}
    
}
