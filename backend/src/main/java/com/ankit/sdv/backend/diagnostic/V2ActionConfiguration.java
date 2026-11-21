package com.ankit.sdv.backend.diagnostic;

import com.ankit.sdv.backend.service.V2VehicleService;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.RestClient;
import tools.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.net.http.HttpClient;
import java.time.Clock;
import java.time.Duration;

@Configuration(proxyBeanMethods = false)
@ConditionalOnProperty(name = "sdv.v2.actions.enabled", havingValue = "true")
@EnableConfigurationProperties(ActionSettings.class)
class V2ActionConfiguration {
    @Bean
    HttpActionExecution v2ActionExecution(ActionSettings settings) {
        var client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2))
                .followRedirects(HttpClient.Redirect.NEVER).build();
        return new HttpActionExecution(settings, RestClient.builder()
                .requestFactory(new JdkClientHttpRequestFactory(client)).build());
    }

    @Bean
    V2ActionTracker v2ActionTracker(ActionSettings settings, HttpActionExecution executor,
            V2VehicleService vehicles, Clock clock, ObjectMapper json) throws IOException {
        var journal = new ActionJournal(settings.journal(), json);
        try {
            return new V2ActionTracker(journal, executor, vehicles, clock);
        } catch (RuntimeException failure) {
            journal.close();
            throw failure;
        }
    }
}
