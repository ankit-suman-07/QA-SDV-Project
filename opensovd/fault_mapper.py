"""
opensovd/fault_mapper.py

Maps Ditto vehicle-001 faults into OpenSOVD-shaped diagnostic resources,
per docs/04-vehicle-health-contracts.md Section 5 (Fault Record),
docs/10-iteration-3-contract.md (Fault Contract, correlated faults), and
Section 7 ("Atharva will finalize OpenSOVD mappings").

OpenSOVD's mock gateway is confirmed read-only (see
docs/evidence/iteration-2/07-opensovd-confirmed-read-only.png), so this
module does not push data into it. It produces output matching the
contract's shape, testable independently of the gateway.

Two fault shapes are supported:
- Single-signal faults (BATTERY_LOW, TEMPERATURE_HIGH, TIRE_PRESSURE_LOW_*)
  - one affected signal, one threshold, WARNING/CRITICAL severity tiers.
- Correlated faults (COOLING_SYSTEM_FAILURE) - two affected signals, both
  must breach their own threshold, single CRITICAL severity per the
  Iteration 3 contract.

Known limitation: faultId, detectedAt/detectedTimestamp, clearedAt,
traceId, actionId, and correlationId require persistent per-fault
lifecycle state. If present in Ditto's diagnostics.activeFaultDetails
feature (matched by code), they are used; otherwise they are returned as
None, pending that state being written by the integration bridge.
"""
from dataclasses import dataclass, asdict
from typing import Optional

# Matches docs/04 Section 4 "Proposed Thresholds"
FAULT_DEFINITIONS = {
    "BATTERY_LOW": {
        "description": "Battery state of charge below safe operating threshold",
        "affected_signal": "batteryPercent",
        "unit": "%",
        "warning_threshold": 20,
        "critical_threshold": 10,
        "direction": "below",
    },
    "TEMPERATURE_HIGH": {
        "description": "Vehicle temperature above safe operating threshold",
        "affected_signal": "temperatureCelsius",
        "unit": "\u00b0C",
        "warning_threshold": 90,
        "critical_threshold": 105,
        "direction": "above",
    },
}

TIRE_POSITIONS = {
    "TIRE_PRESSURE_LOW_FRONT_LEFT": "frontLeft",
    "TIRE_PRESSURE_LOW_FRONT_RIGHT": "frontRight",
    "TIRE_PRESSURE_LOW_REAR_LEFT": "rearLeft",
    "TIRE_PRESSURE_LOW_REAR_RIGHT": "rearRight",
}
TIRE_WARNING_THRESHOLD = 28
TIRE_CRITICAL_THRESHOLD = 24

# Matches docs/10-iteration-3-contract.md "Correlated Health Rule"
CORRELATED_FAULT_DEFINITIONS = {
    "COOLING_SYSTEM_FAILURE": {
        "description": "High temperature correlated with low coolant pressure",
        "severity": "CRITICAL",
        "signals": {
            "temperatureCelsius": {
                "activation_threshold": 105.0,
                "recovery_threshold": 100.0,
                "direction": "above",
            },
            "coolantPressureKpa": {
                "activation_threshold": 150.0,
                "recovery_threshold": 180.0,
                "direction": "below",
            },
        },
    },
}


@dataclass
class OpenSovdFault:
    faultId: Optional[str]
    code: str
    description: str
    severity: str
    status: str
    affectedSignal: str
    observedValue: Optional[float]
    unit: str
    threshold: Optional[float]
    sourceTimestamp: Optional[str]
    detectedTimestamp: Optional[str]
    lastUpdatedTimestamp: Optional[str]
    clearedTimestamp: Optional[str]
    correlationId: Optional[str]

    def to_dict(self):
        return asdict(self)


def _lookup_fault_definition(fault_code: str):
    if fault_code in FAULT_DEFINITIONS:
        return FAULT_DEFINITIONS[fault_code], None
    if fault_code in TIRE_POSITIONS:
        wheel = TIRE_POSITIONS[fault_code]
        return {
            "description": f"Tire pressure below safe threshold ({wheel})",
            "affected_signal": f"tirePressurePsi.{wheel}",
            "unit": "psi",
            "warning_threshold": TIRE_WARNING_THRESHOLD,
            "critical_threshold": TIRE_CRITICAL_THRESHOLD,
            "direction": "below",
        }, wheel
    return None, None


def _get_observed_value(thing: dict, affected_signal: str, wheel: str = None):
    signals = thing.get("features", {}).get("signals", {}).get("properties", {})
    if wheel:
        return signals.get("tirePressurePsi", {}).get(wheel)
    return signals.get(affected_signal)


def _lookup_fault_detail(thing: dict, fault_code: str) -> dict:
    """Looks for a richer fault record in diagnostics.activeFaultDetails,
    matched by code. Returns {} if not present (bridge hasn't written it
    yet) - callers must treat every field here as optional."""
    diagnostics = thing.get("features", {}).get("diagnostics", {}).get("properties", {})
    for detail in diagnostics.get("activeFaultDetails", []):
        if isinstance(detail, dict) and detail.get("code") == fault_code:
            return detail
    return {}


def map_fault_to_opensovd(fault_code: str, thing: dict) -> dict:
    """Maps one active single-signal fault code into an OpenSOVD-shaped
    diagnostic resource."""
    definition, wheel = _lookup_fault_definition(fault_code)
    if definition is None:
        raise ValueError(f"Unknown fault code: {fault_code!r}")

    observed_value = _get_observed_value(thing, definition["affected_signal"], wheel)

    severity, threshold = "WARNING", definition["warning_threshold"]
    if observed_value is not None:
        breach_critical = (
            observed_value <= definition["critical_threshold"]
            if definition["direction"] == "below"
            else observed_value >= definition["critical_threshold"]
        )
        breach_warning = (
            observed_value <= definition["warning_threshold"]
            if definition["direction"] == "below"
            else observed_value >= definition["warning_threshold"]
        )
        if breach_critical:
            severity, threshold = "CRITICAL", definition["critical_threshold"]
        elif breach_warning:
            severity, threshold = "WARNING", definition["warning_threshold"]

    signals = thing.get("features", {}).get("signals", {}).get("properties", {})
    health = thing.get("features", {}).get("health", {}).get("properties", {})
    detail = _lookup_fault_detail(thing, fault_code)

    fault = OpenSovdFault(
        faultId=detail.get("faultId"),
        code=fault_code,
        description=definition["description"],
        severity=severity,
        status="ACTIVE" if fault_code in health.get("activeFaults", []) else "CLEARED",
        affectedSignal=definition["affected_signal"],
        observedValue=observed_value,
        unit=definition["unit"],
        threshold=threshold,
        sourceTimestamp=signals.get("sourceTimestamp"),
        detectedTimestamp=detail.get("detectedAt"),
        lastUpdatedTimestamp=health.get("processedTimestamp"),
        clearedTimestamp=detail.get("clearedAt"),
        correlationId=detail.get("traceId"),
    )
    return fault.to_dict()


def map_correlated_fault_to_opensovd(fault_code: str, thing: dict) -> dict:
    """Maps one active correlated fault code (e.g. COOLING_SYSTEM_FAILURE)
    into the shape defined in docs/10-iteration-3-contract.md's
    'Correlated Fault Representation'."""
    definition = CORRELATED_FAULT_DEFINITIONS.get(fault_code)
    if definition is None:
        raise ValueError(f"Unknown correlated fault code: {fault_code!r}")

    signals = thing.get("features", {}).get("signals", {}).get("properties", {})
    health = thing.get("features", {}).get("health", {}).get("properties", {})
    detail = _lookup_fault_detail(thing, fault_code)

    affected_signals = list(definition["signals"].keys())
    observed_values = {name: signals.get(name) for name in affected_signals}
    activation_thresholds = {
        name: cfg["activation_threshold"] for name, cfg in definition["signals"].items()
    }
    recovery_thresholds = {
        name: cfg["recovery_threshold"] for name, cfg in definition["signals"].items()
    }

    return {
        "code": fault_code,
        "description": definition["description"],
        "severity": definition["severity"],
        "status": "ACTIVE" if fault_code in health.get("activeFaults", []) else "CLEARED",
        "affectedSignals": affected_signals,
        "observedValues": observed_values,
        "activationThresholds": activation_thresholds,
        "recoveryThresholds": recovery_thresholds,
        "detectedAt": detail.get("detectedAt"),
        "clearedAt": detail.get("clearedAt"),
        "eventId": detail.get("eventId"),
        "traceId": detail.get("traceId"),
        "actionId": detail.get("actionId"),
    }


def map_all_active_faults(thing: dict) -> list:
    """Maps every currently-active fault on the twin, dispatching each
    code to the correct mapper (single-signal vs. correlated)."""
    health = thing.get("features", {}).get("health", {}).get("properties", {})
    results = []
    for code in health.get("activeFaults", []):
        if code in CORRELATED_FAULT_DEFINITIONS:
            results.append(map_correlated_fault_to_opensovd(code, thing))
        else:
            results.append(map_fault_to_opensovd(code, thing))
    return results


def build_diagnostic_resource(fault: dict, vehicle_id: str = "vehicle-001") -> dict:
    """Wraps a mapped fault (single-signal or correlated) in the envelope
    from docs/10's 'OpenSOVD-Compatible Diagnostic Contract'."""
    return {
        "vehicleId": vehicle_id,
        "resourceType": "diagnosticFault",
        "fault": fault,
        "traceId": fault.get("traceId") or fault.get("correlationId"),
        "actionId": fault.get("actionId"),
    }