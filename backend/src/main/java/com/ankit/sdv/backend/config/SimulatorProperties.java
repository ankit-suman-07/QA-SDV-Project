package com.ankit.sdv.backend.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

import java.net.URI;
import java.time.Duration;
import java.util.Map;
import java.util.Set;

@ConfigurationProperties("sdv.simulator")
public record SimulatorProperties(@DefaultValue("development") String mode,
        Map<String, URI> providers, @DefaultValue("2s") Duration connectTimeout,
        @DefaultValue("2s") Duration readTimeout) {
    public SimulatorProperties {
        providers = providers == null ? Map.of() : Map.copyOf(providers);
        if (!("development".equals(mode) || "http".equals(mode))
                || !positive(connectTimeout) || !positive(readTimeout)
                || (("http".equals(mode) || !providers.isEmpty())
                    && !providers.keySet().equals(Set.of("vehicle-001", "vehicle-002")))
                || providers.values().stream().anyMatch(uri -> !validEndpoint(uri))) {
            throw new IllegalArgumentException("Invalid simulator mode, provider mapping or timeout configuration");
        }
    }
    private static boolean positive(Duration value) { return value != null && !value.isNegative() && !value.isZero(); }
    private static boolean validEndpoint(URI uri) {
        return uri != null && ("http".equals(uri.getScheme()) || "https".equals(uri.getScheme()))
                && uri.getHost() != null && uri.getUserInfo() == null && uri.getQuery() == null
                && uri.getFragment() == null && uri.getPort() != 0 && uri.getPort() <= 65535;
    }
    @Override public String toString() { return "SimulatorProperties[mode=" + mode + ", endpoints=REDACTED]"; }
}
