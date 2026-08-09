package com.ankit.sdv.backend.controller;

import com.ankit.sdv.backend.dto.DiagnosticActionRequest;
import com.ankit.sdv.backend.dto.DiagnosticActionResponse;
import com.ankit.sdv.backend.service.DiagnosticActionService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;

@RestController
@RequestMapping("/api/v1/diagnostics/actions")
public class DiagnosticActionController {

    private final DiagnosticActionService diagnosticActionService;

    public DiagnosticActionController(
            DiagnosticActionService diagnosticActionService
    ) {
        this.diagnosticActionService =
                diagnosticActionService;
    }

    @PostMapping
    public ResponseEntity<DiagnosticActionResponse>
    submitAction(
            @Valid @RequestBody
            DiagnosticActionRequest request
    ) {
        DiagnosticActionResponse response =
                diagnosticActionService.submit(request);

        return ResponseEntity
                .accepted()
                .body(response);
    }

    @GetMapping("/{actionId}")
    public ResponseEntity<DiagnosticActionResponse>
    getAction(
            @PathVariable("actionId") String actionId
    ) {
        DiagnosticActionResponse response =
                diagnosticActionService.getById(actionId);

        return ResponseEntity.ok(response);
    }
}