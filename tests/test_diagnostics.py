"""``diagnose_cp2k`` maps finished calculations to the stable ``cp2k.*`` codes."""

from pathlib import Path

from conftest import DATA
from httk.codes.cp2k import diagnose_cp2k


def _codes(directory: Path, output: str) -> list[tuple[str, str]]:
    return [(item.code, item.severity) for item in diagnose_cp2k(directory, output=output)]


def test_a_converged_run_has_no_diagnostics() -> None:
    assert diagnose_cp2k(DATA, output="si.out") == ()


def test_an_unconverged_run_is_an_error_whether_cp2k_aborted_or_warned() -> None:
    for output in ("si_noconv.out", "si_noconv_ignored.out"):
        (diagnostic,) = diagnose_cp2k(DATA, output=output)
        assert (diagnostic.code, diagnostic.severity) == ("cp2k.scf_not_converged", "error")
        assert diagnostic.summary == "SCF run NOT converged after 2 steps"


def test_an_abort_is_fatal_and_names_the_message() -> None:
    (diagnostic,) = diagnose_cp2k(DATA, output="si_abort.out")
    assert (diagnostic.code, diagnostic.severity, diagnostic.source) == ("cp2k.abort", "fatal", "si_abort.out")
    assert "found an unknown keyword RUN_TYPO" in diagnostic.summary


def test_a_truncated_or_missing_output_is_incomplete(tmp_path: Path) -> None:
    text = (DATA / "si.out").read_text(encoding="utf-8")
    (tmp_path / "cp2k.out").write_text(text[: len(text) // 2], encoding="utf-8")
    assert _codes(tmp_path, "cp2k.out") == [("cp2k.incomplete", "error")]
    assert _codes(tmp_path, "absent.out") == [("cp2k.incomplete", "error")]
