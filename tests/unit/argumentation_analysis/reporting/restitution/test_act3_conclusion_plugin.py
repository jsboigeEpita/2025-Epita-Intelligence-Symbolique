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
    _COUNTER_LIST_CAP,
    _SUPPORT_NODE_CAP,
    _SUPPORT_PAIR_CAP,
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

    def test_thin_run_keeps_both_motifs_instead_of_overwriting(self):
        """#1615 — the precise motif must survive the generic one.

        On a thin run the quality axis is unavailable AND there are no weak
        points, so both degradation branches fire. They used to write the same
        ``act3_conclusion`` key, and the generic "aucun point faible" motif
        silently replaced the precise "axe qualité non concluable" one — the
        reader was told the wrong reason for the degradation.

        Measured through the real builder before the fix: ``degraded`` held
        ``act3_conclusion`` carrying the GENERIC text, the precise one gone.
        Restoring the single key kills this test (and only this one).
        """
        state = _state(
            identified_arguments={
                "arg_1": "Une revendication défendue par un raisonnement causal étayé.",
                "arg_2": "Une seconde revendication appuyée sur un précédent documenté.",
            },
            argument_quality_scores={},  # axe qualité indisponible
        )
        result = asyncio.get_event_loop().run_until_complete(
            build_act3_conclusion(
                state, llm_callable=_stub_llm(_WOVEN_CONCLUSION)  # type: ignore[arg-type]
            )
        )
        # Both motifs present, each under its own key.
        assert "act3_conclusion" in result.degraded
        assert "qualit" in result.degraded["act3_conclusion"].lower()
        assert "act3_conclusion_thin" in result.degraded
        assert "point faible" in result.degraded["act3_conclusion_thin"].lower()

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
        # The virtue is reported as a virtue, not as a degradation: #1608 made
        # ``degraded`` a verdict (the invoker publishes ``bool(degraded)``), so
        # a virtue filed there marked the best-case act as degraded.
        assert "act3_virtuous_mode" not in result.degraded
        assert bool(result.degraded) is False

    def test_non_virtuous_result_no_virtuous_marker(self):
        """A non-virtuous state must not claim the virtuous shift.

        The former companion assertion (``"act3_virtuous_mode" not in
        result.degraded``) is dropped rather than kept: the key no longer
        exists in any branch, so it could not fail under any implementation —
        a passing assertion that measures nothing. ``is_virtuous`` is the flag
        that still discriminates, and it is the one asserted.
        """
        result = asyncio.get_event_loop().run_until_complete(
            build_act3_conclusion(
                _rich_state(), llm_callable=_stub_llm(_WOVEN_CONCLUSION)  # type: ignore[arg-type]
            )
        )
        assert result.is_virtuous is False

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

    def test_emptied_section_does_not_leave_a_bare_heading(self) -> None:
        """Removing the only sentence of a section must remove its heading too."""
        conclusion = (
            "### Ce que le discours dit\n\n"
            "Le locuteur avance sa thèse avec des exemples concrets.\n\n"
            "### Appui formel\n\n"
            "La logique du premier ordre confirme la structure du discours.\n\n"
            "### Ce qui tient\n\n"
            "Le raisonnement causal tient."
        )
        result = self._run(_rich_state(), conclusion)
        assert "### Appui formel" not in result.narrative
        assert "### Ce que le discours dit" in result.narrative
        assert "### Ce qui tient" in result.narrative

    def test_heading_is_kept_when_its_section_still_has_content(self) -> None:
        """The bite proof for heading removal: a surviving sibling keeps it."""
        conclusion = (
            "### Appui formel\n\n"
            "La logique du premier ordre confirme la structure du discours.\n"
            "Le solveur SAT établit la satisfiabilité de la thèse.\n"
        )
        result = self._run(_rich_state(), conclusion)
        assert "### Appui formel" in result.narrative
        assert "Le solveur SAT établit" in result.narrative
        assert "La logique du premier ordre confirme" not in result.narrative

    def test_wholly_unsupported_conclusion_declares_it_in_the_narrative(
        self,
    ) -> None:
        """If nothing survives, the NARRATIVE must say so — not just `degraded`.

        The structured `degraded` dict does not survive the state round-trip
        (``_write_act3_conclusion_to_state`` stores only the narrative), so a
        fact carried solely there never reaches the reader.
        """
        conclusion = "La logique du premier ordre confirme la cohérence du discours."
        result = self._run(_rich_state(), conclusion)
        assert "Aucune conclusion soutenable" in result.narrative
        assert "Il ne reste aucune conclusion" in result.narrative
        assert "act3_claim_blocked_all" in result.degraded
        assert not result.narrative.startswith("\n")

    def test_partial_removal_does_not_claim_the_conclusion_is_empty(self) -> None:
        """The bite proof: surviving prose must NOT get the emptiness wording."""
        result = self._run(_rich_state(), _CLAIM_ON_ABSENT_AXIS)
        assert "Aucune conclusion soutenable" not in result.narrative
        assert "act3_claim_blocked_all" not in result.degraded
        assert "Affirmation retirée" in result.narrative

    def test_parent_heading_survives_when_its_subsections_carry_the_content(
        self,
    ) -> None:
        """A heading is empty only if its whole SUBTREE is.

        The narrative is free-form markdown conducted by the LLM, so a section
        that holds its content in subsections is ordinary input. Judging
        emptiness on the lines immediately below would delete the parent while
        keeping its children — mangling a hierarchy the gate never touched.
        """
        conclusion = (
            "## Ce que l'analyse établit\n\n"
            "### Appui formel\n\n"
            "La logique du premier ordre confirme la structure du discours.\n\n"
            "### Ce qui tient\n\n"
            "Le raisonnement causal tient et les prémisses sont explicites.\n"
        )
        result = self._run(_rich_state(), conclusion)
        # The blocked claim took `### Appui formel` with it...
        assert "### Appui formel" not in result.narrative
        # ...but the parent keeps its surviving subsection, and both remain.
        assert "## Ce que l'analyse établit" in result.narrative
        assert "### Ce qui tient" in result.narrative
        assert "Le raisonnement causal tient" in result.narrative

    def test_parent_heading_falls_when_its_whole_subtree_is_emptied(self) -> None:
        """The bite proof for the subtree rule: an emptied subtree takes the parent.

        Without this, "keep a parent whose descendants survived" could degrade
        into "always keep parents", which is the symmetrical error.
        """
        conclusion = (
            "## Ce que l'analyse établit\n\n"
            "### Appui formel\n\n"
            "La logique du premier ordre confirme la structure du discours.\n\n"
            "## Ce qui tient\n\n"
            "Le raisonnement causal tient et les prémisses sont explicites.\n"
        )
        result = self._run(_rich_state(), conclusion)
        assert "### Appui formel" not in result.narrative
        assert "## Ce que l'analyse établit" not in result.narrative
        assert "## Ce qui tient" in result.narrative
        assert "Le raisonnement causal tient" in result.narrative


# --- #1622 : la magnitude des contre-arguments circule ------------------------


def _counters(n: int) -> List[dict]:
    """``n`` distinct, well-formed counter-arguments (each passes the filter)."""
    return [
        {
            "target_arg_id": f"arg_{i + 1}",
            "strategy": "contre-exemple",
            "counter_content": (
                f"Contre-argument {i + 1} : la revendication ne tient pas si "
                "l'on considère un cas où la relation causale s'inverse."
            ),
        }
        for i in range(n)
    ]


def _prompt_with_counters(n: int) -> str:
    """Prompt built from a state carrying exactly ``n`` counter-arguments."""
    state = _state(
        identified_arguments={f"arg_{i + 1}": f"Thèse {i + 1}." for i in range(n or 1)},
        counter_arguments=_counters(n),
    )
    evidence = build_act3_evidence(state)
    # Guard the fixture itself: the prompt assertions below are only meaningful
    # if the state really produced ``n`` counter-arguments in the bundle.
    assert evidence.counters_total == n
    return build_act3_prompt(evidence)


class TestCounterTruncationIsAnnounced:
    """#1622 — the Acte III prompt enumerates at most ``_COUNTER_LIST_CAP``
    counter-arguments, and that enumeration is the ONLY place it lists them.

    Measured on 8 real artifacts, 8/8 carried more than the cap (11 to 56), so
    writing the actionable section from a fraction of the material is the
    nominal regime, not an edge case. ``counters_total`` reached the evidence
    bundle but only its *truthiness* had a reader (the axis test); the magnitude
    had none, so nothing could tell the conclusion a remainder existed.
    """

    def test_above_the_cap_the_prompt_states_the_true_total(self) -> None:
        n = _COUNTER_LIST_CAP + 7
        prompt = _prompt_with_counters(n)
        # The true total and the omitted count both reach the prompt — not just
        # "this list is partial", which would leave the magnitude unknown.
        assert str(n) in prompt
        assert str(n - _COUNTER_LIST_CAP) in prompt
        assert "tronquée" in prompt

    def test_at_or_below_the_cap_no_truncation_is_claimed(self) -> None:
        """Anti-pendule: a systematic notice would be a false alarm.

        A run that fits under the cap loses nothing; saying otherwise would tell
        the LLM to hedge a complete list.
        """
        for n in (0, 1, _COUNTER_LIST_CAP - 1, _COUNTER_LIST_CAP):
            prompt = _prompt_with_counters(n)
            assert "tronquée" not in prompt, f"false truncation notice at n={n}"
            assert "non énumérés" not in prompt, f"false omission notice at n={n}"

    def test_two_states_differing_only_in_count_yield_different_prompts(self) -> None:
        """The bite proof, and the one the previous test suite could not give.

        ``test_evidence_counts_counter_arguments`` asserts the *field* is
        computed; it passes identically whether or not anything reads the field.
        This pins the observable consequence: crossing the cap must change the
        prompt. Below vs. above, everything else about the two states is equal.
        """
        below = _prompt_with_counters(_COUNTER_LIST_CAP)
        above = _prompt_with_counters(_COUNTER_LIST_CAP + 1)
        assert below != above

    def test_the_enumeration_itself_stays_capped(self) -> None:
        """Anti-pendule: the remedy is to *say* the list is partial, not to show
        more of it. Removing the cap would blow the prompt budget on a corpus
        with 56 counter-arguments — replacing one line by its opposite.
        """
        n = _COUNTER_LIST_CAP + 20
        prompt = _prompt_with_counters(n)
        listed = prompt.count("  - Pour contrer ")
        assert (
            listed == _COUNTER_LIST_CAP
        ), f"enumerated {listed}, cap is {_COUNTER_LIST_CAP}"


# --- #1667: the PRESENCE channel for structured-argumentation axes -----------
#
# Before this channel, `absent_dimensions` was the ONLY path from a structured
# axis to the Acte III conclusion, and it opens on `degraded=True`. The prose
# had a vocabulary for the axis that FAILED and none for the axis that
# SUCCEEDED — so repairing a module REMOVED its single trace from the
# narrative, and any "does the conclusion mention this axis?" metric read
# exactly backwards. These tests pin the symmetric path.


def _bipolar_state(
    supports: object,
    support_cycles: object = None,
    articulation_points: object = None,
    **extra: object,
) -> SimpleNamespace:
    state = _rich_state()
    entry: dict = {
        "id": "bipolar_1",
        "framework_type": "necessity",
        "arguments": ["A", "B"],
        "supports": supports,
    }
    if support_cycles is not None:
        entry["support_cycles"] = support_cycles
    if articulation_points is not None:
        entry["articulation_points"] = articulation_points
    state.bipolar_results = [entry]
    for k, v in extra.items():
        setattr(state, k, v)
    return state


def _aspic_state(extensions: object) -> SimpleNamespace:
    state = _rich_state()
    state.aspic_results = [
        {
            "id": "aspic_1",
            "reasoner_type": "simple",
            "extensions": extensions,
            "statistics": {"extensions_count": 1},
        }
    ]
    return state


def _aspic_state_with_attacks(
    attacks: list, extensions: object = None
) -> SimpleNamespace:
    """#1649: an ASPIC state carrying the qualified ``attacks`` list (the
    #1681 writer's top-level field). ``attacks`` uses the real handler shape
    (``{attacker_rule, attacker_premises, target, scope}``), verified firsthand
    in the producer tests — this helper feeds the READER, the #1649 deliverable.
    """
    state = _rich_state()
    state.aspic_results = [
        {
            "id": "aspic_1",
            "reasoner_type": "simple",
            "extensions": [[]] if extensions is None else extensions,
            "statistics": {
                "extensions_count": 1,
                "attacks_count": len(attacks),
            },
            "attacks": attacks,
        }
    ]
    return state


class TestStructuredArgPresenceChannel:
    """A structured axis that SUCCEEDS must reach the conclusion (#1667)."""

    def test_baseline_state_yields_no_finding(self) -> None:
        """Non-vacuity floor: nothing in state ⇒ nothing fabricated."""
        ev = build_act3_evidence(_rich_state())
        assert ev.structured_findings == []

    def test_empty_containers_leave_the_prompt_free_of_formal_claims(self) -> None:
        state = _bipolar_state([])
        state.aspic_results = []
        prompt = build_act3_prompt(build_act3_evidence(state))
        assert "aucun cadre d'argumentation structurée n'a établi" in prompt
        # The support-sentence marker specifically — the bare word "appuie"
        # already occurs in the static weaving rule ("le verdict formel appuie
        # un battement narratif"), so asserting on it would pass vacuously.
        assert "» appuie «" not in prompt

    def test_bipolar_support_relation_becomes_a_finding(self) -> None:
        state = _bipolar_state(
            [["La croissance a repris", "La politique menée est bonne"]]
        )
        ev = build_act3_evidence(state)
        (finding,) = ev.structured_findings
        assert finding.capability == "bipolar_argumentation"
        assert "La croissance a repris" in finding.statement
        assert "La politique menée est bonne" in finding.statement

    def test_finding_is_not_a_count(self) -> None:
        """Anti-pendule of this issue: "1 résultat bipolaire" would reproduce
        ``appendix.py``'s ``"disponible"`` one hop further along — the witness
        moved, no decider created. The statement must carry the relation.
        """
        pair = ["Le chômage recule", "La réforme fonctionne"]
        (finding,) = build_act3_evidence(_bipolar_state([pair])).structured_findings
        assert all(node in finding.statement for node in pair)
        assert finding.statement.strip() not in {"1", "1 relation", "disponible"}

    def test_label_is_reader_facing_not_snake_case(self) -> None:
        (finding,) = build_act3_evidence(
            _bipolar_state([["x", "y"]])
        ).structured_findings
        assert "_" not in finding.label
        assert finding.label != finding.capability

    @pytest.mark.parametrize(
        "supports",
        [
            [],
            [["", ""]],
            [["only-one-node"]],
            [["a", "b", "c"]],
            ["not-a-pair"],
            "not-a-list",
        ],
        ids=["empty", "blank-nodes", "arity-1", "arity-3", "scalar-item", "scalar"],
    )
    def test_malformed_or_empty_supports_produce_nothing(self, supports) -> None:
        """Fail-loud (#1019): a channel open onto emptiness is worse than a
        closed one — the axis would count as "evaluated" while saying nothing.
        """
        assert build_act3_evidence(_bipolar_state(supports)).structured_findings == []

    def test_support_pairs_are_capped(self) -> None:
        pairs = [[f"source {i}", f"target {i}"] for i in range(_SUPPORT_PAIR_CAP + 5)]
        (finding,) = build_act3_evidence(_bipolar_state(pairs)).structured_findings
        assert finding.statement.count(" appuie ") == _SUPPORT_PAIR_CAP

    def test_long_support_nodes_are_truncated(self) -> None:
        long_node = "m" * (_SUPPORT_NODE_CAP + 200)
        (finding,) = build_act3_evidence(
            _bipolar_state([[long_node, "court"]])
        ).structured_findings
        assert long_node not in finding.statement
        assert "[…]" in finding.statement

    def test_aspic_empty_extension_produces_nothing(self) -> None:
        """The measured production shape, unanimous on 8 real state artifacts:
        ``extensions: [[]]`` with ``axioms_count: 0``. ``_invoke_aspic`` reads
        ``context["axioms"]``, a key no producer in the orchestration writes, so
        ASPIC+ builds no argument at all and its single extension is empty.
        Emitting here would dress an argument-free theory as a result. This is
        the regression sentinel for the day that producer is repaired.
        """
        assert build_act3_evidence(_aspic_state([[]])).structured_findings == []

    def test_aspic_single_all_inclusive_extension_produces_nothing(self) -> None:
        """The state one hop after the premises are repaired — measured, not
        hypothesised (JVM probe, R766): supplying ordinary premises yields 11
        arguments, **0 attacks**, and ONE extension holding all 11.

        Zero attacks because ``ASPICHandler`` only ever builds
        ``Proposition(head)``, never a ``Negation``: a head string of ``"!x"``
        becomes a proposition *named* ``!x``, conflicting with nothing. An
        extension that excludes no argument arbitrated nothing, and emitting it
        would hand the conclusion a formally-authorised statement with no
        discriminating content (#1631). Fixing premises alone must NOT open this
        channel.
        """
        state = _aspic_state([["def_arg_1: p => c", "def_arg_2: q => d"]])
        assert build_act3_evidence(state).structured_findings == []

    def test_aspic_competing_extensions_become_a_finding(self) -> None:
        """Two extensions that disagree ⇒ a real arbitration happened. The
        finding is the CONTESTED set (union − intersection), because what ASPIC+
        brings that no other axis does is naming which derivations cannot be
        held together — not which ones survived.
        """
        state = _aspic_state(
            [
                ["socle_partagé", "def_arg_1: prémisse => conclusion_plausible"],
                ["socle_partagé", "rebuttal_1: sophisme => conclusion_contraire"],
            ]
        )
        (finding,) = build_act3_evidence(state).structured_findings
        assert finding.capability == "aspic_plus_reasoning"
        assert "def_arg_1: prémisse => conclusion_plausible" in finding.statement
        assert "rebuttal_1: sophisme => conclusion_contraire" in finding.statement
        # The uncontested member is not the finding — it is what both sides keep.
        assert "socle_partagé" not in finding.statement

    def test_aspic_duplicate_extensions_are_not_a_disagreement(self) -> None:
        """Two entries carrying the SAME extension arbitrate nothing. Guards the
        cheap reading of the rule above ("len(extensions) >= 2").
        """
        ext = ["def_arg_1: p => c"]
        assert (
            build_act3_evidence(_aspic_state([ext, list(ext)])).structured_findings
            == []
        )

    def test_both_axes_are_carried_by_one_channel(self) -> None:
        """One channel, not one reader per axis (the eight-half-fixes lesson)."""
        state = _bipolar_state([["s", "t"]])
        state.aspic_results = [
            {
                "extensions": [["socle", "derivation_1"], ["socle", "derivation_2"]],
                "statistics": {},
            },
        ]
        ev = build_act3_evidence(state)
        assert {f.capability for f in ev.structured_findings} == {
            "aspic_plus_reasoning",
            "bipolar_argumentation",
        }

    # ------------------------------------------------------------------
    # #1649 — ASPIC+ attack SCOPE (undercut/rebut/undermine) is the axis's
    # singular contribution: no other axis names HOW a derivation is attacked.
    # The producer (#1678 handler ``_qualify_attacks`` + #1679 translator
    # emitting ``head_negated`` rules) populates ``attacks[*].scope`` ONLY on a
    # real LLM-translator run (CI / no-API-key ⇒ honest empty). These tests use
    # the real handler output shape (verified firsthand: producer tests
    # ``test_aspic_negation_scope_1678`` + ``test_aspic_translator_contradictions_1678``,
    # 13 passed) — they exercise the READER (the #1649 deliverable), not the
    # producer. Coord R782 anti-#1019: the deliverable is that the RENDERED
    # output changes when ``attacks`` changes, verified consumer-side below.
    # ------------------------------------------------------------------

    def test_aspic_qualified_attacks_reach_the_conclusion_1649(self) -> None:
        """Qualified attacks ⇒ the finding names the SCOPE, undercut leading."""
        state = _aspic_state_with_attacks(
            [
                {
                    "attacker_rule": "d_undercut",
                    "attacker_premises": ["arg_d"],
                    "target": "d_main",
                    "scope": "undercut",
                },
                {
                    "attacker_rule": "d_rebut",
                    "attacker_premises": ["arg_b"],
                    "target": "concl_x",
                    "scope": "rebut",
                },
            ]
        )
        (finding,) = build_act3_evidence(state).structured_findings
        assert finding.capability == "aspic_plus_reasoning"
        stmt = finding.statement
        assert "undercut" in stmt
        assert "rebut" in stmt
        # The singular scope (undercut) leads the sentence.
        assert stmt.index("undercut") < stmt.index("rebut")
        # Privacy HARD: raw source-derived atoms never reach the prose.
        assert "d_main" not in stmt
        assert "concl_x" not in stmt

    def test_aspic_rendered_statement_changes_when_attacks_change_1649(self) -> None:
        """Anti-#1019 (coord R782): same state with vs without ``attacks``
        yields DIFFERENT rendered conclusions — the field genuinely drives the
        prose, not just the writer/bundle (the witness-is-not-the-decider trap).
        """
        attacks = [
            {
                "attacker_rule": "d_u",
                "attacker_premises": ["a"],
                "target": "rule_x",
                "scope": "undercut",
            }
        ]
        with_stmt = (
            build_act3_evidence(_aspic_state_with_attacks(attacks))
            .structured_findings[0]
            .statement
        )
        # Same state minus the attacks field (producer honest-empty, vacuous ext).
        without = build_act3_evidence(_aspic_state([[]])).structured_findings
        assert "undercut" in with_stmt
        assert without == []
        assert with_stmt != ""

    def test_aspic_empty_attacks_do_not_open_the_scope_channel_1649(self) -> None:
        """The producer's honest-empty ``attacks=[]`` (ran, no attack) must NOT
        fabricate a scope statement — mirrors the contested-sets honest-absence
        gate. Tri-state safe: an empty list must read as "no attack".
        """
        state = _aspic_state_with_attacks([], extensions=[[]])
        assert build_act3_evidence(state).structured_findings == []

    def test_aspic_attacks_take_priority_over_contested_sets_1649(self) -> None:
        """When BOTH attacks and contested extensions are present, the singular
        contribution (scope) leads; contested sets (Dung-equivalent) defer.
        """
        state = _aspic_state_with_attacks(
            [
                {
                    "attacker_rule": "d_u",
                    "attacker_premises": ["a"],
                    "target": "r",
                    "scope": "undercut",
                }
            ],
            extensions=[["socle", "d1"], ["socle", "d2"]],
        )
        (finding,) = build_act3_evidence(state).structured_findings
        assert "undercut" in finding.statement
        assert "s'excluent mutuellement" not in finding.statement

    @pytest.mark.parametrize(
        "state_factory, payload",
        [
            (
                lambda: _bipolar_state([["la reprise est réelle", "le cap est bon"]]),
                "la reprise est réelle",
            ),
            (
                lambda: _aspic_state(
                    [["socle", "chaine_defaisable_7"], ["socle", "chaine_rivale_2"]]
                ),
                "chaine_defaisable_7",
            ),
        ],
        ids=["bipolar", "aspic"],
    )
    def test_a_present_non_trivial_axis_reaches_the_prompt(
        self, state_factory, payload
    ) -> None:
        """The contract this issue exists to pin: it FAILS if a non-trivial axis
        stops before the Acte III prompt — which is where all of them stopped.
        """
        prompt = build_act3_prompt(build_act3_evidence(state_factory()))
        assert payload in prompt
        assert "CE QUE LES CADRES STRUCTURÉS ÉTABLISSENT" in prompt

    def test_presence_and_absence_are_additive_not_substitutive(self) -> None:
        """Anti-pendule: the absence ledger stays correct and useful. An axis
        that really degraded must keep being named; we ADD the presence lane.
        """
        state = _bipolar_state([["s", "t"]])
        state.structured_arg_status = _ledger("setaf_reasoning")
        ev = build_act3_evidence(state)
        assert [d.capability for d in ev.absent_dimensions] == ["setaf_reasoning"]
        assert [f.capability for f in ev.structured_findings] == [
            "bipolar_argumentation"
        ]
        prompt = build_act3_prompt(ev)
        assert "DIMENSIONS NON ÉVALUÉES" in prompt
        assert "CE QUE LES CADRES STRUCTURÉS ÉTABLISSENT" in prompt


class TestBipolarSupportCycleInsight:
    """#1645 — the bipolar axis's distinctive insight is the support cycle
    (circular authority). The reader must NAME it, not recopy it as innocuous
    pairs. Measured firsthand (E pass 1): before wiring, a planted cycle
    ``prop_alpha <-> prop_beta`` was rendered byte-for-byte identically to an
    acyclic control pair — structurally present in the input, invisible in the
    prose (anti-théâtre #1019).
    """

    def test_support_cycle_is_named_not_recopied(self) -> None:
        """DoD #1501-style differentiation: the singular insight (#1645 section
        A) — two arguments backing each other with no external anchor — must be
        NAMED ('autorité circulaire'), never rendered as two 'appuie' pairs.
        """
        cycle = [["prop_alpha", "prop_beta"], ["prop_beta", "prop_alpha"]]
        (finding,) = build_act3_evidence(
            _bipolar_state(cycle, support_cycles=[["prop_alpha", "prop_beta"]])
        ).structured_findings
        assert "autorité circulaire" in finding.statement
        assert "prop_alpha" in finding.statement
        assert "prop_beta" in finding.statement
        # Named, not recopied: the cycle marker is gone.
        assert " appuie " not in finding.statement

    def test_cycle_takes_priority_over_acyclic_recopy(self) -> None:
        """When a cycle sits alongside ordinary supports, the cycle IS the
        finding — the descriptive recopy must not dilute the named insight.
        """
        supports = [
            ["prop_alpha", "prop_beta"],
            ["prop_beta", "prop_alpha"],
            ["prop_gamma", "prop_concl"],
        ]
        (finding,) = build_act3_evidence(
            _bipolar_state(supports, support_cycles=[["prop_alpha", "prop_beta"]])
        ).structured_findings
        assert "autorité circulaire" in finding.statement
        # The acyclic control pair is dropped when the cycle is named.
        assert "prop_concl" not in finding.statement

    def test_no_cycle_falls_back_to_descriptive_recopy(self) -> None:
        """Backward-compat (#1667): without a cycle the reader recopies pairs.
        The cycle path is strictly additive.
        """
        (finding,) = build_act3_evidence(
            _bipolar_state([["prop_alpha", "prop_beta"]])
        ).structured_findings
        assert " appuie " in finding.statement
        assert "autorité circulaire" not in finding.statement

    def test_empty_cycle_list_falls_back_to_recopy(self) -> None:
        """An explicit empty ``support_cycles`` is an honest 'no cycle detected'
        — the reader recopies, never fabricates a cycle (fail-loud #1019).
        """
        (finding,) = build_act3_evidence(
            _bipolar_state([["prop_a", "prop_b"]], support_cycles=[])
        ).structured_findings
        assert " appuie " in finding.statement
        assert "autorité circulaire" not in finding.statement

    def test_three_node_cycle_is_named(self) -> None:
        """A longer cycle (A->B->C->A) is named 'forment un cycle ... autorité
        circulaire'.
        """
        (finding,) = build_act3_evidence(
            _bipolar_state([], support_cycles=[["prop_a", "prop_b", "prop_c"]])
        ).structured_findings
        assert "forment un cycle" in finding.statement
        assert "autorité circulaire" in finding.statement

    def test_cycle_reaches_the_act3_prompt(self) -> None:
        """DoD item 3: the insight must reach a reader that states it in the
        prose — not only the appendix.
        """
        prompt = build_act3_prompt(
            build_act3_evidence(
                _bipolar_state(
                    [["prop_alpha", "prop_beta"], ["prop_beta", "prop_alpha"]],
                    support_cycles=[["prop_alpha", "prop_beta"]],
                )
            )
        )
        assert "autorité circulaire" in prompt


class TestBipolarArticulationPointInsight:
    """#1645 PR2 — the second distinctive insight (B-insight-3): the support
    articulation point. An argument that is the SOLE backer of one or more others
    structurally carries a weight the text does not flag — removing it collapses
    its dependents' support. The reader must NAME it ('point d'articulation'),
    not recopy it as innocuous pairs. Invisible to attack-only frameworks and to
    LLM fallacy detection, same as the cycle (section A).
    """

    def test_articulation_point_is_named_not_recopied(self) -> None:
        """The singular figure: a sole supporter. Must be NAMED ('point
        d'articulation'), never rendered as an 'appuie' pair.
        """
        (finding,) = build_act3_evidence(
            _bipolar_state(
                [["sole_backer", "dependent_a"]],
                articulation_points=[
                    {"node": "sole_backer", "dependents": ["dependent_a"]}
                ],
            )
        ).structured_findings
        assert "point d'articulation" in finding.statement
        assert "sole_backer" in finding.statement
        assert "dependent_a" in finding.statement
        # Named, not recopied.
        assert " appuie " not in finding.statement

    def test_articulation_takes_priority_over_acyclic_recopy(self) -> None:
        """An articulation sitting alongside ordinary supports IS the finding —
        the descriptive recopy must not dilute the named figure.
        """
        supports = [
            ["sole_backer", "dependent_a"],
            ["prop_gamma", "prop_concl"],
        ]
        (finding,) = build_act3_evidence(
            _bipolar_state(
                supports,
                articulation_points=[
                    {"node": "sole_backer", "dependents": ["dependent_a"]}
                ],
            )
        ).structured_findings
        assert "point d'articulation" in finding.statement
        # The ordinary acyclic pair is dropped when the articulation is named.
        assert "prop_concl" not in finding.statement

    def test_cycle_takes_priority_over_articulation(self) -> None:
        """Priority order: cycle > articulation > recopy. When both a cycle and
        an articulation are present, the cycle (the stronger, more specific
        statement) wins and is the sole finding.
        """
        (finding,) = build_act3_evidence(
            _bipolar_state(
                [["prop_a", "prop_b"], ["prop_b", "prop_a"]],
                support_cycles=[["prop_a", "prop_b"]],
                articulation_points=[{"node": "prop_a", "dependents": ["prop_b"]}],
            )
        ).structured_findings
        assert "autorité circulaire" in finding.statement
        # The articulation wording does not co-occur with the cycle.
        assert "point d'articulation" not in finding.statement

    def test_no_articulation_falls_back_to_recopy(self) -> None:
        """Backward-compat: without an articulation point the reader recopies
        pairs. The articulation path is strictly additive.
        """
        (finding,) = build_act3_evidence(
            _bipolar_state([["prop_alpha", "prop_beta"]])
        ).structured_findings
        assert " appuie " in finding.statement
        assert "point d'articulation" not in finding.statement

    def test_shared_backer_is_not_an_articulation_point(self) -> None:
        """Anti-pendule / anti-over-detection: an argument backed by TWO
        supporters is NOT solely backed — removing either leaves the other, so
        neither is an articulation point. The reader recopies, never fabricates
        a 'sole appui' figure that does not hold (fail-loud #1019).
        """
        supports = [["backer_one", "shared_target"], ["backer_two", "shared_target"]]
        (finding,) = build_act3_evidence(
            # No articulation point: the producer (detect_support_articulation_points)
            # returns [] for a shared backer — modelled here by omission.
            _bipolar_state(supports)
        ).structured_findings
        assert "point d'articulation" not in finding.statement
        assert " appuie " in finding.statement

    def test_multi_dependent_articulation_names_the_count(self) -> None:
        """A sole backer of several arguments names the dependent count, so the
        structural weight ('how much rests on it') reaches the reader.
        """
        (finding,) = build_act3_evidence(
            _bipolar_state(
                [["sole_backer", "dep_a"], ["sole_backer", "dep_b"]],
                articulation_points=[
                    {"node": "sole_backer", "dependents": ["dep_a", "dep_b"]}
                ],
            )
        ).structured_findings
        assert "point d'articulation" in finding.statement
        assert "2 arguments" in finding.statement

    def test_articulation_reaches_the_act3_prompt(self) -> None:
        """DoD item 3: the insight must reach a reader that states it in the
        prose — not only the appendix.
        """
        prompt = build_act3_prompt(
            build_act3_evidence(
                _bipolar_state(
                    [["sole_backer", "dependent_a"]],
                    articulation_points=[
                        {"node": "sole_backer", "dependents": ["dependent_a"]}
                    ],
                )
            )
        )
        assert "point d'articulation" in prompt
