"""Shared test configuration: isolate the httk configuration of every test."""

import os
import shlex
import shutil
from pathlib import Path

import pytest

# Keep each BLAS runtime of the many short-lived runner processes to one thread;
# child runners inherit this.
for _thread_limit in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_thread_limit] = "1"


@pytest.fixture(autouse=True)
def _isolated_httk_config(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """Give every test its own httk config and data home, so no workspace registry leaks between tests."""

    monkeypatch.setenv("HTTK_CONFIG_HOME", str(tmp_path_factory.mktemp("httk-config")))
    monkeypatch.setenv("HTTK_DATA_HOME", str(tmp_path_factory.mktemp("httk-store")))


DATA = Path(__file__).resolve().parent / "data"
REPO_ROOT = Path(__file__).resolve().parent.parent

# The 8-atom conventional cubic diamond silicon cell of the captured tests/data/si.inp.
SILICON_POSCAR = """silicon
5.43
1.0 0.0 0.0
0.0 1.0 0.0
0.0 0.0 1.0
Si
8
Direct
0.00 0.00 0.00
0.00 0.50 0.50
0.50 0.00 0.50
0.50 0.50 0.00
0.25 0.25 0.25
0.25 0.75 0.75
0.75 0.25 0.75
0.75 0.75 0.25
"""

#: The total energy of tests/data/si.out in Hartree.
SILICON_ENERGY_HA = -31.115927819707686


def cp2k_command() -> list[str] | None:
    """The real CP2K command: ``HTTK_TEST_CP2K_COMMAND``, else ``cp2k.psmp`` on PATH, else ``None``."""

    command = os.environ.get("HTTK_TEST_CP2K_COMMAND") or shutil.which("cp2k.psmp")
    return shlex.split(command) if command else None


def cp2k_data_dir() -> Path | None:
    """The ``share/cp2k/data`` directory of the CP2K installation, when the command's prefix has one."""

    command = cp2k_command()
    executable = shutil.which(command[0]) if command else None
    candidate = Path(executable).resolve().parent.parent / "share" / "cp2k" / "data" if executable else None
    return candidate if candidate is not None and (candidate / "GTH_POTENTIALS").is_file() else None


requires_cp2k = pytest.mark.skipif(
    cp2k_command() is None, reason="needs a real CP2K: set HTTK_TEST_CP2K_COMMAND or put cp2k.psmp on PATH"
)
