# Pipeline integration CI

## Goal
Automatically verify the synthetic SDV pipeline:
Simulator → KUKSA → Velocitas → MQTT.

## Planned checks
- Build and start the Docker Compose services.
- Wait for service readiness with bounded timeouts.
- Verify healthy telemetry.
- Inject LiDAR obstruction and observe EMERGENCY_BRAKING.
- Clear the obstruction and observe HEALTHY recovery.
- Collect service logs on failure.
- Stop and clean up the CI environment after every run.

## Boundaries
CARLA, Kanto deployment and image publishing are separate work.