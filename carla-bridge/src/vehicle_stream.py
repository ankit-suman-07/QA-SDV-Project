"""Per-vehicle frame handling and real-time pacing for the CARLA fleet runner.

One VehicleStream per vehicle. A LiDAR frame becomes exactly one observation
with the next sequence number. A missing frame produces only a log entry (no
observation, sequence unchanged): silence is never turned into a reading. A
repeated or older frame is dropped, because consumers require sequence and
frame to increase together.
"""

from carla_observation import build_observation
from front_lidar import extract_front

NO_SENSOR_DATA = "NO_SENSOR_DATA"
STALE_FRAME = "STALE_FRAME"


class VehicleStream:
    def __init__(self, manifest, vehicle_id):
        self._manifest = manifest
        self.vehicle_id = vehicle_id
        self._sequence = 0
        self._last_frame = None

    def _log(self, frame, simulation_seconds, reason, event_id=None, distance=None, available=None):
        return {"vehicleId": self.vehicle_id, "eventId": event_id, "frame": frame,
                "simulationSeconds": simulation_seconds, "distanceMeters": distance,
                "sensorAvailable": available, "reason": reason}

    def on_frame(self, frame, simulation_seconds, raw_data, velocity, processed_at):
        if self._last_frame is not None and frame <= self._last_frame:
            return None, self._log(frame, simulation_seconds, STALE_FRAME)
        reading = extract_front(raw_data)
        observation = build_observation(
            manifest=self._manifest, vehicle_id=self.vehicle_id, sequence=self._sequence,
            frame=frame, simulation_seconds=simulation_seconds, reading=reading,
            processed_at=processed_at, velocity=velocity)
        self._sequence += 1
        self._last_frame = frame
        return observation, self._log(
            frame, observation["simulationSeconds"], reading.reason, observation["eventId"],
            reading.distance_meters, reading.sensor_available)

    def on_missing(self, frame, simulation_seconds):
        return self._log(frame, simulation_seconds, NO_SENSOR_DATA)


def pace_delay(simulation_elapsed, wall_elapsed):
    """Seconds to wait so simulation time never runs ahead of the wall clock."""
    return max(0.0, simulation_elapsed - wall_elapsed)
