"""Parse the text output of CP2K (``cp2k.psmp``).

Pure stdlib parsing: nothing here runs a program or imports *httk* code, so a
result can be read anywhere the output file is.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path

__all__ = ["HA_TO_EV", "Cp2kResult", "parse_cp2k_output"]

#: One Hartree in electronvolts (CODATA 2018), the unit CP2K prints energies in.
HA_TO_EV: float = 27.211386245988

# CP2K 2026 prints "[hartree]", 2022-2023 "[a.u.]:", and older releases "(a.u.):".
_ENERGY = re.compile(
    r"^\s*ENERGY\| Total FORCE_EVAL \( QS \) energy (?:\[hartree\]|\[a\.u\.\]:|\(a\.u\.\):)\s+(\S+)",
    re.MULTILINE,
)
# "*** SCF run converged in N steps ***"; a failed cycle aborts with, or (with
# IGNORE_CONVERGENCE_FAILURE) warns "SCF run NOT converged".
_CONVERGENCE = re.compile(r"SCF run converged in\s+(\d+)\s+steps|SCF run NOT converged")
_LEFT_LOOP = re.compile(r"Leaving inner SCF loop after reaching\s+(\d+)\s+steps")
_LOCATION = re.compile(r"\S+\.F:\d+")
_NOT_CONVERGED = "SCF run NOT converged"


@dataclass(frozen=True)
class Cp2kResult:
    """What one CP2K output says about its calculation.

    :param total_energy_ha: The last Quickstep total energy (the ``ENERGY|`` line) in
        Hartree, or ``None``; also ``None`` when the last SCF cycle did not converge.
    :param converged: Whether the last SCF cycle converged, or ``None`` when no cycle reported.
    :param scf_steps: The step count of the last SCF cycle, or ``None``.
    :param completed: Whether CP2K reached its normal ``PROGRAM ENDED AT`` end.
    :param errors: The messages of the ``[ABORT]`` boxes in the output, each prefixed
        with the source location CP2K names.
    """

    total_energy_ha: float | None
    converged: bool | None
    scf_steps: int | None
    completed: bool
    errors: tuple[str, ...]

    @property
    def total_energy_ev(self) -> float | None:
        """The last converged total energy in eV, or ``None``."""
        return None if self.total_energy_ha is None else self.total_energy_ha * HA_TO_EV


def parse_cp2k_output(path: str | os.PathLike[str]) -> Cp2kResult:
    """Parse one CP2K output file.

    :param path: Read the CP2K output (the ``-o`` file) saved at this path.
    :return: The parsed result.
    :raises FileNotFoundError: If the output file does not exist.
    """

    return _parse(Path(path).read_text(encoding="utf-8", errors="replace"))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def _parse(text: str) -> Cp2kResult:
    energies = _ENERGY.findall(text)
    cycles = list(_CONVERGENCE.finditer(text))
    converged = None if not cycles else cycles[-1].group(1) is not None
    if converged:
        steps: int | None = int(cycles[-1].group(1))
    else:
        left = _LEFT_LOOP.findall(text)
        steps = int(left[-1]) if cycles and left else None
    return Cp2kResult(
        total_energy_ha=float(energies[-1]) if energies and converged is not False else None,
        converged=converged,
        scf_steps=steps,
        completed="PROGRAM ENDED AT" in text,
        errors=_aborts(text),
    )


def _aborts(text: str) -> tuple[str, ...]:
    # An abort box is a full row of stars, the ASCII-art figure with "[ABORT]" in its
    # left 8 columns and the message to its right, the source location last, and a
    # closing row of stars. Other star boxes of the output carry no "[ABORT]".
    lines = text.splitlines()
    errors: list[str] = []
    for index, line in enumerate(lines):
        if "[ABORT]" not in line:
            continue
        parts: list[str] = []
        for row in lines[index + 1 :]:
            inner = row.strip()
            if not inner or set(inner) == {"*"}:
                break
            parts.append(inner.strip("*")[8:].strip())
        parts = [part for part in parts if part]
        location = parts.pop() if parts and _LOCATION.fullmatch(parts[-1]) else None
        message = " ".join(parts)
        entry = f"{location}: {message}" if location else message
        if entry and entry not in errors:
            errors.append(entry)
    return tuple(errors)
