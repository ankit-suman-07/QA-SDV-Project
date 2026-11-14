package com.ankit.sdv.backend.dto;

import com.ankit.sdv.backend.model.DispatchStatus;
import java.time.Instant;

public record DiagnosticDispatchErrorResponse(Instant timestamp, String code, String message,
        String path, String actionId, String traceId, DispatchStatus dispatchStatus) {}
