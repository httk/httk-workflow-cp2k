"""The ``cp2k-*`` subcommands of the private native Bash command bridge.

``httk.workflow._shell_bridge`` mounts these beside its own subcommands through
the ``codes`` registry tier, so each function of ``httk-cp2k.sh`` is one
invocation of one command here. A legitimately absent answer returns the
bridge's uniform exit code ``1``; a refused call raises, which the bridge
reports as ``2``. ``cp2k-run`` has its own outcome codes, the same as
``vasp-run``: ``0`` completed, ``20`` crashed, ``21`` nonconverged, ``22``
process failure, ``124`` timeout; ``cp2k-diagnose`` exits ``20`` when it
found anything, like ``vasp-diagnose``.
"""

import argparse
import json
from pathlib import Path

from httk.workflow.codes import BRIDGE_ABSENT, read_json

from .diagnostics import diagnose_cp2k
from .inputs import write_cp2k_input
from .outputs import parse_cp2k_output
from .reports import run_cp2k

_RUN_EXIT = {"completed": 0, "crashed": 20, "nonconverged": 21, "process_failure": 22, "timeout": 124}


def add_commands(commands: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register the ``cp2k-*`` subcommands on the bridge's subparsers.

    :param commands: the bridge's subcommand collection.
    """

    run = commands.add_parser("cp2k-run")
    run.add_argument("--directory", default=".")
    run.add_argument("--input", default="cp2k.inp")
    run.add_argument("--output", default="cp2k.out")
    run.add_argument("--timeout", type=float)
    run.add_argument("--launch", action=argparse.BooleanOptionalAction, default=None)
    run.add_argument("argv", nargs=argparse.REMAINDER)
    energy = commands.add_parser("cp2k-energy")
    energy.add_argument("--output", default="cp2k.out")
    energy.add_argument("--unit", choices=("ha", "ev"), default="ha")
    converged = commands.add_parser("cp2k-converged")
    converged.add_argument("--output", default="cp2k.out")
    diagnose = commands.add_parser("cp2k-diagnose")
    diagnose.add_argument("--output", default="cp2k.out")
    diagnose.add_argument("--json", action="store_true")
    write = commands.add_parser("cp2k-write-input")
    write.add_argument("--options", required=True)
    write.add_argument("--input", default="cp2k.inp")


def run_command(arguments: argparse.Namespace) -> int:
    """Run one parsed ``cp2k-*`` subcommand.

    :param arguments: the parsed bridge command line.
    :return: the subcommand's exit code.
    """

    command = arguments.command
    if command == "cp2k-run":
        argv = arguments.argv[1:] if arguments.argv[:1] == ["--"] else arguments.argv
        if not argv:
            raise ValueError("cp2k-run needs the CP2K command after --")
        report = run_cp2k(
            argv,
            directory=arguments.directory,
            input_file=arguments.input,
            output_file=arguments.output,
            timeout=arguments.timeout,
            launch=arguments.launch,
        )
        print(Path(arguments.directory, "cp2k-run-report.json"))
        return _RUN_EXIT[report.classification]
    if command == "cp2k-diagnose":
        output = Path(arguments.output)
        diagnostics = diagnose_cp2k(output.parent, output=output.name)
        if arguments.json:
            print(json.dumps([item.as_mapping() for item in diagnostics], sort_keys=True))
        else:
            for item in diagnostics:
                print(f"{item.code}\t{item.severity}\t{item.summary}")
        return 20 if diagnostics else 0
    if command == "cp2k-write-input":
        options = dict(read_json(Path(arguments.options)))
        if options.get("kpoints") is not None:
            options["kpoints"] = tuple(options["kpoints"])
        write_cp2k_input(arguments.input, **options)
        return 0
    result = parse_cp2k_output(arguments.output)
    if command == "cp2k-energy":
        value = result.total_energy_ha if arguments.unit == "ha" else result.total_energy_ev
        if value is None:
            return BRIDGE_ABSENT
        print(f"{value:.16g}")
        return 0
    if command == "cp2k-converged":
        return 0 if result.converged else BRIDGE_ABSENT
    raise AssertionError(command)
