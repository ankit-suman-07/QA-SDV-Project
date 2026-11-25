"""Run three CARLA vehicles with front LiDAR and write V2 observations.

Thin CARLA layer over the tested modules (front_lidar, carla_observation,
run_manifest, vehicle_stream). Requires a running CARLA server; the client
runs in the carla-bridge container (see run-fleet.sh).

Outputs in OUT_DIR:
  manifest.json          session identity, actor/sensor IDs, clock origins, settings
  vehicle-00N.jsonl      one V2-C2 observation per line (observation_publisher input)
  run-log.jsonl          per-frame reason codes and measured distances
  summary.json           counts, pacing lag and cleanup result

Every line is flushed as written, so a publisher can follow a live run.
Session generation is claimed from SESSION_STATE before anything is written.

Environment: CARLA_HOST (host.docker.internal), CARLA_PORT (2000),
DURATION_SECONDS (30), OUT_DIR (/out), SPAWN_POINTS ("1,2,3"),
EXPECT_MAP (Town10HD_Opt), DRIVE (0 = parked, 1 = autopilot), SEED (7),
SESSION_STATE (/state/session-state.json).
"""

import json
import os
import queue
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import carla

from carla_observation import to_json_line
from line_sink import LineSink
from run_manifest import VEHICLE_IDS, build_manifest
from session_state import claim_session
from vehicle_stream import VehicleStream, pace_delay

FIXED_DELTA_SECONDS = 0.1
SENSOR_Z_METERS = 1.5
LIDAR_ATTRIBUTES = {
    "channels": "32",
    "range": "50",
    "points_per_second": "100000",
    "rotation_frequency": "10",
    "upper_fov": "10",
    "lower_fov": "-30",
    "sensor_tick": "0.0",
}
SENSOR_TIMEOUT_SECONDS = 2.0
WARMUP_TICKS = 10


def env(name, default):
    return os.environ.get(name, default)


def spawn_vehicle(world, blueprints, spawn_point, vehicle_id):
    blueprint = blueprints.find("vehicle.tesla.model3")
    blueprint.set_attribute("role_name", vehicle_id)
    actor = world.try_spawn_actor(blueprint, spawn_point)
    if actor is None:
        raise RuntimeError(f"spawn point blocked for {vehicle_id}")
    return actor


def attach_lidar(world, blueprints, vehicle):
    blueprint = blueprints.find("sensor.lidar.ray_cast")
    for key, value in LIDAR_ATTRIBUTES.items():
        blueprint.set_attribute(key, value)
    box = vehicle.bounding_box
    mount = carla.Transform(carla.Location(x=box.location.x + box.extent.x, z=SENSOR_Z_METERS))
    sensor = world.spawn_actor(blueprint, mount, attach_to=vehicle)
    frames = queue.Queue()
    sensor.listen(frames.put)
    return sensor, frames, {"x": round(mount.location.x, 3), "y": 0.0, "z": SENSOR_Z_METERS,
                            "pitch": 0.0, "yaw": 0.0, "roll": 0.0}


def frame_for(frames, wanted):
    """Return the sensor data for world frame `wanted`, discarding older data."""
    deadline = time.monotonic() + SENSOR_TIMEOUT_SECONDS
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        try:
            data = frames.get(timeout=remaining)
        except queue.Empty:
            return None
        if data.frame >= wanted:
            return data


def main():
    out = Path(env("OUT_DIR", "/out"))
    out.mkdir(parents=True, exist_ok=True)
    duration = float(env("DURATION_SECONDS", "30"))
    spawn_indices = [int(i) for i in env("SPAWN_POINTS", "1,2,3").split(",")]
    expect_map = env("EXPECT_MAP", "Town10HD_Opt")
    drive = env("DRIVE", "0") == "1"
    seed = int(env("SEED", "7"))
    random.seed(seed)

    client = carla.Client(env("CARLA_HOST", "host.docker.internal"), int(env("CARLA_PORT", "2000")))
    client.set_timeout(30.0)
    world = client.get_world()
    map_name = world.get_map().name
    if not map_name.endswith(expect_map):
        raise SystemExit(f"loaded map {map_name} is not {expect_map}; load it in CARLA first")

    original = world.get_settings()
    owned, sensors, summary = [], [], {"cleanup": None}
    traffic = None
    try:
        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = FIXED_DELTA_SECONDS
        world.apply_settings(settings)
        if drive:
            traffic = client.get_trafficmanager()
            traffic.set_synchronous_mode(True)
            traffic.set_random_device_seed(seed)

        blueprints = world.get_blueprint_library()
        spawn_points = world.get_map().get_spawn_points()
        vehicles = []
        for vehicle_id, index in zip(VEHICLE_IDS, spawn_indices):
            actor = spawn_vehicle(world, blueprints, spawn_points[index], vehicle_id)
            owned.append(actor)
            sensor, frames, mount = attach_lidar(world, blueprints, actor)
            sensors.append(sensor)
            vehicles.append((vehicle_id, actor, sensor, frames))
            if drive:
                actor.set_autopilot(True, traffic.get_port())

        for _ in range(WARMUP_TICKS):
            world.tick()
        # Bracket the anchor: the simulation origin and the UTC reading are taken
        # within this window, which is recorded as the anchor uncertainty.
        before = time.monotonic()
        simulation_origin = world.get_snapshot().timestamp.elapsed_seconds
        utc_origin = datetime.now(timezone.utc)
        wall_origin = time.monotonic()
        uncertainty = round(wall_origin - before, 6)
        session_id = f"carla-{utc_origin:%Y%m%dT%H%M%S%fZ}"
        generation = claim_session(env("SESSION_STATE", "/state/session-state.json"),
                                   session_id=session_id, utc_origin=utc_origin)

        manifest = build_manifest(
            session_id=session_id, generation=generation,
            utc_origin=utc_origin, simulation_origin=simulation_origin,
            clock_uncertainty_seconds=uncertainty,
            actors=[(vid, actor.id, sensor.id) for vid, actor, sensor, _ in vehicles],
            run={
                "map": map_name,
                "carlaServerVersion": client.get_server_version(),
                "carlaClientVersion": client.get_client_version(),
                "fixedDeltaSeconds": FIXED_DELTA_SECONDS,
                "synchronousMode": True,
                "drive": drive,
                "seed": seed,
                "spawnPointIndices": spawn_indices,
                "sensor": {"type": "sensor.lidar.ray_cast", "attributes": LIDAR_ATTRIBUTES,
                           "transformRelativeToActor": mount},
                "region": {"x": [0, 50], "absY": 1.5, "z": [-1.0, 1.0]},
            })
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

        streams = {vid: VehicleStream(manifest, vid) for vid, _, _, _ in vehicles}
        files = {vid: LineSink(out / f"{vid}.jsonl") for vid, _, _, _ in vehicles}
        log = LineSink(out / "run-log.jsonl")
        counts = {vid: {"observations": 0, "missing": 0, "stale": 0} for vid in streams}
        max_lag = 0.0
        try:
            elapsed_simulation = 0.0
            while True:
                # Wait until the wall clock reaches the next frame's simulation time,
                # so each source timestamp is at or before its processing time.
                next_simulation = elapsed_simulation + FIXED_DELTA_SECONDS
                time.sleep(pace_delay(next_simulation, time.monotonic() - wall_origin))
                wanted = world.tick()
                elapsed_simulation = world.get_snapshot().timestamp.elapsed_seconds - simulation_origin
                if elapsed_simulation > duration:
                    break
                for vid, actor, _, frames in vehicles:
                    data = frame_for(frames, wanted)
                    if data is None:
                        entry = streams[vid].on_missing(wanted, round(elapsed_simulation + simulation_origin, 3))
                        counts[vid]["missing"] += 1
                    else:
                        v = actor.get_velocity()
                        observation, entry = streams[vid].on_frame(
                            data.frame, data.timestamp, bytes(data.raw_data),
                            {"x": v.x, "y": v.y, "z": v.z}, datetime.now(timezone.utc))
                        if observation is None:
                            counts[vid]["stale"] += 1
                        else:
                            files[vid].write(to_json_line(observation))
                            counts[vid]["observations"] += 1
                    log.write(json.dumps(entry) + "\n")
                max_lag = max(max_lag, time.monotonic() - wall_origin - elapsed_simulation)
        finally:
            for handle in list(files.values()) + [log]:
                handle.close()
        summary.update({"sessionId": manifest["sessionId"], "sessionGeneration": generation,
                        "counts": counts,
                        "maxWallLagSeconds": round(max_lag, 3)})
    finally:
        for sensor in sensors:
            sensor.stop()
        destroyed = client.apply_batch_sync(
            [carla.command.DestroyActor(a.id) for a in sensors + owned], True)
        summary["cleanup"] = {"owned": len(sensors) + len(owned),
                              "errors": [r.error for r in destroyed if r.error]}
        if traffic is not None:
            traffic.set_synchronous_mode(False)
        world.apply_settings(original)
        (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary))


if __name__ == "__main__":
    main()
