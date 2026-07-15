import os
from kuksa_client.grpc import VSSClient

def get_client():
    host = os.environ.get("DATABROKER_HOST", "127.0.0.1")
    port = int(os.environ.get("DATABROKER_PORT", 55555))
    return VSSClient(host, port)