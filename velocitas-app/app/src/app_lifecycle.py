"""Bounded lifecycle for this app's pinned native SDK 0.15.7 / Paho 2.1 clients.

The SDK's native stop hook is a no-op. Keep its pub/sub connections, but use
Paho's asynchronous connection lifecycle so SIGTERM also works during outages.
"""
import asyncio
import contextlib
import logging
import threading

LOG = logging.getLogger(__name__)


async def bounded_thread_call(function, timeout):
    """Bound cleanup joins without leaving an unkillable default-executor job.

    A stalled third-party close is a failed shutdown, not success. Daemon helper
    ownership lets that failure terminate the process nonzero within the budget;
    asyncio.run must not wait forever on its default executor after a timeout.
    """
    finished = threading.Event()
    outcome = []

    def work():
        try:
            outcome.append((True, function()))
        except BaseException as error:
            outcome.append((False, error))
        finally:
            finished.set()

    worker = threading.Thread(target=work, name="app-client-close", daemon=True)
    worker.start()

    async def wait():
        while not finished.is_set():
            await asyncio.sleep(0.01)

    await asyncio.wait_for(wait(), timeout)
    ok, result = outcome[0]
    if not ok:
        raise result
    return result


async def finish_inflight(awaitable, timeout=3.0):
    """Cancellation waits for already dispatched, explicitly bounded I/O."""
    task = asyncio.ensure_future(awaitable)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError as cancelled:
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout)
        except asyncio.TimeoutError as error:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            raise RuntimeError('inflight operation did not finish within shutdown budget') from error
        except Exception as error:
            # A bounded read may finish with UNAVAILABLE during shutdown. Preserve
            # cancellation rather than letting the polling retry loop consume it.
            LOG.warning('inflight operation ended during shutdown type=%s', type(error).__name__)
        raise cancelled


async def run_until_stopped(app, stop):
    running = asyncio.create_task(app.run())
    stopping = asyncio.create_task(stop.wait())
    try:
        await asyncio.wait((running, stopping), return_when=asyncio.FIRST_COMPLETED)
        if running.done():
            await running  # Never convert startup/polling errors to exit zero.
    finally:
        stopping.cancel()
        await asyncio.gather(stopping, return_exceptions=True)
        running.cancel()
        try:
            with contextlib.suppress(asyncio.CancelledError):
                await asyncio.wait_for(running, 4.0)
        finally:
            await asyncio.wait_for(app.stop(), 8.0)


class NativeMqttLifecycle:
    def __init__(self, sdk_client):
        self.sdk = sdk_client
        self.clients = tuple(dict.fromkeys((sdk_client._pub_client, sdk_client._sub_client)))
        self.started = []
        self._closing = None

    async def start(self):
        for client in self.clients:
            # Paho public property, set before any connection. Bounds loop-stop
            # when a connect attempt is currently waiting for an absent broker.
            client.connect_timeout = 2.0
            result = client.connect_async(self.sdk._hostname, self.sdk._port or 1883)
            if result not in (None, 0):
                raise RuntimeError('MQTT asynchronous startup failed')
            if client.loop_start() != 0:
                raise RuntimeError('MQTT network loop did not start')
            self.started.append(client)
        while not all(client.is_connected() for client in self.clients):
            await asyncio.sleep(0.05)

    async def close(self):
        if self._closing is None:
            self._closing = asyncio.create_task(self._close())
        await asyncio.shield(self._closing)

    async def _close(self):
        errors = []
        for client in self.clients:
            try:
                # NOT_CONNECTED is expected if startup was cancelled or broker lost.
                result = client.disconnect()
                if result not in (0, 4):
                    raise RuntimeError('MQTT disconnect failed')
            except Exception as error:
                errors.append(error)
        for client in self.started:
            try:
                result = await bounded_thread_call(client.loop_stop, 3.0)
                # Paho2.1 returns INVAL only when its thread is already None
                # (DISCONNECT may have finished it before loop_stop was called).
                if result not in (0, 3):
                    raise RuntimeError('MQTT loop did not stop')
            except Exception as error:
                errors.append(error)
        if errors:
            raise RuntimeError('MQTT cleanup incomplete') from errors[0]
