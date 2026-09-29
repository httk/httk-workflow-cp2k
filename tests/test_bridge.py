"""The ``cp2k-*`` bridge commands and the Bash API that forwards to them.

Code verbs need no attempt, so they run straight through the shell bridge.
Sibling code packages may print unrelated notices on standard error, so only
standard output and exit codes are asserted.
"""

import json
import os
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import pytest

from conftest import DATA, SILICON_POSCAR


def _bridge(cwd: Path, *arguments: str) -> "subprocess.CompletedProcess[str]":
    environment = {name: value for name, value in os.environ.items() if not name.startswith("HTTK_WORKFLOW_")}
    environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    return subprocess.run(
        [sys.executable, "-m", "httk.workflow._shell_bridge", *arguments],
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_energy_and_convergence_answers_and_absences(tmp_path: Path) -> None:
    energy = _bridge(tmp_path, "cp2k-energy", "--output", str(DATA / "si.out"))
    assert (energy.returncode, energy.stdout) == (0, "-31.11592781970769\n")
    in_ev = _bridge(tmp_path, "cp2k-energy", "--output", str(DATA / "si.out"), "--unit", "ev")
    assert float(in_ev.stdout) == pytest.approx(-846.7074, abs=1e-3)
    assert _bridge(tmp_path, "cp2k-converged", "--output", str(DATA / "si.out")).returncode == 0
    for verb in ("cp2k-energy", "cp2k-converged"):
        absent = _bridge(tmp_path, verb, "--output", str(DATA / "si_noconv_ignored.out"))
        assert (absent.returncode, absent.stdout) == (1, "")
    refused = _bridge(tmp_path, "cp2k-energy", "--output", str(tmp_path / "missing.out"))
    assert refused.returncode == 2


def test_diagnose_prints_codes_and_json(tmp_path: Path) -> None:
    clean = _bridge(tmp_path, "cp2k-diagnose", "--output", str(DATA / "si.out"))
    assert (clean.returncode, clean.stdout) == (0, "")
    aborted = _bridge(tmp_path, "cp2k-diagnose", "--output", str(DATA / "si_abort.out"), "--json")
    assert aborted.returncode == 20
    assert [item["code"] for item in json.loads(aborted.stdout)] == ["cp2k.abort"]


def test_write_input_then_run_with_a_replayed_cp2k(tmp_path: Path) -> None:
    pytest.importorskip("httk.atomistic")
    (tmp_path / "POSCAR").write_text(SILICON_POSCAR, encoding="utf-8")
    options = {"structure": "POSCAR", "cutoff_ry": 100, "kpoints": [2, 2, 2], "potential": {"Si": "GTH-PBE-q4"}}
    (tmp_path / "options.json").write_text(json.dumps(options), encoding="utf-8")
    assert _bridge(tmp_path, "cp2k-write-input", "--options", "options.json").returncode == 0
    text = (tmp_path / "cp2k.inp").read_text(encoding="utf-8")
    assert "SCHEME MONKHORST-PACK 2 2 2" in text and "POTENTIAL GTH-PBE-q4" in text

    replay = "import sys; open(sys.argv[-1], 'w').write(open(sys.argv[1]).read()); sys.exit(1)"
    ran = _bridge(tmp_path, "cp2k-run", "--", sys.executable, "-c", replay, str(DATA / "si_noconv.out"))
    assert (ran.returncode, ran.stdout) == (21, "cp2k-run-report.json\n")
    report = json.loads((tmp_path / "cp2k-run-report.json").read_text(encoding="utf-8"))
    assert report["classification"] == "nonconverged"


def test_the_bash_api_forwards_to_the_bridge(tmp_path: Path) -> None:
    workflow_api = files("httk.workflow").joinpath("languages", "bash", "httk-workflow.sh")
    cp2k_api = files("httk.codes.cp2k").joinpath("httk-cp2k.sh")
    script = (
        f'source "{workflow_api}"; source "{cp2k_api}"; '
        f'test "$HTTK_CP2K_BASH_API_VERSION" = 1 && httk_cp2k_energy --output "{DATA / "si.out"}" --unit ha'
    )
    environment = {name: value for name, value in os.environ.items() if not name.startswith("HTTK_WORKFLOW_")}
    environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    environment["HTTK_WORKFLOW_PYTHON"] = sys.executable
    result = subprocess.run(
        ["bash", "-c", script], cwd=tmp_path, env=environment, text=True, capture_output=True, check=False
    )
    assert (result.returncode, result.stdout) == (0, "-31.11592781970769\n"), result.stderr
    unguarded = subprocess.run(
        ["bash", "-c", f'source "{cp2k_api}"; httk_cp2k_energy'], text=True, capture_output=True, check=False
    )
    assert unguarded.returncode == 2 and "source HTTK_WORKFLOW_BASH_API" in unguarded.stderr
