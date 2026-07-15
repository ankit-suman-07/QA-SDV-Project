package com.ankit.sdv.backend.dto;

import java.time.Instant;

public record ApiErrorResponse(
        Instant timestamp,
        String code,
        String message,
        String path
) {
}