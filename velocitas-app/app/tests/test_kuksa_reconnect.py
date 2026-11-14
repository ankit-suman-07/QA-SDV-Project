import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kuksa_reconnect import reconnect  # noqa: E402


class FakeClient:
    def __init__(self, fail_disconnect=False):
        self.calls = []
        self.fail_disconnect = fail_disconnect

    def disconnect(self):
        self.calls.append("disconnect")
        if self.fail_disconnect:
            raise RuntimeError("already closed")

    def connect(self):
        self.calls.append("connect")


def test_reconnect_closes_old_channel_before_connecting():
    client = FakeClient()
    reconnect(client)
    assert client.calls == ["disconnect", "connect"]


def test_reconnect_still_connects_when_disconnect_fails():
    client = FakeClient(fail_disconnect=True)
    reconnect(client)
    assert client.calls == ["disconnect", "connect"]
