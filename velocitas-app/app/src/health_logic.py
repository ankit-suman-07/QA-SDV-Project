from datetime import datetime, timezone


def classify_autonomous_health(
    lidar_sensor_healthy,
    obstacle_warning,
    autonomous_braking,
):
    if not lidar_sensor_healthy:
        return "SENSOR_FAILURE"

    if autonomous_braking:
        return "EMERGENCY_BRAKING"

    if obstacle_warning:
        return "WARNING"

    return "HEALTHY"


def build_status_event(
    vehicle_id,
    speed,
    lidar_distance_m,
    lidar_sensor_healthy,
    obstacle_warning,
    autonomous_braking,
):
    return {
        "vehicleId": vehicle_id,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "healthStatus": classify_autonomous_health(
            lidar_sensor_healthy=lidar_sensor_healthy,
            obstacle_warning=obstacle_warning,
            autonomous_braking=autonomous_braking,
        ),
        "speed": speed,
        "lidarDistanceMeters": lidar_distance_m,
        "lidarSensorHealthy": lidar_sensor_healthy,
        "obstacleWarning": obstacle_warning,
        "autonomousBraking": autonomous_braking,
    }