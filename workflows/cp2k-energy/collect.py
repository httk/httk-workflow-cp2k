"""Collect hook for the ``cp2k.energy`` workflow.

The run leaves ``cp2k.out`` in the persistent workdir.
"""

from httk.codes.cp2k.collect import read_total_energy


def collect(record):
    """Return the converged total energy of the run.

    :param record: The collected job record.
    :return: The ``total_energy`` output role.
    """
    return {"total_energy": read_total_energy(record.result_file("cp2k.out"))}
