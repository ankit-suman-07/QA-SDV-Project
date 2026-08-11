FAULT_CODE = "COOLING_SYSTEM_FAILURE"

FAULT_DESCRIPTION = (
    "High temperature correlated with "
    "low coolant pressure"
)

AFFECTED_SIGNALS = [
    "temperatureCelsius",
    "coolantPressureKpa",
]

ACTIVATION_THRESHOLDS = {
    "temperatureCelsius": 105.0,
    "coolantPressureKpa": 150.0,
}

RECOVERY_THRESHOLDS = {
    "temperatureCelsius": 100.0,
    "coolantPressureKpa": 180.0,
}


def build_active_fault_detail(
    temperature_celsius,
    coolant_pressure_kpa,
    detected_at,
    event_id,
    trace_id,
    action_id=None,
):
    return {
        "code": FAULT_CODE,
        "description": FAULT_DESCRIPTION,
        "severity": "CRITICAL",
        "status": "ACTIVE",
        "affectedSignals": list(
            AFFECTED_SIGNALS
        ),
        "observedValues": {
            "temperatureCelsius": float(
                temperature_celsius
            ),
            "coolantPressureKpa": float(
                coolant_pressure_kpa
            ),
        },
        "activationThresholds": dict(
            ACTIVATION_THRESHOLDS
        ),
        "recoveryThresholds": dict(
            RECOVERY_THRESHOLDS
        ),
        "detectedAt": detected_at,
        "clearedAt": None,
        "eventId": event_id,
        "traceId": trace_id,
        "actionId": action_id,
    }

def is_activation_condition(
    temperature_celsius,
    coolant_pressure_kpa,
):
    return (
        float(temperature_celsius)
        >= ACTIVATION_THRESHOLDS[
            "temperatureCelsius"
        ]
        and float(coolant_pressure_kpa)
        <= ACTIVATION_THRESHOLDS[
            "coolantPressureKpa"
        ]
    )


def is_recovery_condition(
    temperature_celsius,
    coolant_pressure_kpa,
):
    return (
        float(temperature_celsius)
        <= RECOVERY_THRESHOLDS[
            "temperatureCelsius"
        ]
        and float(coolant_pressure_kpa)
        >= RECOVERY_THRESHOLDS[
            "coolantPressureKpa"
        ]
    )