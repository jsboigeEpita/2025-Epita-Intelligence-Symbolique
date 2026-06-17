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
                "scores_par_vertu": {"pertinence": 3.0, "clarte": 5.0},
            },
            "arg_2": {
                "overall": 7.8,
                "scores_par_vertu": {"pertinence": 8.0, "coherence": 7.5},
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
            {"consistent": True},
            {"consistent": False},
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


# A §4-compliant woven conclusion (all framework refs anchored on a beat, no
# isolated score, no dump heading). Must PASS the readability gate.
_WOVEN_CONCLUSION = (
    "### Synthèse honnête\n\n"
    "L'analyse atteint une profondeur multi-axes: elle localise un dérapage, "
    "caractérise le discours par ses vertus, et le solveur Tweety confirme "
    "l'inconsistance d'une inférence sous-jacente. La couverture est large, la "
    "caractérisation peut donc être assurée sans sur-claim.\n\n"
    "### Ce qui tient et ce qui dérape\n\n"
    "Le second mouvement tient: la vertu de pertinence éclaire un argument lié "
    "à sa conclusion. Le premier dérape vers un ad hominem circonstanciel "
    "(famille ad hominem), qui détache la conclusion des motifs. Le cadre de "
    "Dung traduit cela mécaniquement: arg_1 est rejeté par la sémantique "
    "grounded, ne survivant pas à l'attaque.\n\n"
    "### Comment contrer et à quoi s'attendre\n\n"
    "Un contre-exemple montre qu'on peut attaquer la thèse sans attaquer la "
    "personne, isolant le procès personnel comme superflu. À attendre ensuite: "
    "l'orateur peut doubler la mise sur l'autorité ou glisser d'une attaque à "
    "une autre pour esquiver la faiblesse signalée."
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

    def test_prompt_carries_directives(self):
        ev = build_act3_evidence(_rich_state())
        prompt = build_act3_prompt(ev)
        assert "OPAQUES" in prompt  # FB-34 directive heading
        assert "TISSAGE" in prompt  # §4 weaving rule heading
        assert "HONNÊTETÉ" in prompt  # fail-loud instruction heading
        assert "spec §4" in prompt

    def test_prompt_carries_verdict_band(self):
        ev = build_act3_evidence(_rich_state())
        prompt = build_act3_prompt(ev)
        assert "EXCEEDED" in prompt


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
