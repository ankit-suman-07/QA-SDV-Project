"""
opensovd/fault_mapper.py

Maps a Ditto vehicle-001 fault into an OpenSOVD-shaped diagnostic resource,
per docs/04-vehicle-health-contracts.md Section 5 (Fault Record) and
Section 7 ("Atharva will finalize OpenSOVD mappings").

OpenSOVD's mock gateway is confirmed read-only (see
docs/evidence/iteration-2/07-opensovd-confirmed-read-only.png), so this
module does not push data into it. It produces output matching the same
field shape the contract requires, testable independently of the gateway
- this is the documented fallback adapter from the Iteration 1 research.

Known limitation: Ditto currently only stores active fault CODES
(health.activeFaults: [string]), not full Fault Record objects. Fields
requiring persistent per-fault lifecycle state (faultId, detectedTimestamp,
correlationId) cannot be derived from Ditto's current schema and are
returned as None, pending that state being added to the health engine.
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


def map_fault_to_opensovd(fault_code: str, thing: dict) -> dict:
    """Maps one active fault code (as stored in Ditto's health.activeFaults)
    into an OpenSOVD-shaped diagnostic resource."""
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

    fault = OpenSovdFault(
        faultId=None,  # needs persistent per-fault lifecycle tracking - not in Ditto yet
        code=fault_code,
        description=definition["description"],
        severity=severity,
        status="ACTIVE" if fault_code in health.get("activeFaults", []) else "CLEARED",
        affectedSignal=definition["affected_signal"],
        observedValue=observed_value,
        unit=definition["unit"],
        threshold=threshold,
        sourceTimestamp=signals.get("sourceTimestamp"),
        detectedTimestamp=None,  # needs activation-time tracking - not in Ditto yet
        lastUpdatedTimestamp=health.get("processedTimestamp"),
        clearedTimestamp=None,  # null while active; cleared-history not retained yet
        correlationId=None,  # needs trace ID propagation - not implemented yet
    )
    return fault.to_dict()


def map_all_active_faults(thing: dict) -> list:
    """Maps every currently-active fault on the twin."""
    health = thing.get("features", {}).get("health", {}).get("properties", {})
    return [map_fault_to_opensovd(code, thing) for code in health.get("activeFaults", [])]