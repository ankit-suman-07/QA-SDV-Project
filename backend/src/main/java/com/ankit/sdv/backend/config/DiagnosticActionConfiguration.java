package com.ankit.sdv.backend.config;

import com.ankit.sdv.backend.support.ActionIdGenerator;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Clock;
import java.util.UUID;

@Configuration
public class DiagnosticActionConfiguration {

    @Bean
    public Clock systemClock() {
        return Clock.systemUTC();
    }

    @Bean
    public ActionIdGenerator actionIdGenerator() {
        return () -> UUID.randomUUID().toString();
    }
}