package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.dto.DiagnosticActionRequest;
import com.ankit.sdv.backend.dto.DiagnosticActionResponse;

public interface DiagnosticActionService {

    DiagnosticActionResponse submit(
            DiagnosticActionRequest request
    );

    DiagnosticActionResponse getById(String actionId);
}