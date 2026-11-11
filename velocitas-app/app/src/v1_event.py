"""V1 health event contract (docs/v1-interface-contracts.md 1.0.0, C3/C4).

Pure functions with no SDK imports, so they can be unit-tested directly.
Production code must not import scripts/v1_dev (contract C9).
"""

from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone

SCHEMA_VERSION = "1.0.0"
WARNING_DISTANCE_M = 10.0
CRITICAL_DISTANCE_M = 5.0

LIDAR_OBSTRUCTION = "LIDAR_OBSTRUCTION"
LIDAR_SENSOR_FAILURE = "LIDAR_SENSOR_FAILURE"


def topic(vehicle_id: str) -> str:
    return f"sdv/{vehicle_id}/health"


def classify(
    distance: float | None, sensor_available: bool
) -> tuple[str, list[str]]:
    """C4 table. Sensor failure has priority over obstruction."""
    if not sensor_available:
        return "CRITICAL", [LIDAR_SENSOR_FAILURE]
    if distance <= CRITICAL_DISTANCE_M:
        return "CRITICAL", [LIDAR_OBSTRUCTION]
    if distance <= WARNING_DISTANCE_M:
        return "WARNING", [LIDAR_OBSTRUCTION]
    return "HEALTHY", []


def format_timestamp(value: datetime) -> str:
    """UTC ISO 8601 ending in Z. Naive datetimes are rejected, not guessed."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    utc = value.astimezone(timezone.utc).replace(tzinfo=None)
    return utc.isoformat() + "Z"


def new_event_id(vehicle_id: str) -> str:
    return f"{vehicle_id}-{uuid.uuid4().hex}"


def _valid_distance(distance: object) -> bool:
    return (
        type(distance) in (int, float)
        and math.isfinite(distance)
        and distance >= 0
    )


def build_v1_event(
    vehicle_id: str,
    observed_at: datetime,
    distance: object,
    sensor_available: object,
    event_id: str,
) -> dict:
    if type(sensor_available) is not bool:
        raise ValueError("sensor_available must be a boolean")
    if sensor_available and not _valid_distance(distance):
        raise ValueError(f"invalid LiDAR distance: {distance!r}")

    published_distance = float(distance) if sensor_available else None
    health, faults = classify(published_distance, sensor_available)

    return {
        "schemaVersion": SCHEMA_VERSION,
        "eventId": event_id,
        "vehicleId": vehicle_id,
        "sourceTimestamp": format_timestamp(observed_at),
        "health": health,
        "faults": faults,
        "lidar": {
            "distanceMeters": published_distance,
            "sensorAvailable": sensor_available,
        },
    }


def serialize(event: dict) -> str:
    return json.dumps(event, separators=(",", ":"), allow_nan=False)
