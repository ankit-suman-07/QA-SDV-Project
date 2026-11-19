"""THROWAWAY review probe for V2-C3. Mount: front centre, z=1.5 m above road.
For every spawn point: one car, one semantic LiDAR (review only), one full
10 Hz scan. Apply the contract region and report which object class gives the
nearest in-region point. Road/sidewalk/roadline/ground hits are false obstacles.
"""
import collections
import os

import carla

HOST = os.getenv("CARLA_HOST", "host.docker.internal")
MAP = os.getenv("MAP", "")
SURFACE = {1: "Roads", 2: "Sidewalks", 14: "Ground", 24: "RoadLine", 25: "Terrain"}


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
    false_hits = []
    spawns = world.get_map().get_spawn_points()
    try:
        for i, sp in enumerate(spawns):
            car = world.try_spawn_actor(car_bp, sp)
            if not car:
                continue
            ext = car.bounding_box.extent
            got = []
            lidar = world.spawn_actor(bp, carla.Transform(carla.Location(x=ext.x, z=1.5)), attach_to=car)
            lidar.listen(got.append)
            for _ in range(5):
                world.tick()
            lidar.stop()
            data = got[-1] if got else None
            best = None
            if data is not None:
                for d in data:
                    x, y, z = d.point.x, d.point.y, d.point.z
                    if 0 < x <= 50 and abs(y) <= 1.5 and float(os.getenv("ZMIN","-1.0")) <= z <= 1.0:
                        if best is None or x < best[0]:
                            best = (x, d.object_tag, z)
            if best is None:
                tally["NO_FRONT_HIT"] += 1
            else:
                tag = SURFACE.get(best[1])
                tally[tag or "object"] += 1
                if tag:
                    pitch = sp.rotation.pitch
                    false_hits.append((i, tag, round(best[0], 1), round(best[2], 2), round(pitch, 1)))
            lidar.destroy()
            car.destroy()
            world.tick()
        print("map:", world.get_map().name, "spawn points:", len(spawns))
        print("nearest in-region hit by class:", dict(tally))
        print("false obstacles (spawn, class, x m, z m, spawn pitch):")
        for f in sorted(false_hits, key=lambda f: f[2]):
            print("  ", f)
    finally:
        world.apply_settings(original)


if __name__ == "__main__":
    main()
