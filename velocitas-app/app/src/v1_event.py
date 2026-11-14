"""V1 health event contract (docs/v1-interface-contracts.md 1.0.0, C3/C4).

Pure functions with no SDK imports, so they can be unit-tested directly.
Production code must not import scripts/v1_dev (contract C9).
"""

from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

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


@dataclass(frozen=True)
class Observation:
    distance: object
    sensor_available: object
    observed_at: datetime | None


def observation_from_datapoints(distance_dp, health_dp) -> Observation:
    """Build an observation from two KUKSA datapoints (.value, .timestamp).

    The observation time is the later broker timestamp of the two, because
    the provider writes both values in one call.
    """
    distance = distance_dp.value if distance_dp is not None else None
    available = health_dp.value if health_dp is not None else None
    timestamps = [
        dp.timestamp
        for dp in (distance_dp, health_dp)
        if dp is not None and dp.timestamp is not None
    ]
    observed_at = max(timestamps) if len(timestamps) == 2 else None
    return Observation(distance, available, observed_at)


class ObservationGate:
    """Decides what to publish on each poll: a new event, a retry, or nothing.

    - The first valid observation only primes the gate, so a restarted app
      does not republish a reading that ingress has already applied.
    - Only a strictly newer observation produces a new event (new eventId).
    - An unpublished event is retried unchanged until a newer one replaces it.
    - Invalid observations are never published and never drop a pending event.
    """

    def __init__(
        self,
        vehicle_id: str,
        id_factory: Callable[[str], str] = new_event_id,
    ):
        self._vehicle_id = vehicle_id
        self._id_factory = id_factory
        self._latest_at: datetime | None = None
        self._pending: tuple[dict, datetime] | None = None
        # Why the last observation was not published: None, "incomplete"
        # (missing value or timestamp), "invalid" (bad value or naive
        # timestamp) or "older" (observation time went backwards).
        self.last_skip: str | None = None

    def next_event(self, observation: Observation) -> dict | None:
        if observation.observed_at is None:
            self.last_skip = "incomplete"
            return self._pending_event()

        candidate = self._build(observation)
        if candidate is None:
            self.last_skip = "invalid"
            return self._pending_event()

        self.last_skip = None
        if self._latest_at is None:
            self._latest_at = observation.observed_at
            return self._pending_event()

        if observation.observed_at > self._latest_at:
            candidate["eventId"] = self._id_factory(self._vehicle_id)
            self._pending = (candidate, observation.observed_at)
            self._latest_at = observation.observed_at
        elif observation.observed_at < self._latest_at:
            self.last_skip = "older"

        return self._pending_event()

    def mark_published(self, event: dict) -> None:
        pending = self._pending_event()
        if pending is not None and pending["eventId"] == event.get("eventId"):
            self._pending = None

    def _build(self, observation: Observation) -> dict | None:
        try:
            return build_v1_event(
                self._vehicle_id,
                observation.observed_at,
                observation.distance,
                observation.sensor_available,
                event_id="",
            )
        except (ValueError, TypeError):
            return None

    def _pending_event(self) -> dict | None:
        return self._pending[0] if self._pending is not None else None
