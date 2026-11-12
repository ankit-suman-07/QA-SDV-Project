package com.ankit.sdv.backend.config;

import com.ankit.sdv.backend.adapter.simulator.HttpSimulatorControlAdapter;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

import java.net.http.HttpClient;

@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(SimulatorProperties.class)
public class SimulatorControlConfiguration {
    @Bean
    @ConditionalOnProperty(name = "sdv.simulator.mode", havingValue = "http")
    HttpSimulatorControlAdapter httpSimulatorControlAdapter(SimulatorProperties properties) {
        var http = HttpClient.newBuilder().connectTimeout(properties.connectTimeout())
                .followRedirects(HttpClient.Redirect.NEVER).build();
        var factory = new JdkClientHttpRequestFactory(http);
        // The adapter enforces one whole-response deadline, including body reads.
        return new HttpSimulatorControlAdapter(RestClient.builder().requestFactory(factory).build(), properties.providers(), properties.readTimeout());
    }
}
