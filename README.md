# httk-workflow-cp2k

![Status: Early beta](https://img.shields.io/badge/status-early--beta-orange)

> **⚠️ EARLY BETA**
>
> This is an early beta release of *httk₂*. The organization of the packages
> and their APIs should not yet be regarded as stable, and may change between
> releases.

*httk-workflow-cp2k* adds CP2K support to
[*httk-workflow*](https://github.com/httk/httk-workflow), the workflow engine of
[*httk₂*](https://github.com/httk/httk2). It provides `httk.codes.cp2k`: writing
CP2K Quickstep inputs, parsing its output, stable diagnostics, supervised
execution with a classified run report, and helpers for reading workflow
outputs; and the Bash API that exposes the same helpers to Bash runners.
Installing it registers the `cp2k` code with *httk₂*; nothing needs to be
configured.

## Install

```console
python -m pip install "httk-workflow-cp2k[atomistic]"
```

The `atomistic` extra (*httk-atomistic*) is needed only to write inputs from
structures.

## Use

In a Python runner:

```python
from httk.codes.cp2k import run_cp2k, write_cp2k_input

write_cp2k_input("cp2k.inp", structure="POSCAR", cutoff_ry=400, kpoints=(4, 4, 4))
report = run_cp2k(["cp2k.psmp"])
print(report.classification, report.result.total_energy_ev)
```

In a Bash runner, whose manager exports the path of the CP2K API:

```bash
source "$HTTK_WORKFLOW_BASH_API"
: "${HTTK_WORKFLOW_CP2K_BASH_API:?install httk-workflow-cp2k}"
source "$HTTK_WORKFLOW_CP2K_BASH_API"
httk_cp2k_run -- cp2k.psmp
energy=$(httk_cp2k_energy --unit ev)
```

A complete example workflow package, `cp2k.energy`, is in
[`workflows/cp2k-energy`](workflows/cp2k-energy); `httk plugin install` of this
repository installs it. The API is documented in [`docs/usage.md`](docs/usage.md)
and at [docs.httk.org/httk-workflow-cp2k](https://docs.httk.org/httk-workflow-cp2k/).

## Running tests

`make test` runs the normal profile; `make ci` runs formatting, lint, both type
checkers and the extended tests. The end-to-end test runs the real CP2K only
when `HTTK_TEST_CP2K_COMMAND` names it or `cp2k.psmp` is on `PATH`, and skips
otherwise.
