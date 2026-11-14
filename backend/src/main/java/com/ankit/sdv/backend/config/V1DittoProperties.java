package com.ankit.sdv.backend.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

import java.net.URI;
import java.time.Duration;
import java.util.List;
import java.util.Map;

/** Read-path configuration, independent of the legacy sdv.ditto.mode writer. */
@ConfigurationProperties("sdv.v1.ditto")
public record V1DittoProperties(
        @DefaultValue("live") String mode,
        URI baseUrl,
        @DefaultValue("2s") Duration connectTimeout,
        @DefaultValue("2s") Duration readTimeout,
        @DefaultValue("5s") Duration staleAfter,
        @DefaultValue("30s") Duration unavailableAfter,
        String username,
        String password,
        Map<String, String> things
) {
    private static final Map<String, String> V1_THINGS = Map.of(
            "vehicle-001", "sdv:vehicle-001", "vehicle-002", "sdv:vehicle-002");

    public V1DittoProperties {
        things = things == null ? V1_THINGS : Map.copyOf(things);
        if (!("mock".equals(mode) || "live".equals(mode)) || baseUrl == null
                || !("http".equals(baseUrl.getScheme()) || "https".equals(baseUrl.getScheme()))
                || baseUrl.getHost() == null || baseUrl.getUserInfo() != null
                || baseUrl.getQuery() != null || baseUrl.getFragment() != null
                || baseUrl.getPort() == 0 || baseUrl.getPort() > 65535
                || !positive(connectTimeout) || !positive(readTimeout)
                || !positive(staleAfter) || unavailableAfter == null
                || unavailableAfter.compareTo(staleAfter) <= 0 || !V1_THINGS.equals(things)) {
            throw new IllegalArgumentException("Invalid V1 Ditto mode, endpoint, time limits or identity mapping");
        }
        boolean hasUser = username != null && !username.isEmpty();
        boolean hasPassword = password != null && !password.isEmpty();
        if (hasUser != hasPassword || (hasUser && (username.isBlank()
                || !username.equals(username.strip()) || username.contains(":")))) {
            throw new IllegalArgumentException("V1 Ditto Basic authentication requires a valid username/password pair");
        }
    }

    private static boolean positive(Duration duration) {
        return duration != null && !duration.isNegative() && !duration.isZero();
    }

    public List<String> vehicleIds() { return things.keySet().stream().sorted().toList(); }

    @Override public String toString() { return "V1DittoProperties[mode=" + mode + ", credentials=REDACTED]"; }
}
