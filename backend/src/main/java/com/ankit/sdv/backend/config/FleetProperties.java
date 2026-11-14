package com.ankit.sdv.backend.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;
import java.time.Duration;

/** Service credentials are separate from A2 read credentials and provisioning authority. */
@ConfigurationProperties("sdv.v1.fleet")
public record FleetProperties(@DefaultValue("false") boolean enabled,
        @DefaultValue("2s") Duration interval, @DefaultValue("2s") Duration initialDelay,
        @DefaultValue("2s") Duration writeTimeout, String username, String password) {
    public FleetProperties {
        if (!positive(interval) || !positive(initialDelay) || !positive(writeTimeout)
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
