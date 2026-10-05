# Using the CP2K helpers

*httk-workflow-cp2k* ships the CP2K helpers that workflow runners are built on,
in two languages: the Python package {py:mod}`httk.codes.cp2k` and the Bash CP2K
API, whose `httk_cp2k_*` functions call the same code through the
*httk-workflow* shell bridge.

## Install

```console
python -m pip install "httk-workflow-cp2k[atomistic]"
```

The distribution depends on *httk-core* and *httk-workflow*. Installing it
registers the `cp2k` code through the `httk.registry.codes.cp2k` registration
package, which makes the `cp2k-*` bridge commands and the Bash API available to
every job the manager starts; nothing needs to be configured. Writing inputs
from structures needs *httk-atomistic*, the `atomistic` extra; parsing,
diagnostics, running and collecting do not.

## Python

```python
from httk.codes.cp2k import run_cp2k, write_cp2k_input

write_cp2k_input(
    "cp2k.inp",
    structure="POSCAR",
    cutoff_ry=400,
    kpoints=(4, 4, 4),
    potential={"Si": "GTH-PBE-q4"},
)
report = run_cp2k(["cp2k.psmp"], timeout=3600)
if report.ok:
    print(report.result.total_energy_ev)
else:
    print(report.classification, [item.code for item in report.diagnostics])
```

- {py:func}`~httk.codes.cp2k.write_cp2k_input` writes a Quickstep single-point
  energy input from a POSCAR/CIF path or an *httk* structure: `&GLOBAL`, and a
  `&FORCE_EVAL` with `&DFT` (basis and potential files, `&MGRID`, `&SCF`, `&XC`,
  and `&KPOINTS` for a Monkhorst-Pack grid, else the Gamma point) and
  `&SUBSYS` (cell vectors in Å, fractional `SCALED` coordinates, one `&KIND`
  per species). `basis` and `potential` take one name for every species or a
  map per species; the default potential `GTH-PBE` is the alias the
  `GTH_POTENTIALS` file lists for each element's default valence, so CP2K
  resolves it (`Si GTH-PBE-q4 GTH-PBE`). `data_dir` names the directory of the
  basis and potential files when CP2K's own data directory is not wanted.
  `extra_global` adds or overrides `&GLOBAL` keywords. A POSCAR path is read
  as the decimals it writes, so its numbers reach the input unchanged.
- {py:func}`~httk.codes.cp2k.parse_cp2k_output` returns a
  {py:class}`~httk.codes.cp2k.Cp2kResult`: the last Quickstep total energy
  (Hartree, and eV through `total_energy_ev`; withheld when the SCF did not
  converge, although CP2K prints one under `IGNORE_CONVERGENCE_FAILURE`), SCF
  convergence and step count, whether `PROGRAM ENDED AT` was reached, and the
  messages of `[ABORT]` boxes, each prefixed with the source location CP2K names.
- {py:func}`~httk.codes.cp2k.run_cp2k` runs the command with
  `-i cp2k.inp -o cp2k.out` under the *httk-workflow* process supervisor and
  returns a {py:class}`~httk.codes.cp2k.Cp2kRunReport` classified as
  `completed`, `crashed`, `nonconverged`, `process_failure` or `timeout`, also
  written to `cp2k-run-report.json`. CP2K appends to an existing output file,
  so an earlier `cp2k.out` is removed first.
- {py:func}`~httk.codes.cp2k.diagnose_cp2k` diagnoses a finished calculation.

### ELPA on a single MPI rank

The inputs set `PREFERRED_DIAG_LIBRARY SL` in `&GLOBAL`, selecting ScaLAPACK
for diagonalization, because ELPA, which CP2K prefers where it is built in, can
crash (segfault) when CP2K runs on a single MPI rank. On multi-rank runs where
ELPA is wanted, pass `extra_global={"PREFERRED_DIAG_LIBRARY": "ELPA"}`.

## Diagnostics

| Code | Severity | Meaning |
| --- | --- | --- |
| `cp2k.abort` | fatal | CP2K stopped with an `[ABORT]` box; the summary is its source location and message |
| `cp2k.scf_not_converged` | error | the last SCF cycle reported `SCF run NOT converged`, whether CP2K aborted on it (its default) or only warned (`IGNORE_CONVERGENCE_FAILURE`) |
| `cp2k.incomplete` | error | no `PROGRAM ENDED AT` and no abort, e.g. a killed process |

A converged, completed calculation has no diagnostics. CP2K exits nonzero when
it aborts on SCF non-convergence; {py:func}`~httk.codes.cp2k.run_cp2k` still
classifies that run as `nonconverged`.

## Bash

The manager exports the path of the CP2K API as `HTTK_WORKFLOW_CP2K_BASH_API`
when *httk-workflow-cp2k* is installed, so a Bash runner guards it and sources
it after the generic library:

```bash
source "$HTTK_WORKFLOW_BASH_API"
: "${HTTK_WORKFLOW_CP2K_BASH_API:?install httk-workflow-cp2k}"
source "$HTTK_WORKFLOW_CP2K_BASH_API"

httk_cp2k_write_input --options options.json   # the write_cp2k_input keywords as JSON
httk_cp2k_run --timeout 3600 -- cp2k.psmp
energy=$(httk_cp2k_energy --unit ev)
```

The command names only the program: the attempt's launch prefix (the parallel start, the `HTTK_WORKFLOW_LAUNCH` variable the workflow manager sets from the `manager.launch_template` setting, or the built-in Slurm prefix) is prepended to it, and `--no-launch` (`launch=False` in Python) runs the command as given. A command that already starts with a launcher such as `mpirun` or `srun` is refused when a prefix applies.

| Function | Bridge command | Exit status |
| --- | --- | --- |
| `httk_cp2k_write_input --options FILE [--input cp2k.inp]` | `cp2k-write-input` | `0` |
| `httk_cp2k_run [--directory] [--input] [--output] [--timeout] [--no-launch] -- CMD...` | `cp2k-run` | `0` completed, `20` crashed, `21` nonconverged, `22` process failure, `124` timeout (as `vasp-run`); prints the report path |
| `httk_cp2k_energy [--output cp2k.out] [--unit ha\|ev]` | `cp2k-energy` | `0` and the energy, `1` when there is none |
| `httk_cp2k_converged [--output cp2k.out]` | `cp2k-converged` | `0` converged, `1` not converged or unknown |
| `httk_cp2k_diagnose [--output cp2k.out] [--json]` | `cp2k-diagnose` | `0` clean, `20` when it printed diagnostics |

A refused call (for example a missing output file) exits `2`. The API sets
`HTTK_CP2K_BASH_API_VERSION=1`.

## The example workflow

The repository's `workflows/cp2k-energy` is the workflow package `cp2k.energy`:
one Python runner step that stages the `structure` input, writes `cp2k.inp`,
runs CP2K, and fails with the first diagnostic code when the calculation is not
clean. There are no pseudopotential files to stage: CP2K reads the basis and
potential files by name. Install it with `httk plugin install` of the
repository, or use it directly with `--workflow-dir`:

```console
httk workspace settings set --key cp2k.command --value cp2k.psmp WORKSPACE
httk job new --workflow cp2k.energy --input structure=POSCAR --parameter 'kpoints=[4, 4, 4]'
httk workflow run
httk collect --into results.sqlite
```

Its parameters are `basis` (default `DZVP-MOLOPT-SR-GTH`), `potential` (default
`GTH-PBE`), `xc` (default `PBE`), `cutoff_ry` (default 400), `rel_cutoff_ry`
(default 50) and `kpoints` (default: the Gamma point); the settings
`cp2k.command` (default `cp2k.psmp`) and `cp2k.data_dir` (default: CP2K's own
data directory) say how to run CP2K and where the `BASIS_MOLOPT` and
`GTH_POTENTIALS` files are.

## Collecting

{py:func}`~httk.codes.cp2k.collect.read_total_energy` reads the converged total
energy from a CP2K output file as a {py:class}`httk.core.DataRecord` of the
property `https://schemas.httk.org/defs/v0.1/properties/core/total_energy` in
eV. An output without a converged energy is refused.

The packaged workflow's `collect.py` hook shows how a workflow locates the file
with `record.result_file` and returns the role mapping; to collect more outputs,
add lines to your copy of the hook:

```python
from httk.codes.cp2k.collect import read_total_energy


def collect(record):
    return {"total_energy": read_total_energy(record.result_file("cp2k.out"))}
```

### Recognized calculations

A finished CP2K run that was not started by a workspace is collected by the
registered `cp2k.calculation` collector:
`httk.workflow.collect_tree(root)` finds every directory holding exactly one
`<stem>.out` whose first 100 lines carry the CP2K header (`CP2K| version
string:`) together with `<stem>.inp`, compressed or not, and collects its
converged total energy. The identity is a digest of the input file, so moving
the directory keeps it. A directory with several CP2K outputs or without the
input is reported as unclaimed; an unconverged output is claimed and degraded.
{py:func}`~httk.codes.cp2k.collect.find_outputs` is the same header-based finder.
