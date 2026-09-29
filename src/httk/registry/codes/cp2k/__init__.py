"""Register the CP2K code support implemented by :mod:`httk.codes.cp2k`."""

from httk.core.register import register_code

register_code("cp2k", bridge="httk.codes.cp2k._bridge", bash_api="httk.codes.cp2k:httk-cp2k.sh")
