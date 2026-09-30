"""Register the CP2K code support implemented by :mod:`httk.codes.cp2k`."""

from httk.core.register import register_code, register_collector

register_code("cp2k", bridge="httk.codes.cp2k._bridge", bash_api="httk.codes.cp2k:httk-cp2k.sh")
register_collector("cp2k.calculation", package="httk.codes.cp2k:collectors/cp2k")
