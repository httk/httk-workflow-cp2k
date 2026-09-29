#!/usr/bin/env python3
"""cp2k.energy: one CP2K Quickstep single-point energy calculation of one structure.

The single ``run`` step stages the structure (the ``structure`` input, staged
as ``files/POSCAR``), writes ``cp2k.inp``, runs CP2K under supervision, and
fails with the first diagnostic code (``cp2k.abort``,
``cp2k.scf_not_converged``, ...) when the calculation is not clean. There are
no pseudopotential files to stage: CP2K reads its basis and potential files by
name.

Settings, resolved job parameter -> ``HTTK_*`` variable -> workspace setting:

* ``cp2k.command``: the command that starts CP2K (default ``cp2k.psmp``), e.g.
  ``mpirun -np 4 cp2k.psmp``;
* ``cp2k.data_dir``: the directory holding the ``BASIS_MOLOPT`` and
  ``GTH_POTENTIALS`` files (default: CP2K's own data directory).
"""

import shlex
import shutil
from typing import cast

from httk.workflow import Attempt, Runner

from httk.codes.cp2k import run_cp2k, write_cp2k_input

run = Runner("cp2k.energy")


@run.step(name="run")
def run_step(a: Attempt) -> None:
    """Prepare and run CP2K, then succeed or fail with what was diagnosed."""

    shutil.copyfile(a.payload / "files" / "POSCAR", a.workdir / "POSCAR")
    kpoints = a.parameter("kpoints", None)
    grid = None
    if kpoints is not None:
        nx, ny, nz = (int(n) for n in cast(list[int], kpoints))
        grid = (nx, ny, nz)
    data_dir = a.setting("cp2k.data_dir", None)
    try:
        write_cp2k_input(
            a.workdir / "cp2k.inp",
            structure=a.workdir / "POSCAR",
            basis=str(a.parameter("basis", "DZVP-MOLOPT-SR-GTH")),
            potential=str(a.parameter("potential", "GTH-PBE")),
            xc=str(a.parameter("xc", "PBE")),
            cutoff_ry=float(cast(float, a.parameter("cutoff_ry", 400))),
            rel_cutoff_ry=float(cast(float, a.parameter("rel_cutoff_ry", 50))),
            kpoints=grid,
            data_dir=str(data_dir) if data_dir else None,
        )
    except ValueError as exception:
        a.fail("cp2k.input_invalid", str(exception))
        return
    try:
        report = run_cp2k(shlex.split(str(a.setting("cp2k.command", "cp2k.psmp"))), directory=a.workdir)
    except OSError as exception:
        a.fail("cp2k.failed", f"could not start CP2K: {exception}")
        return
    if not report.ok:
        first = report.diagnostics[0] if report.diagnostics else None
        code = first.code if first else f"cp2k.{report.classification}"
        a.fail(code, first.summary if first else f"CP2K {report.classification}")
        return
    a.state.merge({"total_energy_ha": report.result.total_energy_ha})
    a.succeed()


if __name__ == "__main__":
    raise SystemExit(run.main())
