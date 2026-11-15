import importlib.util
import os
import sys

import pytest

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, SRC)

from scenario_controller import WrongVehicleError  # noqa: E402


@pytest.fixture
def provider_main(monkeypatch):
    monkeypatch.setenv("SIMULATED_VEHICLE_ID", "vehicle-002")
    monkeypatch.delenv("INJECT_FAULT", raising=False)
    # Load by path: other test packages also have a main.py on sys.path.
    spec = importlib.util.spec_from_file_location(
        "provider_main",
        os.path.join(SRC, "main.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    yield module


def test_production_controller_enforces_configured_vehicle(provider_main):
    controller = provider_main.create_scenario_controller()

    with pytest.raises(WrongVehicleError):
        controller.execute(
            vehicle_id="vehicle-001",
            action="INJECT_SCENARIO",
            scenario="LIDAR_OBSTRUCTION",
            action_id="a",
            trace_id="t",
        )

    state = controller.execute(
        vehicle_id="vehicle-002",
        action="INJECT_SCENARIO",
        scenario="LIDAR_OBSTRUCTION",
        action_id="a",
        trace_id="t",
    )
    assert state["active"] is True


def test_ladder_step_is_not_published_to_kuksa(provider_main):
    assert "lidar_step" not in provider_main.SIGNAL_PATHS


class Stop:
    def __init__(self, stop_after=4):
        self.waits = []
        self.stopped = False
        self.stop_after = stop_after

    def is_set(self):
        return self.stopped

    def wait(self, seconds):
        self.waits.append(seconds)
        self.stopped = len(self.waits) >= self.stop_after
        return self.stopped


@pytest.mark.parametrize("failures", [1, 4])
def test_provider_reconnects_with_bounded_backoff_and_preserves_scenario(
    provider_main, monkeypatch, failures,
):
    """Removing retry/retaining failed state would lose the active scenario or stop publication."""
    from kuksa_client.grpc import VSSClientError
    controller = provider_main.create_scenario_controller()
    controller.execute(vehicle_id="vehicle-002", action="INJECT_SCENARIO",
                       scenario="LIDAR_OBSTRUCTION", action_id="a", trace_id="t")
    stop = Stop(stop_after=failures + 2)
    clients = []
    writes = []

    class Client:
        closed = False

        def __enter__(self):
            clients.append(self)
            return self

        def __exit__(self, *args):
            self.closed = True

        def set_current_values(self, values, **kwargs):
            assert kwargs['timeout'] == 2.0
            if len(clients) <= failures:
                raise VSSClientError({'code': 14, 'reason': 'unavailable'}, [])
            writes.append(values)

    monkeypatch.setattr(provider_main, 'get_client', Client)
    provider_main.publish_loop(controller, stop)
    assert all(client.closed for client in clients)
    assert len(clients) == failures + 1
    assert stop.waits[:failures] == [min(2 ** n, 5) for n in range(failures)]
    path = provider_main.SIGNAL_PATHS['lidar_distance_m']
    assert [write[path].value for write in writes] == [20.0, 8.0]
    assert controller.is_active(vehicle_id='vehicle-002', scenario='LIDAR_OBSTRUCTION')


def test_shutdown_interrupts_unavailable_dependency_backoff(provider_main, monkeypatch):
    from kuksa_client.grpc import VSSClientError
    closed = []

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            closed.append(True)

        def set_current_values(self, *args, **kwargs):
            raise VSSClientError({'code': 4, 'reason': 'deadline'}, [])

    monkeypatch.setattr(provider_main, 'get_client', Client)
    stop = Stop(stop_after=1)
    provider_main.publish_loop(provider_main.create_scenario_controller(), stop)
    assert closed == [True]
    assert stop.waits == [1]


def test_non_transient_client_error_is_not_retried(provider_main, monkeypatch):
    from kuksa_client.grpc import VSSClientError

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def set_current_values(self, *args, **kwargs):
            raise VSSClientError({'code': 7, 'reason': 'permission denied'}, [])

    monkeypatch.setattr(provider_main, 'get_client', Client)
    stop = Stop()
    with pytest.raises(VSSClientError):
        provider_main.publish_loop(provider_main.create_scenario_controller(), stop)
    assert stop.waits == []


@pytest.mark.parametrize('vehicle', ['vehicle-001', 'vehicle-002'])
@pytest.mark.parametrize('failure_code', [4, 14])
def test_recovery_publishes_kpa_once_without_advancing_failed_psi_state(
    provider_main, monkeypatch, vehicle, failure_code,
):
    """An inline raw write, state advance on failure or reconversion must fail."""
    from kuksa_client.grpc import VSSClientError
    monkeypatch.setattr(provider_main, 'SIMULATED_VEHICLE_ID', vehicle)
    controller = provider_main.create_scenario_controller()
    stop = Stop(stop_after=3)
    inputs, writes, attempts, closed = [], [], [], []

    def observation(state, **scenarios):
        inputs.append(state['tire_pressure'])
        return dict(state, tire_pressure=state['tire_pressure'] + 1)

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            closed.append(True)

        def set_current_values(self, values, **kwargs):
            assert kwargs == {'timeout': 2.0}
            attempts.append(values)
            if len(attempts) == 1:
                raise VSSClientError({'code': failure_code, 'reason': 'transient'}, [])
            writes.append(values[provider_main.SIGNAL_PATHS['tire_pressure']].value)

    monkeypatch.setattr(provider_main, 'next_state', observation)
    monkeypatch.setattr(provider_main, 'get_client', Client)
    provider_main.publish_loop(controller, stop)
    assert inputs == [32.0, 32.0, 33.0]
    assert writes == [228, 234]  # 33/34 psi quantized once, not raw or re-converted
    assert all(type(value) is int for value in writes)
    assert closed == [True, True]
    assert stop.waits == [1.0, provider_main.PUBLISH_INTERVAL_SECONDS,
                          provider_main.PUBLISH_INTERVAL_SECONDS]
