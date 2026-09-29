"""Classify a finished CP2K calculation into stable diagnostics."""

import os
from pathlib import Path

from httk.workflow.codes import Diagnostic

from .outputs import _NOT_CONVERGED, _parse, _read

__all__ = ["diagnose_cp2k"]


def diagnose_cp2k(directory: str | os.PathLike[str] = ".", *, output: str = "cp2k.out") -> tuple[Diagnostic, ...]:
    """Diagnose a CP2K calculation from its output.

    The codes are stable: ``cp2k.abort`` (fatal; CP2K stopped with an
    ``[ABORT]`` box), ``cp2k.scf_not_converged`` (error; the last SCF cycle did
    not converge, whether CP2K aborted on it, its default, or only warned under
    ``IGNORE_CONVERGENCE_FAILURE``), and ``cp2k.incomplete`` (error; no
    ``PROGRAM ENDED AT`` and no abort, e.g. a killed process). A converged,
    completed run has none. A missing output file is diagnosed like an empty one.

    :param directory: Read the calculation files from this directory.
    :param output: The name of the CP2K output file in *directory*.
    :return: The diagnostics, empty for a clean run.
    """

    result = _parse(_read(Path(directory) / output))
    aborts = [message for message in result.errors if _NOT_CONVERGED not in message]
    diagnostics: list[Diagnostic] = []
    if aborts:
        diagnostics.append(Diagnostic("cp2k.abort", "fatal", aborts[0], output, "\n".join(aborts)))
    elif not result.completed and not result.errors:
        diagnostics.append(Diagnostic("cp2k.incomplete", "error", f"{output} has no PROGRAM ENDED AT line", output))
    if result.converged is False:
        steps = f" after {result.scf_steps} steps" if result.scf_steps is not None else ""
        diagnostics.append(Diagnostic("cp2k.scf_not_converged", "error", f"SCF run NOT converged{steps}", output))
    return tuple(diagnostics)
