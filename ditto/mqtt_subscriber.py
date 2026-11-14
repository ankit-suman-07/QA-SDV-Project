"""MQTT 3.1.1 transport for B1. Instantiate with B2's TwinWriter adapter."""
from dataclasses import dataclass, field
import logging
import math
import os
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread

from ditto.mqtt_ingress import EventError, VEHICLES, decode_event

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class MqttConfig:
    host: str = 'localhost'
    port: int = 1883
    client_id: str = 'sdv-v1-twin-ingress'
    username: str | None = None
    password: str | None = field(default=None, repr=False)
    tls_ca: str | None = None
    keepalive: int = 60
    queue_size: int = 100
    retry_seconds: float = 1.0

    def __post_init__(self):
        if not self.host.strip() or not self.client_id.strip():
            raise ValueError('MQTT host and stable client ID are required')
        if not 1 <= self.port <= 65535 or self.keepalive <= 0 or self.queue_size <= 0:
            raise ValueError('invalid MQTT port, keepalive or queue size')
        if not math.isfinite(self.retry_seconds) or self.retry_seconds <= 0:
            raise ValueError('retry seconds must be finite and positive')
        if self.password is not None and self.username is None:
            raise ValueError('MQTT password requires username')

    @classmethod
    def from_env(cls, environ=None):
        env = os.environ if environ is None else environ
        return cls(host=env.get('SDV_MQTT_HOST', 'localhost'),
                   port=int(env.get('SDV_MQTT_PORT', '1883')),
                   client_id=env.get('SDV_MQTT_CLIENT_ID', 'sdv-v1-twin-ingress'),
                   username=env.get('SDV_MQTT_USERNAME'), password=env.get('SDV_MQTT_PASSWORD'),
                   tls_ca=env.get('SDV_MQTT_TLS_CA'),
                   keepalive=int(env.get('SDV_MQTT_KEEPALIVE', '60')),
                   queue_size=int(env.get('SDV_MQTT_QUEUE_SIZE', '100')),
                   retry_seconds=float(env.get('SDV_MQTT_RETRY_SECONDS', '1')))


def create_client(config):
    # Lazy import keeps domain tests and existing legacy paths dependency-free.
    import paho.mqtt.client as mqtt
    return mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                       client_id=config.client_id, clean_session=False,
                       protocol=mqtt.MQTTv311, manual_ack=True)


class Subscriber:
    """Bounded per-vehicle workers and explicit persistence-gated MQTT ACKs.

    Reconnects use the same persistent broker session and always resubscribe.
    A failing downstream is retried at retry_seconds without ACK or watermark
    advancement. Another vehicle continues independently. Queue overflow is a
    visible fatal stop, leaving work unacknowledged for broker replay on restart.
    Never run two subscribers/writers for the same pair of individual twins.
    """
    def __init__(self, ingress, config=None, *, client=None):
        self.ingress = ingress
        self.config = config or MqttConfig.from_env()
        self.client = client if client is not None else create_client(self.config)
        self._stopping = Event()
        self._session_lock = Lock()
        self._generation = 0
        self._connected = False
        self._fatal = None
        self._queues = {vehicle: Queue(self.config.queue_size) for vehicle in VEHICLES}
        self.client.manual_ack_set(True)
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        if self.config.username is not None:
            self.client.username_pw_set(self.config.username, self.config.password)
        if self.config.tls_ca:
            self.client.tls_set(ca_certs=self.config.tls_ca)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_subscribe = self.on_subscribe
        self.client.on_message = self.on_message
        self._threads = [Thread(target=self._worker, args=(queue,), daemon=True,
                                name=f'ingress-{vehicle}')
                         for vehicle, queue in self._queues.items()]
        for thread in self._threads:
            thread.start()

    def _fail(self, code):
        LOG.error('mqtt_failure code=%s', code)
        self._fatal = code
        self._stopping.set()
        with self._session_lock:
            self._connected = False
            self._generation += 1
        self.client.disconnect()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if self._stopping.is_set():
            client.disconnect()
            return
        with self._session_lock:
            self._generation += 1
            self._connected = reason_code == 0
        if reason_code != 0:
            LOG.warning('mqtt_connection_rejected')
            return
        result, _mid = client.subscribe('sdv/+/health', qos=1)
        if result != 0:
            self._fail('SUBSCRIBE_FAILED')

    def on_subscribe(self, client, userdata, mid, reason_codes, properties):
        if not reason_codes or any(code != 1 for code in reason_codes):
            self._fail('SUBSCRIBE_QOS_REJECTED')

    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        with self._session_lock:
            self._connected = False
            self._generation += 1
        if not self._stopping.is_set():
            LOG.warning('mqtt_disconnected reconnect_pending=true')

    def _ack(self, mid, qos, generation):
        failed = False
        with self._session_lock:
            if self._connected and generation == self._generation and qos == 1:
                failed = self.client.ack(mid, qos) != 0
        if failed:
            self._fail('ACK_FAILED')

    def on_message(self, client, userdata, message):
        if self._stopping.is_set():
            return
        with self._session_lock:
            generation = self._generation
        try:
            if message.retain or message.qos != 1:
                raise EventError('INVALID_MQTT_DELIVERY')
            event = decode_event(message.topic, message.payload)
        except EventError as error:
            LOG.warning('event_rejected code=%s topic=%r vehicle=%r event=%r',
                        error.code, message.topic, error.vehicle_id, error.event_id)
            self._ack(message.mid, message.qos, generation)
            return
        # Enqueue only validated, size-limited input; never block the network loop.
        try:
            self._queues[event['vehicleId']].put_nowait(
                (message.topic, bytes(message.payload), message.mid, message.qos, generation, event))
        except Full:
            self._fail('QUEUE_FULL')

    def _worker(self, queue):
        while not self._stopping.is_set():
            try:
                topic, payload, mid, qos, generation, event = queue.get(timeout=0.1)
            except Empty:
                continue
            try:
                while not self._stopping.is_set():
                    try:
                        self.ingress.process(topic, payload)
                    except EventError as error:
                        LOG.warning('event_rejected code=%s topic=%r vehicle=%r event=%r',
                                    error.code, topic, event['vehicleId'], event['eventId'])
                    except Exception as error:
                        # Do not log dependency exception text: URLs may contain credentials.
                        LOG.error('persistence_pending code=%s topic=%r vehicle=%r event=%r',
                                  getattr(error, 'code', type(error).__name__),
                                  topic, event['vehicleId'], event['eventId'])
                        self._stopping.wait(self.config.retry_seconds)
                        continue
                    else:
                        LOG.info('event_persisted topic=%r vehicle=%r event=%r',
                                 topic, event['vehicleId'], event['eventId'])
                    self._ack(mid, qos, generation)
                    break
            finally:
                queue.task_done()

    def wait_idle(self):
        """Wait for queued writes while running; can block during downstream outage."""
        for queue in self._queues.values():
            queue.join()

    def run(self):
        try:
            self.client.connect_async(self.config.host, self.config.port, self.config.keepalive)
            self.client.loop_forever(retry_first_connection=True)
            if self._fatal:
                raise RuntimeError(self._fatal)
        finally:
            self.stop()

    def stop(self):
        self._stopping.set()
        with self._session_lock:
            self._connected = False
            self._generation += 1
        self.client.disconnect()
        for thread in self._threads:
            thread.join(timeout=2)
            if thread.is_alive():
                LOG.error('writer_shutdown_pending worker=%s', thread.name)
