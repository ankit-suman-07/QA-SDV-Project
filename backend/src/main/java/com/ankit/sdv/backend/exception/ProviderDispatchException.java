package com.ankit.sdv.backend.exception;

import com.ankit.sdv.backend.dto.DiagnosticActionResponse;
import com.ankit.sdv.backend.model.DiagnosticActionStatus;
import com.ankit.sdv.backend.model.DispatchStatus;
import org.springframework.http.HttpStatus;

/** Safe failure classification. No provider URL, body or raw network exception is exposed. */
public class ProviderDispatchException extends RuntimeException {
    public enum Reason {
        REJECTED(HttpStatus.BAD_GATEWAY, "PROVIDER_REJECTED", DiagnosticActionStatus.REJECTED, DispatchStatus.REJECTED,
                "Provider rejected the scenario request"),
        UNAVAILABLE(HttpStatus.SERVICE_UNAVAILABLE, "PROVIDER_UNAVAILABLE", DiagnosticActionStatus.FAILED, DispatchStatus.FAILED,
                "Provider connection is unavailable"),
        TIMEOUT(HttpStatus.GATEWAY_TIMEOUT, "PROVIDER_TIMEOUT", DiagnosticActionStatus.FAILED, DispatchStatus.UNKNOWN,
                "Provider dispatch timed out; execution outcome is unknown"),
        BAD_RESPONSE(HttpStatus.BAD_GATEWAY, "PROVIDER_BAD_RESPONSE", DiagnosticActionStatus.FAILED, DispatchStatus.FAILED,
                "Provider returned no trustworthy acknowledgement");

        public final HttpStatus httpStatus;
        public final String code;
        public final DiagnosticActionStatus lifecycle;
        public final DispatchStatus dispatch;
        private final String message;
        Reason(HttpStatus httpStatus, String code, DiagnosticActionStatus lifecycle, DispatchStatus dispatch, String message) {
            this.httpStatus = httpStatus; this.code = code; this.lifecycle = lifecycle; this.dispatch = dispatch; this.message = message;
        }
    }
    private final Reason reason;
    private final DiagnosticActionResponse action;
    public ProviderDispatchException(Reason reason) { this(reason, null); }
    private ProviderDispatchException(Reason reason, DiagnosticActionResponse action) {
        super(reason.message); this.reason = reason; this.action = action;
    }
    public Reason reason() { return reason; }
    public DiagnosticActionResponse action() { return action; }
    public ProviderDispatchException correlate(DiagnosticActionResponse action) { return new ProviderDispatchException(reason, action); }
}
