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
    _fol_verified,
    _is_guest_formal_entry,
    _pl_verified,
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
            governance_decisions=[
                {"method": "majority", "winner": "N/A", "scores": {}}
            ],
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

    def test_governance_jargon_leak_guarded(self):
        """Regression for po-2023 finding R487 (Acte III half) — the conclusion
        prose leaked raw internal identifiers (« agent_1 » / « social_choice »).

        The Acte III prompt mirrors the Acte II guardrail: the governance data
        line must flag its identifiers as INTERNAL and instruct a role-based
        description, and the CONSIGNE must carry the general anti-jargon
        guardrail. (Without this fix the Acte III leak survived the Acte II-only
        fix — surfaced by the R488 validation re-run.) FB-34 source-opacity is
        orthogonal — describing by role deanonymises nothing.
        """
        state = _state(
            governance_decisions=[
                {
                    "method": "social_choice",
                    "winner": "agent_1",
                    "scores": {"agent_1": 0.9},
                }
            ],
        )
        ev = build_act3_evidence(state)
        prompt = build_act3_prompt(ev)
        # Data line flags the id as internal and instructs role-based prose.
        assert "identifiant interne" in prompt.lower()
        assert "rôle" in prompt.lower()
        # CONSIGNE carries the general anti-jargon guardrail.
        assert "JARGON INTERNE INTERDIT" in prompt
        assert "snake_case" in prompt
        # FB-34 source-opacity explicitly preserved.
        assert "déanonymise aucune source" in prompt.lower()

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
                {
                    "target_arg_id": "arg_1",
                    "strategy": "contre-exemple",
                    "counter_content": "réponse",
                }
            ],
            dung_frameworks={
                "fw_1": {
                    "arguments": ["arg_1"],
                    "extensions": {},
                    "semantics": "grounded",
                }
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

        state = _state(propositional_analysis_results=[{"satisfiable": True}])
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

        state = _state(propositional_analysis_results=[{"satisfiable": None}])
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

    @pytest.mark.parametrize(
        "deanonymized,expect_opaque", [(True, False), (False, True)]
    )
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
        assert (
            "indisponible" in report.markdown.lower()
            or "acte" in report.markdown.lower()
        )


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


# --- #1605: the conclusion must carry what the run failed to evaluate --------


def _ledger(*capabilities: str) -> dict:
    """A ``structured_arg_status`` ledger marking ``capabilities`` degraded.

    Mirrors the shape written by ``state_writers._record_structured_arg_status``.
    """
    return {
        cap: {
            "capability": cap,
            "status": "absent_no_translator",
            "degraded": True,
            "reason": f"{cap} not genuinely evaluated: no translator wired.",
            "extension_count": 1,
        }
        for cap in capabilities
    }


_SILENT_CONCLUSION = (
    "### Ce que le discours dit vraiment\n\n"
    "Le locuteur défend sa position en disqualifiant son contradicteur.\n\n"
    "### Ce qui tient et ce qui ne tient pas\n\n"
    "L'analyse formelle confirme la cohérence d'une partie du raisonnement.\n\n"
    "### Comment se faire son avis\n\n"
    "Recevoir avec prudence l'attaque personnelle, retenir l'argument causal."
)


class TestAbsentDimensionsCollected:
    """``structured_arg_status`` reaches the evidence (it reached nothing before)."""

    def test_no_ledger_yields_no_absence(self):
        ev = build_act3_evidence(_rich_state())
        assert ev.absent_dimensions == []

    def test_evaluated_capability_is_not_an_absence(self):
        state = _rich_state()
        state.structured_arg_status = {
            "setaf_reasoning": {
                "capability": "setaf_reasoning",
                "status": "evaluated",
                "degraded": False,
                "reason": "Genuine structured input supplied via context.",
                "extension_count": 3,
            }
        }
        ev = build_act3_evidence(state)
        assert ev.absent_dimensions == []

    def test_degraded_capabilities_are_collected(self):
        state = _rich_state()
        state.structured_arg_status = _ledger("aspic_plus_reasoning", "setaf_reasoning")
        ev = build_act3_evidence(state)
        assert {d.capability for d in ev.absent_dimensions} == {
            "aspic_plus_reasoning",
            "setaf_reasoning",
        }

    def test_label_is_reader_facing_not_snake_case(self):
        # The prose forbids raw identifiers; a capability key must never reach
        # the narrative as-is.
        state = _rich_state()
        state.structured_arg_status = _ledger("weighted_argumentation")
        ev = build_act3_evidence(state)
        (dim,) = ev.absent_dimensions
        assert "_" not in dim.label
        assert dim.label != dim.capability

    def test_unknown_capability_is_still_surfaced(self):
        # An absence we have no French label for must still be said, not dropped.
        state = _rich_state()
        state.structured_arg_status = _ledger("some_future_formalism")
        ev = build_act3_evidence(state)
        assert len(ev.absent_dimensions) == 1
        assert "_" not in ev.absent_dimensions[0].label


class TestAbsencePromptBlock:
    """The prompt states the absence in BOTH directions (present / none)."""

    def test_block_lists_the_lost_axes(self):
        state = _rich_state()
        state.structured_arg_status = _ledger("aba_reasoning")
        prompt = build_act3_prompt(build_act3_evidence(state))
        assert "[DIMENSIONS NON ÉVALUÉES" in prompt
        assert "hypothèses et contraires" in prompt

    def test_block_says_explicitly_when_nothing_was_lost(self):
        # An absent section would be ambiguous; the healthy run says so.
        prompt = build_act3_prompt(build_act3_evidence(_rich_state()))
        assert "aucune dimension perdue" in prompt


class TestConclusionCarriesTheAbsence:
    """The guarantee is deterministic — it does not depend on the LLM complying."""

    def _run(self, state, completion):
        return asyncio.get_event_loop().run_until_complete(
            build_act3_conclusion(state, llm_callable=_stub_llm(completion))  # type: ignore[arg-type]
        )

    def test_silent_prose_gets_the_scope_note_appended(self):
        state = _rich_state()
        state.structured_arg_status = _ledger("aspic_plus_reasoning")
        result = self._run(state, _SILENT_CONCLUSION)
        assert "Portée de cette analyse" in result.narrative
        assert "act3_scope_note_appended" in result.degraded

    def test_compliant_prose_is_not_duplicated(self):
        # The detector must be able to return True — otherwise the append is
        # unconditional and the check measures nothing.
        state = _rich_state()
        state.structured_arg_status = _ledger("aspic_plus_reasoning")
        compliant = _SILENT_CONCLUSION + (
            "\n\nL'examen du raisonnement défaisable n'a pas abouti sur ce texte."
        )
        result = self._run(state, compliant)
        assert "Portée de cette analyse" not in result.narrative
        assert "act3_scope_note_appended" not in result.degraded
        assert "act3_absent_dimensions" in result.degraded

    def test_generic_hedge_does_not_count_as_naming_the_absence(self):
        # "certaines analyses n'ont pas abouti" leaves the reader unable to know
        # WHICH angle is missing — the note must still be appended.
        state = _rich_state()
        state.structured_arg_status = _ledger("setaf_reasoning")
        hedged = _SILENT_CONCLUSION + (
            "\n\nCertaines analyses n'ont pas abouti sur ce texte."
        )
        result = self._run(state, hedged)
        assert "Portée de cette analyse" in result.narrative

    def test_healthy_run_gets_no_scope_note(self):
        result = self._run(_rich_state(), _SILENT_CONCLUSION)
        assert "Portée de cette analyse" not in result.narrative
        assert result.degraded.get("act3_absent_dimensions") is None

    def test_conclusion_discriminates_three_run_states(self):
        """The falsifiable control: 0 / 2 / 4 lost axes → three distinct outputs.

        Measured on three real corpora (#1605): before this wiring, the three
        conclusions were 3447 / 3742 / 3560 chars and none mentioned anything —
        a reader could not tell the amputated run from the healthy one.
        """
        healthy = _rich_state()
        two_lost = _rich_state()
        two_lost.structured_arg_status = _ledger(
            "setaf_reasoning", "weighted_argumentation"
        )
        four_lost = _rich_state()
        four_lost.structured_arg_status = _ledger(
            "setaf_reasoning",
            "weighted_argumentation",
            "aba_reasoning",
            "aspic_plus_reasoning",
        )

        counts = [
            len(build_act3_evidence(s).absent_dimensions)
            for s in (healthy, two_lost, four_lost)
        ]
        assert counts == [0, 2, 4]

        narratives = [
            self._run(s, _SILENT_CONCLUSION).narrative
            for s in (healthy, two_lost, four_lost)
        ]
        # Three genuinely different run states must yield three different texts.
        assert len(set(narratives)) == 3
        assert "Portée de cette analyse" not in narratives[0]
        assert "attaques collectives" in narratives[1]
        assert "hypothèses et contraires" in narratives[2]


# --- #1605: guest formalisms must not credit the host axis -------------------


def _dl_entry() -> dict:
    """The shape ``state_writers._write_dl_to_state`` really writes (measured)."""
    return {
        "id": "fol_1",
        "formulas": ["DL: Knowledge base is consistent."],
        "consistent": True,
        "inferences": [],
        "confidence": 1.0,
    }


def _real_fol_entry(consistent: bool = False) -> dict:
    """A genuine first-order theory decided by a first-order prover."""
    return {
        "id": "fol_2",
        "formulas": ["forall X: (humain(X) => mortel(X))", "humain(socrate)"],
        "consistent": consistent,
        "inferences": [],
        "confidence": 1.0,
    }


class TestGuestFormalEntriesDoNotCreditHostAxis:
    """A formalism writing into another's container must not earn its axis.

    Measured on the real runs: ``fol_analysis_results`` also receives
    Description Logic verdicts, and on 2 of 3 corpora the ``formal_fol`` axis was
    carried *solely* by such an entry — on runs where the real FOL theory failed
    to parse. The conclusion was granted first-order support that no first-order
    prover ever produced.
    """

    def test_dl_entry_is_recognised_as_guest(self) -> None:
        assert _is_guest_formal_entry(_dl_entry()) is True

    def test_real_fol_entry_is_not_guest(self) -> None:
        assert _is_guest_formal_entry(_real_fol_entry()) is False

    def test_entry_mixing_real_and_marker_formulas_keeps_credit(self) -> None:
        """Conservative by design: only an ALL-marker entry is a guest."""
        mixed = {
            "formulas": ["DL: Knowledge base is consistent.", "humain(socrate)"],
            "consistent": True,
        }
        assert _is_guest_formal_entry(mixed) is False

    def test_entry_without_formulas_is_not_guest(self) -> None:
        """``all([])`` is True — the empty case must not be swept in silently."""
        assert _is_guest_formal_entry({"consistent": True}) is False
        assert _is_guest_formal_entry({"formulas": [], "consistent": True}) is False

    def test_dl_only_state_loses_the_fol_axis(self) -> None:
        state = _state(fol_analysis_results=[_dl_entry()])
        assert _fol_verified(state) == 0
        axes = build_act3_evidence(state).verdict.nontrivial_axes
        assert "formal_fol" not in axes

    def test_real_fol_verdict_keeps_the_fol_axis(self) -> None:
        """The bite-proving negative: the filter removes guests, not the axis."""
        state = _state(fol_analysis_results=[_dl_entry(), _real_fol_entry()])
        assert _fol_verified(state) == 1
        axes = build_act3_evidence(state).verdict.nontrivial_axes
        assert "formal_fol" in axes

    def test_guest_cl_and_qbf_do_not_credit_the_pl_axis(self) -> None:
        """CL and QBF write into the propositional container the same way."""
        guests_only = _state(
            propositional_analysis_results=[
                {
                    "formulas": ["CL(0 conditionals): No query specified."],
                    "satisfiable": True,
                },
                {"formulas": ["QBF: <texte brut du document>"], "satisfiable": True},
            ]
        )
        assert _pl_verified(guests_only) == 0
        assert (
            "formal_pl" not in build_act3_evidence(guests_only).verdict.nontrivial_axes
        )

        with_host = _state(
            propositional_analysis_results=[
                {
                    "formulas": ["CL(0 conditionals): No query specified."],
                    "satisfiable": True,
                },
                {"formulas": ["p && q"], "satisfiable": True},
            ]
        )
        assert _pl_verified(with_host) == 1
        assert "formal_pl" in build_act3_evidence(with_host).verdict.nontrivial_axes


# --- #1605: the blocking half of the conclusion gate -------------------------


# A conclusion asserting first-order support. ``_rich_state`` has no formal_fol
# axis, so this claim rests on nothing.
_CLAIM_ON_ABSENT_AXIS = (
    "### Ce que le discours dit\n\n"
    "Le locuteur disqualifie l'adversaire avant de défendre sa thèse sur le "
    "fond. La logique du premier ordre confirme que la structure profonde du "
    "discours est cohérente. Le lecteur peut donc suivre le second mouvement "
    "sans réserve.\n\n"
    "### Ce qui tient\n\n"
    "Le raisonnement causal tient et reste lisible pour qui suit le débat."
)


class TestUnsupportedClaimBlocked:
    """The DoD's blocking half: an affirmation refused for lack of a dimension.

    ``_band_claim_ceiling`` *instructs* the LLM about how strongly it may
    characterise the discourse. Nothing verified the produced prose afterwards.
    This gate is that verification, per axis — the band cannot do it, because
    losing an entire formalism moves 6 axes to 5 and keeps the same band.
    """

    def _run(self, state: object, conclusion: str) -> Act3Result:
        return asyncio.run(build_act3_conclusion(state, _stub_llm(conclusion)))

    def test_claim_on_absent_axis_is_removed_from_the_narrative(self) -> None:
        result = self._run(_rich_state(), _CLAIM_ON_ABSENT_AXIS)
        assert "La logique du premier ordre confirme" not in result.narrative

    def test_removal_is_reported_in_degraded(self) -> None:
        result = self._run(_rich_state(), _CLAIM_ON_ABSENT_AXIS)
        assert "act3_claim_blocked" in result.degraded
        assert "premier ordre" in result.degraded["act3_claim_blocked"]

    def test_removal_note_names_the_axis_for_the_reader(self) -> None:
        result = self._run(_rich_state(), _CLAIM_ON_ABSENT_AXIS)
        assert "Affirmation retirée" in result.narrative
        assert "la logique du premier ordre" in result.narrative

    def test_same_claim_survives_when_the_axis_is_present(self) -> None:
        """The bite proof: identical prose, one axis added, no removal."""
        supported = _rich_state()
        supported.fol_analysis_results = [_real_fol_entry(consistent=True)]
        result = self._run(supported, _CLAIM_ON_ABSENT_AXIS)
        assert "La logique du premier ordre confirme" in result.narrative
        assert "act3_claim_blocked" not in result.degraded
        assert "Affirmation retirée" not in result.narrative

    def test_honest_absence_statement_is_not_blocked(self) -> None:
        """Naming an absent axis to SAY it is absent is what #1609 asks for."""
        honest = _CLAIM_ON_ABSENT_AXIS.replace(
            "La logique du premier ordre confirme que la structure profonde du "
            "discours est cohérente.",
            "La logique du premier ordre n'a pas abouti sur ce texte.",
        )
        result = self._run(_rich_state(), honest)
        assert "n'a pas abouti sur ce texte" in result.narrative
        assert "act3_claim_blocked" not in result.degraded

    def test_conclusion_making_no_unsupported_claim_is_untouched(self) -> None:
        result = self._run(_rich_state(), _WOVEN_CONCLUSION)
        assert "act3_claim_blocked" not in result.degraded
        assert "Affirmation retirée" not in result.narrative

    def test_gate_preserves_the_rest_of_the_conclusion(self) -> None:
        """Fail loud, not fail hard: one sentence goes, the conclusion stays."""
        result = self._run(_rich_state(), _CLAIM_ON_ABSENT_AXIS)
        assert "Le locuteur disqualifie l'adversaire" in result.narrative
        assert "Le raisonnement causal tient" in result.narrative
        assert result.status == "woven"
