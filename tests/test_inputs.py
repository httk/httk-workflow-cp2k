"""``write_cp2k_input`` writes an input the real CP2K accepts."""

import os
import subprocess
from pathlib import Path

import pytest

from conftest import SILICON_ENERGY_HA, SILICON_POSCAR, cp2k_command, requires_cp2k
from httk.codes.cp2k import parse_cp2k_output, write_cp2k_input

pytest.importorskip("httk.atomistic")


def _write(tmp_path: Path, **extra: object) -> str:
    (tmp_path / "POSCAR").write_text(SILICON_POSCAR, encoding="utf-8")
    options: dict[str, object] = {"structure": tmp_path / "POSCAR", "cutoff_ry": 100, "rel_cutoff_ry": 40}
    write_cp2k_input(tmp_path / "cp2k.inp", **(options | extra))  # type: ignore[arg-type]
    return (tmp_path / "cp2k.inp").read_text(encoding="utf-8")


def test_the_input_has_the_sections_of_the_captured_input(tmp_path: Path) -> None:
    text = _write(tmp_path)
    lines = text.splitlines()
    for line in (
        "&GLOBAL",
        "  RUN_TYPE ENERGY",
        "  PREFERRED_DIAG_LIBRARY SL",
        "    BASIS_SET_FILE_NAME BASIS_MOLOPT",
        "      CUTOFF 100.0",
        "      REL_CUTOFF 40.0",
        "      &XC_FUNCTIONAL PBE",
        "      A 5.4300000000 0.0000000000 0.0000000000",
        "      Si 0.7500000000 0.7500000000 0.2500000000",
        "    &KIND Si",
        "      BASIS_SET DZVP-MOLOPT-SR-GTH",
        "      POTENTIAL GTH-PBE",
    ):
        assert line in lines
    assert "KPOINTS" not in text and text.endswith("&END FORCE_EVAL\n")


def test_options_override_and_extend(tmp_path: Path) -> None:
    text = _write(
        tmp_path,
        kpoints=(2, 3, 4),
        potential={"Si": "GTH-PBE-q4"},
        data_dir="/opt/cp2k/data",
        extra_global={"preferred_diag_library": "ELPA", "SEED": "7"},
    )
    lines = text.splitlines()
    assert "      SCHEME MONKHORST-PACK 2 3 4" in lines and "      POTENTIAL GTH-PBE-q4" in lines
    assert "    POTENTIAL_FILE_NAME /opt/cp2k/data/GTH_POTENTIALS" in lines
    assert "  PREFERRED_DIAG_LIBRARY ELPA" in lines and "  PREFERRED_DIAG_LIBRARY SL" not in lines
    assert "  SEED 7" in lines


# Few-digit hexagonal ZnO: httk-atomistic's default POSCAR load would snap -1.92
# to -23/12, the simplest rational within its written digits.
HEXAGONAL_POSCAR = """hexagonal
1.0
3.84 0.0 0.0
-1.92 3.3255 0.0
0.0 0.0 6.27
Zn O
1 1
Direct
0.333333 0.666667 0.0
0.333333 0.666667 0.382
"""


@pytest.mark.parametrize("name", ["POSCAR", "contcar"])
def test_a_poscar_reaches_the_input_as_its_written_floats(tmp_path: Path, name: str) -> None:
    from httk.core.report import collect_reports

    (tmp_path / name).write_text(HEXAGONAL_POSCAR, encoding="utf-8")
    # The default POSCAR load warns that no precision was given; this path gives one.
    with collect_reports() as reports:
        write_cp2k_input(tmp_path / "cp2k.inp", structure=tmp_path / name)
    assert reports.records == []
    text = (tmp_path / "cp2k.inp").read_text(encoding="utf-8")
    cell = [
        [float(x) for x in line.split()[1:]] for line in text.splitlines() if line.strip()[:2] in ("A ", "B ", "C ")
    ]
    assert cell == [[3.84, 0.0, 0.0], [-1.92, 3.3255, 0.0], [0.0, 0.0, 6.27]]
    assert "      O 0.3333330000 0.6666670000 0.3820000000" in text.splitlines()


def test_invalid_options_are_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no basis given for species Si"):
        _write(tmp_path, basis={"Ge": "DZVP-MOLOPT-SR-GTH"})
    with pytest.raises(ValueError, match="kpoints"):
        _write(tmp_path, kpoints=(2, 0, 2))
    with pytest.raises(ValueError, match="cutoff_ry"):
        _write(tmp_path, cutoff_ry=0)
    with pytest.raises(ValueError, match="single-line"):
        _write(tmp_path, extra_global={"SEED": "7\n&END GLOBAL"})
    with pytest.raises(ValueError, match="token"):
        _write(tmp_path, data_dir="/my data")


@requires_cp2k
def test_the_real_cp2k_accepts_the_input_and_reproduces_the_capture(tmp_path: Path) -> None:
    command = cp2k_command()
    assert command is not None
    _write(tmp_path)
    subprocess.run(
        [*command, "-i", "cp2k.inp", "-o", "cp2k.out"],
        cwd=tmp_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=os.environ | {"OMP_NUM_THREADS": "1"},
        check=True,
        timeout=300,
    )
    result = parse_cp2k_output(tmp_path / "cp2k.out")
    assert result.converged and result.completed
    assert result.total_energy_ha == pytest.approx(SILICON_ENERGY_HA, abs=1e-8)
