#!/usr/bin/env bash

# Native httk CP2K Bash API, version 1. Source httk-workflow.sh first.
#
# Every function is one cp2k-* bridge subcommand, and every option of that
# subcommand is available here: the arguments are passed through untouched.
#
#   httk_cp2k_write_input --options OPTIONS.json [--input cp2k.inp]
#   httk_cp2k_run [--directory .] [--input cp2k.inp] [--output cp2k.out] [--timeout S] -- cp2k.psmp ...
#       prints the report path; exits 0 completed, 20 crashed, 21 nonconverged,
#       22 process failure, 124 timeout
#   httk_cp2k_energy [--output cp2k.out] [--unit ha|ev]   exits 1 when there is no energy
#   httk_cp2k_converged [--output cp2k.out]               exits 1 when not converged
#   httk_cp2k_diagnose [--output cp2k.out] [--json]       exits 20 when it found anything
HTTK_CP2K_BASH_API_VERSION=1

_httk_cp2k_require_workflow_api() {
    if ! declare -F _httk_workflow_bridge >/dev/null 2>&1; then
        printf 'httk-workflow: source HTTK_WORKFLOW_BASH_API before HTTK_WORKFLOW_CP2K_BASH_API\n' >&2
        return 2
    fi
}

httk_cp2k_write_input() {
    _httk_cp2k_require_workflow_api || return
    _httk_workflow_bridge cp2k-write-input "$@"
}

httk_cp2k_run() {
    _httk_cp2k_require_workflow_api || return
    _httk_workflow_bridge cp2k-run "$@"
}

httk_cp2k_energy() {
    _httk_cp2k_require_workflow_api || return
    _httk_workflow_bridge cp2k-energy "$@"
}

httk_cp2k_converged() {
    _httk_cp2k_require_workflow_api || return
    _httk_workflow_bridge cp2k-converged "$@"
}

httk_cp2k_diagnose() {
    _httk_cp2k_require_workflow_api || return
    _httk_workflow_bridge cp2k-diagnose "$@"
}
