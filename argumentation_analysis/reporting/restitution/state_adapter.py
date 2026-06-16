"""Adapt a ``UnifiedAnalysisState`` to the appendix mapping (file-disjoint wiring).

The renderer's appendix wants a plain ``dict`` (see :mod:`.appendix`). The
spectacular shared-state is a dataclass (:class:`UnifiedAnalysisState`); this
adapter reads the spec §2 keys off it via ``getattr`` with honest ``None``
defaults — it does **not** import the state class (avoids coupling the renderer
to the dataclass, and avoids touching ``shared_state.py`` which is on the R3
serialized lane). Any object exposing the named attributes works.

Privacy: this adapter never copies ``raw_text``. The appendix layer strips
leak keys defensively regardless; this adapter simply does not list them.
"""

from __future__ import annotations

from typing import Any, Dict

# The spec §2 block→state-key mapping, as attribute names. Honest default is
# "absent" (None) — the appendix renders an honest "indisponible" for any
# missing axis rather than fabricating one.
_STATE_KEYS = (
    "identified_arguments",
    "identified_fallacies",
    "counter_arguments",
    "argument_quality_scores",
    "propositional_analysis_results",
    "fol_analysis_results",
    "modal_analysis_results",
    "dung_frameworks",
    "aspic_results",
    "narrative_synthesis",
    "formal_synthesis_reports",
    "stakes_and_stakeholders",
    "source_metadata",
    "workflow_results",
)


def state_to_appendix_mapping(state: Any) -> Dict[str, Any]:
    """Read the spec §2 keys off ``state`` into a plain dict for the appendix.

    Works on a dataclass, a dict, or any object exposing the named attributes.
    Missing keys are simply omitted (the appendix reports them as "indisponible").
    """
    out: Dict[str, Any] = {}
    for key in _STATE_KEYS:
        value: Any = None
        if isinstance(state, dict):
            value = state.get(key)
        else:
            value = getattr(state, key, None)
        if value is not None:
            out[key] = value
    return out
