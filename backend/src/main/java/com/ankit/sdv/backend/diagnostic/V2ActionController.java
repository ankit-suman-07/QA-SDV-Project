package com.ankit.sdv.backend.diagnostic;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.JsonNode;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;

import static com.ankit.sdv.backend.diagnostic.V2ActionTracker.error;

@RestController
@RequestMapping("/api/v2/diagnostics")
@ConditionalOnProperty(name = "sdv.v2.actions.enabled", havingValue = "true")
class V2ActionController {
    private final V2ActionTracker tracker;
    private final HttpActionExecution executor;
    private final byte[] authorization;

    V2ActionController(V2ActionTracker tracker, HttpActionExecution executor, ActionSettings settings) {
        this.tracker = tracker;
        this.executor = executor;
        authorization = ("Bearer " + settings.token()).getBytes(StandardCharsets.UTF_8);
    }

    @PostMapping(path = "/actions", consumes = MediaType.APPLICATION_JSON_VALUE)
    ResponseEntity<V2Action.Entry> create(@RequestHeader(value = "Authorization", required = false) String token,
            @RequestBody byte[] body) {
        authorize(token);
        if (body.length > 65536) throw error(HttpStatus.BAD_REQUEST, "Invalid action request");
        V2Action.Request request;
        try {
            var payload = HttpActionExecution.JSON.readTree(body);
            if (payload == null || !payload.isObject()) throw error(HttpStatus.BAD_REQUEST, "Invalid action request");
            for (String name : payload.propertyNames()) {
                if (!List.of("vehicleId", "actionId", "traceId", "action", "scenario").contains(name)
                        || !(payload.get(name).isTextual() || ("scenario".equals(name) && payload.get(name).isNull()))) {
                    throw error(HttpStatus.BAD_REQUEST, "Invalid action request");
                }
            }
            request = HttpActionExecution.JSON.treeToValue(payload, V2Action.Request.class);
        } catch (JacksonException malformed) {
            throw error(HttpStatus.BAD_REQUEST, "Invalid action request");
        }
        var record = tracker.create(request);
        var status = record.status() == V2Action.Status.ACCEPTED
                ? HttpStatus.ACCEPTED : HttpStatus.OK;
        return ResponseEntity.status(status).body(record);
    }

    @GetMapping("/actions/{actionId}")
    V2Action.Entry read(@RequestHeader(value = "Authorization", required = false) String token,
            @PathVariable String actionId) {
        authorize(token);
        return tracker.read(actionId);
    }

    @GetMapping("/vehicles/{vehicleId}/actions")
    List<V2Action.Entry> history(@RequestHeader(value = "Authorization", required = false) String token,
            @PathVariable String vehicleId) {
        authorize(token);
        return tracker.history(vehicleId);
    }

    @GetMapping("/vehicles/{vehicleId}/health")
    JsonNode health(@RequestHeader(value = "Authorization", required = false) String token, @PathVariable String vehicleId) {
        authorize(token);
        return executor.diagnostic(vehicleId, HttpActionExecution.Diagnostic.HEALTH);
    }

    @GetMapping("/vehicles/{vehicleId}/faults")
    JsonNode faults(@RequestHeader(value = "Authorization", required = false) String token, @PathVariable String vehicleId) {
        authorize(token);
        return executor.diagnostic(vehicleId, HttpActionExecution.Diagnostic.FAULTS);
    }

    private void authorize(String token) {
        if (token == null || !MessageDigest.isEqual(authorization, token.getBytes(StandardCharsets.UTF_8))) {
            throw error(HttpStatus.UNAUTHORIZED, "Action service authentication required");
        }
    }
}
