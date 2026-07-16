import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GENERATED_PROTO_PATH = PROJECT_ROOT / "uprotocol" / "generated"

sys.path.insert(0, str(GENERATED_PROTO_PATH))

import common_pb2
import vehicle_status_pb2


def publish_vehicle_status(
        vehicle_id,
        speed_kph,
        battery_percent,
        temperature_celsius,
        tire_pressure_psi
):
    timestamp = datetime.now(timezone.utc).isoformat()

    metadata = common_pb2.EventMetadata(
        vehicle_id=vehicle_id,
        event_id=str(uuid.uuid4()),
        source_timestamp=timestamp,
        event_timestamp=timestamp
    )

    event = vehicle_status_pb2.VehicleStatusUpdated(
        metadata=metadata,
        speed_kph=speed_kph,
        battery_percent=battery_percent,
        temperature_celsius=temperature_celsius,
        tire_pressure_psi=vehicle_status_pb2.TirePressure(
            front_left=tire_pressure_psi,
            front_right=tire_pressure_psi,
            rear_left=tire_pressure_psi,
            rear_right=tire_pressure_psi
        )
    )

    serialized_event = event.SerializeToString()

    print(
        f"[uProtocol Publisher] eventId={metadata.event_id} "
        f"vehicleId={vehicle_id} bytes={len(serialized_event)}"
    )

    return serialized_event


def receive_vehicle_status(serialized_event):
    event = vehicle_status_pb2.VehicleStatusUpdated()
    event.ParseFromString(serialized_event)

    print(
        f"[uProtocol Receiver] eventId={event.metadata.event_id} "
        f"vehicleId={event.metadata.vehicle_id} "
        f"battery={event.battery_percent}"
    )

    return event