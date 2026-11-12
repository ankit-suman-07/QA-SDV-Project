package com.ankit.sdv.backend.config;

import com.ankit.sdv.backend.BackendApplication;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;

import static org.assertj.core.api.Assertions.assertThat;

class V1DittoConfigurationTest {
    @org.junit.jupiter.api.Test
    void explicitMockAndLiveModesStartWithoutChangingTheLegacyWriteMode() {
        for (String mode : new String[]{"mock", "live"}) {
            new ApplicationContextRunner().withUserConfiguration(BackendApplication.class)
                    .withPropertyValues("sdv.v1.ditto.mode=" + mode, "sdv.v1.ditto.base-url=http://localhost:8080")
                    .run(context -> assertThat(context).hasNotFailed());
        }
    }

    @ParameterizedTest
    @ValueSource(strings = {"sdv.v1.ditto.mode=generated", "sdv.v1.ditto.mode=development",
            "sdv.v1.ditto.connect-timeout=0s", "sdv.v1.ditto.read-timeout=-1s",
            "sdv.v1.ditto.stale-after=30s", "sdv.v1.ditto.unavailable-after=1s",
            "sdv.v1.ditto.base-url=http://user:secret@localhost:8080",
            "sdv.v1.ditto.base-url=http://localhost:8080?token=secret",
            "sdv.v1.ditto.base-url=ftp://localhost", "sdv.v1.ditto.base-url=",
            "sdv.v1.ditto.things[vehicle-002]=sdv:vehicle-001",
            "sdv.v1.ditto.things[vehicle-999]=sdv:vehicle-999",
            "sdv.v1.ditto.username=user", "sdv.v1.ditto.password=secret"})
    void unsupportedOrUnsafeConfigurationFailsStartup(String property) {
        new ApplicationContextRunner().withUserConfiguration(BackendApplication.class)
                .withPropertyValues("sdv.v1.ditto.mode=live", "sdv.v1.ditto.base-url=http://localhost:8080", property)
                .run(context -> assertThat(context).hasFailed());
    }
}
