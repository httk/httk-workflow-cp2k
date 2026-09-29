"""CP2K support for *httk₂* workflows: the *httk-workflow-cp2k* package.

``inputs`` writes CP2K Quickstep inputs, ``outputs`` parses its text output,
``diagnostics`` classifies a finished calculation, ``reports`` runs it under
supervision, and ``collect`` turns a finished job into workflow outputs. This
package is a thin facade re-exporting their surface. The example workflow
package ``workflows/cp2k-energy`` in this distribution's repository builds on it.
"""

from httk.core import register_citation

register_citation(
    applies_to="Calculations with CP2K",
    references=(
        {
            "authors": ({"name": "Thomas D. Kühne"},),
            "note": "Kühne et al.; the DOI record lists every author",
            "title": (
                "CP2K: An electronic structure and molecular dynamics software package - "
                "Quickstep: Efficient and accurate electronic structure calculations"
            ),
            "journal": "The Journal of Chemical Physics",
            "volume": "152",
            "pages": "194103",
            "year": "2020",
            "doi": "10.1063/5.0007045",
            "bib_type": "article",
        },
    ),
)

from .collect import collect_cp2k
from .diagnostics import diagnose_cp2k
from .inputs import write_cp2k_input
from .outputs import HA_TO_EV, Cp2kResult, parse_cp2k_output
from .reports import Cp2kRunReport, run_cp2k

__all__ = [
    "HA_TO_EV",
    "Cp2kResult",
    "Cp2kRunReport",
    "collect_cp2k",
    "diagnose_cp2k",
    "parse_cp2k_output",
    "run_cp2k",
    "write_cp2k_input",
]
