"""``run_cp2k`` classifies a supervised run and writes its report.

A stand-in CP2K replays a captured output into the ``-o`` file, so the
classification is exercised without a real CP2K.
"""

import json
import sys
from pathlib import Path

import pytest

from conftest import DATA, SILICON_ENERGY_HA
from httk.codes.cp2k import run_cp2k

# Appends the named captured output to the file after ``-o`` (as CP2K appends) and
# exits with a code; run_cp2k appends ``-i cp2k.inp -o cp2k.out``.
_REPLAY = "import sys; open(sys.argv[-1], 'a').write(open(sys.argv[1]).read()); sys.exit(int(sys.argv[2]))"


def _replay(output: str, code: int = 0) -> list[str]:
    return [sys.executable, "-c", _REPLAY, str(DATA / output), str(code)]


@pytest.mark.parametrize(
    ("argv", "classification"),
    [
        (_replay("si.out"), "completed"),
        # CP2K exits 1 when it aborts on SCF non-convergence; that is still nonconverged.
        (_replay("si_noconv.out", 1), "nonconverged"),
        (_replay("si_noconv_ignored.out"), "nonconverged"),
        (_replay("si_abort.out", 1), "crashed"),
        (_replay("si.out", 3), "process_failure"),
    ],
)
def test_the_run_is_classified_and_reported(tmp_path: Path, argv: list[str], classification: str) -> None:
    report = run_cp2k(argv, directory=tmp_path)
    assert report.classification == classification
    assert report.ok == (classification == "completed")
    assert report.process.argv[-4:] == ("-i", "cp2k.inp", "-o", "cp2k.out")
    saved = json.loads((tmp_path / "cp2k-run-report.json").read_text(encoding="utf-8"))
    assert saved["format"] == "httk-cp2k-run-report" and saved["classification"] == classification
    if classification == "completed":
        assert saved["result"]["total_energy_ha"] == SILICON_ENERGY_HA
        assert report.diagnostics == ()


def test_a_stale_output_is_removed_before_the_run(tmp_path: Path) -> None:
    # CP2K appends to an existing output, so an earlier abort would otherwise remain.
    (tmp_path / "cp2k.out").write_text((DATA / "si_abort.out").read_text(encoding="utf-8"), encoding="utf-8")
    assert run_cp2k(_replay("si.out"), directory=tmp_path).ok
