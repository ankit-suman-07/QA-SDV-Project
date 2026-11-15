import os
from kuksa_client.grpc import VSSClient

def get_client():
    host = os.environ.get("DATABROKER_HOST", "127.0.0.1")
    port = int(os.environ.get("DATABROKER_PORT", 55555))
    # The provider bounds its actual RPCs; the default startup GetServerInfo
    # has no deadline in kuksa_client 0.5.1. Connecting itself is nonblocking.
    return VSSClient(host, port, ensure_startup_connection=False)
