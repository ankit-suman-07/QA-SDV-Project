"""Publish contract v1 health events with QoS 1 and retain=false (C3).

The pinned velocitas-sdk 0.15.7 exposes only publish_event(topic, data),
which calls paho without a QoS argument and therefore sends QoS 0. The
merged ingress rejects anything that is not QoS 1, so v1 events go through
paho directly on the SDK's own publisher connection.
"""

import asyncio
import logging

from v1_event import ObservationGate, serialize

logger = logging.getLogger(__name__)

V1_QOS = 1
ACK_TIMEOUT_SECONDS = 2.0


def pub_client_of(pubsub_client):
    """The paho client behind the SDK's MQTT pub/sub client."""
    client = getattr(pubsub_client, "_pub_client", None)
    if client is None:
        raise RuntimeError(
            "v1 publishing needs the paho publisher of velocitas-sdk 0.15.7 "
            "(MqttClient._pub_client); check the SDK version"
        )
    return client


async def publish_v1_event(
    client,
    topic: str,
    payload: str,
    ack_timeout: float = ACK_TIMEOUT_SECONDS,
) -> bool:
    """True only when the broker acknowledged the message (PUBACK)."""
    try:
        info = client.publish(topic, payload, qos=V1_QOS, retain=False)
        if info.rc != 0:
            logger.warning("v1: publish not queued (rc=%s)", info.rc)
            return False
        # Blocks until PUBACK or timeout; keep it off the event loop.
        await asyncio.to_thread(info.wait_for_publish, ack_timeout)
        return info.is_published()
    except Exception:
        logger.warning("v1: publish failed", exc_info=True)
        return False


async def deliver(
    gate: ObservationGate,
    event: dict,
    client,
    topic: str,
    ack_timeout: float = ACK_TIMEOUT_SECONDS,
) -> bool:
    """Publish a pending event; only an acknowledged one leaves the gate.

    A failure keeps the event pending, so the next poll retries it with the
    same eventId and sourceTimestamp. Ingress ignores a repeated latest ID.
    """
    if not await publish_v1_event(client, topic, serialize(event), ack_timeout):
        return False
    gate.mark_published(event)
    return True
