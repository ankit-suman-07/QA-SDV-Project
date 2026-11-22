"""Per-vehicle frame handling (stub: names only, behaviour pending)."""

NO_SENSOR_DATA = "NO_SENSOR_DATA"
STALE_FRAME = "STALE_FRAME"


class VehicleStream:
    def __init__(self, manifest, vehicle_id):
        pass

    def on_frame(self, frame, simulation_seconds, raw_data, velocity, processed_at):
        return None, {}

    def on_missing(self, frame, simulation_seconds):
        return {}


def pace_delay(simulation_elapsed, wall_elapsed):
    return -1.0
