"""Reconnect a kuksa_client VSSClient without leaking gRPC channels.

VSSClient.connect() registers a new channel in the client's exit stack and
never closes the previous one, so it must be preceded by disconnect().
"""

import logging

logger = logging.getLogger(__name__)


def reconnect(client) -> None:
    try:
        client.disconnect()
    except Exception:
        logger.debug("KUKSA disconnect before reconnect failed", exc_info=True)
    client.connect()
