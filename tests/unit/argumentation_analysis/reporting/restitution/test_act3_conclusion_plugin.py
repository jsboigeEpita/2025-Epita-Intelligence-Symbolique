"""Tests for the Acte III generator — actionable conclusion (R4 #1138).

Pins the spec §1.3 contract (gated verdict + balanced appréciations + que-faire)
and the §4 weaving contract (LLM-conducted conclusion passes the readability
gate; enumeration does not). The verdict band is computed from the real
analytical coverage (adapted from #1008 §2) — EXCEEDED/MATCH/PARTIAL/BELOW
govern how strongly the discourse may be characterised.

The G1–G4 non-triviality gates (#1008 §3) gate the synthesis beat: on any gate
failure the conclusion degrades honestly (no fabricated verdict).

All deterministic — no JVM, no LLM service, no network: the LLM is an injectable
async stub and the state is a ``SimpleNamespace`` (the plugin reads attributes
via ``getattr``).

Privacy HARD is asserted: corpus-derived fields are truncated before entering
the prompt, and the prompt carries the opaque-ID directive.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import List

import pytest

from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    Act3Result,
    build_act3_conclusion,
    build_act3_evidence,
    build_act3_prompt,
    weave_act3_conclusion,
)
from argumentation_analysis.reporting.restitution.readability_gate import (
    ReadabilityGate,
)


# --- state stubs -------------------------------------------------------------


def _state(**fields: object) -> SimpleNamespace:
    """Build a lightweight state stub with the Acte III-relevant fields."""
    base = dict(
        identified_arguments={},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks={},
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        narrative_synthesis="",
        governance_decisions=[],
        debate_transcripts=[],
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _rich_state() -> SimpleNamespace:
    """A state with broad analytical coverage → verdict band EXCEEDED.

    5 non-trivial axes: fallacies + quality + counters + formal_pl + dung.
    Has formal depth (PL inconsistency) AND quality → EXCEEDED (≥5 axes + formal
    + quality, per the band threshold).
    """
    return _state(
        identified_arguments={
            "arg_1": "Le locuteur disqualifie l'adversaire par une attaque personnelle.",
            "arg_2": "Une revendication défendue par un raisonnement causal étayé.",
        },
        identified_fallacies={
            "fl_1": {
                "target_argument_id": "arg_1",
                "family": "ad hominem",
                "type": "ad hominem circonstanciel",
                "taxonomy_path": "racine > sophismes de pertinence > ad hominem",
                "justification": (
                    "L'argument attaque la personne plutôt que la thèse, "
                    "ce qui détache la conclusion des motifs."
                ),
            }
        },
        argument_quality_scores={
            "arg_1": {
                "overall": 4.2,
                "scores": {"pertinence": 3.0, "clarte": 5.0},
            },
            "arg_2": {
                "overall": 7.8,
                "scores": {"pertinence": 8.0, "coherence": 7.5},
            },
        },
        counter_arguments=[
            {
                "target_arg_id": "arg_1",
                "strategy": "contre-exemple",
                "counter_content": (
                    "On peut attaquer la thèse sans attaquer la personne, ce qui "
                    "montre que le procès personnel est superflu."
                ),
            }
        ],
        dung_frameworks={
            "fw_1": {
                "arguments": ["arg_1", "arg_2"],
                "extensions": {"all_members": ["arg_2"]},
                "semantics": "grounded",
            }
        },
        propositional_analysis_results=[
            {"satisfiable": True},
            {"satisfiable": False},
        ],
    )


# --- async LLM stubs ---------------------------------------------------------


def _stub_llm(return_value: str) -> object:
    """An async LLM callable stub returning a fixed conclusion."""

    async def _call(_prompt: str) -> str:
        return return_value

    return _call


def _raising_llm(exc: BaseException) -> object:
    async def _call(_prompt: str) -> str:
        raise exc

    return _call


# A §4-compliant woven conclusion (reader-oriented per #1262: names the
# speaker, cites what was said, plain-language verdict, formal as support).
# All framework refs anchored on a beat, no isolated score, no dump heading.
# Must PASS the readability gate.
_WOVEN_CONCLUSION = (
    "### Ce que le discours dit\n\n"
    "Le locuteur défend sa position en disqualifiant l'adversaire par une "
    "attaque personnelle, puis appuie une revendication sur un raisonnement "
    "causal étayé. Le premier mouvement vise à écarter l'opposant plutôt qu'à "
    "prouver la thèse ; le second cherche, lui, à convaincre sur le fond.\n\n"
    "### Ce qui tient et ce qui ne tient pas\n\n"
    "Le second mouvement tient : la vertu de pertinence éclaire un argument "
    "liée à sa conclusion, et le lecteur peut s'y fier. Le premier ne tient "
    "pas : il dérape vers un ad hominem circonstanciel qui détache la "
    "conclusion des motifs. Le cadre d'argumentation traduit cela "
    "mécaniquement — la revendication attaquée est isolée comme rejetée, ne "
    "survivant pas à la réfutation.\n\n"
    "### Comment se faire son avis\n\n"
    "Le lecteur doit recevoir le premier mouvement avec prudence : ce n'est "
    "pas la thèse qui est défendue là, mais la personne qui est écartée. Le "
    "second mouvement, en revanche, mérite d'être pris au sérieux sur le "
    "fond. Un contre-exemple le confirme : on peut attaquer la thèse sans "
    "attaquer la personne, ce qui isole le procès personnel comme superflu."
)

# An enumeration (bare refs + dump headings) — must NOT pass the gate.
_ENUMERATION = (
    "Sophisme 1: ad hominem (0.8)\n"
    "Sophisme 2: ad verecundiam (0.7)\n"
    "Argument 1: quality 0.4\n"
    "Verdict: Tweety 0.8\n"
)


# ============================================================================
# build_act3_evidence — deterministic verdict + weak points
# ============================================================================


class TestBuildEvidence:
    def test_rich_state_is_exceeded_band(self):
        ev = build_act3_evidence(_rich_state())
        assert ev.verdict is not None
        assert ev.verdict.band == "EXCEEDED"
        assert ev.verdict.axes_count == 5
        assert "formal_pl" in ev.verdict.nontrivial_axes
        assert "quality" in ev.verdict.nontrivial_axes

    def test_counts_and_axes(self):
        ev = build_act3_evidence(_rich_state())
        assert ev.args_total == 2
        assert ev.fallacies_total == 1
        assert ev.counters_total == 1
        assert ev.quality_axis_available is True

    def test_claim_excerpts_carry_real_text(self):
        """#1262 — the reader-oriented conclusion must cite what was said:
        Act3Evidence carries the real (truncated) claim text, not just arg_N
        counts. _rich_state has 2 identified_arguments → 2 excerpts."""
        ev = build_act3_evidence(_rich_state())
        assert len(ev.claim_excerpts) == 2
        # Real claim text present (not opaque IDs).
        assert "disqualifie" in ev.claim_excerpts[0]
        assert "causal" in ev.claim_excerpts[1]

    def test_claim_excerpts_empty_when_no_arguments(self):
        """#1262 — honest absence: no arguments extracted → empty excerpts
        (G1 not passed), not fabricated."""
        ev = build_act3_evidence(_state())
        assert ev.claim_excerpts == []

    def test_weak_points_collect_fallacy_and_formal_and_dung(self):
        ev = build_act3_evidence(_rich_state())
        sources = {wp.source for wp in ev.weak_points}
        # fallacy (ad hominem) + dung (arg_1 rejected) + pl (1 inconsistency).
        assert "fallacy" in sources
        assert "dung" in sources
        assert "pl" in sources

    def test_counter_strategies_collected(self):
        ev = build_act3_evidence(_rich_state())
        assert len(ev.counter_strategies) == 1
        assert ev.counter_strategies[0].strategy == "contre-exemple"

    def test_counter_validation_surfaced_g6(self):
        """G6 (#1180): validation verdict (from 5-criteria eval) reaches Acte III."""
        state = _state(
            counter_arguments=[
                {
                    "target_arg_id": "arg_1",
                    "strategy": "contre-exemple",
                    "counter_content": "Attaque la thèse, pas la personne.",
                    "validation": {
                        "is_valid_attack": True,
                        "counter_succeeds": True,
                        "original_survives": False,
                        "logical_consistency": True,
                    },
                }
            ]
        )
        ev = build_act3_evidence(state)
        assert len(ev.counter_strategies) == 1
        cs = ev.counter_strategies[0]
        assert cs.is_valid_attack is True
        assert cs.counter_succeeds is True

    def test_counter_validation_absent_is_none_g6(self):
        """When the evaluator did not run, validation stays None (no #1019 fabrication)."""
        state = _state(
            counter_arguments=[
                {
                    "target_arg_id": "arg_1",
                    "strategy": "contre-exemple",
                    "counter_content": "Attaque la thèse.",
                }
            ]
        )
        ev = build_act3_evidence(state)
        cs = ev.counter_strategies[0]
        assert cs.is_valid_attack is None
        assert cs.counter_succeeds is None

    def test_governance_and_debate_surfaced_sv(self):
        """SV (#1182): governance verdict + debate exchange reach Acte III."""
        state = _state(
            governance_decisions=[
                {"method": "copeland", "winner": "opt_X", "scores": {"opt_X": 0.9}}
            ],
            debate_transcripts=[
                {
                    "topic": "t",
                    "exchanges": [{"point": "la thèse P", "rebuttal": "or Q"}],
                    "winner": "pro",
                }
            ],
        )
        ev = build_act3_evidence(state)
        assert ev.governance_verdict is not None
        assert ev.governance_verdict.winner == "opt_X"
        assert ev.governance_verdict.method == "copeland"
        assert len(ev.debate_exchanges) == 1
        assert ev.debate_exchanges[0].point == "la thèse P"

    def test_governance_trivial_winner_is_none_sv(self):
        """SV fail-loud: a placeholder 'N/A' winner carries no verdict (#1019)."""
        state = _state(
            governance_decisions=[{"method": "majority", "winner": "N/A", "scores": {}}],
            debate_transcripts=[{"exchanges": [{"point": "", "rebuttal": ""}]}],
        )
        ev = build_act3_evidence(state)
        assert ev.governance_verdict is None
        assert ev.debate_exchanges == []

    def test_deliberation_block_in_prompt_sv(self):
        """SV: the deliberation block reaches the conducted prompt."""
        state = _state(
            governance_decisions=[
                {"method": "copeland", "winner": "opt_X", "scores": {"opt_X": 0.9}}
            ],
        )
        ev = build_act3_evidence(state)
        prompt = build_act3_prompt(ev)
        assert "DÉLIBÉRATION COLLECTIVE" in prompt
        assert "opt_X" in prompt

    def test_debate_scheme_grounding_g8(self):
        """G8 (#1184): a scheme-grounded exchange surfaces scheme + CQ.

        SV reader contract (point/rebuttal) intact; scheme/critical_question
        extend it optionally. None when no scheme matched (fail-loud, #1019).
        """
        state = _state(
            debate_transcripts=[
                {
                    "topic": "t",
                    "exchanges": [
                        {
                            "point": "Selon un expert du domaine, P tient.",
                            "rebuttal": "mais hors domaine",
                            "scheme": "Argument d'autorité (advice of an expert)",
                            "critical_question": "E est-elle experte ?",
                        }
                    ],
                }
            ]
        )
        ev = build_act3_evidence(state)
        ex = ev.debate_exchanges[0]
        assert ex.point == "Selon un expert du domaine, P tient."
        assert ex.scheme == "Argument d'autorité (advice of an expert)"
        assert ex.critical_question == "E est-elle experte ?"

    def test_quality_strengths_collected(self):
        ev = build_act3_evidence(_rich_state())
        virtues = {s.virtue for s in ev.quality_strengths}
        assert "pertinence" in virtues
        assert "clarte" in virtues

    def test_gates_pass_on_rich_state(self):
        ev = build_act3_evidence(_rich_state())
        assert ev.gates["G1_arguments_extracted"] is True
        assert ev.gates["G2_one_dimension_nontrivial"] is True
        assert ev.gates["G3_verdict_computed"] is True
        assert ev.gates["G4_no_fabrication"] is True

    def test_empty_state_g1_fails_and_below_band(self):
        ev = build_act3_evidence(_state())
        assert ev.gates["G1_arguments_extracted"] is False
        assert ev.verdict is not None
        assert ev.verdict.band == "BELOW"
        assert ev.verdict.axes_count == 0

    def test_match_band_without_formal_depth(self):
        # 4 axes but no formal depth (no PL/FOL) → MATCH, not EXCEEDED.
        state = _state(
            identified_arguments={"arg_1": "un argument"},
            identified_fallacies={
                "fl_1": {
                    "target_argument_id": "arg_1",
                    "family": "ad hominem",
                    "type": "ad hominem",
                }
            },
            argument_quality_scores={"arg_1": {"scores_par_vertu": {"clarte": 5.0}}},
            counter_arguments=[
                {"target_arg_id": "arg_1", "strategy": "contre-exemple", "counter_content": "réponse"}
            ],
            dung_frameworks={
                "fw_1": {"arguments": ["arg_1"], "extensions": {}, "semantics": "grounded"}
            },
        )
        ev = build_act3_evidence(state)
        assert ev.verdict is not None
        assert ev.verdict.band == "MATCH"

    def test_partial_band_with_two_axes(self):
        state = _state(
            identified_arguments={"arg_1": "un argument"},
            identified_fallacies={
                "fl_1": {
                    "target_argument_id": "arg_1",
                    "family": "ad hominem",
                    "type": "ad hominem",
                }
            },
            argument_quality_scores={"arg_1": {"scores_par_vertu": {"clarte": 5.0}}},
        )
        ev = build_act3_evidence(state)
        assert ev.verdict is not None
        assert ev.verdict.band == "PARTIAL"

    def test_below_band_with_one_axis(self):
        state = _state(
            identified_arguments={"arg_1": "un argument"},
            identified_fallacies={
                "fl_1": {
                    "target_argument_id": "arg_1",
                    "family": "ad hominem",
                    "type": "ad hominem",
                }
            },
        )
        ev = build_act3_evidence(state)
        assert ev.verdict is not None
        assert ev.verdict.band == "BELOW"

    def test_consistent_pl_credits_formal_axis_d1c(self):
        """D1c (#1167): a CONSISTENT PL theory (satisfiable True) is a real
        formal result — the formal_pl axis must be credited so a coherent
        text (no inconsistency) still surfaces a formal finding. satisfiable
        IS a result."""
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            _pl_verified,
        )

        state = _state(
            propositional_analysis_results=[{"satisfiable": True}]
        )
        assert _pl_verified(state) == 1
        ev = build_act3_evidence(state)
        assert "formal_pl" in ev.verdict.nontrivial_axes

    def test_consistent_fol_credits_formal_axis_d1c(self):
        """D1c (#1167): a CONSISTENT FOL theory credits the formal_fol axis."""
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            _fol_verified,
        )

        state = _state(fol_analysis_results=[{"consistent": True}])
        assert _fol_verified(state) == 1
        ev = build_act3_evidence(state)
        assert "formal_fol" in ev.verdict.nontrivial_axes

    def test_unverified_pl_does_not_credit_formal_axis_d1c(self):
        """D1c (#1167): an unverified theory (None) is NOT a result — never
        ``bool()`` a formal verdict (#1019: None ≠ False)."""
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            _pl_verified,
        )

        state = _state(
            propositional_analysis_results=[{"satisfiable": None}]
        )
        assert _pl_verified(state) == 0


class TestPrivacy:
    def test_long_justification_truncated_in_prompt(self):
        long_just = "x" * 500  # well over the _JUSTIFICATION_CAP
        state = _state(
            identified_arguments={"arg_1": "arg"},
            identified_fallacies={
                "fl_1": {
                    "target_argument_id": "arg_1",
                    "family": "ad hominem",
                    "type": "ad hominem",
                    "justification": long_just,
                }
            },
        )
        ev = build_act3_evidence(state)
        prompt = build_act3_prompt(ev)
        assert long_just not in prompt
        assert "[…]" in prompt

    @pytest.mark.parametrize("deanonymized,expect_opaque", [(True, False), (False, True)])
    def test_opaque_directive_gated_by_deanonymized(self, deanonymized, expect_opaque):
        # Epic #1258 / Track 1 #1259 — opaque-ID directive present only when
        # NOT deanonymized; weaving rule + fail-loud always present.
        state = _rich_state()
        state.deanonymized = deanonymized
        ev = build_act3_evidence(state)
        prompt = build_act3_prompt(ev)
        assert ("OPAQUES" in prompt) == expect_opaque  # FB-34 directive heading
        assert "TISSAGE" in prompt  # §4 weaving rule heading (always)
        assert "HONNÊTETÉ" in prompt  # fail-loud instruction heading (always)
        assert "spec §4" in prompt

    def test_prompt_carries_verdict_band(self):
        ev = build_act3_evidence(_rich_state())
        prompt = build_act3_prompt(ev)
        assert "EXCEEDED" in prompt

    def test_prompt_carries_real_claim_excerpts(self):
        """#1262 — the prompt feeds the LLM the real claim text so it can cite
        what was actually said. The debate-prep framing is dropped (anti-pendule:
        subtraction, not a counter-directive)."""
        ev = build_act3_evidence(_rich_state())
        prompt = build_act3_prompt(ev)
        assert "CE QUI A ÉTÉ DIT" in prompt  # real-claims data block
        assert "disqualifie" in prompt  # real claim text present
        # Reader-oriented beats present (replaces the old debate-prep beats).
        assert "orientée lecteur" in prompt.lower()
        assert "se faire son avis" in prompt.lower()
        # Anti-pendule: the debate-prep framing is SUBTRACTED (not re-labelled).
        assert "comment CONTRER" not in prompt
        assert "points faibles à viser" not in prompt.lower()


# ============================================================================
# weave_act3_conclusion — fail-loud
# ============================================================================


class TestWeaveFailLoud:
    def test_llm_error_returns_empty(self):
        ev = build_act3_evidence(_rich_state())
        out = asyncio.get_event_loop().run_until_complete(
            weave_act3_conclusion(ev, _raising_llm(RuntimeError("boom")))  # type: ignore[arg-type]
        )
        assert out == ""

    def test_llm_empty_returns_empty(self):
        ev = build_act3_evidence(_rich_state())
        out = asyncio.get_event_loop().run_until_complete(
            weave_act3_conclusion(ev, _stub_llm(""))  # type: ignore[arg-type]
        )
        assert out == ""


# ============================================================================
# build_act3_conclusion — orchestrator + G1-G4 gates + §4 self-check
# ============================================================================


class TestBuildConclusion:
    def test_no_llm_is_fail_loud_unavailable(self):
        result = asyncio.get_event_loop().run_until_complete(
            build_act3_conclusion(_rich_state(), llm_callable=None)
        )
        assert result.status == "unavailable"
        assert result.narrative == ""
        assert "act3_conclusion" in result.degraded

    def test_empty_state_is_fail_loud_empty_state(self):
        result = asyncio.get_event_loop().run_until_complete(
            build_act3_conclusion(_state(), llm_callable=_stub_llm(_WOVEN_CONCLUSION))  # type: ignore[arg-type]
        )
        assert result.status == "empty_state"
        assert result.narrative == ""
        assert "G1" in result.degraded.get("act3_conclusion", "")

    def test_woven_conclusion_passes_gate_self_check(self):
        """DoD: the conducted conclusion passes our own §4 gate."""
        result = asyncio.get_event_loop().run_until_complete(
            build_act3_conclusion(
                _rich_state(), llm_callable=_stub_llm(_WOVEN_CONCLUSION)  # type: ignore[arg-type]
            )
        )
        assert result.status == "woven"
        assert result.narrative == _WOVEN_CONCLUSION
        assert result.gate_verdict is not None
        assert result.gate_verdict.band == "PASS", result.gate_verdict.reasons

    def test_enumeration_is_detected_honestly(self):
        """The self-check must NOT pass an enumeration (honest, no curve)."""
        result = asyncio.get_event_loop().run_until_complete(
            build_act3_conclusion(
                _rich_state(), llm_callable=_stub_llm(_ENUMERATION)  # type: ignore[arg-type]
            )
        )
        assert result.status == "woven"  # LLM produced text, but…
        assert result.gate_verdict is not None
        assert result.gate_verdict.band == "FAIL"
        assert result.degraded  # surfaced honestly

    def test_quality_unavailable_recorded_as_degraded(self):
        state = _rich_state()
        state.argument_quality_scores = {}
        result = asyncio.get_event_loop().run_until_complete(
            build_act3_conclusion(
                state, llm_callable=_stub_llm(_WOVEN_CONCLUSION)  # type: ignore[arg-type]
            )
        )
        assert any(
            "qualité" in v.lower() or "qualit" in v.lower()
            for v in result.degraded.values()
        )

    def test_g2_failure_flags_gate_note(self):
        """G2 fails when no axis is non-trivial but args exist (vacuous)."""
        state = _state(identified_arguments={"arg_1": "un argument sans analyse"})
        result = asyncio.get_event_loop().run_until_complete(
            build_act3_conclusion(
                state, llm_callable=_stub_llm(_WOVEN_CONCLUSION)  # type: ignore[arg-type]
            )
        )
        # G1 passes (arg exists), G2 fails (no non-trivial axis) → gate note set,
        # verdict nulled in the evidence so the synthesis beat degrades honestly.
        assert result.status == "woven"
        assert "act3_conclusion_gates" in result.degraded
        assert "G2" in result.degraded["act3_conclusion_gates"]


# ============================================================================
# The woven fixture itself passes the gate independently (belt + braces)
# ============================================================================


class TestWovenFixtureIsGateCompliant:
    def test_woven_conclusion_passes_gate_directly(self):
        gate = ReadabilityGate()
        verdict = gate.check_body(_WOVEN_CONCLUSION)
        assert verdict.passed, verdict.reasons

    def test_enumeration_fails_gate_directly(self):
        gate = ReadabilityGate()
        verdict = gate.check_body(_ENUMERATION)
        assert not verdict.passed


# ============================================================================
# DoD (d): state.act3_conclusion is consumed by the R6 renderer end-to-end.
# ============================================================================


class TestConsumedByRenderer:
    def test_state_act3_flows_to_renderer(self):
        from argumentation_analysis.reporting.restitution.acts import (
            RestitutionActs,
        )
        from argumentation_analysis.reporting.restitution.renderer import (
            render_restitution_report,
        )

        # A state whose act3 phase has run (state_writer populated the key).
        state = SimpleNamespace(act3_conclusion=_WOVEN_CONCLUSION)
        # The 1-liner wiring: the act-builder maps state→RestitutionActs.
        acts = RestitutionActs(source_id="doc_A", act3_conclusion=state.act3_conclusion)

        report = render_restitution_report(acts)
        # The woven act3 conclusion is rendered into the body verbatim.
        assert _WOVEN_CONCLUSION.splitlines()[0] in report.markdown
        # act1/act2 are reported as missing (fail-loud), not silently dropped.
        assert "indisponible" in report.markdown.lower() or "acte" in report.markdown.lower()


# ============================================================================
# R5 volet-2 (#1139) — virtuous mode: Acte III titles the virtues (spec §5).
# ============================================================================


def _virtuous_state() -> SimpleNamespace:
    """A virtuous text: zero localized fallacies + measured quality virtues.

    No fallacies, real per-virtue scores under the canonical ``scores`` key, a
    PL inference the solver validated (formal robustness). The conclusion must
    title on the virtues, not on the absence of fallacies (spec §5 / DoD #1139).
    """
    return _state(
        identified_arguments={
            "arg_1": "Un raisonnement causal étayé par des sources vérifiées.",
            "arg_2": "Une conclusion qui suit logiquement ses prémisses.",
        },
        identified_fallacies={},  # zero localized fallacies — the honest result
        argument_quality_scores={
            "arg_1": {
                "overall": 8.0,
                "scores": {"clarte": 8.0, "coherence": 8.5, "pertinence": 7.5},
            },
            "arg_2": {
                "overall": 7.5,
                "scores": {"coherence": 8.0, "pertinence": 7.0},
            },
        },
        propositional_analysis_results=[{"satisfiable": True}],  # inferences hold
    )


class TestVirtuousMode:
    def test_virtuous_state_flagged(self):
        ev = build_act3_evidence(_virtuous_state())
        assert ev.virtuous_mode is not None
        assert ev.virtuous_mode.is_virtuous is True
        # no weak points on a virtuous text (nothing fabricated)
        assert ev.weak_points == []

    def test_non_virtuous_state_not_flagged(self):
        # _rich_state has a localized fallacy → not virtuous (don't hide it)
        ev = build_act3_evidence(_rich_state())
        assert ev.virtuous_mode is not None
        assert ev.virtuous_mode.is_virtuous is False

    def test_prompt_titles_on_virtues_when_virtuous(self):
        ev = build_act3_evidence(_virtuous_state())
        prompt = build_act3_prompt(ev)
        assert "MODE VIRTUEUX" in prompt
        assert "TIENT" in prompt  # titles on what holds
        # no fabrication instruction present when non-virtuous
        ev2 = build_act3_evidence(_rich_state())
        assert "MODE VIRTUEUX" not in build_act3_prompt(ev2)

    def test_virtuous_result_carries_positive_marker(self):
        result = asyncio.get_event_loop().run_until_complete(
            build_act3_conclusion(
                _virtuous_state(), llm_callable=_stub_llm(_WOVEN_CONCLUSION)  # type: ignore[arg-type]
            )
        )
        assert result.is_virtuous is True
        assert result.status == "woven"
        assert "act3_virtuous_mode" in result.degraded

    def test_non_virtuous_result_no_virtuous_marker(self):
        result = asyncio.get_event_loop().run_until_complete(
            build_act3_conclusion(
                _rich_state(), llm_callable=_stub_llm(_WOVEN_CONCLUSION)  # type: ignore[arg-type]
            )
        )
        assert result.is_virtuous is False
        assert "act3_virtuous_mode" not in result.degraded

    def test_no_fabricated_fallacy_in_virtuous_prompt(self):
        # the virtuous prompt must NOT invent a weak point to fill a beat
        ev = build_act3_evidence(_virtuous_state())
        prompt = build_act3_prompt(ev)
        assert "fabrique" in prompt.lower() or "ne fabrique" in prompt.lower()
        assert ev.weak_points == []
