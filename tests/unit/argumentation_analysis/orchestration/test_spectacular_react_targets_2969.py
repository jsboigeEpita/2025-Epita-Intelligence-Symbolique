# -*- coding: utf-8 -*-
"""#2969 — Functional witnesses: reacts_to says what the run consumed, the
governance record keeps its populations apart, the Acts present divergence.

* quality: a hierarchical_fallacy output targeting one unit makes that unit
  carry the #289 fallacy_penalty (positive control of the consumption path —
  on the real run this read came back empty because the producer ran in the
  same level, so 0/8 units were penalized);
* governance: a vote whose methods diverge keeps ALL distinct winners in the
  state record (winner_provenance="vote_aggregate"), the LLM's stakeholder
  influences live in their own field, and the Acts II/III readers carry the
  winners so the narrative presents the divergence instead of erasing it
  behind a single winner (measured on doc_A: arg_16/arg_23 distinct winners,
  the record kept one).

reacts_to witnesses: the trace names the producers whose payloads were
actually there, and names the empty ones in the summary — never the static
literal that claimed reactions which did not happen.
"""

import asyncio
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.invoke_callables import (
    _invoke_governance,
    _invoke_quality_evaluator,
)
from argumentation_analysis.orchestration.state_writers import (
    _write_governance_to_state,
)
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    _collect_governance as _collect_governance_act2,
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    _collect_governance as _collect_governance_act3,
    build_act3_evidence,
    build_act3_prompt,
)

SOURCE = (
    "Le rapport affirme que la réforme a réduit le chômage de deux points. "
    "Cependant, les économistes cités contestent la méthode de calcul, car "
    "l'enquête exclut les demandeurs d'emploi en formation. Enfin, l'auteur "
    "conclut que le débat reste ouvert."
)

UNIT_1 = {
    "unit_id": "arg_1",
    "text": "La réforme a réduit le chômage de deux points, selon le rapport.",
    "source_quote": "la réforme a réduit le chômage",
}
UNIT_2 = {
    "unit_id": "arg_2",
    "text": "Les économistes contestent la méthode de calcul de l'enquête.",
    "source_quote": "contestent la méthode de calcul",
}


class _TraceRecorder:
    """Minimal state stand-in that records add_trace_entry calls."""

    def __init__(self) -> None:
        self.entries: List[Dict[str, Any]] = []

    def add_trace_entry(self, **kwargs: Any) -> None:
        self.entries.append(kwargs)


def _no_enrichment(*_a: Any, **_k: Any) -> None:
    return None


class TestQualityPenaltyConsumed:
    """#2969 — the #289 penalty applies when the fallacy output is THERE."""

    @staticmethod
    def _run(state: Any, fallacies: List[Dict[str, Any]]) -> Dict[str, Any]:
        context = {
            "phase_extract_output": {"arguments": [dict(UNIT_1), dict(UNIT_2)]},
            "phase_hierarchical_fallacy_output": {"fallacies": fallacies},
            "_state_object": state,
        }
        # Same hermetic pair as test_quality_passage_2403._run: the agentic
        # virtue detectors take their no-route branch and the enrichment
        # pass is inert — the gate demands zero egress per run (#2444).
        with patch(
            "argumentation_analysis.orchestration.invoke_callables"
            "._make_agentic_llm_callable",
            return_value=(None, "no_route", ""),
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables"
            "._llm_enrich_quality",
            side_effect=_no_enrichment,
        ):
            return asyncio.run(_invoke_quality_evaluator(SOURCE, context))

    def test_targeted_unit_carries_fallacy_penalty(self) -> None:
        output = self._run(
            None,
            [{"type": "appels_a_l_autorite", "target_argument": "arg_2"}],
        )
        scores = output["per_argument_scores"]
        assert "arg_2" in scores, "the targeted unit must be evaluated"
        penalty = scores["arg_2"].get("fallacy_penalty", {})
        assert penalty.get("applied") is True, (
            "a hierarchical_fallacy output naming arg_2 must lower its score "
            "(#289) — on the real run this read came back empty because the "
            "producer ran in the same level (0/8 units penalized on doc_A)"
        )
        assert penalty.get("fallacies") == ["appels_a_l_autorite"]
        assert penalty.get("penalty_factor", 0) > 0
        assert "fallacy_penalty" not in scores.get(
            "arg_1", {}
        ), "the untargeted unit carries no penalty"

    def test_trace_reacts_to_names_what_was_consumed(self) -> None:
        state = _TraceRecorder()
        self._run(state, [{"type": "appels_a_l_autorite", "target_argument": "arg_2"}])
        entry = next(e for e in state.entries if e.get("phase") == "quality")
        assert entry["reacts_to"] == ["extract", "hierarchical_fallacy"]

    def test_trace_names_the_empty_input(self) -> None:
        """No fallacy output in context → the trace says the input was empty
        instead of claiming a reaction that did not happen."""
        state = _TraceRecorder()
        output = self._run(state, [])
        entry = next(e for e in state.entries if e.get("phase") == "quality")
        assert entry["reacts_to"] == ["extract"]
        assert "hierarchical_fallacy" in entry["summary"], entry["summary"]
        assert output["per_argument_scores"], "units still evaluated"


class _GovernanceStateRecorder:
    """Minimal state stand-in for the governance writer."""

    def __init__(self) -> None:
        self.decisions: List[Dict[str, Any]] = []

    def add_governance_decision(self, **kwargs: Any) -> str:
        self.decisions.append(kwargs)
        return f"gov_{len(self.decisions)}"


class TestGovernancePopulationsApart:
    """#2969 Expected 4 — the record keeps its populations apart."""

    @staticmethod
    def _writer_output() -> Dict[str, Any]:
        return {
            "recommended_method": "condorcet",
            "vote_result": {
                "winner": "arg_16",
                "votes": {"arg_16": 4, "arg_23": 3},
                "method": "formal-aggregation",
                "copeland_scores": {"arg_16": 1.0, "arg_23": 0.5, "arg_40": -1.0},
                "results": {
                    "distinct_winners": ["arg_16", "arg_23"],
                    "inter_method_disagreement": True,
                    "winners_per_method": {
                        "majority": "arg_16",
                        "borda": "arg_23",
                    },
                },
            },
            "conflicts": [{"agents": ["agent_1", "agent_2"], "level": 0.8}],
            "extraction_method": "heuristic",
            "llm_governance_assessment": {
                "stakeholder_analysis": [
                    {"agent": "parti_A", "influence": 0.7},
                    {"agent": "parti_B", "influence": 0.4},
                ],
                "recommended_resolution": "arg_16",
            },
        }

    def test_divergent_vote_keeps_every_distinct_winner(self) -> None:
        state = _GovernanceStateRecorder()
        _write_governance_to_state(
            self._writer_output(), state, {"phase": "governance"}
        )
        assert len(state.decisions) == 1
        record = state.decisions[0]
        assert record["winners"] == ["arg_16", "arg_23"], (
            "two methods named distinct winners — the record must carry BOTH, "
            "not the one the field ``winner`` kept"
        )
        assert record["winner"] == "arg_16"
        assert record["winner_provenance"] == "vote_aggregate"
        assert record["method_provenance"] == "llm_recommendation"

    def test_scores_and_stakeholder_scores_are_separate_populations(self) -> None:
        state = _GovernanceStateRecorder()
        _write_governance_to_state(
            self._writer_output(), state, {"phase": "governance"}
        )
        record = state.decisions[0]
        assert set(record["scores"]) == {"arg_16", "arg_23", "arg_40"}, (
            "scores carries the VOTE's option scores only (Copeland), "
            f"measured: {record['scores']}"
        )
        assert record["stakeholder_scores"] == {"parti_A": 0.7, "parti_B": 0.4}, (
            "the LLM's stakeholder influences are labels, not units — they "
            "must not share the vote's field"
        )

    def test_real_state_stores_the_new_fields(self) -> None:
        """End-to-end through UnifiedAnalysisState.add_governance_decision:
        optional fields stored only when set (honest absence)."""
        state = UnifiedAnalysisState("2969 synthetic probe")
        gd_id = state.add_governance_decision(
            "condorcet",
            "arg_16",
            {"arg_16": 1.0, "arg_23": 0.5},
            extraction_method="heuristic",
            winners=["arg_16", "arg_23"],
            stakeholder_scores={"parti_A": 0.7},
            winner_provenance="vote_aggregate",
            method_provenance="llm_recommendation",
        )
        entry = next(d for d in state.governance_decisions if d["id"] == gd_id)
        assert entry["winners"] == ["arg_16", "arg_23"]
        assert entry["stakeholder_scores"] == {"parti_A": 0.7}
        assert entry["winner_provenance"] == "vote_aggregate"
        # honest absence: a plain call adds none of the optional fields
        plain_id = state.add_governance_decision("majority", "arg_1", {"arg_1": 1.0})
        plain = next(d for d in state.governance_decisions if d["id"] == plain_id)
        for absent in ("winners", "stakeholder_scores", "winner_provenance"):
            assert absent not in plain

    def test_governance_trace_reacts_to_names_consumed_only(self) -> None:
        """The governance trace names the axes whose payloads were there —
        on the real run the literal claimed jtms while jtms ran one level
        later and had not written."""
        state = _TraceRecorder()
        context: Dict[str, Any] = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "Première position synthétique sur le budget."},
                    {"text": "Seconde position détaillée sur la fiscalité."},
                ]
            },
            "phase_quality_output": {"per_argument_scores": {"arg_1": {}}},
            "phase_counter_output": {
                "llm_counter_arguments": [{"counter_argument": "c"}]
            },
            "phase_debate_output": {"llm_debate_assessment": {"winner": "arg_1"}},
            "phase_jtms_output": {"beliefs": [{"name": "b1"}]},
            "_state_object": state,
        }
        with patch(
            "argumentation_analysis.orchestration.invoke_callables"
            "._get_openai_client",
            return_value=(None, ""),
        ):
            asyncio.run(_invoke_governance("synthetic neutral text", context))
        entry = next(e for e in state.entries if e.get("phase") == "governance")
        for consumed in ("extract", "counter", "debate", "quality", "jtms"):
            assert consumed in entry["reacts_to"], (
                f"the run consumed {consumed} — the trace must say so: "
                f"{entry['reacts_to']}"
            )
        assert (
            "hierarchical_fallacy" not in entry["reacts_to"]
        ), "no fallacy payload in context — the trace must not claim it"

    def test_positions_carry_unit_text_not_dict_repr(self) -> None:
        """str(dict) of an extract record is a repr — the conflict detector
        read that repr and all conflicts degenerated at level 1.0."""
        state = _TraceRecorder()
        context: Dict[str, Any] = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "Première position synthétique sur le budget."},
                    {"text": "Seconde position détaillée sur la fiscalité."},
                ]
            },
            "_state_object": state,
        }
        with patch(
            "argumentation_analysis.orchestration.invoke_callables"
            "._get_openai_client",
            return_value=(None, ""),
        ):
            result = asyncio.run(_invoke_governance("synthetic neutral text", context))
        positions = result.get("positions") or {}
        assert positions, "positions must exist for a two-argument context"
        for value in positions.values():
            assert (
                "{" not in value
            ), f"a position must be the unit's text, not a dict repr: {value!r}"


def _divergent_state() -> UnifiedAnalysisState:
    state = UnifiedAnalysisState("2969 synthetic probe")
    state.governance_decisions.append(
        {
            "method": "condorcet",
            "winner": "arg_16",
            "scores": {"arg_16": 1.0, "arg_23": 0.5},
            "extraction_method": "heuristic",
            "winners": ["arg_16", "arg_23"],
            "winner_provenance": "vote_aggregate",
        }
    )
    return state


class TestActsPresentDivergence:
    """#2969 Expected 4 — Acts II/III carry the divergence to the reader."""

    def test_act2_collector_carries_every_winner(self) -> None:
        gv = _collect_governance_act2(_divergent_state())
        assert gv is not None
        assert gv.winners == ["arg_16", "arg_23"]
        assert gv.winner == "arg_16"

    def test_act3_collector_carries_every_winner(self) -> None:
        gv = _collect_governance_act3(_divergent_state())
        assert gv is not None
        assert gv.winners == ["arg_16", "arg_23"]
        assert gv.winner == "arg_16"

    def test_act2_prompt_presents_the_divergence(self) -> None:
        state = _divergent_state()
        prompt = build_act2_prompt(build_act2_evidence(state))
        assert "DIVERGE" in prompt, (
            "two methods named distinct winners — the narrative prompt must "
            "say the vote diverges, not present one leading argument"
        )
        assert "arg_16" in prompt and "arg_23" in prompt

    def test_act3_prompt_presents_the_divergence(self) -> None:
        state = _divergent_state()
        prompt = build_act3_prompt(build_act3_evidence(state))
        assert "DIVERGE" in prompt, (
            "the conclusion prompt must say the vote diverges instead of "
            "reducing it to a single winner"
        )
        assert "arg_16" in prompt and "arg_23" in prompt

    def test_undiverged_vote_adds_no_divergence_line(self) -> None:
        """Positive control the other way: one winner → no DIVERGE sentence
        (the line is earned by the record, not unconditional)."""
        state = UnifiedAnalysisState("2969 synthetic probe")
        state.governance_decisions.append(
            {"method": "condorcet", "winner": "arg_16", "scores": {"arg_16": 1.0}}
        )
        assert "DIVERGE" not in build_act2_prompt(build_act2_evidence(state))
