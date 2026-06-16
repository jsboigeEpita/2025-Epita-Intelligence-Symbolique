"""Restitution reporting package — the readable 3-act report (Epic #1134 / R6).

Assembles the spectacular ``UnifiedAnalysisState`` into a narrative a
non-specialist can read, *replacing* the dimensional dump as the default
spectacular output. The dump survives, folded, as an engineering appendix.

See ``docs/architecture/RESTITUTION_REPORT_SPEC.md`` (R1, #1135) for the
blueprint this package implements.
"""

from .acts import ACT_TITLES, RestitutionActs
from .appendix import render_appendix
from .readability_gate import (
    GateVerdict,
    ReadabilityGate,
    ReaderCheckResult,
)
from .renderer import (
    RenderedReport,
    RestitutionReportRenderer,
    render_restitution_report,
)
from .state_adapter import state_to_appendix_mapping
from .virtuous_identification import (
    ExtractProfile,
    VirtuousCandidate,
    VirtuousInventory,
    identify,
    render_inventory_report,
)

__all__ = [
    "ACT_TITLES",
    "RestitutionActs",
    "RestitutionReportRenderer",
    "RenderedReport",
    "ReadabilityGate",
    "GateVerdict",
    "ReaderCheckResult",
    "render_appendix",
    "render_restitution_report",
    "state_to_appendix_mapping",
    # R5 volet-1 — virtuous-text candidate identification (spec §5.1)
    "ExtractProfile",
    "VirtuousCandidate",
    "VirtuousInventory",
    "identify",
    "render_inventory_report",
]
