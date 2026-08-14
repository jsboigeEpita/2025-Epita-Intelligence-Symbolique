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
    # #1646 — belief revision reaches the Acte III conclusion: the minimal-
    # retraction insight is NAMED by ``_belief_revision_finding`` (act3). The
    # appendix attests the axis so a report whose conclusion rests on "the one
    # belief to give up" carries that provenance in its own coverage table.
    # Mirrors the #1667 carry of ``bipolar_results`` when that axis reached prose.
    "belief_revision_results",
    # #1624 — three axes the PROSE mobilises that the appendix could not attest
    # at all, not even as "indisponible": a report whose conclusion rests on the
    # deliberation, on the governance vote and on the bipolar support relation
    # carried no trace of any of them in its own coverage table. Carried here so
    # the table can name them; the omission was the asymmetry, not a choice.
    # ``bipolar_results`` reached the prose in #1667 (act3 presence channel) and
    # was flagged there as owed to this issue.
    "bipolar_results",
    "debate_transcripts",
    "governance_decisions",
    # Deliberately NOT carried: ``deanonymized``. The prose reads it in all three
    # acts, so it is on the prose surface — but it is a rendering *flag* (are
    # entity names shown in clear?), not an analytical dimension. The appendix
    # table attests what backs the narrative; a boolean about how names are
    # printed has no "disponible / mobilisée" reading. Its absence from this
    # tuple is the justification required by #1624 item 3, recorded at the site.
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
    # #1676 — decision at this site. The three keys below are carried here so
    # the opt-in full-state dump stays their traceability; only one gets an
    # annexe row. ``stakes_and_stakeholders`` is attested (the ``enjeux`` row,
    # by cardinality) because the Acte I framing mobilises it and a live writer
    # fills it (``invoke_callables._invoke_stakes_extractor``, measured
    # populated on real runs, #1604 R751).
    "stakes_and_stakeholders",
    # #1676 privacy decision (HARD): NO annexe row. The values are nominative
    # (``{genre, speaker_role, channel, title, ...}`` — a title is a source name
    # per CLAUDE.md privacy), and a count of metadata fields informs nobody.
    # The prose reads it for the Acte I framing; its values are opacified on the
    # export boundary (``sanitize_state._OPAQUE_DICT_VALUES``), and carrying the
    # key here keeps the opt-in dump traceable without surfacing content.
    "source_metadata",
    # #1676 decision: NO annexe row. Distinct case — neither the prose nor any
    # annexe line reads it: a generic bag of phase/workflow results (and
    # value-gate ledgers) with no informative count. Other surfaces read it
    # (html_report durations, multi_format_exporter), the restitution does not.
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
