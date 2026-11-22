#!/usr/bin/env bash
set -euo pipefail
scratch=$(mktemp -d)
prefix="sdv56-probe-$$"
cleanup() {
    docker stop -t 2 "$prefix-kuksa" "$prefix-mqtt" >/dev/null 2>&1 || true
}
trap cleanup EXIT
printf 'listener 1883\nallow_anonymous true\npersistence false\n' > "$scratch/mosquitto.conf"
docker run --rm --pull never -d --name "$prefix-kuksa" -p 127.0.0.1::55555 \
    -v "$PWD/vehicle-simulator/config/vss-with-autonomous-sensors.json:/config/vss.json:ro" \
    ghcr.io/eclipse-kuksa/kuksa-databroker:0.7.0 --insecure --vss /config/vss.json >/dev/null
docker run --rm --pull never -d --name "$prefix-mqtt" -p 127.0.0.1::1883 \
    -v "$scratch/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro" eclipse-mosquitto:2 >/dev/null
kuksa_port=$(docker port "$prefix-kuksa" 55555/tcp)
mqtt_port=$(docker port "$prefix-mqtt" 1883/tcp)
"$HOME/.local/share/qa-sdv-v1/runtime/venv-3.12/bin/python" - "$scratch" "${kuksa_port##*:}" "${mqtt_port##*:}" <<'PY'
import json
import subprocess
import sys
import threading
from pathlib import Path

from kuksa_client.grpc import VSSClient
from paho.mqtt import client as mqtt
from scripts.v1_dev.contract import parse_timestamp
from scripts.v2_dev.observation_mapping import DISTANCE, SPEED, VALIDITY

root, kuksa_port, mqtt_port = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
fixtures = Path("tests/fixtures/v2/observations")
manifest = json.loads((fixtures / "session-manifest.json").read_text())
for index, vehicle in enumerate(manifest["vehicles"], start=1):
    vehicle.update(broker="127.0.0.1", brokerPort=kuksa_port if index == 1 else kuksa_port + index)
config = root / "manifest.json"
config.write_text(json.dumps(manifest))
observation = json.loads((fixtures / "vehicle-001-motion.json").read_text())
wire = json.dumps(observation)

ready = threading.Event()
received = threading.Event()
messages = []
topic = "sdv/vehicle-001/v2/observations"
subscriber = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
subscriber.connect_timeout = 2
subscriber.on_connect = lambda c, u, f, r, p: c.subscribe(topic, qos=1)
subscriber.on_subscribe = lambda *args: ready.set()

def receive(client, userdata, message):
    messages.append((message.topic, message.payload.decode(), message.qos, message.retain))
    received.set()

subscriber.on_message = receive
subscriber.connect("127.0.0.1", mqtt_port)
subscriber.loop_start()
try:
    assert ready.wait(4), "no MQTT SUBACK"
    command = [sys.executable, "-m", "scripts.v2_dev.observation_publisher",
               "--vehicle", "vehicle-001", "--manifest", str(config),
               "--state-dir", str(root / "state"), "--mqtt-port", str(mqtt_port)]
    subprocess.run(command, input=wire + "\n", text=True, check=True, timeout=30)
    assert received.wait(4), "no companion"
    assert messages == [(topic, wire + "\n", 1, False)], messages
    # Check the persistent journal prevents a duplicate across process restart.
    received.clear()
    subprocess.run(command, input=wire + "\n", text=True, check=True, timeout=10)
    assert not received.wait(0.4), "completed retry published again"
    with VSSClient("127.0.0.1", kuksa_port, ensure_startup_connection=False) as client:
        values = client.get_current_values([DISTANCE, VALIDITY, SPEED], timeout=2)
    assert {k: v.value for k, v in values.items()} == {DISTANCE: 20.0, VALIDITY: True, SPEED: 18.0}
    source = parse_timestamp(observation["sourceTimestamp"])
    print("Isolated component probe: unchanged companion, QoS 1, retain false, VSS values and restart duplicate suppression passed")
    print("KUKSA readback source timestamp preserved:", {k: v.timestamp == source for k, v in values.items()})
    print("Companion source timestamp:", observation["sourceTimestamp"])
    print("KUKSA readback timestamps:", {k: str(v.timestamp) for k, v in values.items()})
finally:
    subscriber.disconnect()
    subscriber.loop_stop()
PY
