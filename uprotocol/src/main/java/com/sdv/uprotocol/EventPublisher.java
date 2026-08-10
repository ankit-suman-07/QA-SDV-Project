package com.sdv.uprotocol;

import java.time.Instant;
import java.util.UUID;

/**
 * Bridge between the health engine and uProtocol events.
 *
 * This connects the part of the system that decides whether the car has
 * a problem to the part that announces that problem to the rest of the
 * system.
 *
 * Integration point: call these methods wherever the health engine's
 * result is compared against the PREVIOUS health status - not from
 * inside the health-check logic itself, since that logic only knows the
 * current reading, not whether anything actually changed.
 *
 * Status and fault names are passed in as plain Strings rather than a
 * shared enum type, so the backend and this messaging layer don't need
 * to depend on each other's internal types. This file is the only place
 * that needs to know both naming schemes.
 */
public class EventPublisher {

    // backend status names -> uProtocol event schema names
    private static String mapHealthStatus(String backendStatus) {
        switch (backendStatus) {
            case "HEALTHY":
                return "HEALTH_HEALTHY";
            case "WARNING":
                return "HEALTH_WARNING";
            case "CRITICAL":
                return "HEALTH_CRITICAL";
            default:
                throw new IllegalArgumentException(
                        "Unknown health status value: " + backendStatus);
        }
    }

    private static String nowTimestamp() {
        return Instant.now().toString(); // RFC3339, matches proto field comments
    }

    /**
     * Call this only when the health status has just CHANGED
     * (e.g. Healthy -> Warning). Do not call this on every check -
     * only on an actual transition, otherwise duplicate events will
     * be published for no reason.
     *
     * @param vehicleId        e.g. "vehicle-001"
     * @param previousStatus   the status before this check, e.g. "HEALTHY"
     * @param newStatus        the status after this check, e.g. "WARNING"
     * @param triggeringSignal e.g. "temperatureCelsius"
     */
    public static void publishHealthStatusChanged(
            String vehicleId,
            String previousStatus,
            String newStatus,
            String triggeringSignal) {

        String eventId = UUID.randomUUID().toString();
        String mappedPrevious = mapHealthStatus(previousStatus);
        String mappedNew = mapHealthStatus(newStatus);

        // TODO: replace with real up-java UMessage construction + publish
        // once the up-java version is pinned (see pom.xml TODO).
        System.out.println("[PUBLISHED HealthStatusChanged] "
                + "vehicleId=" + vehicleId
                + " eventId=" + eventId
                + " timestamp=" + nowTimestamp()
                + " previousStatus=" + mappedPrevious
                + " newStatus=" + mappedNew
                + " triggeringSignal=" + triggeringSignal);
    }

    /**
     * Call this the moment a fault's activation condition is met
     * (e.g. temperature crosses its warning/critical threshold).
     *
     * @param vehicleId      e.g. "vehicle-001"
     * @param faultCode      "BATTERY_LOW", "TEMP_HIGH", or "TIRE_PRESSURE_LOW"
     * @param severity       "FAULT_WARNING" or "FAULT_CRITICAL"
     * @param affectedSignal e.g. "temperatureCelsius"
     * @param detectedValue  the actual reading that triggered the fault
     * @param threshold      the threshold that was crossed
     * @return the eventId generated for this fault - save it and pass the
     *         SAME id into publishFaultCleared later, so the two events
     *         can be matched together as one fault's full lifecycle
     */
    public static String publishFaultDetected(
            String vehicleId,
            String faultCode,
            String severity,
            String affectedSignal,
            double detectedValue,
            double threshold) {

        String eventId = UUID.randomUUID().toString();

        System.out.println("[PUBLISHED FaultDetected] "
                + "vehicleId=" + vehicleId
                + " eventId=" + eventId
                + " timestamp=" + nowTimestamp()
                + " faultCode=" + faultCode
                + " severity=" + severity
                + " affectedSignal=" + affectedSignal
                + " detectedValue=" + detectedValue
                + " threshold=" + threshold);

        return eventId;
    }

    /**
     * Call this the moment a previously-detected fault's recovery
     * condition is met (the problem is genuinely resolved, not just
     * slightly improved).
     *
     * @param vehicleId    e.g. "vehicle-001"
     * @param eventId      must be the SAME id returned by the matching
     *                     publishFaultDetected call, so the two events
     *                     can be linked together
     * @param faultCode    must match the original fault's code
     * @param clearedValue the reading at the moment of recovery
     */
    public static void publishFaultCleared(
            String vehicleId,
            String eventId,
            String faultCode,
            double clearedValue) {

        System.out.println("[PUBLISHED FaultCleared] "
                + "vehicleId=" + vehicleId
                + " eventId=" + eventId
                + " timestamp=" + nowTimestamp()
                + " faultCode=" + faultCode
                + " clearedValue=" + clearedValue);
    }

    /**
     * Call this on every normal signal reading cycle - this is the
     * routine "here's the car's current state" update, sent regardless
     * of whether anything is wrong.
     */
    public static void publishVehicleStatusUpdated(
            String vehicleId,
            double speedKph,
            double batteryPercent,
            double temperatureCelsius,
            double tireFrontLeft,
            double tireFrontRight,
            double tireRearLeft,
            double tireRearRight) {

        String eventId = UUID.randomUUID().toString();

        System.out.println("[PUBLISHED VehicleStatusUpdated] "
                + "vehicleId=" + vehicleId
                + " eventId=" + eventId
                + " timestamp=" + nowTimestamp()
                + " speedKph=" + speedKph
                + " batteryPercent=" + batteryPercent
                + " temperatureCelsius=" + temperatureCelsius
                + " tirePressure=[" + tireFrontLeft + "," + tireFrontRight
                + "," + tireRearLeft + "," + tireRearRight + "]");
    }
}