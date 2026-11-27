"""THROWAWAY review probe for V2-C3, revision 2 (2026-11-25).

Same geometry and sensor as c3_region_probe.py (kept unchanged as the
original evidence), but every spawn point gets exactly one outcome:

  SPAWN_FAILED   the car could not be spawned; no scan was attempted
  MISSING_SCAN   no LiDAR callback for the final tick within the timeout
  EMPTY_SCAN     a callback arrived with zero points
  NO_FRONT_HIT   a valid scan with no point inside the region
  OBJECT         nearest in-region point is a non-surface object
  FALSE_SURFACE  nearest in-region point is road/sidewalk/roadline/ground/terrain

Only the last four are valid scans. MISSING_SCAN is never counted as clear.
Prints one JSON line per spawn point and a final JSON summary.
"""
import collections
import json
import os
import queue
import time

import carla

HOST = os.getenv("CARLA_HOST", "host.docker.internal")
MAP = os.getenv("MAP", "")
ZMIN = float(os.getenv("ZMIN", "-1.0"))
TICKS = 5
TIMEOUT = 2.0
SURFACE = {1: "Roads", 2: "Sidewalks", 14: "Ground", 24: "RoadLine", 25: "Terrain"}


def scan_for(frames, wanted):
    deadline = time.monotonic() + TIMEOUT
    while (left := deadline - time.monotonic()) > 0:
        try:
            data = frames.get(timeout=left)
        except queue.Empty:
            return None
        if data.frame >= wanted:
            return data
    return None


def main():
    client = carla.Client(HOST, 2000)
    client.set_timeout(400.0)
    world = client.load_world(MAP) if MAP else client.get_world()
    original = world.get_settings()
    s = world.get_settings()
    s.synchronous_mode, s.fixed_delta_seconds = True, 0.1
    world.apply_settings(s)
    lib = world.get_blueprint_library()
    car_bp = lib.find("vehicle.tesla.model3")
    bp = lib.find("sensor.lidar.ray_cast_semantic")
    for k, v in dict(channels="32", range="50", points_per_second="320000",
                     rotation_frequency="10", upper_fov="10", lower_fov="-30").items():
        bp.set_attribute(k, v)

    tally = collections.Counter()
    spawns = world.get_map().get_spawn_points()
    try:
        for i, sp in enumerate(spawns):
            row = {"spawn": i, "pitch": round(sp.rotation.pitch, 1)}
            car = world.try_spawn_actor(car_bp, sp)
            if not car:
                row["outcome"] = "SPAWN_FAILED"
            else:
                frames = queue.Queue()
                mount = carla.Transform(carla.Location(x=car.bounding_box.extent.x, z=1.5))
                lidar = world.spawn_actor(bp, mount, attach_to=car)
                lidar.listen(frames.put)
                for _ in range(TICKS):
                    wanted = world.tick()
                data = scan_for(frames, wanted)
                lidar.stop()
                if data is None:
                    row["outcome"] = "MISSING_SCAN"
                elif len(data) == 0:
                    row["outcome"] = "EMPTY_SCAN"
                else:
                    best = None
                    for d in data:
                        x, y, z = d.point.x, d.point.y, d.point.z
                        if 0 < x <= 50 and abs(y) <= 1.5 and ZMIN <= z <= 1.0:
                            if best is None or x < best[0]:
                                best = (x, d.object_tag, z)
                    row["points"] = len(data)
                    if best is None:
                        row["outcome"] = "NO_FRONT_HIT"
                    else:
                        tag = SURFACE.get(best[1])
                        row.update(outcome="FALSE_SURFACE" if tag else "OBJECT",
                                   cls=tag or best[1], x=round(best[0], 1), z=round(best[2], 2))
                lidar.destroy()
                car.destroy()
                world.tick()
            tally[row["outcome"]] += 1
            print(json.dumps(row), flush=True)
        valid = sum(tally[k] for k in ("EMPTY_SCAN", "NO_FRONT_HIT", "OBJECT", "FALSE_SURFACE"))
        print(json.dumps({"map": world.get_map().name, "zmin": ZMIN,
                          "spawnPoints": len(spawns), "validScans": valid, **tally}))
    finally:
        world.apply_settings(original)


if __name__ == "__main__":
    main()
