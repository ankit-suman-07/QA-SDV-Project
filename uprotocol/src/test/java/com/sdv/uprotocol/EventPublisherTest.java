package com.sdv.uprotocol;

import org.junit.jupiter.api.Test;
import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

import static org.junit.jupiter.api.Assertions.*;

class EventPublisherTest {

    private String captureOutput(Runnable action) {
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        PrintStream originalOut = System.out;
        System.setOut(new PrintStream(buffer));
        try {
            action.run();
        } finally {
            System.setOut(originalOut);
        }
        return buffer.toString();
    }

    @Test
    void publishHealthStatusChanged_printsTranslatedStatusNames() {
        String output = captureOutput(() ->
            EventPublisher.publishHealthStatusChanged(
                "vehicle-001", "HEALTHY", "WARNING", "temperatureCelsius"));

        assertTrue(output.contains("vehicleId=vehicle-001"));
        assertTrue(output.contains("previousStatus=HEALTH_HEALTHY"));
        assertTrue(output.contains("newStatus=HEALTH_WARNING"));
        assertTrue(output.contains("triggeringSignal=temperatureCelsius"));
    }

    @Test
    void publishHealthStatusChanged_rejectsUnknownStatus() {
        assertThrows(IllegalArgumentException.class, () ->
            EventPublisher.publishHealthStatusChanged(
                "vehicle-001", "NOT_A_REAL_STATUS", "WARNING", "temperatureCelsius"));
    }

    @Test
    void publishFaultDetected_returnsNonNullEventId() {
        String eventId = EventPublisher.publishFaultDetected(
            "vehicle-001", "BATTERY_LOW", "FAULT_WARNING",
            "batteryPercent", 18.5, 20.0);

        assertNotNull(eventId);
        assertFalse(eventId.isBlank());
    }

    @Test
    void publishFaultDetected_printsAllRequiredFields() {
        String output = captureOutput(() ->
            EventPublisher.publishFaultDetected(
                "vehicle-001", "TEMP_HIGH", "FAULT_CRITICAL",
                "temperatureCelsius", 110.0, 105.0));

        assertTrue(output.contains("faultCode=TEMP_HIGH"));
        assertTrue(output.contains("severity=FAULT_CRITICAL"));
        assertTrue(output.contains("affectedSignal=temperatureCelsius"));
        assertTrue(output.contains("detectedValue=110.0"));
        assertTrue(output.contains("threshold=105.0"));
    }

    @Test
    void faultDetectedAndFaultCleared_shareTheSameEventId() {
        String eventId = EventPublisher.publishFaultDetected(
            "vehicle-001", "BATTERY_LOW", "FAULT_WARNING",
            "batteryPercent", 18.5, 20.0);

        String output = captureOutput(() ->
            EventPublisher.publishFaultCleared(
                "vehicle-001", eventId, "BATTERY_LOW", 25.2));

        assertTrue(output.contains("eventId=" + eventId));
    }

    @Test
    void publishVehicleStatusUpdated_printsAllSignalValues() {
        String output = captureOutput(() ->
            EventPublisher.publishVehicleStatusUpdated(
                "vehicle-001", 60.0, 74.0, 88.0, 32.0, 32.0, 31.5, 32.0));

        assertTrue(output.contains("speedKph=60.0"));
        assertTrue(output.contains("batteryPercent=74.0"));
        assertTrue(output.contains("temperatureCelsius=88.0"));
        assertTrue(output.contains("tirePressure=[32.0,32.0,31.5,32.0]"));
    }

    @Test
    void differentCalls_generateDifferentEventIds() {
        String id1 = EventPublisher.publishFaultDetected(
            "vehicle-001", "TEMP_HIGH", "FAULT_CRITICAL",
            "temperatureCelsius", 110.0, 105.0);
        String id2 = EventPublisher.publishFaultDetected(
            "vehicle-001", "TEMP_HIGH", "FAULT_CRITICAL",
            "temperatureCelsius", 111.0, 105.0);

        assertNotEquals(id1, id2);
    }
}
