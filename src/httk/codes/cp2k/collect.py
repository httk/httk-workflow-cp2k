"""Building blocks for the collect hooks of CP2K workflows."""

from pathlib import Path

from httk.core import DataRecord
from httk.core.datastream.compression import open_compressed, split_compression_suffix

from .outputs import parse_cp2k_output

__all__ = ["find_outputs", "read_total_energy"]

_TOTAL_ENERGY_DEFINITION = "https://schemas.httk.org/defs/v0.1/properties/core/total_energy"
_TOTAL_ENERGY_NAME = "_httk_total_energy"
_BANNER = "CP2K| version string:"
_HEAD_LINES = 100


def _has_banner(path: Path) -> bool:
    """Whether the CP2K header line appears within the first lines of *path*."""

    try:
        with path.open("rb") as raw, open_compressed(raw, compression="extension", name=path.name) as stream:
            for number, line in enumerate(stream):
                if number >= _HEAD_LINES:
                    return False
                if _BANNER in line.decode("utf-8", "replace"):
                    return True
    except (OSError, EOFError):
        pass
    return False


def find_outputs(directory: Path) -> tuple[Path, ...]:
    """Find the CP2K output files of a directory, sorted by name.

    A ``*.out`` file (optionally compressed) counts as an output when the CP2K
    header line ``CP2K| version string:`` appears within its first 100 lines;
    only that head is read, so other programs' ``.out`` files are rejected cheaply.

    :param directory: The directory to look in.
    :return: The output files, sorted by name.
    """

    names = sorted(
        path
        for path in Path(directory).iterdir()
        if path.is_file() and split_compression_suffix(path.name)[0].lower().endswith(".out")
    )
    return tuple(path for path in names if _has_banner(path))


def read_total_energy(path: Path) -> DataRecord:
    """Read the converged total energy, in eV, from one CP2K output file.

    :param path: The CP2K output file, optionally compressed.
    :return: The energy as a ``total_energy`` property record.
    :raises ValueError: If the output is incomplete or holds no converged total energy.
    """

    result = parse_cp2k_output(path)
    energy = result.total_energy_ev
    if energy is None:
        raise ValueError(f"{path} holds no converged total energy")
    if not result.completed:
        raise ValueError(f"{path} is incomplete: CP2K did not report PROGRAM ENDED AT")
    return DataRecord.from_value(_TOTAL_ENERGY_DEFINITION, _TOTAL_ENERGY_NAME, energy)
