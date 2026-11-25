"""V2-C3 front-region extraction from raw sensor.lidar.ray_cast data.

Sensor coordinates: x forward, y right, z up, metres. Each detection is four
little-endian float32 values (x, y, z, intensity), 16 bytes. The reading is the
minimum x inside the front region, measured from the sensor (not the bumper and
not Euclidean range). Health is decided downstream by Velocitas, never here.
"""

import math
import struct
from typing import NamedTuple, Optional

RANGE_METERS = 50.0
HALF_WIDTH_METERS = 1.5
Z_MIN_METERS = -1.0
Z_MAX_METERS = 1.0

NO_FRONT_HIT = "NO_FRONT_HIT"
INVALID_FRAME = "INVALID_FRAME"

_POINT = struct.Struct("<4f")


class FrontReading(NamedTuple):
    distance_meters: Optional[float]
    sensor_available: bool
    reason: Optional[str]


UNAVAILABLE = FrontReading(None, False, INVALID_FRAME)


def extract_front(raw_data: bytes) -> FrontReading:
    if not raw_data or len(raw_data) % _POINT.size:
        return UNAVAILABLE

    nearest = math.inf
    for x, y, z, intensity in _POINT.iter_unpack(raw_data):
        if not all(map(math.isfinite, (x, y, z, intensity))):
            return UNAVAILABLE
        if (0 < x <= RANGE_METERS and abs(y) <= HALF_WIDTH_METERS
                and Z_MIN_METERS <= z <= Z_MAX_METERS):
            nearest = min(nearest, x)

    if nearest == math.inf:
        return FrontReading(RANGE_METERS, True, NO_FRONT_HIT)
    return FrontReading(float(nearest), True, None)
