"""Offline V2 health and recovery for validated, ordered-source observations."""

from datetime import datetime, timedelta
from hashlib import sha256
from math import isfinite

from v1_event import classify, format_timestamp

RECOVERY_WINDOW = timedelta(seconds=2)
MAX_OBSERVATION_GAP = timedelta(milliseconds=500)
MAX_OBSERVATION_AGE = timedelta(seconds=5)
MAX_FUTURE_OFFSET = timedelta(seconds=1)
# The contract gives no event-ID retention limit. Bound the in-memory ledger
# at about 109 minutes at the nominal 10 Hz rate. At capacity, reject further
# observations until the caller supplies an authorized successor session.
MAX_SESSION_EVENT_IDS = 65_536


class V2HealthRecovery:
    """Track one vehicle with injected UTC and monotonic receipt clocks.

    The caller supplies validated V2 observations from an authorized source
    session. Receipt time is measured in monotonic seconds. Accepted event IDs
    are tracked as fixed-size digests for the current vehicle and session.
    The ledger does not evict entries and is not persisted across process restarts.
    """

    def __init__(self, vehicle_id, utc_now, monotonic_now):
        self._vehicle_id = vehicle_id
        self._utc_now = utc_now
        self._monotonic_now = monotonic_now
        self._health = "HEALTHY"
        self._faults = []
        self._started_at = None
        self._latest = None
        self._accepted_event_ids = set()

    def evaluate_silence(self) -> dict:
        """Evaluate clock-only dropout and return a local per-vehicle snapshot."""
        latest = self._latest
        source_silent = (
            latest is None
            or self._monotonic_now() > latest[-1] + MAX_OBSERVATION_GAP.total_seconds()
        )
        if source_silent:
            self._started_at = None

        recovering = self._started_at is not None
        return {
            "vehicleId": self._vehicle_id,
            "sourceSilent": source_silent,
            "health": self._health if latest is not None else None,
            "faults": self._faults.copy() if latest is not None else None,
            "recoveryState": "IN_PROGRESS" if recovering else "NONE",
            "recoveryStartedAt": format_timestamp(self._started_at) if recovering else None,
        }

    def process(self, observation):
        """Return a V2 health event while retaining the original observation fields."""
        if observation["vehicleId"] != self._vehicle_id:
            raise ValueError("observation vehicle does not match recovery vehicle")

        session = (observation["sessionGeneration"], observation["sessionId"])
        event_id = observation["eventId"]
        event_key = sha256(event_id.encode("utf-8")).digest()
        latest = self._latest
        if latest is not None:
            previous_session, previous_id, *_ = latest
            if session[0] <= previous_session[0] and session != previous_session:
                raise ValueError("out-of-order source session")
            if event_id == previous_id or (
                session == previous_session and event_key in self._accepted_event_ids
            ):
                raise ValueError("duplicate event ID")
            if session == previous_session and len(self._accepted_event_ids) >= MAX_SESSION_EVENT_IDS:
                raise ValueError("source session event-ID capacity reached")

        source = datetime.fromisoformat(
            observation["sourceTimestamp"].replace("Z", "+00:00")
        )
        if source.utcoffset() != timedelta(0):
            self._started_at = None
            raise ValueError("sourceTimestamp must be UTC")
        now = self._utc_now()
        receipt = self._monotonic_now()
        sequence = observation["sequence"]
        frame = observation["frame"]

        if self._latest is not None:
            _, _, previous_sequence, previous_frame, previous_source, previous_receipt = self._latest
            if (
                source <= previous_source
                or receipt < previous_receipt
                or (
                    session == previous_session
                    and (sequence <= previous_sequence or frame <= previous_frame)
                )
            ):
                raise ValueError("duplicate or out-of-order observation")
            if (
                session != previous_session
                or source - previous_source > MAX_OBSERVATION_GAP
                or receipt > previous_receipt + MAX_OBSERVATION_GAP.total_seconds()
            ):
                self._started_at = None

        lidar = observation["lidar"]
        available = lidar["sensorAvailable"]
        distance = lidar["distanceMeters"]
        if type(available) is not bool or (
            available and (type(distance) not in (int, float) or not isfinite(distance) or distance < 0)
        ) or (not available and distance is not None):
            self._started_at = None
            raise ValueError("invalid LiDAR observation")

        health, faults = classify(distance, available)
        fresh = -MAX_FUTURE_OFFSET <= now - source <= MAX_OBSERVATION_AGE
        if health != "HEALTHY":
            self._health, self._faults = health, faults
            self._started_at = None
        elif not fresh:
            self._started_at = None
        elif self._health != "HEALTHY":
            if self._started_at is None:
                self._started_at = source
            if source - self._started_at >= RECOVERY_WINDOW:
                self._health, self._faults = health, faults
                self._started_at = None

        if latest is not None and session != previous_session:
            self._accepted_event_ids.clear()
        self._accepted_event_ids.add(event_key)
        self._latest = session, event_id, sequence, frame, source, receipt
        recovering = self._started_at is not None
        return {
            **observation,
            "lidar": lidar.copy(),
            "health": self._health,
            "faults": self._faults.copy(),
            "recoveryState": "IN_PROGRESS" if recovering else "NONE",
            "recoveryStartedAt": format_timestamp(self._started_at) if recovering else None,
            "sourceSilent": False,
        }
