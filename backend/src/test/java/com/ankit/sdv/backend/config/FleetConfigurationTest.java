package com.ankit.sdv.backend.config;

import com.ankit.sdv.backend.service.FleetService;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import java.time.*;
import java.net.URI;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.mock;

class FleetConfigurationTest {
    final ApplicationContextRunner runner = new ApplicationContextRunner().withUserConfiguration(FleetConfiguration.class)
            .withBean(FleetService.class, () -> mock(FleetService.class))
            .withBean(Clock.class, Clock::systemUTC)
            .withBean(V1DittoProperties.class, () -> new V1DittoProperties("live", URI.create("http://localhost:8080"),
                    Duration.ofSeconds(2), Duration.ofSeconds(2), Duration.ofSeconds(5), Duration.ofSeconds(30), null, null, null));
    @Test void disabledByDefaultAndLiveWritesRequireSeparateServiceCredentials() {
        runner.run(context -> assertThat(context).doesNotHaveBean("fleetMaterializer"));
        runner.withPropertyValues("sdv.v1.fleet.enabled=true")
                .run(context -> assertThat(context).hasFailed());
        runner.withPropertyValues("sdv.v1.fleet.enabled=true", "sdv.v1.fleet.username=fleet", "sdv.v1.fleet.password=test-only")
                .run(context -> assertThat(context).hasBean("fleetMaterializer"));
    }
    @Test void invalidTimeoutsAndPartialCredentialsFailBinding() {
        for (String property : new String[]{"sdv.v1.fleet.interval=0s", "sdv.v1.fleet.initial-delay=-1s",
                "sdv.v1.fleet.write-timeout=0s", "sdv.v1.fleet.username=only-user"}) {
            runner.withPropertyValues(property).run(context -> assertThat(context).hasFailed());
        }
    }
}
