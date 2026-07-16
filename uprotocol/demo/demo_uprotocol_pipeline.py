"""
Smart interactive uProtocol demo.

Instead of asking for fault/health values separately, this version
evaluates YOUR entered signal values against the project's actual
fault-rule baseline (proposal Section 12) and automatically decides
whether a HealthStatusChanged and/or FaultDetected/FaultCleared should
fire -- the same way the real backend health engine will behave.

Run: python3 demo_uprotocol_pipeline_smart.py
"""
import sys
import time
import uuid
sys.path.insert(0, "generated")

import common_pb2
import vehicle_status_pb2
import health_status_pb2
import vehicle_fault_pb2

# --- Fault rule baseline, per project proposal Section 12 ---
RULES = {
    "BATTERY_LOW": {
        "signal": "batteryPercent",
        "activation": lambda v: v < 20.0,
        "recovery": lambda v: v >= 25.0,
        "threshold": 20.0,
        "severity": "FAULT_WARNING",
        "health_severity": "HEALTH_WARNING",
    },
    "TEMP_HIGH": {
        "signal": "temperatureCelsius",
        "activation": lambda v: v > 105.0,
        "recovery": lambda v: v <= 100.0,
        "threshold": 105.0,
        "severity": "FAULT_CRITICAL",
        "health_severity": "HEALTH_CRITICAL",
    },
    "TIRE_PRESSURE_LOW": {
        "signal": "tirePressure (any wheel)",
        "activation": lambda v: v < 28.0,
        "recovery": lambda v: v >= 30.0,
        "threshold": 28.0,
        "severity": "FAULT_WARNING",
        "health_severity": "HEALTH_WARNING",
    },
}

# Priority for overall health when multiple faults are active: CRITICAL > WARNING > HEALTHY
SEVERITY_RANK = {"HEALTH_HEALTHY": 0, "HEALTH_WARNING": 1, "HEALTH_CRITICAL": 2}


def ask_float(prompt, default=0.0):
    raw = input(f"{prompt} [{default}]: ").strip()
    if raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        print(f"  Not a number, using default {default}")
        return default


# --- in-process transport adapter ---
_subscribers = []

def subscribe(callback):
    _subscribers.append(callback)

def publish(topic, message_bytes):
    print(f"[PUBLISH] topic={topic} bytes={len(message_bytes)}")
    for cb in _subscribers:
        cb(topic, message_bytes)

received = []

def on_message(topic, message_bytes):
    received.append((topic, message_bytes))
    print(f"[RECEIVED] topic={topic} bytes={len(message_bytes)}")

subscribe(on_message)

def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


print("=" * 60)
print("1. Enter real vehicle signal values")
print("=" * 60)

speed = ask_float("Speed (kph)")
battery = ask_float("Battery percent")
temp = ask_float("Temperature (C)")
fl = ask_float("Tire pressure - front left (psi)")
fr = ask_float("Tire pressure - front right (psi)")
rl = ask_float("Tire pressure - rear left (psi)")
rr = ask_float("Tire pressure - rear right (psi)")

meta1 = common_pb2.EventMetadata(
    vehicle_id="vehicle-001",
    event_id=str(uuid.uuid4()),
    source_timestamp=now(),
    event_timestamp=now(),
)
status_msg = vehicle_status_pb2.VehicleStatusUpdated(
    metadata=meta1,
    speed_kph=speed,
    battery_percent=battery,
    temperature_celsius=temp,
    tire_pressure_psi=vehicle_status_pb2.TirePressure(
        front_left=fl, front_right=fr, rear_left=rl, rear_right=rr
    ),
)
serialized = status_msg.SerializeToString()
publish("sdv/vehicle-001/vehicle_status_updated", serialized)
roundtrip = vehicle_status_pb2.VehicleStatusUpdated()
roundtrip.ParseFromString(serialized)
assert roundtrip == status_msg
print("[OK] VehicleStatusUpdated round-trip verified\n")

print("=" * 60)
print("2. Automatically evaluating your values against fault rules...")
print("=" * 60)

# Check each rule against the relevant entered value
tire_values = {"front_left": fl, "front_right": fr, "rear_left": rl, "rear_right": rr}
active_faults = []  # list of (fault_code, detected_value)

if RULES["BATTERY_LOW"]["activation"](battery):
    active_faults.append(("BATTERY_LOW", battery))
    print(f"  -> BATTERY_LOW activation condition MET (batteryPercent={battery} < 20.0)")
else:
    print(f"  -> BATTERY_LOW not triggered (batteryPercent={battery} >= 20.0)")

if RULES["TEMP_HIGH"]["activation"](temp):
    active_faults.append(("TEMP_HIGH", temp))
    print(f"  -> TEMP_HIGH activation condition MET (temperatureCelsius={temp} > 105.0)")
else:
    print(f"  -> TEMP_HIGH not triggered (temperatureCelsius={temp} <= 105.0)")

lowest_tire_name, lowest_tire_value = min(tire_values.items(), key=lambda kv: kv[1])
if RULES["TIRE_PRESSURE_LOW"]["activation"](lowest_tire_value):
    active_faults.append(("TIRE_PRESSURE_LOW", lowest_tire_value))
    print(f"  -> TIRE_PRESSURE_LOW activation condition MET "
          f"({lowest_tire_name}={lowest_tire_value} < 28.0)")
else:
    print(f"  -> TIRE_PRESSURE_LOW not triggered (lowest tire "
          f"{lowest_tire_name}={lowest_tire_value} >= 28.0)")

# Determine overall health status: highest severity among active faults wins
if not active_faults:
    new_health = "HEALTH_HEALTHY"
else:
    new_health = max(
        (RULES[code]["health_severity"] for code, _ in active_faults),
        key=lambda s: SEVERITY_RANK[s],
    )
print(f"\nDerived overall health status: {new_health}\n")

print("=" * 60)
print("3. HealthStatusChanged (only fires if health actually changed)")
print("=" * 60)

previous_health = input("What was the PREVIOUS health status? "
                         "[HEALTH_HEALTHY/HEALTH_WARNING/HEALTH_CRITICAL] "
                         "(default HEALTH_HEALTHY): ").strip() or "HEALTH_HEALTHY"

if previous_health != new_health:
    triggering_signal = active_faults[0][0] if active_faults else "n/a"
    meta2 = common_pb2.EventMetadata(
        vehicle_id="vehicle-001",
        event_id=str(uuid.uuid4()),
        source_timestamp=now(),
        event_timestamp=now(),
    )
    health_msg = health_status_pb2.HealthStatusChanged(
        metadata=meta2,
        previous_status=getattr(health_status_pb2, previous_health),
        new_status=getattr(health_status_pb2, new_health),
        triggering_signal=triggering_signal,
    )
    serialized = health_msg.SerializeToString()
    publish("sdv/vehicle-001/health_status_changed", serialized)
    roundtrip = health_status_pb2.HealthStatusChanged()
    roundtrip.ParseFromString(serialized)
    assert roundtrip == health_msg
    print(f"[OK] HealthStatusChanged fired: {previous_health} -> {new_health}\n")
else:
    print(f"[SKIPPED] Health status unchanged ({previous_health}) - "
          f"no event fires, matching real system behavior.\n")

print("=" * 60)
print("4. FaultDetected (fires automatically for each triggered rule)")
print("=" * 60)

fired_fault_ids = []
if not active_faults:
    print("[SKIPPED] No fault conditions were met with your entered values.\n")
else:
    for fault_code, detected_value in active_faults:
        rule = RULES[fault_code]
        fault_event_id = str(uuid.uuid4())
        meta3 = common_pb2.EventMetadata(
            vehicle_id="vehicle-001",
            event_id=fault_event_id,
            source_timestamp=now(),
            event_timestamp=now(),
        )
        fault_detected = vehicle_fault_pb2.FaultDetected(
            metadata=meta3,
            fault_code=getattr(vehicle_fault_pb2, fault_code),
            severity=getattr(vehicle_fault_pb2, rule["severity"]),
            affected_signal=rule["signal"],
            detected_value=detected_value,
            threshold=rule["threshold"],
        )
        serialized = fault_detected.SerializeToString()
        publish(f"sdv/vehicle-001/fault_detected", serialized)
        roundtrip = vehicle_fault_pb2.FaultDetected()
        roundtrip.ParseFromString(serialized)
        assert roundtrip == fault_detected
        print(f"[OK] FaultDetected fired: {fault_code} "
              f"(value={detected_value}, threshold={rule['threshold']})\n")
        fired_fault_ids.append((fault_code, fault_event_id, rule))

print("=" * 60)
print("5. FaultCleared (test recovery for each fault that fired above)")
print("=" * 60)

if not fired_fault_ids:
    print("[SKIPPED] No faults fired above, nothing to clear.\n")
else:
    for fault_code, fault_event_id, rule in fired_fault_ids:
        recovered_value = ask_float(
            f"Enter a recovery value for {fault_code}", 0.0)
        if not rule["recovery"](recovered_value):
            print(f"  [NOTE] {recovered_value} does NOT meet the real recovery "
                  f"condition for {fault_code} -- in the real system this fault "
                  f"would remain ACTIVE, not clear. Publishing anyway for testing.\n")
        meta4 = common_pb2.EventMetadata(
            vehicle_id="vehicle-001",
            event_id=fault_event_id,  # correlates to the FaultDetected above
            source_timestamp=now(),
            event_timestamp=now(),
        )
        fault_cleared = vehicle_fault_pb2.FaultCleared(
            metadata=meta4,
            fault_code=getattr(vehicle_fault_pb2, fault_code),
            cleared_value=recovered_value,
        )
        serialized = fault_cleared.SerializeToString()
        publish("sdv/vehicle-001/fault_cleared", serialized)
        roundtrip = vehicle_fault_pb2.FaultCleared()
        roundtrip.ParseFromString(serialized)
        assert roundtrip == fault_cleared
        assert roundtrip.metadata.event_id == fault_event_id
        print(f"[OK] FaultCleared fired for {fault_code}, "
              f"correlated event_id matches: True\n")

print("=" * 60)
print(f"SUMMARY: {len(received)} event(s) published and received successfully")
print(f"Derived health status from your inputs: {new_health}")
print(f"Faults triggered by your inputs: "
      f"{[f[0] for f in active_faults] if active_faults else 'none'}")
print("=" * 60)
