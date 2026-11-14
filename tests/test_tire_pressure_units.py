"""Real source/boundary contract regressions, including uint16 quantization."""
import ast
import importlib.util
from pathlib import Path
import sys

import pytest
from opensovd.fault_mapper import map_fault_to_opensovd

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT/'vehicle-simulator/src'))
from signal_generator import initial_state, next_state


def provider():
    spec = importlib.util.spec_from_file_location('pressure_provider', ROOT/'vehicle-simulator/src/main.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('psi,kpa', [(0, 0), (24, 165), (28, 193), (32, 221), (34, 234)])
def test_provider_converts_intended_psi_to_declared_uint16_kpa(psi, kpa):
    app = provider()
    state = initial_state()
    state['tire_pressure'] = psi
    values = app.publication_values(state)
    actual = values[app.SIGNAL_PATHS['tire_pressure']].value
    assert type(actual) is int
    assert actual == kpa
    assert state['tire_pressure'] == psi  # publication must not reconvert state
    assert app.publication_values(state)[app.SIGNAL_PATHS['tire_pressure']].value == kpa


@pytest.mark.parametrize('kpa,psi', [(0, 0), (165, 23.931208726), (193, 27.992262328), (221, 32.053315931)])
def test_legacy_boundary_converts_kpa_to_psi_once(kpa, psi):
    from ditto.pressure_units import kpa_to_psi
    assert kpa_to_psi(kpa) == pytest.approx(psi, abs=1e-8)


def test_runtime_bridge_uses_kpa_conversion_before_protobuf():
    # The bridge has a live top-level loop; inspect its runtime call expression
    # rather than importing it and contacting shared services.
    tree = ast.parse((ROOT/'ditto/scripts/interim-kuksa-to-ditto-bridge.py').read_text())
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id=='publish_vehicle_status']
    value = next(k.value for k in calls[0].keywords if k.arg=='tire_pressure_psi')
    assert ast.unparse(value) == 'kpa_to_psi(tire_fl)'


@pytest.mark.parametrize('psi,severity,threshold', [(24, 'CRITICAL', 24), (24.01, 'WARNING', 28), (28, 'WARNING', 28)])
def test_roundtrip_uses_legacy_psi_thresholds_without_double_conversion(psi, severity, threshold):
    from ditto.pressure_units import kpa_to_psi
    app = provider()
    state = initial_state()
    state['tire_pressure'] = psi
    kpa = app.publication_values(state)[app.SIGNAL_PATHS['tire_pressure']].value
    diagnostic = kpa_to_psi(kpa)
    mapped = map_fault_to_opensovd('TIRE_PRESSURE_LOW_FRONT_LEFT', {'features': {'signals': {'properties': {'tirePressurePsi': {'frontLeft': diagnostic}}},
                      'health': {'properties': {'activeFaults': ['TIRE_PRESSURE_LOW_FRONT_LEFT']}}}})
    assert mapped['unit'] == 'psi'
    assert mapped['observedValue'] == diagnostic
    assert mapped['severity'] == severity
    assert mapped['threshold'] == threshold
    assert abs(diagnostic-psi) <= .5/6.894757293168


def test_source_fault_pressure_decreases_without_changing_lidar_contract():
    state = initial_state()
    assert state['tire_pressure'] == 32
    for _ in range(20):
        state = next_state(state, fault=True)
    assert state['tire_pressure'] < 30
    assert state['lidar_distance_m'] == 35
