
package com.ankit.sdv.backend.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.messaging.support.GenericMessage;
import tools.jackson.databind.ObjectMapper;

import java.time.Instant;
import java.time.temporal.ChronoUnit;

import static org.junit.jupiter.api.Assertions.*;

class VehicleEventConsumerTest {

    private VehicleEventConsumer consumer;

    @BeforeEach
    void setUp() {
        consumer = new VehicleEventConsumer(
                new ObjectMapper(),
                "vehicle-001,vehicle-002"
        );
    }

    private String event(
            String vehicleId,
            Instant timestamp,
            String healthStatus
    ) {
        return """
                {
                  "vehicleId": "%s",
                  "timestamp": "%s",
                  "healthStatus": "%s",
                  "speed": 20.0,
                  "lidarDistanceMeters": 10.0,
                  "lidarSensorHealthy": true,
                  "obstacleWarning": false,
                  "autonomousBraking": false
                }
                """.formatted(
                vehicleId,
                timestamp,
                healthStatus
        );
    }

    private void send(String json) {
        consumer.receive(new GenericMessage<>(json));
    }

    @Test
    void acceptsTwoIndependentVehicles() {
        Instant now = Instant.now();

        String first = event(
                "vehicle-001", now, "HEALTHY"
        );
        String second = event(
                "vehicle-002", now, "BRAKING"
        );

        send(first);
        send(second);

        assertEquals(
                first,
                consumer.latestPayloadFor("vehicle-001")
        );
        assertEquals(
                second,
                consumer.latestPayloadFor("vehicle-002")
        );
    }

    @Test
    void ignoresDuplicateEvent() {
        Instant now = Instant.now();

        String first = event(
                "vehicle-001", now, "HEALTHY"
        );

        String duplicate = event(
                "vehicle-001", now, "BRAKING"
        );

        send(first);
        send(duplicate);

        assertEquals(
                first,
                consumer.latestPayloadFor("vehicle-001")
        );
    }

    @Test
    void rejectsOlderEvent() {
        Instant now = Instant.now();

        String latest = event(
                "vehicle-001", now, "HEALTHY"
        );

        String older = event(
                "vehicle-001",
                now.minusSeconds(10),
                "BRAKING"
        );

        send(latest);
        send(older);

        assertEquals(
                latest,
                consumer.latestPayloadFor("vehicle-001")
        );
    }

    @Test
    void rejectsStaleEvent() {
        String stale = event(
                "vehicle-001",
                Instant.now().minus(2, ChronoUnit.MINUTES),
                "HEALTHY"
        );

        send(stale);

        assertNull(
                consumer.latestPayloadFor("vehicle-001")
        );
    }

    @Test
    void rejectsUnknownVehicle() {
        String unknown = event(
                "vehicle-999",
                Instant.now(),
                "HEALTHY"
        );

        send(unknown);

        assertNull(
                consumer.latestPayloadFor("vehicle-999")
        );
    }

    @Test
    void rejectsMalformedJson() {
        send("{invalid-json}");

        assertNull(
                consumer.latestPayloadFor("vehicle-001")
        );
    }

    @Test
    void rejectsMissingRequiredFields() {
        send("""
                {
                  "vehicleId": "vehicle-001",
                  "healthStatus": "HEALTHY"
                }
                """);

        assertNull(
                consumer.latestPayloadFor("vehicle-001")
        );
    }

    @Test
    void rejectsFutureTimestamp() {
        String future = event(
                "vehicle-001",
                Instant.now().plusSeconds(60),
                "HEALTHY"
        );

        send(future);

        assertNull(
                consumer.latestPayloadFor("vehicle-001")
        );
    }
    
    @Test
        void newVehicleHasUnknownAvailability() {
        assertEquals(
                VehicleEventConsumer.Availability.UNKNOWN,
                consumer.getAvailability("vehicle-001")
        );
    }

    @Test
        void recentlyUpdatedVehicleIsLive() {
        send(event(
                "vehicle-001",
                Instant.now(),
                "HEALTHY"
        ));

        assertEquals(
                VehicleEventConsumer.Availability.LIVE,
                consumer.getAvailability("vehicle-001")
        );
    }

    @Test
        void silentVehicleBecomesStaleIndependently() {
        send(event(
                "vehicle-001",
                Instant.now(),
                "HEALTHY"
        ));

        Instant later = Instant.now().plusSeconds(11);

        assertEquals(
                VehicleEventConsumer.Availability.STALE,
                consumer.availabilityAt("vehicle-001", later)
        );

        assertEquals(
                VehicleEventConsumer.Availability.UNKNOWN,
                consumer.availabilityAt("vehicle-002", later)
        );
    }

}
