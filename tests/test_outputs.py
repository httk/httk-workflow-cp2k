"""``parse_cp2k_output`` reads real captured CP2K 2026.2 output."""

from pathlib import Path

import pytest

from conftest import DATA, SILICON_ENERGY_HA
from httk.codes.cp2k import HA_TO_EV, parse_cp2k_output


def test_a_converged_energy_run() -> None:
    result = parse_cp2k_output(DATA / "si.out")
    assert result.total_energy_ha == SILICON_ENERGY_HA
    assert result.total_energy_ev == pytest.approx(SILICON_ENERGY_HA * HA_TO_EV)
    assert (result.converged, result.scf_steps, result.completed, result.errors) == (True, 12, True, ())


def test_an_scf_run_cp2k_aborted_unconverged() -> None:
    result = parse_cp2k_output(DATA / "si_noconv.out")
    assert (result.total_energy_ha, result.converged, result.scf_steps, result.completed) == (None, False, 2, False)
    (message,) = result.errors
    assert message.startswith("qs_scf.F:702: SCF run NOT converged. To continue the calculation regardless,")
    assert message.endswith(" please set the keyword IGNORE_CONVERGENCE_FAILURE.")


def test_an_unconverged_energy_is_withheld_although_cp2k_prints_it() -> None:
    result = parse_cp2k_output(DATA / "si_noconv_ignored.out")
    assert "ENERGY| Total FORCE_EVAL" in (DATA / "si_noconv_ignored.out").read_text(encoding="utf-8")
    assert (result.total_energy_ha, result.converged, result.scf_steps, result.completed) == (None, False, 2, True)
    assert result.errors == ()


def test_an_abort_box_is_read_with_its_source_location() -> None:
    result = parse_cp2k_output(DATA / "si_abort.out")
    assert (result.total_energy_ha, result.converged, result.completed) == (None, None, False)
    assert result.errors == ("input/input_parsing.F:253: found an unknown keyword RUN_TYPO in section GLOBAL",)


@pytest.mark.parametrize("unit", ["[hartree]", "[a.u.]:", "(a.u.):"])
def test_every_release_spelling_of_the_energy_line_is_read(tmp_path: Path, unit: str) -> None:
    # Synthetic one-line snippets: CP2K 2026 prints "[hartree]", 2022-2023 "[a.u.]:",
    # older releases "(a.u.):".
    path = tmp_path / "snippet.out"
    path.write_text(f" ENERGY| Total FORCE_EVAL ( QS ) energy {unit}      -31.115927819707686\n", encoding="utf-8")
    assert parse_cp2k_output(path).total_energy_ha == SILICON_ENERGY_HA


def test_a_compressed_output_parses_like_the_plain_one(tmp_path: Path) -> None:
    import bz2

    (tmp_path / "si.out.bz2").write_bytes(bz2.compress((DATA / "si.out").read_bytes()))
    assert parse_cp2k_output(tmp_path / "si.out.bz2") == parse_cp2k_output(DATA / "si.out")
