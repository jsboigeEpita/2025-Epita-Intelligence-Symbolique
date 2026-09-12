"""Synthesis package.

The synthesis surface is ``DeepSynthesisAgent``: the 9-section
template-driven, state-grounded report (FB-18, Tracks DD/GG/NN). The
former eponymous ``SynthesisAgent`` was removed (#2140): its two agent
fabriques could never succeed in production (no writer ever populated
their caches) and its ``except`` blocks wrote the exception text into
result fields — a failure traveling as data (#1019).
"""

from .deep_synthesis_agent import DeepSynthesisAgent
from .deep_synthesis_models import DeepSynthesisReport

__all__ = [
    "DeepSynthesisAgent",
    "DeepSynthesisReport",
]
