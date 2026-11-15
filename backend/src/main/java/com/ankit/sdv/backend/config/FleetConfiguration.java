package com.ankit.sdv.backend.config;

import com.ankit.sdv.backend.service.FleetMaterializer;
import com.ankit.sdv.backend.service.FleetService;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

import java.net.http.HttpClient;
import java.time.Clock;

@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(FleetProperties.class)
public class FleetConfiguration {
    @Bean
    @ConditionalOnProperty(name = "sdv.v1.fleet.enabled", havingValue = "true")
    FleetMaterializer fleetMaterializer(FleetService fleet, FleetProperties properties, V1DittoProperties ditto, Clock clock) {
        if ("live".equals(ditto.mode()) && !properties.authenticated()) {
            throw new IllegalArgumentException("Live fleet writes require service authentication");
        }
        var http = HttpClient.newBuilder().connectTimeout(ditto.connectTimeout())
                .followRedirects(HttpClient.Redirect.NEVER).build();
        var factory = new JdkClientHttpRequestFactory(http);
        factory.setReadTimeout(properties.writeTimeout());
        var builder = RestClient.builder().requestFactory(factory)
                // One field avoids Ditto rejecting Spring/JDK automatic gzip + deflate duplicates.
                .defaultHeader("Accept-Encoding", "gzip, deflate");
        if (properties.authenticated()) builder.defaultHeaders(h -> h.setBasicAuth(properties.username(), properties.password()));
        return new FleetMaterializer(fleet, builder.build(), ditto.baseUrl(), properties.writeTimeout(), clock);
    }
}
