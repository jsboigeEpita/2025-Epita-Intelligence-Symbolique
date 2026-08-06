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
    "structured_arg_status",
    "narrative_synthesis",
    # #1620 — not a spec §2 axis of its own. The *synthesis* axis has two
    # writers: the pipeline files it under ``narrative_synthesis``, while on the
    # conversational voie the PM is instructed (``pm/prompts.py`` l.95) to copy
    # its synthèse into ``set_final_conclusion``. This projection is what the
    # appendix reader receives, so a key absent here is invisible downstream no
    # matter what the reader tries to resolve — the two-lane resolver in
    # ``appendix._provenance_counts`` was inert until this key was carried.
    # Kept under its own name rather than aliased onto ``narrative_synthesis``:
    # the opt-in full-state dump renders mapped content verbatim, and filing one
    # field's text under the other's name would misattribute it.
    "final_conclusion",
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
