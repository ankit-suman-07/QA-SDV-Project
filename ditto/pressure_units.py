"""Explicit VSS kPa -> legacy diagnostic psi boundary.

Protobuf tire_pressure_psi, Ditto tirePressurePsi and OpenSOVD thresholds
already use psi and must not convert again. VSS uint16 rounds to whole kPa.
"""

KPA_PER_PSI = 6.894757293168


def kpa_to_psi(pressure_kpa):
    return float(pressure_kpa) / KPA_PER_PSI
