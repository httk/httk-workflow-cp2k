"""Extract workflow outputs from a collected CP2K job."""

from httk.core import DataRecord
from httk.workflow.collecting import JobRecord

from .outputs import parse_cp2k_output

__all__ = ["collect_cp2k"]

_TOTAL_ENERGY_DEFINITION = "https://schemas.httk.org/defs/v0.1/properties/core/total_energy"
_TOTAL_ENERGY_NAME = "_httk_total_energy"


def collect_cp2k(record: JobRecord, *, output: str = "cp2k.out") -> dict[str, object]:
    """Extract the converged total energy, in eV, of one CP2K job.

    The output is read from the job's published data when it has any, else
    from its persistent workdir.

    :param record: The collected job record.
    :param output: The CP2K output file name.
    :return: The ``total_energy`` output role.
    :raises ValueError: If the output is missing or holds no converged total energy.
    """

    root = record.data if record.data is not None else record.workdir
    identity = f"{record.workspace_id}:{record.job_id}"
    if root is None or not (root / output).is_file():
        raise ValueError(f"{identity}: expected the CP2K output {output!r}, but the job has none")
    energy = parse_cp2k_output(root / output).total_energy_ev
    if energy is None:
        raise ValueError(f"{identity}: {root / output} holds no converged total energy")
    return {"total_energy": DataRecord.from_value(_TOTAL_ENERGY_DEFINITION, _TOTAL_ENERGY_NAME, energy)}
