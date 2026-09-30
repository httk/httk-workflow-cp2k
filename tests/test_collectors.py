"""The ``cp2k.calculation`` collector recognizes and collects free-standing runs via ``collect_tree``."""

import bz2
import lzma
import shutil
from pathlib import Path

import pytest
from httk.workflow import claims, collect_tree
from httk.workflow.calculations import content_digest

from conftest import DATA, SILICON_ENERGY_HA
from httk.codes.cp2k import HA_TO_EV
from httk.codes.cp2k.collect import find_outputs

ORCA_HEAD = "\n                                 *****************\n                                 * O   R   C   A *\n"


def _run(directory: Path, output: str = "si.out", stem: str = "run") -> Path:
    directory.mkdir(parents=True)
    shutil.copy(DATA / output, directory / f"{stem}.out")
    shutil.copy(DATA / "si.inp", directory / f"{stem}.inp")
    return directory


def test_a_converged_run_is_collected(tmp_path: Path) -> None:
    directory = _run(tmp_path / "si")
    (item,) = collect_tree(tmp_path)
    identity = content_digest(directory, ["run.inp"])
    assert item.missing_collector is None
    assert item.run.source_id == f"cp2k.calculation:{identity}"
    assert item.outputs["total_energy"].value == pytest.approx(SILICON_ENERGY_HA * HA_TO_EV)  # type: ignore[attr-defined]


def test_an_unconverged_run_is_claimed_and_degraded(tmp_path: Path) -> None:
    _run(tmp_path / "si", "si_noconv.out")
    (outcome,) = claims(tmp_path)
    assert outcome.kind == "claimed" and outcome.collector == "cp2k.calculation"
    (item,) = collect_tree(tmp_path)
    assert item.missing_collector is not None and "no converged total energy" in item.missing_collector


def test_a_scheduler_log_is_no_candidate(tmp_path: Path) -> None:
    (tmp_path / "slurm-1.out").write_text("Job started\n" * 5, encoding="utf-8")
    assert list(claims(tmp_path)) == []
    assert find_outputs(tmp_path) == ()


def test_several_outputs_are_unclaimed(tmp_path: Path) -> None:
    directory = _run(tmp_path / "si")
    shutil.copy(DATA / "si.out", directory / "other.out")
    (outcome,) = claims(tmp_path)
    assert outcome.kind == "unclaimed"
    assert outcome.reason == "several CP2K outputs: other.out, run.out"
    assert list(collect_tree(tmp_path)) == []


def test_a_missing_input_is_unclaimed(tmp_path: Path) -> None:
    directory = _run(tmp_path / "si")
    (directory / "run.inp").unlink()
    (outcome,) = claims(tmp_path)
    assert (outcome.kind, outcome.reason) == ("unclaimed", "no run.inp beside run.out")


def test_compressed_files_are_collected(tmp_path: Path) -> None:
    directory = _run(tmp_path / "si")
    (directory / "run.out.bz2").write_bytes(bz2.compress((directory / "run.out").read_bytes()))
    (directory / "run.inp.lzma").write_bytes(
        lzma.compress((directory / "run.inp").read_bytes(), format=lzma.FORMAT_ALONE)
    )
    (directory / "run.out").unlink()
    (directory / "run.inp").unlink()
    (item,) = collect_tree(tmp_path)
    assert item.missing_collector is None
    assert item.outputs["total_energy"].value == pytest.approx(SILICON_ENERGY_HA * HA_TO_EV)  # type: ignore[attr-defined]


def test_another_programs_output_is_not_claimed(tmp_path: Path) -> None:
    (tmp_path / "run.out").write_text(ORCA_HEAD, encoding="utf-8")
    (tmp_path / "run.inp").write_text("! HF\n", encoding="utf-8")
    assert find_outputs(tmp_path) == ()
    assert [item for item in claims(tmp_path) if item.collector == "cp2k.calculation"] == []


def test_an_uppercase_output_finds_its_input(tmp_path: Path) -> None:
    directory = _run(tmp_path / "x", stem="RUN")
    (directory / "RUN.out").rename(directory / "RUN.OUT")
    (item,) = collect_tree(tmp_path)
    assert item.run.source_id == f"cp2k.calculation:{content_digest(directory, ['RUN.inp'])}"
