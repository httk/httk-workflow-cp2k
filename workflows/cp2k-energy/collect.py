"""Collect hook for the ``cp2k.energy`` workflow."""

from httk.codes.cp2k import collect_cp2k


def collect(record):
    """Extract the converged total energy from the job record.

    :param record: The collected job record.
    :return: The ``total_energy`` output role.
    """
    return collect_cp2k(record)
