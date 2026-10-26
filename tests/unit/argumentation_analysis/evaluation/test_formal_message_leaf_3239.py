# -*- coding: utf-8 -*-
"""#3239 — the formal-logic status ``message`` leaf never leaves the machine.

The last family of the frozen #1702 baseline: the ``message`` leaf on
``fol_analysis_results``, ``propositional_analysis_results`` and
``modal_analysis_results``. It is not closed vocabulary at every producer —

* PL writes two literals (``pl_handler.check_consistency``),
* FOL adds prover notes and the Mace4 interpretation
  (``fol_handler.check_consistency_by``),
* modal writes parser and JVM exception text
  (``modal_handler.is_modal_kb_consistent``),
* the SAT writer stores the backend's ``error`` string
  (``_write_sat_to_state``).

The coordinator measured 0/0/2 argument-text matches on 80 stored states (2
on modal), so the leaf cannot be declared closed vocabulary. No export reader
reads it either: the axis readers consume ``consistent`` / ``satisfiable`` /
``valid`` and counts, and ``pattern_mining`` reads ``valid``. The tri-state
verdict already attests degradation honestly.

Decision (the #3229 / #3217 gesture on the status axis): drop the leaf, keep
the record. This witness is born red on the pre-#3239 scrubber — all three
leaves survive ``sanitize_state`` verbatim — and the substitution control
below proves the drop comes from the named table entry, not from a catch-all.
"""

from __future__ import annotations

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.evaluation import sanitize_state as _sanitize_mod
from argumentation_analysis.evaluation.sanitize_state import sanitize_state

CANARY = (
    "CANARY_3239 the speaker argues that the proposed measure should be "
    "withdrawn because its cost was never made public"
)

AXES = (
    "fol_analysis_results",
    "propositional_analysis_results",
    "modal_analysis_results",
)


def _canaried_state() -> UnifiedAnalysisState:
    state = UnifiedAnalysisState("initial text")
    state.add_fol_analysis_result(["P(a)"], None, [], 0.0, message=CANARY)
    state.add_propositional_analysis_result(
        ["p ∨ ¬p"], None, {"p": True}, message=CANARY
    )
    state.add_modal_analysis_result(["□p"], None, ["necessity"], message=CANARY)
    return state


def test_the_status_message_leaf_is_dropped_from_all_three_axes() -> None:
    out = sanitize_state(_canaried_state().get_state_snapshot())

    # The measurement comes first: every axis must have produced a record, or
    # the absence assertions below would pass on an empty container.
    for field in AXES:
        assert len(out[field]) == 1, (field, out[field])
        assert "message" not in out[field][0], (field, out[field][0])
        assert CANARY not in repr(out[field]), field

    # The record and its honest tri-state verdict survive the leaf drop.
    assert out["fol_analysis_results"][0]["consistent"] is None
    assert out["fol_analysis_results"][0]["formulas"] == ["P(a)"]
    assert out["propositional_analysis_results"][0]["satisfiable"] is None
    assert out["propositional_analysis_results"][0]["formulas"] == ["p ∨ ¬p"]
    assert out["modal_analysis_results"][0]["valid"] is None
    assert out["modal_analysis_results"][0]["modalities"] == ["necessity"]


def test_the_drop_is_the_named_table_entry(monkeypatch) -> None:
    """Substitution control: remove the three entries and the leaf returns.

    A guard that stays green under table surgery would prove nothing; this one
    names the mechanism that does the work.
    """
    tables = dict(_sanitize_mod._TEXT_STRIP_LISTS)
    for field in AXES:
        tables[field] = set(tables[field]) - {"message"}
    monkeypatch.setattr(_sanitize_mod, "_TEXT_STRIP_LISTS", tables)

    out = sanitize_state(_canaried_state().get_state_snapshot())

    for field in AXES:
        assert out[field][0]["message"] == CANARY, field
