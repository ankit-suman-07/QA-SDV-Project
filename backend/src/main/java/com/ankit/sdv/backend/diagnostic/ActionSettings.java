package com.ankit.sdv.backend.diagnostic;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.net.URI;
import java.nio.file.Path;
import java.util.Map;

@ConfigurationProperties("sdv.v2.actions")
public record ActionSettings(Path journal, String token, Map<String, URI> scenarioProviders,
        Map<String, URI> lifecycleExecutors, Map<String, URI> results, URI fixtureBase) {
    public ActionSettings {
        scenarioProviders = endpoints(scenarioProviders);
        lifecycleExecutors = endpoints(lifecycleExecutors);
        results = endpoints(results);
        if (journal == null || token == null || token.isBlank()
                || (fixtureBase != null && (!valid(fixtureBase) || !loopback(fixtureBase)
                    || !lifecycleExecutors.isEmpty() || !results.isEmpty()))) {
            throw new IllegalArgumentException("Invalid V2 action journal, credentials or fixture configuration");
        }
    }

    static boolean loopback(URI uri) { return "127.0.0.1".equals(uri.getHost()) || "localhost".equals(uri.getHost()); }

    private static Map<String, URI> endpoints(Map<String, URI> endpoints) {
        if (endpoints == null) return Map.of();
        if (!endpoints.keySet().stream().allMatch(id -> id.matches("vehicle-00[123]"))
                || !endpoints.values().stream().allMatch(ActionSettings::valid)) {
            throw new IllegalArgumentException("Invalid V2 per-vehicle action endpoints");
        }
        return Map.copyOf(endpoints);
    }

    private static boolean valid(URI uri) {
        return uri != null && uri.getHost() != null && uri.getUserInfo() == null
                && uri.getQuery() == null && uri.getFragment() == null
                && uri.getPort() != 0 && uri.getPort() <= 65535
                && ("https".equals(uri.getScheme()) || (loopback(uri) && "http".equals(uri.getScheme())));
    }

    @Override public String toString() { return "ActionSettings[credentials=REDACTED]"; }
}
