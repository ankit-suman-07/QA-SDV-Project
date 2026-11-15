package com.ankit.sdv.backend.config;

import com.ankit.sdv.backend.adapter.ditto.HttpVehicleTwinReader;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

import java.net.http.HttpClient;

@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(V1DittoProperties.class)
public class V1DittoConfiguration {
    @Bean
    HttpVehicleTwinReader httpVehicleTwinReader(V1DittoProperties properties) {
        HttpClient http = HttpClient.newBuilder().connectTimeout(properties.connectTimeout())
                .followRedirects(HttpClient.Redirect.NEVER).build();
        JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(http);
        factory.setReadTimeout(properties.readTimeout());
        RestClient.Builder builder = RestClient.builder().requestFactory(factory)
                // One field avoids Ditto rejecting Spring/JDK automatic gzip + deflate duplicates.
                .defaultHeader("Accept-Encoding", "gzip, deflate");
        if (properties.username() != null && !properties.username().isEmpty()) {
            builder.defaultHeaders(headers -> headers.setBasicAuth(properties.username(), properties.password()));
        }
        return new HttpVehicleTwinReader(builder.build(), properties.baseUrl());
    }
}
