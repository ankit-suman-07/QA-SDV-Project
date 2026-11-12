package com.ankit.sdv.backend.config;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;

import java.net.InetSocketAddress;
import java.net.URI;
import java.time.Duration;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;

class V1DittoTransportTest {
    V1DittoProperties config(int port) {
        return new V1DittoProperties("mock", URI.create("http://127.0.0.1:" + port),
                Duration.ofMillis(100), Duration.ofMillis(100), Duration.ofSeconds(5), Duration.ofSeconds(30), null, null, null);
    }
    @Test void aRealDelayedHttpResponseIsBoundedAndARefusedConnectionIsUnavailable() throws Exception {
        var server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        var executor = Executors.newCachedThreadPool();
        var entered = new CountDownLatch(1);
        var release = new CountDownLatch(1);
        server.setExecutor(executor);
        server.createContext("/", exchange -> {
            entered.countDown();
            try { release.await(5, TimeUnit.SECONDS); }
            catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); }
            finally { exchange.close(); }
        });
        server.start();
        int port = server.getAddress().getPort();
        try {
            var reader = new V1DittoConfiguration().httpVehicleTwinReader(config(port));
            long start = System.nanoTime();
            assertThat(reader.read("vehicle-002", "sdv:vehicle-002")).isEmpty();
            assertThat(Duration.ofNanos(System.nanoTime() - start)).isLessThan(Duration.ofSeconds(3));
            assertThat(entered.await(1, TimeUnit.SECONDS)).isTrue();
        } finally {
            release.countDown();
            server.stop(0);
            executor.shutdownNow();
        }
        var reader = new V1DittoConfiguration().httpVehicleTwinReader(config(port));
        assertThat(reader.read("vehicle-001", "sdv:vehicle-001")).isEmpty();
    }
}
