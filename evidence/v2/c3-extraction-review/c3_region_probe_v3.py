"""THROWAWAY review probe for V2-C3, revision 3 (2026-11-25).

c3_region_probe.py (Nov 18) and c3_region_probe_v2.py (Nov 25) are kept
unchanged with their outputs. Changes from v2, after review of PR #67:

  - Only the scan for the requested (final tick) frame is used. Older scans are
    discarded; a later frame arriving first means the requested scan is missing
    (FRAME_MISMATCH), never a substitute for it.
  - EMPTY_SCAN is not a valid scan.
  - Every row records the requested frame and the frame actually received.

Outcomes per spawn point: SPAWN_FAILED, MISSING_SCAN, FRAME_MISMATCH,
EMPTY_SCAN, and the valid ones NO_FRONT_HIT, OBJECT, FALSE_SURFACE.
Only valid outcomes count in validScans. The frame and outcome logic is
CARLA-free and covered by tests/test_c3_region_probe_v3.py.
"""
import collections
import json
import os
import queue
import time

SURFACE = {1: "Roads", 2: "Sidewalks", 14: "Ground", 24: "RoadLine", 25: "Terrain"}
VALID = ("NO_FRONT_HIT", "OBJECT", "FALSE_SURFACE")
TICKS = 5
TIMEOUT = 2.0


def scan_for(get, wanted, timeout):
    """Return (scan, None) for frame `wanted`, or (None, first later frame or None)."""
    deadline = time.monotonic() + timeout
    while (left := deadline - time.monotonic()) > 0:
        try:
            data = get(timeout=left)
        except queue.Empty:
            return None, None
        if data.frame == wanted:
            return data, None
        if data.frame > wanted:
            return None, data.frame
    return None, None


def classify(points, zmin):
    """Outcome of one received scan; points have x, y, z and a semantic tag."""
    if len(points) == 0:
        return {"outcome": "EMPTY_SCAN", "points": 0}
    best = None
    for p in points:
        if 0 < p.x <= 50 and abs(p.y) <= 1.5 and zmin <= p.z <= 1.0:
            if best is None or p.x < best.x:
                best = p
    row = {"points": len(points)}
    if best is None:
        row["outcome"] = "NO_FRONT_HIT"
    else:
        tag = SURFACE.get(best.tag)
        row.update(outcome="FALSE_SURFACE" if tag else "OBJECT", cls=tag or best.tag,
                   x=round(best.x, 1), z=round(best.z, 2))
    return row


def summarize(rows):
    tally = collections.Counter(row["outcome"] for row in rows)
    return {"spawnPoints": len(rows), "validScans": sum(tally[k] for k in VALID), **tally}


def main():
    import carla

    Point = collections.namedtuple("Point", "x y z tag")
    client = carla.Client(os.getenv("CARLA_HOST", "host.docker.internal"), 2000)
    client.set_timeout(400.0)
    world = client.load_world(os.environ["MAP"]) if os.getenv("MAP") else client.get_world()
    zmin = float(os.getenv("ZMIN", "-1.0"))
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

    rows = []
    try:
        for i, sp in enumerate(world.get_map().get_spawn_points()):
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
                data, later = scan_for(frames.get, wanted, TIMEOUT)
                lidar.stop()
                row["requestedFrame"] = wanted
                if data is not None:
                    row["receivedFrame"] = data.frame
                    row.update(classify([Point(d.point.x, d.point.y, d.point.z, d.object_tag)
                                         for d in data], zmin))
                elif later is not None:
                    row.update(outcome="FRAME_MISMATCH", receivedFrame=later)
                else:
                    row.update(outcome="MISSING_SCAN", receivedFrame=None)
                lidar.destroy()
                car.destroy()
                world.tick()
            rows.append(row)
            print(json.dumps(row), flush=True)
        print(json.dumps({"map": world.get_map().name, "zmin": zmin, **summarize(rows)}))
    finally:
        world.apply_settings(original)


if __name__ == "__main__":
    main()
