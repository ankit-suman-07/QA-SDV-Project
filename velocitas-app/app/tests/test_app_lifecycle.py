"""Owned task/client lifecycle regressions; fake clients, no external services."""
import asyncio
import importlib
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))


def api():
    assert (Path(__file__).resolve().parents[1]/'src/app_lifecycle.py').exists(), 'orderly lifecycle is absent'
    return importlib.import_module('app_lifecycle')


class Client:
    def __init__(self, connected=True, fail=False):
        self.connected=connected;self.fail=fail;self.calls=[]
    def connect_async(self,host,port): self.calls.append('connect_async');return 0
    def loop_start(self): self.calls.append('loop_start');return 0
    def is_connected(self):return self.connected
    def disconnect(self):self.calls.append('disconnect');return 0
    def loop_stop(self):
        self.calls.append('loop_stop')
        if self.fail:raise RuntimeError('failed cleanup')
        return 0


def test_stop_cancels_and_awaits_owned_run_before_cleanup():
    m=api()
    async def case():
        entered=asyncio.Event();stop=asyncio.Event();calls=[]
        class App:
            async def run(self):
                entered.set()
                try:await asyncio.Future()
                finally:calls.append('task_finished')
            async def stop(self):calls.append('closed')
        task=asyncio.create_task(m.run_until_stopped(App(),stop))
        await entered.wait();stop.set();await asyncio.wait_for(task,1)
        assert calls==['task_finished','closed']
    asyncio.run(case())


def test_startup_exception_is_preserved_and_cleanup_still_runs():
    m=api()
    async def case():
        calls=[]
        class App:
            async def run(self):raise ValueError('startup failed')
            async def stop(self):calls.append('closed')
        with pytest.raises(ValueError):await m.run_until_stopped(App(),asyncio.Event())
        assert calls==['closed']
    asyncio.run(case())


def test_native_clients_close_once_and_both_close_even_on_failure():
    m=api()
    async def case():
        class SDK:
            _hostname='127.0.0.1';_port=1883
            _pub_client=Client(fail=True);_sub_client=Client()
        sdk=SDK();life=m.NativeMqttLifecycle(sdk)
        await life.start()
        with pytest.raises(RuntimeError):await life.close()
        with pytest.raises(RuntimeError):await life.close()
        for c in (sdk._pub_client,sdk._sub_client):
            assert c.calls==['connect_async','loop_start','disconnect','loop_stop']
    asyncio.run(case())


def test_cancel_during_absent_broker_startup_closes_started_loops():
    m=api()
    async def case():
        class SDK:
            _hostname='127.0.0.1';_port=1883
            _pub_client=Client(connected=False);_sub_client=Client(connected=False)
        sdk=SDK();life=m.NativeMqttLifecycle(sdk);t=asyncio.create_task(life.start())
        await asyncio.sleep(0.02);t.cancel()
        with pytest.raises(asyncio.CancelledError):await t
        await life.close();await life.close()
        assert all(c.calls.count('loop_stop')==1 for c in (sdk._pub_client,sdk._sub_client))
    asyncio.run(case())


def test_cancel_waits_for_bounded_inflight_work_before_returning():
    m=api()
    async def case():
        finished=[]
        async def operation():await asyncio.sleep(0.04);finished.append(True)
        t=asyncio.create_task(m.finish_inflight(operation()))
        await asyncio.sleep(0.01);t.cancel()
        with pytest.raises(asyncio.CancelledError):await t
        assert finished==[True]
    asyncio.run(case())


def test_cleanup_error_is_not_reported_as_successful_shutdown():
    m=api()
    async def case():
        class App:
            async def run(self):await asyncio.Future()
            async def stop(self):raise RuntimeError('not closed')
        stop=asyncio.Event();stop.set()
        with pytest.raises(RuntimeError):await m.run_until_stopped(App(),stop)
    asyncio.run(case())


def test_failed_inflight_read_cannot_swallow_shutdown_cancellation():
    m=api()
    async def case():
        async def read():
            await asyncio.sleep(0.03)
            raise ConnectionError('dependency unavailable')
        t=asyncio.create_task(m.finish_inflight(read()))
        await asyncio.sleep(0.01);t.cancel()
        with pytest.raises(asyncio.CancelledError):await t
    asyncio.run(case())


def test_paho_loop_already_stopped_after_disconnect_is_complete():
    m=api()
    async def case():
        class Finished(Client):
            def loop_stop(self):
                self.calls.append('loop_stop')
                return 3  # Paho2.1: _thread is already None after DISCONNECT.
        class SDK:
            _hostname='127.0.0.1';_port=1883
            _pub_client=Finished();_sub_client=Finished()
        life=m.NativeMqttLifecycle(SDK())
        await life.start();await life.close()
    asyncio.run(case())
