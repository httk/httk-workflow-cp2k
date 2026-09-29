# *httk-workflow-cp2k*

This site documents the *httk-workflow-cp2k* module. For the full documentation
of *httk₂*, see [docs.httk.org](https://docs.httk.org).

The module adds CP2K support to *httk-workflow*: the Python helpers in
`httk.codes.cp2k` (input writing, output parsing, diagnostics, supervised
execution and a result collector), the Bash API a Bash runner sources as
`$HTTK_WORKFLOW_CP2K_BASH_API`, and the `cp2k-*` bridge commands behind that
API. Installing it registers the `cp2k` code with *httk₂* through the
`httk.registry.codes.cp2k` registration package. The repository also carries
the example workflow package `cp2k.energy`.

```{admonition} Quick links
:class: tip

- {doc}`usage` — the Python and Bash API, the example workflow, and the diagnostics
- {doc}`reference/index` — the generated API reference
```

## Install

```console
python -m pip install "httk-workflow-cp2k[atomistic]"
```

```{toctree}
:maxdepth: 2
:caption: Documentation

usage
reference/index
```
