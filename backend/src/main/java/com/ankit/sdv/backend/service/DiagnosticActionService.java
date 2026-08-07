package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.dto.DiagnosticActionRequest;
import com.ankit.sdv.backend.dto.DiagnosticActionResponse;
import com.ankit.sdv.backend.model.DiagnosticActionStatus;

public interface DiagnosticActionService {

    DiagnosticActionResponse submit(
            DiagnosticActionRequest request
    );

    DiagnosticActionResponse getById(String actionId);

    DiagnosticActionResponse updateStatus(String actionId, DiagnosticActionStatus status);
}