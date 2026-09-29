"""The ``cp2k`` code is registered through the ``codes`` registry tier, with its citation."""

import argparse
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import httk.core  # noqa: F401  (importing httk.core runs registry discovery)
from httk.core.register import code_support, known_codes


def test_cp2k_is_a_known_code_with_its_packaged_bash_api() -> None:
    assert "cp2k" in known_codes()
    assert code_support("cp2k").bash_api_path() == Path(str(files("httk.codes.cp2k").joinpath("httk-cp2k.sh")))


def test_the_bridge_mounts_the_cp2k_commands() -> None:
    parser = argparse.ArgumentParser()
    code_support("cp2k").resolve_bridge().add_commands(parser.add_subparsers(dest="command"))
    assert parser.parse_args(["cp2k-energy"]).command == "cp2k-energy"


def test_the_cp2k_credit_is_registered_on_import() -> None:
    script = """
from httk.core import credits
assert "Calculations with CP2K" not in credits.entries()
import httk.codes.cp2k
assert len(credits.entries()["Calculations with CP2K"]) == 1
"""
    subprocess.run([sys.executable, "-c", script], check=True)
