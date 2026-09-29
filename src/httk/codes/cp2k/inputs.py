"""Write CP2K input files from *httk* structures."""

import fractions
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

__all__ = ["write_cp2k_input"]


def write_cp2k_input(
    path: str | os.PathLike[str],
    *,
    structure: object,
    basis: Mapping[str, str] | str = "DZVP-MOLOPT-SR-GTH",
    potential: Mapping[str, str] | str = "GTH-PBE",
    xc: str = "PBE",
    cutoff_ry: float = 400,
    rel_cutoff_ry: float = 50,
    kpoints: tuple[int, int, int] | None = None,
    basis_file: str = "BASIS_MOLOPT",
    potential_file: str = "GTH_POTENTIALS",
    data_dir: str | None = None,
    project: str = "cp2k",
    extra_global: Mapping[str, str] | None = None,
) -> Path:
    """Write a CP2K Quickstep single-point energy input for one periodic structure.

    The input has a ``&GLOBAL`` section (``PROJECT``, ``RUN_TYPE ENERGY``,
    ``PRINT_LEVEL LOW`` and ``PREFERRED_DIAG_LIBRARY SL``) and a ``&FORCE_EVAL``
    with ``&DFT`` (basis and potential files, ``&MGRID``, ``&SCF`` with atomic
    guess and standard diagonalization, ``&XC``, and ``&KPOINTS`` when a grid is
    given, else the Gamma point) and ``&SUBSYS`` (``&CELL`` vectors ``A``/``B``/``C``
    in Å, ``SCALED`` fractional ``&COORD``, one ``&KIND`` per species).

    ``PREFERRED_DIAG_LIBRARY SL`` selects ScaLAPACK because ELPA, CP2K's default
    where built in, can crash on a single MPI rank; pass
    ``extra_global={"PREFERRED_DIAG_LIBRARY": "ELPA"}`` to restore it. The
    default potential ``GTH-PBE`` is the alias the ``GTH_POTENTIALS`` file lists
    beside each element's default valence (``Si GTH-PBE-q4 GTH-PBE``), so CP2K
    picks the valence; name a specific one, e.g. ``{"Fe": "GTH-PBE-q8"}``, where
    the default is not wanted. A CP2K input is inherently floating point, so the
    cell and coordinates are written as floats of the structure's exact values.
    A POSCAR path (``POSCAR``, ``CONTCAR``, ``*.poscar``, ``*.vasp``) is read
    as the decimals it writes, so its floats reach the input unchanged, rather
    than as the simplest rationals within its written digits, which is what
    *httk-atomistic* loads by default.
    This needs *httk-atomistic* (the ``atomistic`` extra).

    :param path: Write the input file to this path.
    :param structure: The structure: a POSCAR/CIF path or anything
        ``httk.atomistic.UnitcellStructureView`` accepts.
    :param basis: The basis set name for every species, or a map from every species name to one.
    :param potential: The pseudopotential name for every species, or a map from every species name to one.
    :param xc: The ``&XC_FUNCTIONAL`` section name.
    :param cutoff_ry: The finest plane-wave grid cutoff (``&MGRID CUTOFF``) in Ry.
    :param rel_cutoff_ry: The Gaussian-to-grid mapping cutoff (``&MGRID REL_CUTOFF``) in Ry.
    :param kpoints: The Monkhorst-Pack grid, or ``None`` for the Gamma point only.
    :param basis_file: The basis set file name.
    :param potential_file: The pseudopotential file name.
    :param data_dir: The directory holding *basis_file* and *potential_file*, or ``None``
        for CP2K's own data directory and the working directory.
    :param project: The CP2K project name, the prefix of the files CP2K writes.
    :param extra_global: Additional ``&GLOBAL`` keywords; they override the generated ones.
    :return: The written path.
    :raises ValueError: If a cutoff or the grid is not positive, a species has no basis or
        potential, a species is not a single element, or a value is not one input token line.
    """

    for label, cutoff in (("cutoff_ry", cutoff_ry), ("rel_cutoff_ry", rel_cutoff_ry)):
        if not cutoff > 0:
            raise ValueError(f"{label} must be positive, not {cutoff!r}")
    if kpoints is not None and (
        len(kpoints) != 3 or any(not isinstance(n, int) or isinstance(n, bool) or n < 1 for n in kpoints)
    ):
        raise ValueError(f"kpoints must be three positive integers or None, not {kpoints!r}")
    view = _structure_view(structure)
    kinds: list[tuple[str, str, str, str]] = []
    for item in view.species:
        if len(item.chemical_symbols) != 1:
            raise ValueError(f"species {item.name} is not a single element; CP2K needs one element per kind")
        basis_name = basis if isinstance(basis, str) else basis.get(item.name)
        potential_name = potential if isinstance(potential, str) else potential.get(item.name)
        if basis_name is None or potential_name is None:
            raise ValueError(f"no {'basis' if basis_name is None else 'potential'} given for species {item.name}")
        kinds.append((item.name, item.chemical_symbols[0], basis_name, potential_name))
    files = [name if data_dir is None else str(Path(data_dir, name)) for name in (basis_file, potential_file)]
    settings = {"PROJECT": project, "RUN_TYPE": "ENERGY", "PRINT_LEVEL": "LOW", "PREFERRED_DIAG_LIBRARY": "SL"}
    settings |= {key.upper(): value for key, value in (extra_global or {}).items()}
    # Every value lands inside one keyword line; whitespace in a name, or a line
    # break or CP2K comment character in any value, would change the input's structure.
    names = [xc, project, basis_file, potential_file, data_dir or "-", *settings]
    names += [name for kind in kinds for name in kind[2:]]
    for token in (*names, *settings.values()):
        if not isinstance(token, str) or not token or any(character in token for character in "\n\r!#"):
            raise ValueError(f"{token!r} is not a valid single-line CP2K input token")
    for token in names:
        if token.split() != [token]:
            raise ValueError(f"{token!r} is not a valid CP2K input token")
    lines = ["&GLOBAL", *(f"  {key} {value}" for key, value in settings.items()), "&END GLOBAL", ""]
    lines += [
        "&FORCE_EVAL",
        "  METHOD Quickstep",
        "  &DFT",
        f"    BASIS_SET_FILE_NAME {files[0]}",
        f"    POTENTIAL_FILE_NAME {files[1]}",
        "    &MGRID",
        f"      CUTOFF {float(cutoff_ry)!r}",
        f"      REL_CUTOFF {float(rel_cutoff_ry)!r}",
        "    &END MGRID",
        "    &QS",
        "    &END QS",
        "    &SCF",
        "      SCF_GUESS ATOMIC",
        "      EPS_SCF 1.0E-6",
        "      MAX_SCF 50",
        "      &DIAGONALIZATION",
        "        ALGORITHM STANDARD",
        "      &END DIAGONALIZATION",
        "    &END SCF",
        "    &XC",
        f"      &XC_FUNCTIONAL {xc}",
        "      &END XC_FUNCTIONAL",
        "    &END XC",
    ]
    if kpoints is not None:
        lines += ["    &KPOINTS", "      SCHEME MONKHORST-PACK {} {} {}".format(*kpoints), "    &END KPOINTS"]
    lines += ["  &END DFT", "  &SUBSYS", "    &CELL"]
    for label, row in zip("ABC", view.lattice_vectors, strict=True):
        lines.append(f"      {label} " + " ".join(f"{float(x):.10f}" for x in row))
    lines += ["    &END CELL", "    &COORD", "      SCALED"]
    for name, row in zip(view.species_at_sites, view.fractional_site_positions, strict=True):
        lines.append(f"      {name} " + " ".join(f"{float(x):.10f}" for x in row))
    lines.append("    &END COORD")
    for name, element, basis_name, potential_name in kinds:
        lines += [f"    &KIND {name}"]
        if name != element:
            lines.append(f"      ELEMENT {element}")
        lines += [f"      BASIS_SET {basis_name}", f"      POTENTIAL {potential_name}", "    &END KIND"]
    lines += ["  &END SUBSYS", "&END FORCE_EVAL", ""]
    destination = Path(path)
    destination.write_text("\n".join(lines), encoding="utf-8")
    return destination


def _structure_view(structure: object) -> Any:
    from httk.atomistic import UnitcellStructureView  # pyright: ignore[reportMissingImports]

    if not isinstance(structure, str | os.PathLike):
        return UnitcellStructureView(cast(Any, structure))
    source = Path(structure)
    if source.name.upper() not in ("POSCAR", "CONTCAR") and source.suffix.lower() not in (".poscar", ".vasp"):
        return UnitcellStructureView(cast(Any, source))
    # ponytail: httk-atomistic snaps POSCAR decimals to the simplest rationals within
    # their digits (-1.92 -> -23/12) and has no option to keep them; re-reading the
    # neutral payload with every number as its exact decimal does. Replace this with
    # the loader option once httk-atomistic has one. The precision passed only records
    # a realistic tolerance (and skips the digit-derived one and its warning).
    import httk.core
    from httk.atomistic.integrations.vasp import VASPStructure  # pyright: ignore[reportMissingImports]

    payload = dict(httk.core.load(str(source), raw=True, precision=1e-5))
    for key in ("cell", "coords"):
        payload[key] = [[fractions.Fraction(token) for token in row] for row in payload[key]]
    for key in ("scale", "volume"):
        if payload[key] is not None:
            payload[key] = fractions.Fraction(payload[key])
    return UnitcellStructureView(VASPStructure(payload))
