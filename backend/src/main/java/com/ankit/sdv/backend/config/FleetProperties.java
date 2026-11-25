package com.ankit.sdv.backend.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;
import org.springframework.boot.context.properties.bind.ConstructorBinding;
import java.time.Duration;

/** Service credentials are separate from A2 read credentials and provisioning authority. */
@ConfigurationProperties("sdv.v1.fleet")
public record FleetProperties(@DefaultValue("false") boolean enabled,
        @DefaultValue("2s") Duration interval, @DefaultValue("2s") Duration initialDelay,
        @DefaultValue("2s") Duration writeTimeout, String username, String password,
        @DefaultValue("v1") String version) {
    public FleetProperties(boolean enabled, Duration interval, Duration initialDelay,
            Duration writeTimeout, String username, String password) {
        this(enabled, interval, initialDelay, writeTimeout, username, password, "v1");
    }

    @ConstructorBinding
    public FleetProperties {
        if (!("v1".equals(version) || "v2".equals(version)) || !positive(interval) || !positive(initialDelay) || !positive(writeTimeout)
                || present(username) != present(password)
                || (present(username) && (username.isBlank() || !username.equals(username.strip()) || username.contains(":")))) {
            throw new IllegalArgumentException("Invalid fleet timeouts or service credentials");
        }
    }
    private static boolean positive(Duration value) { return value != null && value.toMillis() > 0; }
    private static boolean present(String value) { return value != null && !value.isEmpty(); }
    public boolean authenticated() { return present(username); }
    @Override public String toString() { return "FleetProperties[enabled=" + enabled + ", credentials=REDACTED]"; }
}
