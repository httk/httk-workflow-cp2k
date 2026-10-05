"""Supervised CP2K execution and its classified run report."""

import dataclasses
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from httk.workflow.codes import Diagnostic, ProcessReport, ProcessSupervisor, launch_command, write_json_atomic

from .diagnostics import diagnose_cp2k
from .outputs import Cp2kResult, _parse, _read

__all__ = ["Cp2kRunReport", "run_cp2k"]


@dataclass(frozen=True)
class Cp2kRunReport:
    """Classified result of one supervised CP2K execution.

    The classification is one of ``completed``, ``crashed`` (a ``cp2k.abort``
    diagnostic), ``nonconverged``, ``process_failure`` (a nonzero exit or an
    incomplete output) and ``timeout``. A run CP2K aborted because its SCF did
    not converge is ``nonconverged`` although CP2K exits nonzero then.

    :param process: The supervised process result.
    :param classification: The final run classification.
    :param diagnostics: The diagnostics of the finished calculation.
    :param result: What the CP2K output says.
    """

    process: ProcessReport
    classification: str
    diagnostics: tuple[Diagnostic, ...]
    result: Cp2kResult

    @property
    def ok(self) -> bool:
        """Whether the calculation completed cleanly and converged."""
        return self.classification == "completed"

    def as_mapping(self) -> dict[str, object]:
        """Serialize the report for JSON storage.

        :return: The JSON-compatible report mapping.
        """
        return {
            "format": "httk-cp2k-run-report",
            "format_version": 1,
            "process": self.process.as_mapping(),
            "classification": self.classification,
            "diagnostics": [item.as_mapping() for item in self.diagnostics],
            "result": {**dataclasses.asdict(self.result), "errors": list(self.result.errors)},
        }

    def write(self, path: str | os.PathLike[str]) -> Path:
        """Write the report as JSON.

        :param path: Write the report to this path.
        :return: The report path.
        """
        destination = Path(path)
        write_json_atomic(destination, self.as_mapping())
        return destination


def run_cp2k(
    argv: Sequence[str],
    *,
    directory: str | os.PathLike[str] = ".",
    input_file: str = "cp2k.inp",
    output_file: str = "cp2k.out",
    timeout: float | None = None,
    launch: bool | None = None,
    termination_grace: float = 10.0,
    report_path: str | os.PathLike[str] = "cp2k-run-report.json",
) -> Cp2kRunReport:
    """Run CP2K under supervision and write a classified report.

    *argv* names the program (for example ``["cp2k.psmp"]``); ``-i INPUT_FILE -o OUTPUT_FILE`` is appended to
    it. CP2K appends to an existing output file, so one left by an earlier run
    is removed first. Standard output and standard error, normally empty or
    launcher messages, are saved beside the output with the suffixes
    ``.stdout`` and ``.err``.

    The attempt's launch prefix (the parallel start, ``HTTK_WORKFLOW_LAUNCH``) is
    prepended by default; ``launch=False`` runs *argv* as given, and a command that
    already starts with a launcher such as ``srun`` or ``mpirun`` is refused with
    :class:`ValueError` when a prefix applies.

    :param argv: The CP2K command argument vector, without the input and output options.
    :param directory: Run CP2K in this directory.
    :param input_file: The input file name in *directory*.
    :param output_file: The output file name CP2K writes in *directory*.
    :param timeout: Stop the process after this many seconds when set.
    :param launch: Prepend the attempt's launch prefix when true, the default (``None``);
        ``False`` runs *argv* as given.
    :param termination_grace: Allow this many seconds for graceful termination.
    :param report_path: Write the report at this directory-relative path.
    :return: The classified run report.
    """

    root = Path(directory).resolve()
    output = root / output_file
    output.unlink(missing_ok=True)
    # ponytail: no live monitor or remedy ladder; add them when a real campaign needs them.
    process = ProcessSupervisor().run(
        [*launch_command(argv, launch=launch is not False), "-i", input_file, "-o", output_file],
        timeout=timeout,
        cwd=root,
        termination_grace=termination_grace,
        stdout_path=output.with_suffix(".stdout"),
        stderr_path=output.with_suffix(".err"),
    )
    diagnostics = (*process.diagnostics, *diagnose_cp2k(root, output=output_file))
    codes = {item.code for item in diagnostics}
    if process.timed_out:
        classification = "timeout"
    elif "cp2k.abort" in codes:
        classification = "crashed"
    elif "cp2k.scf_not_converged" in codes:
        classification = "nonconverged"
    elif process.returncode or any(item.severity in {"error", "fatal"} for item in diagnostics):
        classification = "process_failure"
    else:
        classification = "completed"
    report = Cp2kRunReport(process, classification, diagnostics, _parse(_read(output)))
    report.write(root / report_path)
    return report
