"""``read_total_energy`` reads one CP2K output; the packaged hook finds it with ``result_file``."""

import runpy
import shutil
from pathlib import Path, PurePosixPath

import pytest
from httk.core import DataRecord
from httk.workflow.collecting import JobRecord

from conftest import DATA, SILICON_ENERGY_HA
from httk.codes.cp2k import HA_TO_EV
from httk.codes.cp2k.collect import read_total_energy

HOOK = Path(__file__).parent.parent / "workflows" / "cp2k-energy" / "collect.py"
JOB_ID = "12345678-1234-4234-8234-123456789abc"


def test_the_energy_is_read_in_ev() -> None:
    assert read_total_energy(DATA / "si.out").value == pytest.approx(SILICON_ENERGY_HA * HA_TO_EV)


def test_an_unconverged_output_is_refused() -> None:
    with pytest.raises(ValueError, match="no converged total energy"):
        read_total_energy(DATA / "si_noconv.out")


def test_the_packaged_hook_reads_the_workdir_output(tmp_path: Path) -> None:
    (tmp_path / "run").mkdir()
    shutil.copy(DATA / "si.out", tmp_path / "run" / "cp2k.out")
    record = JobRecord(
        workspace_root=tmp_path,
        workspace_id="ws",
        job_id=JOB_ID,
        job_key=f"job--{JOB_ID}",
        job={},
        runner_provenance=None,
        state="succeeded",
        failure=None,
        placement=PurePosixPath("jobs"),
        payload_path=PurePosixPath(f"jobs/job--{JOB_ID}"),
        workdir_path=PurePosixPath("run"),
        data_path=None,
        data_generation=None,
        provenance={},
        runner_steps=None,
        children={},
        declarations={},
    )
    outputs = runpy.run_path(str(HOOK))["collect"](record)
    assert set(outputs) == {"total_energy"}
    assert isinstance(outputs["total_energy"], DataRecord)
    assert outputs["total_energy"].value == pytest.approx(SILICON_ENERGY_HA * HA_TO_EV)
