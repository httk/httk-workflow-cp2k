"""End to end with the real CP2K: install, run, and collect the ``cp2k.energy`` workflow.

Runs only with a real CP2K (``HTTK_TEST_CP2K_COMMAND`` or ``cp2k.psmp`` on
PATH). The workflow is installed as the ``httk_plugin.toml`` plugin of this
repository, as ``httk plugin install`` does, into the test's isolated data home.
"""

import json
import shlex
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from conftest import REPO_ROOT, SILICON_POSCAR, cp2k_command, cp2k_data_dir, requires_cp2k
from httk.codes.cp2k import parse_cp2k_output

pytestmark = [requires_cp2k, pytest.mark.slow]


@pytest.fixture
def installed_plugin(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    from httk.core.plugins import install_plugin
    from httk.workflow.packages import _reset_plugin_workflow_cache

    source = tmp_path_factory.mktemp("plugin-source") / "httk-workflow-cp2k"
    shutil.copytree(REPO_ROOT / "workflows", source / "workflows", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(REPO_ROOT / "httk_plugin.toml", source)
    install_plugin(source)
    _reset_plugin_workflow_cache()
    yield
    _reset_plugin_workflow_cache()


def test_cp2k_energy_runs_cp2k_and_collects_the_total_energy(
    tmp_path: Path, installed_plugin: None, capsys: pytest.CaptureFixture[str]
) -> None:
    pytest.importorskip("httk.atomistic")
    store = pytest.importorskip("httk.store")
    from httk.core import DataRecord, Run
    from httk.core.cli import CLIContext
    from httk.workflow import TaskManager, Workspace
    from httk.workflow.collecting import job_records
    from httk.workflow.registry import register_workspace
    from httk.workflow.scaffold import new_job
    from httk.workflow.workflow_cli import command

    workspace = Workspace.initialize(tmp_path / "workspace")
    workspace.set_setting("cp2k.command", shlex.join(cp2k_command() or ()))
    data_dir = cp2k_data_dir()
    if data_dir is not None:
        workspace.set_setting("cp2k.data_dir", str(data_dir))
    (tmp_path / "POSCAR").write_text(SILICON_POSCAR, encoding="utf-8")
    job = new_job(
        workspace,
        "cp2k.energy",
        inputs={"structure": tmp_path / "POSCAR"},
        parameters={"cutoff_ry": 100, "rel_cutoff_ry": 40},
        install=True,
    )
    with TaskManager(workspace, heartbeat_interval=0.01) as manager:
        manager.run_until_idle(timeout=600.0)
    [record] = job_records(workspace, states=("succeeded", "failed"))
    assert (record.job_id, record.state) == (job.job_id, "succeeded"), record.failure
    (output,) = (tmp_path / "workspace").rglob("cp2k.out")
    parsed = parse_cp2k_output(output).total_energy_ev
    assert parsed == pytest.approx(-846.707, abs=0.01)

    register_workspace("cp2k", str(workspace.root))
    database = tmp_path / "results.sqlite"
    arguments = ["collect", "--workspace", "cp2k", "--into", str(database), "--id-base", "httk.test", "--no-id-ledger"]
    assert command(arguments, CLIContext("httk", tmp_path)) == 0
    report = json.loads(capsys.readouterr().out.splitlines()[0])
    assert set(report["outputs"]) == {"total_energy"} and report["stored"]["run"]

    with store.Backend.sqlite(database) as backend:
        searcher = store.SqlStore(backend).searcher()
        energies: list[Any] = [row.energy for row in searcher.results(energy=searcher.variable(DataRecord))]
        searcher = store.SqlStore(backend).searcher()
        runs = list(searcher.results(run=searcher.variable(Run)))
    assert [energy.value for energy in energies] == [pytest.approx(parsed, abs=1e-9)]
    assert len(runs) == 1
