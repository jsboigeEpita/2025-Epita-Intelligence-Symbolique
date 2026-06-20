"""FP-10 #1208 — PL verdict persists into the state snapshot (persistence contract).

The PL/PySAT handler decided correctly (real sat/unsat + model), but the
invoke-callable fabricated a placeholder model ``{p1: True, p2: True}`` and the
summarized state snapshot exposed only a counter — dropping the real solver
witness before it reached ``UnifiedAnalysisState`` (same failure class as a
buried solver, #1019). The FP-5 matrix therefore classed PL ``absent`` even on
corpora where PySAT decided.

These tests pin the persistence contract (#1208 DoD): the real PySAT model +
verdict + axiom/query counts must land in the state snapshot. They run without
a JVM — the contract is the state plumbing, not the solver binary.
"""

import pytest


def test_state_writer_persists_real_model_not_placeholder():
    """The PL state writer must forward the real PySAT model + counts.

    #1208: before the fix, ``_invoke_propositional_logic`` returned a
    fabricated ``{p1: True, ...}`` model regardless of the solver result. The
    state writer then persisted that fake witness, so a real UNSAT could be
    recorded with a "model" attached. The writer must now persist the genuine
    model + axiom/query counts the handler produced.
    """
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState
    from argumentation_analysis.orchestration.state_writers import (
        _write_propositional_to_state,
    )

    state = UnifiedAnalysisState("test")
    output = {
        "formulas": ["is_mortal && foreign_threat"],
        "satisfiable": True,
        "model": {"is_mortal": True, "foreign_threat": True},
        "axiom_count": 2,
        "query_count": 0,
        "message": "Consistent (SAT). Model: {...}",
        "logic_type": "propositional",
    }
    _write_propositional_to_state(output, state, {})

    assert len(state.propositional_analysis_results) == 1
    entry = state.propositional_analysis_results[0]
    # The real named model must be preserved — NOT a {p1: True} placeholder.
    assert entry["model"] == {"is_mortal": True, "foreign_threat": True}
    assert entry["satisfiable"] is True
    assert entry["axiom_count"] == 2
    assert entry["query_count"] == 0
    assert entry["message"].startswith("Consistent (SAT)")


def test_state_writer_persists_unsat_with_empty_model():
    """An UNSAT verdict must persist an empty model, never a fabricated witness.

    #1208/#1019: the old code attached ``{p1: True}`` even to inconsistent KBs
    (it derived the placeholder from ``len(args)``, not the solver). An UNSAT
    result must carry an empty model so the witness is honest.
    """
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState
    from argumentation_analysis.orchestration.state_writers import (
        _write_propositional_to_state,
    )

    state = UnifiedAnalysisState("test")
    output = {
        "formulas": ["claim", "!claim"],
        "satisfiable": False,
        "model": {},  # UNSAT — no model
        "axiom_count": 2,
        "query_count": 0,
        "message": "Inconsistent (UNSAT).",
    }
    _write_propositional_to_state(output, state, {})

    entry = state.propositional_analysis_results[0]
    assert entry["satisfiable"] is False
    assert entry["model"] == {}


def test_summarized_snapshot_exposes_pl_results_not_just_count():
    """``get_state_snapshot(summarize=True)`` must expose the real PL entries.

    #1208: the summarized snapshot only exposed ``propositional_analysis_count``
    (an integer), hiding whether the persisted verdict was real or a fabricated
    placeholder. The state IS the contract — surfacing the list (which already
    lives in the state object) subtracts the masking; it does not add a
    counterweight.
    """
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState

    state = UnifiedAnalysisState("test")
    state.add_propositional_analysis_result(
        ["a && b"], True, {"a": True, "b": True}, axiom_count=1, query_count=0
    )
    snap = state.get_state_snapshot(summarize=True)

    # Count is still there (backward compat).
    assert snap["propositional_analysis_count"] == 1
    # The real entries are now exposed — not just the counter.
    results = snap["propositional_analysis_results"]
    assert len(results) == 1
    assert results[0]["satisfiable"] is True
    assert results[0]["model"] == {"a": True, "b": True}


@pytest.mark.jpype
def test_check_consistency_detailed_returns_real_pysat_model():
    """PLHandler.check_consistency_detailed returns the genuine SAT model.

    #1208: the wired PL path must return ``(is_consistent, named_model, msg)``
    where ``named_model`` is the real PySAT assignment (not None, not a
    fabricated ``{p1}`` dict). Requires a JVM (TweetyBridge construction) and
    PySAT.
    """
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import (
            TweetyBridge,
        )
        from argumentation_analysis.agents.core.logic.sat_handler import (
            PYSAT_AVAILABLE,
        )
    except ImportError:
        pytest.skip("TweetyBridge / sat_handler not importable")
    if not PYSAT_AVAILABLE:
        pytest.skip("PySAT not installed")

    bridge = TweetyBridge()
    # SAT: a && b, a => c  (model must assign a, b, c)
    is_c, model, _msg = bridge.check_consistency_detailed(
        "alpha && beta\nalpha => gamma", "propositional"
    )
    assert is_c is True
    assert isinstance(model, dict)
    assert model.get("alpha") is True
    assert model.get("beta") is True

    # UNSAT: claim, !claim
    is_c2, model2, _msg2 = bridge.check_consistency_detailed(
        "claim\n!claim", "propositional"
    )
    assert is_c2 is False
    assert not model2  # None or empty — never a fabricated witness
