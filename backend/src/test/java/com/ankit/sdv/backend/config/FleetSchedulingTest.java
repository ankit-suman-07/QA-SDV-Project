package com.ankit.sdv.backend.config;

import com.ankit.sdv.backend.dto.FleetResponse;
import com.ankit.sdv.backend.service.FleetMaterializer;
import com.ankit.sdv.backend.service.FleetService;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.context.annotation.Bean;
import java.util.concurrent.atomic.AtomicBoolean;

import java.net.*;
import java.time.*;
import java.util.List;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class FleetSchedulingTest {
    static final AtomicInteger writing = new AtomicInteger();
    static volatile CountDownLatch otherTaskRan;
    @Configuration @EnableScheduling static class Scheduling {
        @Bean Heartbeat heartbeat() { return new Heartbeat(); }
    }
    static class Heartbeat {
        @Scheduled(fixedDelay = 10) public void tick() {
            if (writing.get() > 0) otherTaskRan.countDown();
        }
    }

    @Test void schedulerRetriesOnConfiguredDelayWithoutOverlappingWrites() throws Exception {
        var server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        var executor = Executors.newVirtualThreadPerTaskExecutor();
        otherTaskRan = new CountDownLatch(3);
        var progressed = new AtomicBoolean();
        var attempts = new AtomicInteger(); var active = new AtomicInteger(); var maximum = new AtomicInteger();
        var recovered = new CountDownLatch(1);
        var now = Instant.parse("2026-01-01T00:00:04Z");
        server.setExecutor(executor);
        server.createContext("/", exchange -> {
            int attempt = attempts.incrementAndGet();
            maximum.accumulateAndGet(active.incrementAndGet(), Math::max);
            writing.incrementAndGet();
            try {
                progressed.set(otherTaskRan.await(300, TimeUnit.MILLISECONDS));
                exchange.getRequestBody().readAllBytes();
                exchange.sendResponseHeaders(attempt == 1 ? 503 : 204, -1);
                if (attempt > 1) recovered.countDown();
            } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
            finally { writing.decrementAndGet(); active.decrementAndGet(); exchange.close(); }
        });
        server.start();
        var fleet = mock(FleetService.class);
        when(fleet.read()).thenReturn(new FleetResponse(now, 0, 0, 0, 0, 0, 0, 0, List.of()));
        try {
            new ApplicationContextRunner().withUserConfiguration(FleetConfiguration.class, Scheduling.class)
                    .withPropertyValues("sdv.v1.fleet.enabled=true", "sdv.v1.fleet.interval=30ms", "sdv.v1.fleet.initial-delay=10ms")
                    .withBean(FleetService.class, () -> fleet)
                    .withBean(Clock.class, () -> Clock.fixed(now, ZoneOffset.UTC))
                    .withBean(V1DittoProperties.class, () -> new V1DittoProperties("mock", URI.create("http://127.0.0.1:" + server.getAddress().getPort()),
                            Duration.ofSeconds(1), Duration.ofSeconds(1), Duration.ofSeconds(5), Duration.ofSeconds(30), null, null, null))
                    .run(context -> {
                        assertThat(context).hasNotFailed();
                        assertThat(recovered.await(4, TimeUnit.SECONDS)).isTrue();
                        var writer = context.getBean(FleetMaterializer.class);
                        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(1);
                        while (writer.lastSuccess() == null && System.nanoTime() < deadline) Thread.sleep(5);
                        assertThat(writer.lastSuccess()).isEqualTo(now);
                        assertThat(writer.failureCount()).isEqualTo(1);
                        assertThat(maximum).hasValue(1);
                        assertThat(progressed).as("fleet I/O must not block legacy scheduled tasks").isTrue();
                        verify(fleet, atLeast(2)).read();
                    });
        } finally { server.stop(0); executor.shutdownNow(); }
    }
}
