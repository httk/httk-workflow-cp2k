"""Collect hook for the ``cp2k.calculation`` collector.

The directory holds one CP2K output, found by its header, whatever its name.
"""

from httk.workflow.collecting import JobRecord

from httk.codes.cp2k.collect import find_outputs, read_total_energy


def collect(record: JobRecord):
    """Return the converged total energy of the calculation.

    :param record: The stand-in job record of the directory.
    :return: The ``total_energy`` output role.
    """
    if record.workdir is None:
        raise ValueError("the job has no working directory")
    (output,) = find_outputs(record.workdir)
    return {"total_energy": read_total_energy(output)}
