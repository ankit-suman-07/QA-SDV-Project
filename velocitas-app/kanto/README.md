# Eclipse Kanto deployment

This directory contains the Eclipse Kanto deployment configuration for the
Velocitas `AutonomousHealthApp`.

## Deployment contents

- `autonomous-health-app.json` defines the Kanto container configuration.
- `deploy.sh` builds, publishes, creates, and starts the vehicle application
  using `kanto-cm`.
- `../app/tests/test_kanto_deployment.py` verifies that the descriptor remains
  consistent with the Velocitas application manifest and runtime endpoints.

## Runtime architecture

The application expects the following services on the Kanto host network:

- KUKSA Data Broker: `127.0.0.1:55555`
- MQTT broker: `127.0.0.1:1883`
- Local container registry: `127.0.0.1:12345`

The application reads vehicle and autonomous sensor signals from KUKSA,
classifies the autonomous health state, and publishes status events to:

```text
sdv/autonomy/status
```

## V1 vehicle-002 pilot preparation

The vehicle-001 descriptor and `deploy.sh` above remain the legacy workflow.
For non-deploying vehicle-002 rendering, dry-run checks, dependencies and pending
Linux/MQTT/Ditto evidence, see [V1-PILOT.md](V1-PILOT.md).
