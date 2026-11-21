"""Offline preparation of per-vehicle LiDAR writes from the C2 replay envelope."""

import json
from datetime import timedelta

from scripts.v1_dev.contract import ContractError, decode_event, parse_timestamp, require
from scripts.v2_dev.contract import validate

DISTANCE = "Vehicle.Automation.Lidar.Front.NearestObstacleDistance"
VALIDITY = "Vehicle.Automation.Lidar.Front.IsHealthy"


def prepare_observation(wire, *, vehicle_id, manifest, now, previous=None):
    """Return the original envelope and VSS values, or None for an exact retry.

    The caller supplies a trusted session manifest and the last accepted envelope
    for this vehicle, including across session rollover. This function performs
    no I/O and does not advance the watermark.
    """
    try:
        if isinstance(wire, bytes):
            wire = wire.decode("utf-8")
        event = decode_event(wire)
        # json.loads can produce infinity for overflowing numeric literals.
        json.dumps(event, allow_nan=False)
        validate(event)
    except ContractError:
        raise
    except (ValueError, OverflowError, RecursionError) as error:
        raise ContractError("MALFORMED_JSON", "invalid UTF-8, nesting or numeric value") from error

    require(event["vehicleId"] == vehicle_id, "TARGET_MISMATCH", "configured vehicle")
    require(any(row["vehicleId"] == vehicle_id for row in manifest["vehicles"]),
            "UNKNOWN_VEHICLE", "vehicle absent from trusted manifest")
    session = event["sessionGeneration"], event["sessionId"]
    require(session == (manifest["sessionGeneration"], manifest["sessionId"]),
            "UNREGISTERED_SESSION", "configured session")
    require("distanceMeters" in event["lidar"], "MISSING_FIELD", "lidar.distanceMeters")

    if "actionId" in event or "traceId" in event:
        for key in ("actionId", "traceId"):
            value = event.get(key)
            require(isinstance(value, str) and bool(value.strip()), "INVALID_TYPE", key)

    source = parse_timestamp(event["sourceTimestamp"])
    try:
        expected_source = parse_timestamp(manifest["utcOrigin"]) + timedelta(
            seconds=event["simulationSeconds"] - manifest["simulationOrigin"]
        )
    except OverflowError as error:
        raise ContractError("CLOCK_MAPPING", "simulation time outside UTC range") from error
    require(source == expected_source, "CLOCK_MAPPING", "source time disagrees with manifest")
    require(source - now <= timedelta(seconds=1), "FUTURE_SOURCE", "source time exceeds tolerance")

    if previous is not None:
        require(previous["vehicleId"] == vehicle_id, "TARGET_MISMATCH", "watermark vehicle")
        if event["eventId"] == previous["eventId"]:
            require(event == previous, "EVENT_ID_CONFLICT", "changed payload")
            return None
        require(source > parse_timestamp(previous["sourceTimestamp"]),
                "OUT_OF_ORDER", "source time must advance")
        if session == (previous["sessionGeneration"], previous["sessionId"]):
            require(all(event[key] > previous[key] for key in ("sequence", "frame")),
                    "OUT_OF_ORDER", "sequence and frame must advance")
        else:
            require(event["sessionGeneration"] > previous["sessionGeneration"],
                    "OUT_OF_ORDER", "session generation must advance")

    lidar = event["lidar"]
    signals = {VALIDITY: lidar["sensorAvailable"]}
    if lidar["sensorAvailable"]:
        distance = lidar["distanceMeters"]
        require(distance <= float.fromhex("0x1.fffffep127"), "INVALID_TYPE", "distance exceeds VSS float")
        signals[DISTANCE] = float(distance)
    return event, signals
