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

## The nested twin (coordinator R1115 measurement, extended here)

Dropping the container's own ``message`` did not finish the surface. The
external-solver re-check attaches a SECOND, deeper NL leaf —
``external_checks[*].message`` (``_attach_external_recheck``,
state_writers.py:2921-2928) — that the flat table cannot read. On the stored
corpus the twin is never the same string as the top-level leaf (this seat:
28 FOL + 28 modal nested twins, **0 identical**), so the outer drop scrubs
none of it. The coordinator replayed 84 states on ai-01 and measured 410 → 42
survivors: the 42 are exactly this nested twin (22 FOL + 20 modal).

The same verdict applies one level down — drop the leaf, keep the record —
and the tests below carry the nested canary themselves. That is deliberate:
the #1702 guard's oracle plants the top-level leaf only, so the nested shape
is outside its reach (named in the PR, and the guard's plant list is extended
in this same change so the frozen baseline sees it).
"""

from __future__ import annotations

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.evaluation import sanitize_state as _sanitize_mod
from argumentation_analysis.evaluation.sanitize_state import sanitize_state
from argumentation_analysis.orchestration.state_writers import (
    _write_external_fol_solver_to_state,
    _write_external_modal_solver_to_state,
)

CANARY = (
    "CANARY_3239 the speaker argues that the proposed measure should be "
    "withdrawn because its cost was never made public"
)

# A distinct string on purpose: the measured corpus never carries the same text
# in both slots (0 identical / 42 on ai-01, 0 identical / 56 on this seat), so a
# witness that reused one canary could not tell which leaf a survivor came from.
NESTED_CANARY = (
    "CANARY_3239b the prover notes that the theory was reduced to a single "
    "clause before the contradiction surfaced"
)

AXES = (
    "fol_analysis_results",
    "propositional_analysis_results",
    "modal_analysis_results",
)

# The two containers that grow ``external_checks`` (the only callers of
# ``_attach_external_recheck``; the PL leg has no external re-check writer).
NESTED_AXES = ("fol_analysis_results", "modal_analysis_results")


def _canaried_state() -> UnifiedAnalysisState:
    state = UnifiedAnalysisState("initial text")
    state.add_fol_analysis_result(["P(a)"], None, [], 0.0, message=CANARY)
    state.add_propositional_analysis_result(
        ["p ∨ ¬p"], None, {"p": True}, message=CANARY
    )
    state.add_modal_analysis_result(["□p"], None, ["necessity"], message=CANARY)
    return state


def _nested_canaried_state() -> UnifiedAnalysisState:
    """Both nested axes through the REAL external-solver producers.

    ``_attach_external_recheck`` only attaches when the formula list matches an
    entry already present, so each entry is added first and the external writer
    then re-checks THE SAME theory — the nested route, not the append one.
    """
    state = UnifiedAnalysisState("initial text")
    state.add_fol_analysis_result(["P(a)"], True, [], 0.0)
    state.add_modal_analysis_result(["□p"], True, ["necessity"])
    _write_external_fol_solver_to_state(
        {
            "formulas": ["P(a)"],
            "solver": "eprover",
            "consistent": False,
            "message": NESTED_CANARY,
        },
        state,
        {},
    )
    _write_external_modal_solver_to_state(
        {
            "formulas": ["□p"],
            "solver": "vampire",
            "valid": False,
            "message": NESTED_CANARY,
        },
        state,
        {},
    )
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


def test_the_nested_recheck_message_is_dropped_from_both_axes() -> None:
    """``external_checks[*].message`` leaves; the re-check record stays whole."""
    raw = _nested_canaried_state().get_state_snapshot()

    # The measurement comes first: prove the plant really landed on the nested
    # path, or the absence assertions below would pass on a shape never built.
    for field in NESTED_AXES:
        assert len(raw[field]) == 1, (field, raw[field])
        checks = raw[field][0]["external_checks"]
        assert len(checks) == 1, (field, checks)
        assert NESTED_CANARY in checks[0]["message"], (field, checks[0])

    out = sanitize_state(raw)

    for field in NESTED_AXES:
        assert len(out[field]) == 1, (field, out[field])
        checks = out[field][0]["external_checks"]
        # Arity survives: the re-check is still a record, one leaf lighter.
        assert len(checks) == 1, (field, checks)
        assert "message" not in checks[0], (field, checks[0])
        assert NESTED_CANARY not in repr(out[field]), field
        # What a reader weighs is still there.
        assert checks[0]["solver"] in {"eprover", "vampire"}, (field, checks[0])
        assert checks[0]["agrees"] is False, (field, checks[0])

    assert out["fol_analysis_results"][0]["external_checks"][0]["consistent"] is False
    assert out["modal_analysis_results"][0]["external_checks"][0]["valid"] is False
    # The verdict the re-check displaced travels with its source, not erased.
    assert out["fol_analysis_results"][0]["superseded_verdict"]["consistent"] is True
    assert out["fol_analysis_results"][0]["consistent"] is False
    assert out["modal_analysis_results"][0]["valid"] is False


def test_the_nested_drop_is_the_named_table_entry(monkeypatch) -> None:
    """Substitution control on the nested table: empty it and the leaf returns.

    Scoped to the nested table alone — the outer ``message`` entries stay, so a
    survivor here can only come from the deep leaf the new pass governs.
    """
    monkeypatch.setattr(_sanitize_mod, "_NESTED_TEXT_STRIP_SUBKEYS", {})

    out = sanitize_state(_nested_canaried_state().get_state_snapshot())

    for field in NESTED_AXES:
        checks = out[field][0]["external_checks"]
        assert NESTED_CANARY in checks[0]["message"], (field, checks[0])
