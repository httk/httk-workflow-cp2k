"""Building blocks for the collect hooks of CP2K workflows."""

from pathlib import Path

from httk.core import DataRecord

from .outputs import parse_cp2k_output

__all__ = ["read_total_energy"]

_TOTAL_ENERGY_DEFINITION = "https://schemas.httk.org/defs/v0.1/properties/core/total_energy"
_TOTAL_ENERGY_NAME = "_httk_total_energy"


def read_total_energy(path: Path) -> DataRecord:
    """Read the converged total energy, in eV, from one CP2K output file.

    :param path: The CP2K output file.
    :return: The energy as a ``total_energy`` property record.
    :raises ValueError: If the output holds no converged total energy.
    """

    energy = parse_cp2k_output(path).total_energy_ev
    if energy is None:
        raise ValueError(f"{path} holds no converged total energy")
    return DataRecord.from_value(_TOTAL_ENERGY_DEFINITION, _TOTAL_ENERGY_NAME, energy)
