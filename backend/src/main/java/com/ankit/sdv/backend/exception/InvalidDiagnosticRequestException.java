package com.ankit.sdv.backend.exception;

public class InvalidDiagnosticRequestException extends IllegalArgumentException {
    public InvalidDiagnosticRequestException() { super("Invalid diagnostic action fields or padded vehicle ID"); }
}
