"""V2-C1/C2 run manifest: one CARLA session's identity mapping and clock origins.

Same vehicle rows as tests/fixtures/v2/observations/session-manifest.json, so
consumers (scripts.v2_dev.observation_mapping) read it unchanged. Actor and
sensor IDs are runtime values recorded for evidence; they are never identities.
Origins are rounded to milliseconds so the observation clock mapping is exact.
"""

from datetime import timedelta, timezone

VEHICLE_IDS = ("vehicle-001", "vehicle-002", "vehicle-003")
BROKER_PORT = 55555


def _iso_ms(moment):
    moment = moment.astimezone(timezone.utc)
    moment -= timedelta(microseconds=moment.microsecond % 1000)
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def build_manifest(*, session_id, generation, utc_origin, simulation_origin, actors, run):
    if type(generation) is not int or generation < 1:
        raise ValueError("session generation must be an integer >= 1")
    rows = sorted(actors)
    if tuple(vehicle for vehicle, _, _ in rows) != VEHICLE_IDS:
        raise ValueError("actors must map vehicle-001, vehicle-002 and vehicle-003 exactly once")
    runtime_ids = [actor for _, actor, _ in rows] + [sensor for _, _, sensor in rows]
    if len(set(runtime_ids)) != len(runtime_ids):
        raise ValueError("each actor and sensor ID must be distinct")

    vehicles = []
    for vehicle_id, actor_id, sensor_id in rows:
        number = vehicle_id.rsplit("-", 1)[1]
        vehicles.append({
            "vehicleId": vehicle_id,
            "actorId": actor_id,
            "sensorId": sensor_id,
            "provider": f"provider-{number}",
            "broker": f"kuksa-{number}",
            "brokerPort": BROKER_PORT,
            "app": f"app-{number}",
            "twinId": f"sdv:{vehicle_id}",
        })

    return {
        "provenance": "CARLA",
        "sessionId": session_id,
        "sessionGeneration": generation,
        "utcOrigin": _iso_ms(utc_origin),
        "simulationOrigin": round(simulation_origin, 3),
        "vehicles": vehicles,
        "run": run,
    }
