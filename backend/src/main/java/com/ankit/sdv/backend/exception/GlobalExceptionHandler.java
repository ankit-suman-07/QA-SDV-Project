package com.ankit.sdv.backend.exception;

import com.ankit.sdv.backend.dto.ApiErrorResponse;
import com.ankit.sdv.backend.dto.DiagnosticDispatchErrorResponse;
import org.springframework.http.converter.HttpMessageNotReadableException;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import org.springframework.web.bind.MethodArgumentNotValidException;
import java.util.NoSuchElementException;

import java.util.stream.Collectors;

import java.time.Instant;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ProviderDispatchException.class)
    public ResponseEntity<DiagnosticDispatchErrorResponse> handleDispatchFailure(
            ProviderDispatchException exception, HttpServletRequest request) {
        var action = exception.action();
        var response = new DiagnosticDispatchErrorResponse(Instant.now(), exception.reason().code,
                exception.getMessage(), request.getRequestURI(), action == null ? null : action.actionId(),
                action == null ? null : action.traceId(), exception.reason().dispatch);
        return ResponseEntity.status(exception.reason().httpStatus).body(response);
    }

    @ExceptionHandler({InvalidDiagnosticRequestException.class, HttpMessageNotReadableException.class})
    public ResponseEntity<ApiErrorResponse> handleInvalidRequest(Exception exception, HttpServletRequest request) {
        return ResponseEntity.badRequest().body(new ApiErrorResponse(Instant.now(), "VALIDATION_ERROR",
                "Invalid diagnostic request fields or JSON", request.getRequestURI()));
    }


    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ApiErrorResponse>
    handleIllegalArgumentException(
            IllegalArgumentException exception,
            HttpServletRequest request
    ) {

        ApiErrorResponse response = new ApiErrorResponse(
                Instant.now(),
                "VEHICLE_NOT_FOUND",
                exception.getMessage(),
                request.getRequestURI()
        );

        return ResponseEntity
                .status(HttpStatus.NOT_FOUND)
                .body(response);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiErrorResponse>
    handleValidationException(
            MethodArgumentNotValidException exception,
            HttpServletRequest request
    ) {
        String message = exception
                .getBindingResult()
                .getFieldErrors()
                .stream()
                .map(error ->
                        error.getField() + ": "
                                + error.getDefaultMessage()
                )
                .sorted()
                .collect(Collectors.joining(", "));

        ApiErrorResponse response = new ApiErrorResponse(
                Instant.now(),
                "VALIDATION_ERROR",
                message,
                request.getRequestURI()
        );

        return ResponseEntity
                .status(HttpStatus.BAD_REQUEST)
                .body(response);
    }

    @ExceptionHandler(NoSuchElementException.class)
    public ResponseEntity<ApiErrorResponse>
    handleNoSuchElementException(
            NoSuchElementException exception,
            HttpServletRequest request
    ) {
        ApiErrorResponse response =
                new ApiErrorResponse(
                        Instant.now(),
                        "ACTION_NOT_FOUND",
                        exception.getMessage(),
                        request.getRequestURI()
                );

        return ResponseEntity
                .status(HttpStatus.NOT_FOUND)
                .body(response);
    }
}