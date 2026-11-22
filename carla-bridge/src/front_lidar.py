"""V2-C3 front-region extraction (stub: names only, behaviour pending)."""

from typing import NamedTuple, Optional

RANGE_METERS = 50.0
NO_FRONT_HIT = "NO_FRONT_HIT"
INVALID_FRAME = "INVALID_FRAME"


class FrontReading(NamedTuple):
    distance_meters: Optional[float]
    sensor_available: bool
    reason: Optional[str]


def extract_front(raw_data: bytes) -> FrontReading:
    return FrontReading(None, True, None)
