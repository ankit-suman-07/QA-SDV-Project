package com.ankit.sdv.backend.adapter.ditto;

import com.ankit.sdv.backend.dto.V1VehicleResponse.Lidar;
import com.ankit.sdv.backend.dto.V2VehicleResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import tools.jackson.core.JacksonException;
import tools.jackson.core.StreamReadFeature;
import tools.jackson.databind.DeserializationFeature;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.math.BigDecimal;
import java.math.BigInteger;
import java.util.function.Function;
import java.net.URI;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.DateTimeException;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.regex.Pattern;

/** Whole-Thing reads only: no cache, write path, retries or generated fallback. */
public final class HttpVehicleTwinReader {
    private static final Logger LOG = LoggerFactory.getLogger(HttpVehicleTwinReader.class);
    private static final int MAX_RESPONSE_BYTES = 1024 * 1024;
    private static final Pattern UTC = Pattern.compile(
            "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\\.([0-9]+))?(?:Z|\\+00:00)");
    private final JsonMapper json = JsonMapper.builder()
            .enable(StreamReadFeature.STRICT_DUPLICATE_DETECTION)
            .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS).build();
    private final RestClient client;
    private final String baseUrl;

    public HttpVehicleTwinReader(RestClient client, URI baseUrl) {
        this.client = client;
        this.baseUrl = baseUrl.toString().replaceAll("/+$", "");
    }

    public Optional<TwinSnapshot> read(String vehicleId, String thingId) {
        return read(vehicleId, thingId, "v1", this::parseV1);
    }

    public Optional<V2Snapshot> readV2(String vehicleId, String thingId) {
        return read(vehicleId, thingId, "v2", props -> parseV2(vehicleId, thingId, props));
    }

    private <T> Optional<T> read(String vehicleId, String thingId, String feature, Function<JsonNode, T> parse) {
        try {
            return client.get().uri(URI.create(baseUrl + "/api/2/things/" + thingId))
                    .accept(MediaType.APPLICATION_JSON).exchange((request, response) -> {
                        int status = response.getStatusCode().value();
                        if (status != 200) {
                            if (status == 401 || status == 403) {
                                LOG.error("ditto_read_failed vehicle={} code=AUTH_CONFIGURATION status={}", vehicleId, status);
                            } else {
                                LOG.warn("ditto_read_failed vehicle={} code=HTTP_STATUS status={}", vehicleId, status);
                            }
                            return Optional.empty();
                        }
                        byte[] body = response.getBody().readNBytes(MAX_RESPONSE_BYTES + 1);
                        if (body.length > MAX_RESPONSE_BYTES) {
                            LOG.warn("ditto_read_failed vehicle={} code=RESPONSE_TOO_LARGE", vehicleId);
                            return Optional.empty();
                        }
                        try {
                            return Optional.of(parse.apply(properties(vehicleId, thingId, feature, body)));
                        } catch (JacksonException | IllegalArgumentException | DateTimeException exception) {
                            // Never emit raw JSON, URLs, credentials or dependency exception text.
                            LOG.warn("ditto_read_failed vehicle={} code=INVALID_SNAPSHOT", vehicleId);
                            return Optional.empty();
                        }
                    });
        } catch (RestClientException exception) {
            LOG.warn("ditto_read_failed vehicle={} code=TRANSPORT_UNAVAILABLE", vehicleId);
            return Optional.empty();
        }
    }

    private JsonNode properties(String vehicleId, String thingId, String feature, byte[] body) {
        JsonNode thing = json.readTree(body);
        require(thing != null && thing.isObject());
        validateJsonValues(thing);
        require(thingId.equals(text(thing, "thingId")));
        require(vehicleId.equals(text(thing.path("attributes"), "vehicleId")));
        JsonNode props = thing.at("/features/" + feature + "/properties");
        require(props.isObject());
        require(vehicleId.equals(text(props, "vehicleId")));
        return props;
    }

    private TwinSnapshot parseV1(JsonNode props) {
        require("1.0.0".equals(text(props, "schemaVersion")));
        String source = text(props, "sourceTimestamp");
        BigDecimal epoch = sourceEpoch(source);
        String eventId = text(props, "lastEventId");
        for (String context : List.of("actionId", "traceId")) {
            if (props.has(context)) text(props, context);
        }
        String health = text(props, "health");
        require(List.of("HEALTHY", "WARNING", "CRITICAL").contains(health));
        JsonNode faultsNode = props.path("faults");
        require(faultsNode.isArray());
        List<String> faults = new ArrayList<>();
        for (JsonNode fault : faultsNode) {
            require(fault.isTextual());
            faults.add(fault.asText());
        }
        JsonNode lidar = props.path("lidar");
        require(lidar.isObject() && lidar.path("sensorAvailable").isBoolean() && lidar.has("distanceMeters"));
        boolean sensor = lidar.get("sensorAvailable").booleanValue();
        JsonNode distanceNode = lidar.get("distanceMeters");
        BigDecimal distance = null;
        if (!distanceNode.isNull()) {
            require(distanceNode.isNumber() && (distanceNode.isIntegralNumber() || Double.isFinite(distanceNode.doubleValue()))
                    && distanceNode.decimalValue().signum() >= 0);
            distance = distanceNode.decimalValue();
        } else require(!sensor);
        String expectedHealth = !sensor || distance.compareTo(BigDecimal.valueOf(5)) <= 0 ? "CRITICAL" : distance.compareTo(BigDecimal.TEN) <= 0 ? "WARNING" : "HEALTHY";
        List<String> expectedFaults = !sensor ? List.of("LIDAR_SENSOR_FAILURE")
                : distance.compareTo(BigDecimal.TEN) <= 0 ? List.of("LIDAR_OBSTRUCTION") : List.of();
        require(expectedHealth.equals(health) && expectedFaults.equals(faults));
        return new TwinSnapshot(health, List.copyOf(faults), new Lidar(distance, sensor), source, eventId, epoch);
    }

    private V2Snapshot parseV2(String vehicleId, String thingId, JsonNode props) {
        require("2.0.0".equals(text(props, "schemaVersion")));
        String source = text(props, "sourceTimestamp");
        BigDecimal epoch = sourceEpoch(source);
        sourceEpoch(text(props, "processingTimestamp"));
        require(List.of("CARLA", "SYNTHETIC").contains(text(props, "provenance")));
        JsonNode simulation = props.path("simulationSeconds");
        require(simulation.isNumber() && Double.isFinite(simulation.doubleValue()) && simulation.decimalValue().signum() >= 0);
        if (props.has("actionId") || props.has("traceId")) {
            text(props, "actionId");
            text(props, "traceId");
        }

        JsonNode lidar = props.path("lidar");
        require(lidar.isObject() && lidar.path("sensorAvailable").isBoolean() && lidar.has("distanceMeters"));
        boolean sensorAvailable = lidar.get("sensorAvailable").booleanValue();
        JsonNode value = lidar.get("distanceMeters");
        require(sensorAvailable
                ? value.isNumber() && Double.isFinite(value.doubleValue()) && value.decimalValue().signum() >= 0
                : value.isNull());
        BigDecimal distance = sensorAvailable ? value.decimalValue() : null;
        String health = text(props, "health");
        JsonNode faultNode = props.path("faults");
        require(faultNode.isArray());
        List<String> faults = new ArrayList<>();
        for (JsonNode fault : faultNode) {
            require(fault.isTextual());
            faults.add(fault.asText());
        }
        String recovery = text(props, "recoveryState");
        require(props.path("sourceSilent").isBoolean() && props.has("recoveryStartedAt"));
        boolean silent = props.get("sourceSilent").booleanValue();
        String started = null;
        boolean recovering = "IN_PROGRESS".equals(recovery);
        if (recovering) {
            started = text(props, "recoveryStartedAt");
            require(sourceEpoch(started).compareTo(epoch) <= 0 && !silent);
        } else {
            require("NONE".equals(recovery) && props.get("recoveryStartedAt").isNull());
        }
        require(trustedHealth(health, faults, distance, recovering));
        return new V2Snapshot(new V2VehicleResponse(vehicleId, thingId, health, null, List.copyOf(faults),
                new Lidar(distance, sensorAvailable), source, text(props, "lastEventId"), text(props, "sessionId"),
                integer(props, "sessionGeneration", 1), integer(props, "sequence", 0), integer(props, "frame", 0),
                recovery, started, silent), epoch);
    }

    private static boolean trustedHealth(String health, List<String> faults, BigDecimal distance, boolean recovering) {
        var obstruction = List.of("LIDAR_OBSTRUCTION");
        var sensorFailure = List.of("LIDAR_SENSOR_FAILURE");
        if (recovering) {
            return distance != null && distance.compareTo(BigDecimal.TEN) > 0
                    && (("CRITICAL".equals(health) && (faults.equals(obstruction) || faults.equals(sensorFailure)))
                        || ("WARNING".equals(health) && faults.equals(obstruction)));
        }
        if (distance == null) return "CRITICAL".equals(health) && faults.equals(sensorFailure);
        if (distance.compareTo(BigDecimal.valueOf(5)) <= 0) return "CRITICAL".equals(health) && faults.equals(obstruction);
        if (distance.compareTo(BigDecimal.TEN) <= 0) return "WARNING".equals(health) && faults.equals(obstruction);
        // A recovery reset can retain the critical obstruction and the last accepted clear distance.
        return ("HEALTHY".equals(health) && faults.isEmpty())
                || ("CRITICAL".equals(health) && faults.equals(obstruction));
    }

    private static BigInteger integer(JsonNode props, String name, int minimum) {
        JsonNode value = props.path(name);
        require(value.isIntegralNumber() && value.bigIntegerValue().compareTo(BigInteger.valueOf(minimum)) >= 0);
        return value.bigIntegerValue();
    }

    public record V2Snapshot(V2VehicleResponse state, BigDecimal sourceEpochSeconds) {}

    private static String text(JsonNode object, String field) {
        JsonNode value = object.path(field);
        require(value.isTextual() && !value.asText().isBlank());
        return value.asText();
    }

    private static BigDecimal sourceEpoch(String source) {
        var match = UTC.matcher(source);
        require(match.matches());
        // Validate date/time without rounding away fractional source precision.
        String wholeSeconds = source.substring(0, 19);
        require(Integer.parseInt(source.substring(17, 19)) < 60); // Instant.parse otherwise accepts leap seconds.
        var instant = LocalDateTime.parse(wholeSeconds).toInstant(ZoneOffset.UTC);
        String fraction = match.group(1);
        return BigDecimal.valueOf(instant.getEpochSecond()).add(
                fraction == null ? BigDecimal.ZERO : new BigDecimal("0." + fraction));
    }

    private static void validateJsonValues(JsonNode root) {
        // No recursive copying of extension data; only the compact typed projection escapes.
        ArrayDeque<JsonNode> pending = new ArrayDeque<>();
        pending.add(root);
        while (!pending.isEmpty()) {
            JsonNode value = pending.removeLast();
            if (value.isFloatingPointNumber()) require(Double.isFinite(value.doubleValue()));
            if (value.isTextual()) validateUnicode(value.asText());
            if (value.isObject()) for (String key : value.propertyNames()) validateUnicode(key);
            if (value.isContainer()) for (JsonNode child : value) pending.add(child);
        }
    }

    private static void validateUnicode(String text) {
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            if (Character.isHighSurrogate(c)) {
                require(i + 1 < text.length() && Character.isLowSurrogate(text.charAt(++i)));
            } else require(!Character.isLowSurrogate(c));
        }
    }

    private static void require(boolean valid) {
        if (!valid) throw new IllegalArgumentException("Invalid individual twin snapshot");
    }
}
