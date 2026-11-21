package com.ankit.sdv.backend.diagnostic;

import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;

import static java.nio.file.StandardCopyOption.ATOMIC_MOVE;
import static java.nio.file.StandardCopyOption.REPLACE_EXISTING;
import static java.nio.file.StandardOpenOption.*;

final class ActionJournal implements AutoCloseable {
    private final ObjectMapper json;
    private final Path path;
    private final FileChannel channel;
    private final FileLock lock;
    private final Map<String, V2Action.Entry> loaded;

    ActionJournal(Path path, ObjectMapper json) throws IOException {
        this.path = path.toAbsolutePath().normalize();
        this.json = json;
        Files.createDirectories(this.path.getParent());
        channel = FileChannel.open(this.path.resolveSibling(this.path.getFileName() + ".lock"), CREATE, WRITE);
        try {
            lock = channel.tryLock();
            if (lock == null) throw new IOException("Action journal is already in use");
            loaded = Files.exists(this.path) ? json.readValue(Files.readAllBytes(this.path),
                    new TypeReference<LinkedHashMap<String, V2Action.Entry>>() {}) : Map.of();
        } catch (IOException | RuntimeException failure) {
            channel.close();
            throw failure;
        }
    }

    Map<String, V2Action.Entry> loaded() { return loaded; }

    void save(Map<String, V2Action.Entry> entries) {
        Path temp = null;
        try {
            temp = Files.createTempFile(path.getParent(), ".action-journal-", ".tmp");
            try (var file = FileChannel.open(temp, WRITE)) {
                var data = ByteBuffer.wrap(json.writeValueAsBytes(entries));
                while (data.hasRemaining()) file.write(data);
                file.force(true);
            }
            Files.move(temp, path, ATOMIC_MOVE, REPLACE_EXISTING);
        } catch (IOException | RuntimeException failure) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "Action journal write failed");
        } finally {
            if (temp != null) {
                try { Files.deleteIfExists(temp); } catch (IOException ignored) { /* previous journal still usable */ }
            }
        }
    }

    @Override public void close() throws IOException {
        try (channel) { lock.release(); }
    }
}
