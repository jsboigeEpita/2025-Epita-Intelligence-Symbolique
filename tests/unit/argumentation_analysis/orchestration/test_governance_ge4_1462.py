"""GE-4 #1462 — governance genuine vote aggregation tests.

Anti-théâtre contract: governance must DECIDE firsthand via a FORMAL vote
aggregation (>=3 of the 7 real methods + social-choice), NOT via an LLM-scored
ranking. Inter-method divergence is surfaced verbatim, NEVER reconciled into a
single number (cf. multi-prover FOL / I5 discipline). When the material carries
no orderable preferences (<2 args, no virtue scores), the axis is
honest-degraded (branch-OR, as SetAF on corpus A/C) — never a fake vote.

No JVM, no real LLM, synthetic opaque inputs only (privacy HARD).
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from unittest.mock import patch

import pytest

from argumentation_analysis.orchestration.invoke_callables import (
    _aggregate_governance_votes,
    _derive_governance_profile,
    _invoke_governance,
)
from argumentation_analysis.agents.core.governance.governance_agent import Agent


def _no_llm() -> Tuple[None, str]:
    """Stub for _get_openai_client: no LLM available (honest)."""
    return None, ""


# ---------------------------------------------------------------------------
# _derive_governance_profile — honest derivation
# ---------------------------------------------------------------------------


def test_derive_profile_concordant_three_electors():
    """3 args x 3 virtues -> arg_2 is the Condorcet winner (beats others on 2/3)."""
    quality = {
        "per_argument_scores": {
            "arg_1": {"scores_par_vertu": {"clarte": 9.0, "pertinence": 4.0, "structure": 3.0}},
            "arg_2": {"scores_par_vertu": {"clarte": 5.0, "pertinence": 8.0, "structure": 7.0}},
            "arg_3": {"scores_par_vertu": {"clarte": 2.0, "pertinence": 6.0, "structure": 5.0}},
        }
    }
    options, ballots, agents, derivable, reason = _derive_governance_profile(quality)
    assert derivable is True
    assert options == ["arg_1", "arg_2", "arg_3"]
    assert len(agents) == 3   # one elector per virtue
    # clarte ranks arg_1 first; pertinence + structure rank arg_2 first.
    assert ballots[0][0] == "arg_1"   # clarte elector
    assert ballots[1][0] == "arg_2"   # pertinence elector
    assert ballots[2][0] == "arg_2"   # structure elector
    assert "3 electors" in reason


def test_derive_profile_degraded_single_argument():
    """<2 evaluated arguments -> honest-degraded (no collective choice)."""
    quality = {
        "per_argument_scores": {
            "arg_1": {"scores_par_vertu": {"clarte": 9.0}},
        }
    }
    options, ballots, agents, derivable, reason = _derive_governance_profile(quality)
    assert derivable is False
    assert options == []
    assert agents == []
    assert "fewer than 2" in reason


def test_derive_profile_degraded_no_virtue_scores():
    """Per-arg results without scores_par_vertu -> honest-degraded."""
    quality = {
        "per_argument_scores": {
            "arg_1": {"note_finale": 7.0},
            "arg_2": {"note_finale": 5.0},
        }
    }
    _options, _ballots, _agents, derivable, reason = _derive_governance_profile(quality)
    assert derivable is False
    assert "no per-virtue scores" in reason


# ---------------------------------------------------------------------------
# _aggregate_governance_votes — divergence never reconciled
# ---------------------------------------------------------------------------


def test_aggregate_divergence_plurality_vs_condorcet_never_reconciled():
    """Plurality elects the Condorcet LOSER while Condorcet elects the winner:
    inter-method divergence must be surfaced verbatim (distinct_winners holds
    BOTH), never collapsed into a single number (#1019 / I5 anti-reconcile)."""
    # 7 electors: 3 rank arg_1 first (-> plurality), 4 rank arg_2 above arg_1
    # (-> arg_2 is the Condorcet winner, arg_1 the Condorcet loser).
    agents: List[Any] = [
        Agent("e1", "stubborn", ["arg_1", "arg_2", "arg_3"]),
        Agent("e2", "stubborn", ["arg_1", "arg_3", "arg_2"]),
        Agent("e3", "stubborn", ["arg_1", "arg_2", "arg_3"]),
        Agent("e4", "stubborn", ["arg_2", "arg_1", "arg_3"]),
        Agent("e5", "stubborn", ["arg_2", "arg_3", "arg_1"]),
        Agent("e6", "stubborn", ["arg_3", "arg_2", "arg_1"]),
        Agent("e7", "stubborn", ["arg_3", "arg_2", "arg_1"]),
    ]
    options = ["arg_1", "arg_2", "arg_3"]
    ballots = [list(a.preferences) for a in agents]

    verdict = _aggregate_governance_votes(agents, options, ballots)
    wpm = verdict["winners_per_method"]

    # Plurality/majority elect arg_1 (3 first-places); Condorcet elects arg_2.
    assert wpm["majority"] == "arg_1"
    assert verdict["condorcet_winner"] == "arg_2"
    # Divergence surfaced verbatim — BOTH winners present, never reconciled.
    assert verdict["inter_method_disagreement"] is True
    assert "arg_1" in verdict["distinct_winners"]
    assert "arg_2" in verdict["distinct_winners"]
    # DoD: >=3 methods decided firsthand.
    assert verdict["n_methods_decided"] >= 3


def test_aggregate_concordant_profile_single_winner():
    """UNANIMOUS profile (all electors share one ordering) -> empty divergence,
    reported honestly (NOT degraded — concordance is a genuine collective
    decision). Unanimity guarantees even the stochastic methods (byzantine with
    0 faulty agents, raft with universal acceptance) elect the same option."""
    agents = [
        Agent("e1", "stubborn", ["arg_1", "arg_2", "arg_3"]),
        Agent("e2", "stubborn", ["arg_1", "arg_2", "arg_3"]),
        Agent("e3", "stubborn", ["arg_1", "arg_2", "arg_3"]),
    ]
    options = ["arg_1", "arg_2", "arg_3"]
    ballots = [list(a.preferences) for a in agents]
    verdict = _aggregate_governance_votes(agents, options, ballots)
    assert verdict["condorcet_winner"] == "arg_1"
    assert verdict["inter_method_disagreement"] is False
    assert verdict["distinct_winners"] == ["arg_1"]
    assert verdict["n_methods_decided"] >= 3


# ---------------------------------------------------------------------------
# _invoke_governance — end-to-end handler (DoD test guard)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handler_guard_governance_decides_firsthand_condorcet():
    """DoD test guard: on a synthetic quality profile with a known Condorcet
    winner, the handler decides FIRSTHAND via formal aggregation (no LLM)."""
    quality = {
        "per_argument_scores": {
            "arg_1": {"scores_par_vertu": {"clarte": 9.0, "pertinence": 4.0, "structure": 3.0}},
            "arg_2": {"scores_par_vertu": {"clarte": 5.0, "pertinence": 8.0, "structure": 7.0}},
            "arg_3": {"scores_par_vertu": {"clarte": 2.0, "pertinence": 6.0, "structure": 5.0}},
        }
    }
    context: Dict[str, Any] = {
        "phase_extract_output": {"arguments": ["a", "b", "c"]},
        "phase_quality_output": quality,
        "_state_object": None,
    }
    with patch(
        "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
        return_value=(None, ""),
    ):
        result = await _invoke_governance("synthetic neutral text", context)

    assert result["governance_decided_firsthand"] is True
    verdict = result["governance_verdict"]
    assert verdict["degraded"] is False
    assert verdict["condorcet_winner"] == "arg_2"
    assert verdict["n_methods_decided"] >= 3
    # The LLM assessment is NOT the verdict (absent here — no LLM).
    assert "llm_governance_assessment" not in result
    assert result["extraction_method"] == "heuristic"


@pytest.mark.asyncio
async def test_handler_degraded_when_single_argument():
    """DoD: honest-degraded when <2 arguments (branch-OR, never a fake vote)."""
    quality = {
        "per_argument_scores": {
            "arg_1": {"scores_par_vertu": {"clarte": 9.0, "pertinence": 4.0}},
        }
    }
    context: Dict[str, Any] = {
        "phase_extract_output": {"arguments": ["a"]},
        "phase_quality_output": quality,
        "_state_object": None,
    }
    with patch(
        "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
        return_value=(None, ""),
    ):
        result = await _invoke_governance("synthetic neutral text", context)

    assert result["governance_decided_firsthand"] is False
    verdict = result["governance_verdict"]
    assert verdict["degraded"] is True
    assert "fewer than 2" in verdict["reason"]
