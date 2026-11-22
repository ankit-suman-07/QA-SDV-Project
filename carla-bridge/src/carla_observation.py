"""V2-C2 observation envelopes from front LiDAR readings.

One envelope per vehicle per LiDAR frame. Source UTC is derived from the
session manifest: sourceUTC = utcOrigin + (simulationSeconds - simulationOrigin).
Simulation seconds are rounded to milliseconds so the UTC string and the
consumer's manifest check agree exactly. Reason codes (NO_FRONT_HIT,
INVALID_FRAME) belong in run logs, not in the envelope.
"""

import json
from datetime import datetime, timedelta, timezone

SCHEMA_VERSION = "2.0.0"
PROVENANCE = "CARLA"


def _utc(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _iso(moment):
    return moment.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def build_observation(*, manifest, vehicle_id, sequence, frame, simulation_seconds,
                      reading, processed_at, velocity=None):
    if not any(row["vehicleId"] == vehicle_id for row in manifest["vehicles"]):
        raise ValueError(f"{vehicle_id} is not in the session manifest")
    if processed_at.utcoffset() != timedelta(0):
        raise ValueError("processed_at must be a UTC datetime")

    seconds = round(simulation_seconds, 3)
    if seconds < manifest["simulationOrigin"]:
        raise ValueError(f"simulation time {seconds} is before the manifest origin")
    source = _utc(manifest["utcOrigin"]) + timedelta(seconds=seconds - manifest["simulationOrigin"])
    generation = manifest["sessionGeneration"]

    observation = {
        "schemaVersion": SCHEMA_VERSION,
        "vehicleId": vehicle_id,
        "eventId": f"{vehicle_id}-s{generation}-{sequence}",
        "sessionId": manifest["sessionId"],
        "sessionGeneration": generation,
        "sequence": sequence,
        "frame": frame,
        "simulationSeconds": seconds,
        "sourceTimestamp": _iso(source),
        "processingTimestamp": _iso(processed_at),
        "provenance": PROVENANCE,
        "lidar": {
            "distanceMeters": reading.distance_meters,
            "sensorAvailable": reading.sensor_available,
        },
    }
    if velocity is not None:
        observation["velocityMetersPerSecond"] = {
            axis: float(velocity[axis]) for axis in ("x", "y", "z")
        }
    return observation


def to_json_line(observation):
    return json.dumps(observation, allow_nan=False, separators=(",", ":")) + "\n"
