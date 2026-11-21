"""Per-vehicle CARLA observation publisher. Run with --help for configuration."""

import argparse
import fcntl
import json
import os
import signal
import sqlite3
import sys
import time
from contextlib import ExitStack, closing
from datetime import datetime, timezone
from pathlib import Path

from scripts.v1_dev.contract import ContractError, parse_timestamp
from scripts.v2_dev.contract import VEHICLES
from scripts.v2_dev.observation_mapping import DISTANCE, SPEED, VALIDITY, prepare_observation

ATTEMPTS = 3
TIMEOUT = 2.0


class DeliveryError(RuntimeError):
    """Delivery could not be confirmed."""


def retry(send, *, pause=time.sleep):
    for attempt in range(ATTEMPTS):
        try:
            send()
            return
        except DeliveryError:
            if attempt == ATTEMPTS - 1:
                raise
            pause(0.25 * 2**attempt)


class Publisher:
    """One vehicle, one durable pending observation, one ordered writer."""

    def __init__(self, db, vehicle, manifest, kuksa, mqtt, *, clock, pause=time.sleep):
        self.db, self.vehicle, self.manifest = db, vehicle, manifest
        self.kuksa, self.mqtt, self.clock, self.pause = kuksa, mqtt, clock, pause
        db.execute("""CREATE TABLE IF NOT EXISTS publication (
            vehicle TEXT PRIMARY KEY, completed TEXT, pending TEXT,
            kuksa_confirmed INTEGER NOT NULL DEFAULT 0
        )""")
        db.execute("CREATE TABLE IF NOT EXISTS event_ids (event_id TEXT PRIMARY KEY)")
        with db:
            row = db.execute("SELECT vehicle FROM publication").fetchone()
            if row and row[0] != vehicle:
                raise ValueError("state database belongs to another vehicle")
            db.execute("INSERT OR IGNORE INTO publication(vehicle) VALUES (?)", (vehicle,))

    def state(self):
        return self.db.execute(
            "SELECT completed, pending, kuksa_confirmed FROM publication WHERE vehicle = ?",
            (self.vehicle,),
        ).fetchone()

    def prepare(self, wire, previous):
        return prepare_observation(
            wire, vehicle_id=self.vehicle, manifest=self.manifest, now=self.clock(),
            previous=json.loads(previous) if previous else None,
        )

    def resume(self):
        previous, pending, confirmed = self.state()
        if pending is None:
            return
        envelope, values = self.prepare(pending, previous)
        if not confirmed:
            source = parse_timestamp(envelope["sourceTimestamp"])
            retry(lambda: self.kuksa.write(values, source), pause=self.pause)
            with self.db:
                self.db.execute("UPDATE publication SET kuksa_confirmed = 1")
        topic = f"sdv/{self.vehicle}/v2/observations"
        retry(lambda: self.mqtt.publish(topic, pending), pause=self.pause)
        with self.db:
            self.db.execute(
                "UPDATE publication SET completed = pending, pending = NULL, kuksa_confirmed = 0"
            )

    def accept(self, wire):
        previous, pending, _ = self.state()
        prepared = self.prepare(wire, previous)
        if pending is not None:
            if prepared is None or prepared[0] != json.loads(pending):
                raise DeliveryError("an older pending observation must finish first")
            self.resume()
            return "published"
        if prepared is None:
            return "duplicate"
        envelope, _ = prepared
        if isinstance(wire, bytes):
            wire = wire.decode("utf-8")
        with self.db:
            try:
                self.db.execute("INSERT INTO event_ids VALUES (?)", (envelope["eventId"],))
            except sqlite3.IntegrityError as error:
                raise ContractError("EVENT_ID_CONFLICT", "observation ID already used") from error
            self.db.execute("UPDATE publication SET pending = ?", (wire,))
        self.resume()
        return "published"


class Kuksa:
    def __init__(self, client):
        self.client = client

    def close(self):
        self.client.disconnect()

    def write(self, values, source):
        from grpc import RpcError
        from kuksa_client.grpc import DataEntry, DataType, Datapoint, EntryUpdate, Field, VSSClientError

        try:
            if not self.client.connected:
                self.client.connect()
            metadata = self.client.get_metadata(values, timeout=TIMEOUT)
            expected = {
                DISTANCE: (DataType.FLOAT, "m"),
                VALIDITY: (DataType.BOOLEAN, None),
                SPEED: (DataType.FLOAT, "km/h"),
            }
            for path in values:
                entry = metadata.get(path)
                data_type, unit = expected[path]
                if entry is None or entry.data_type != data_type or (unit and entry.unit != unit):
                    raise DeliveryError(f"KUKSA metadata mismatch for {path}")
            # Explicit VAL v1 checks response.error and response.errors and keeps
            # the deadline. Explicit metadata on EntryUpdate would request a
            # metadata change, so pass only a timestamped VALUE.
            self.client.set(
                [EntryUpdate(DataEntry(path, value=Datapoint(value, timestamp=source)), (Field.VALUE,))
                 for path, value in values.items()],
                try_v2=False, timeout=TIMEOUT,
            )
        except (VSSClientError, RpcError, DeliveryError) as error:
            self.close()
            raise DeliveryError("KUKSA did not confirm all required signal writes") from error


class Mqtt:
    def __init__(self, create_client, host, port):
        self.create_client, self.host, self.port = create_client, host, port
        self.client = None
        self.accepted = None

    def close(self):
        if self.client is not None:
            self.client.disconnect()
            self.client = None
        self.accepted = None

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        self.accepted = reason_code == 0

    def _on_publish(self, client, userdata, mid, reason_code, properties):
        self.ack = (mid, not reason_code.is_failure)

    def _wait(self, predicate):
        deadline = time.monotonic() + TIMEOUT
        while not predicate():
            remaining = deadline - time.monotonic()
            if remaining <= 0 or self.client.loop(timeout=min(remaining, 0.1)) != 0:
                raise DeliveryError("MQTT acknowledgement missing or connection lost")

    def publish(self, topic, wire):
        try:
            if self.client is None:
                self.client = self.create_client()
                self.client.on_connect = self._on_connect
                self.client.on_publish = self._on_publish
                if self.client.connect(self.host, self.port, keepalive=30, clean_start=True) != 0:
                    raise DeliveryError("MQTT CONNECT failed")
                self._wait(lambda: self.accepted is not None)
                if not self.accepted:
                    raise DeliveryError("MQTT CONNACK rejected")
            self.ack = None
            result = self.client.publish(topic, wire, qos=1, retain=False)
            if result.rc != 0:
                raise DeliveryError("MQTT publish was not queued")
            self._wait(lambda: self.ack is not None)
            if self.ack != (result.mid, True):
                raise DeliveryError("MQTT PUBACK rejected or mismatched")
        except (DeliveryError, OSError, RuntimeError) as error:
            self.close()
            raise DeliveryError("MQTT did not confirm companion publication") from error


def broker_for(manifest, vehicle):
    endpoints = {row["vehicleId"]: (row["broker"], row["brokerPort"]) for row in manifest["vehicles"]}
    if (len(manifest["vehicles"]) != len(VEHICLES) or set(endpoints) != set(VEHICLES)
            or len(set(endpoints.values())) != len(VEHICLES)):
        raise ValueError("manifest requires three registered vehicles and distinct KUKSA endpoints")
    return endpoints[vehicle]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vehicle", choices=VEHICLES, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--mqtt-host", default="127.0.0.1")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--mqtt-ca", type=Path)
    parser.add_argument("--mqtt-user")
    parser.add_argument("--kuksa-ca", type=Path)
    args = parser.parse_args(argv)

    import paho.mqtt.client as mqtt
    from kuksa_client.grpc import VSSClient

    manifest = json.loads(args.manifest.read_text())
    host, port = broker_for(manifest, args.vehicle)
    if host not in ("127.0.0.1", "localhost") and not args.kuksa_ca:
        parser.error("--kuksa-ca required for non-loopback KUKSA")
    if args.mqtt_host not in ("127.0.0.1", "localhost") and not args.mqtt_ca:
        parser.error("--mqtt-ca required for non-loopback MQTT")
    if os.environ.get("SDV_KUKSA_TOKEN") and not args.kuksa_ca:
        parser.error("--kuksa-ca required with KUKSA credentials")
    if args.mqtt_user and not args.mqtt_ca:
        parser.error("--mqtt-ca required with MQTT credentials")

    def mqtt_client():
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sdv-observation-{args.vehicle}",
                             protocol=mqtt.MQTTv5)
        client.connect_timeout = TIMEOUT
        if args.mqtt_ca:
            client.tls_set(str(args.mqtt_ca))
        if args.mqtt_user:
            client.username_pw_set(args.mqtt_user, os.environ.get("SDV_MQTT_PASSWORD"))
        return client

    def stop(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    try:
        args.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        with ExitStack() as stack:
            lock = stack.enter_context((args.state_dir / f"{args.vehicle}.lock").open("a"))
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            db = stack.enter_context(closing(sqlite3.connect(args.state_dir / f"{args.vehicle}.sqlite3")))
            kuksa = Kuksa(VSSClient(host, port, token=os.environ.get("SDV_KUKSA_TOKEN"),
                                    root_certificates=args.kuksa_ca, ensure_startup_connection=False))
            companion = Mqtt(mqtt_client, args.mqtt_host, args.mqtt_port)
            stack.callback(kuksa.close)
            stack.callback(companion.close)
            publisher = Publisher(db, args.vehicle, manifest, kuksa, companion,
                                  clock=lambda: datetime.now(timezone.utc))
            publisher.resume()
            while wire := sys.stdin.buffer.readline(65537):
                try:
                    publisher.accept(wire)
                except ContractError as error:
                    # Oversize records can spill into subsequent bounded reads.
                    if len(wire) > 65536:
                        raise DeliveryError("oversize input line") from error
                    print(f"rejected observation: {error.code}", file=sys.stderr)
    except (DeliveryError, ContractError, OSError, sqlite3.Error) as error:
        print(f"publisher stopped: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
