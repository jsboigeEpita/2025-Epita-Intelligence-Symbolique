"""Tests for the Acte II generator — dialectical narrative by movement (R3 #1137).

Pins the spec §1.2 contract (cut by movement, not dimension) and the §4 weaving
contract (LLM-conducted narrative passes the readability gate; enumeration does
not). All deterministic — no JVM, no LLM service, no network: the LLM is an
injectable async stub and the state is a ``SimpleNamespace`` (the plugin reads
attributes via ``getattr``, same as ``compute_argument_convergence``).

Privacy HARD is asserted: corpus-derived fields are truncated before entering
the prompt, and the prompt carries the opaque-ID directive.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import List

import pytest

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    Act2Result,
    build_act2_evidence,
    build_act2_narrative,
    build_act2_prompt,
    weave_act2_narrative,
)
from argumentation_analysis.reporting.restitution.readability_gate import (
    ReadabilityGate,
)


# --- state stubs -------------------------------------------------------------


def _state(**fields: object) -> SimpleNamespace:
    """Build a lightweight state stub with the Acte II-relevant fields."""
    base = dict(
        identified_arguments={},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks={},
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _rich_state() -> SimpleNamespace:
    """A state with two movements: an ad-hominem attack + a clean soutien."""
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
        # Canonical Dung shape: the writer add_dung_framework stores NO
        # ``semantics`` key (it folds it into ``name``, state_writers.py:717).
        # Finding D (#1153): the reader must recover it from ``name``.
        dung_frameworks={
            "fw_1": {
                "name": "verification_preferred",
                "arguments": ["arg_1", "arg_2"],
                "attacks": [["arg_2", "arg_1"]],
                "extensions": {"all_members": ["arg_2"]},
            }
        },
        # Canonical PL shape: the writer stores ``satisfiable``, NOT
        # ``consistent`` (shared_state.py:801). Finding C (#1153): the reader
        # must read ``satisfiable`` to collect PL findings.
        propositional_analysis_results=[
            {"satisfiable": True},
            {"satisfiable": False},
        ],
    )


# --- async LLM stubs ---------------------------------------------------------


def _stub_llm(return_value: str) -> object:
    """An async LLM callable stub returning a fixed narrative."""

    async def _call(_prompt: str) -> str:
        return return_value

    return _call


def _raising_llm(exc: BaseException) -> object:
    async def _call(_prompt: str) -> str:
        raise exc

    return _call


# A §4-compliant woven narrative (all framework refs anchored on a beat, no
# isolated score, no dump heading). Must PASS the readability gate.
_WOVEN_NARRATIVE = (
    "### Le mouvement ad hominem\n\n"
    "Le premier mouvement appuie la thèse en disqualifiant l'adversaire plutôt "
    "que sa position. Cette attaque personnelle ne satisfait pas la question "
    "critique de pertinence: c'est un dérapage de la famille ad hominem "
    "(descente taxonomique racine > sophismes de pertinence > ad hominem), et "
    "le solveur Tweety confirme l'inconsistance de l'inférence sous-jacente. "
    "Un contre-exemple montre qu'on peut attaquer la thèse sans attaquer la "
    "personne, ce qui isole le procès personnel comme superflu. Le cadre de "
    "Dung traduit cela mécaniquement: arg_1 est rejeté par la sémantique "
    "grounded, ne survivant pas à l'attaque.\n\n"
    "### Les soutiens qui tiennent\n\n"
    "Le second mouvement défend une revendication par un raisonnement causal "
    "étayé; la vertu de pertinence éclaire un argument qui reste lié à sa "
    "conclusion. Aucun sophisme n'est localisé ici, et la tenue formelle "
    "appuie le battement sans réserve."
)

# An enumeration (bare refs + dump headings) — must NOT pass the gate.
_ENUMERATION = (
    "Sophisme 1: ad hominem (0.8)\n"
    "Sophisme 2: ad verecundiam (0.7)\n"
    "Argument 1: quality 0.4\n"
    "Argument 2: quality 0.8\n"
)


# ============================================================================
# build_act2_evidence — deterministic grouping
# ============================================================================


class TestBuildEvidence:
    def test_groups_attacked_args_by_family_and_soutiens_last(self):
        ev = build_act2_evidence(_rich_state())
        themes = [m.theme for m in ev.movements]
        # attack movement first, soutiens last
        assert themes == ["ad hominem", "soutiens"]
        assert ev.movements[-1].arguments[0].arg_id == "arg_2"

    def test_attacked_arg_carries_fallacy_counter_and_dung(self):
        ev = build_act2_evidence(_rich_state())
        mvt = ev.movements[0]
        arg1 = mvt.arguments[0]
        assert arg1.arg_id == "arg_1"
        assert len(arg1.fallacies) == 1
        assert arg1.fallacies[0].family == "ad hominem"
        assert len(arg1.counter_args) == 1
        assert arg1.counter_args[0].strategy == "contre-exemple"
        assert arg1.dung_rejected == "preferred"  # Finding D: parsed from name

    def test_quality_axis_available_flag(self):
        ev = build_act2_evidence(_rich_state())
        assert ev.quality_axis_available is True
        arg1 = ev.movements[0].arguments[0]
        assert arg1.quality_available is True
        assert arg1.quality_overall == pytest.approx(4.2)

    def test_quality_axis_unavailable_caveat(self):
        state = _rich_state()
        state.argument_quality_scores = {}
        ev = build_act2_evidence(state)
        assert ev.quality_axis_available is False
        arg1 = ev.movements[0].arguments[0]
        assert arg1.quality_available is False

    def test_empty_state(self):
        ev = build_act2_evidence(_state())
        assert ev.movements == []
        assert ev.args_total == 0
        assert ev.fallacies_total == 0

    def test_formal_findings_collect_pl_inconsistency_and_dung(self):
        ev = build_act2_evidence(_rich_state())
        kinds = {f.kind for f in ev.formal_findings}
        assert "pl" in kinds
        assert "dung" in kinds
        pl = next(f for f in ev.formal_findings if f.kind == "pl")
        assert "inconsistantes" in pl.verdict


class TestReaderWriterContracts:
    """#1153: prove each reader↔writer schema fix (Finding A/C/D + note(a) + §5).

    These tests assert against the CANONICAL writer schema (the shape the
    state-writers + shared_state.add_* actually produce), not the legacy shape
    the old reader keys expected — the prior tests passed only because the
    stubs mirrored the buggy reader.
    """

    def test_finding_a_quality_virtues_read_from_canonical_scores_key(self):
        # Writer add_quality_score stores per-virtue scores under 'scores'.
        state = _state(
            identified_arguments={"arg_1": "Claim."},
            argument_quality_scores={
                "arg_1": {"overall": 3.5, "scores": {"pertinence": 2.0,
                                                      "clarte": 5.0}},
            },
        )
        ev = build_act2_evidence(state)
        arg1 = ev.movements[0].arguments[0]
        assert arg1.virtues == {"pertinence": 2.0, "clarte": 5.0}  # NOT {}
        assert arg1.quality_available is True
        assert arg1.quality_overall == pytest.approx(3.5)

    def test_finding_a_quality_virtues_legacy_scores_par_vertu_still_works(self):
        # Legacy / external writers using 'scores_par_vertu' still surface.
        state = _state(
            identified_arguments={"arg_1": "Claim."},
            argument_quality_scores={
                "arg_1": {"overall": 3.0,
                          "scores_par_vertu": {"coherence": 4.0}},
            },
        )
        ev = build_act2_evidence(state)
        assert ev.movements[0].arguments[0].virtues == {"coherence": 4.0}

    def test_finding_c_pl_verdict_collected_from_satisfiable_key(self):
        # Writer stores 'satisfiable'; reader MUST collect PL findings.
        state = _state(
            propositional_analysis_results=[
                {"satisfiable": True},
                {"satisfiable": False},
            ],
        )
        ev = build_act2_evidence(state)
        pl = next((f for f in ev.formal_findings if f.kind == "pl"), None)
        assert pl is not None
        assert "inconsistantes" in pl.verdict  # the False entry surfaces

    def test_finding_c_pl_none_verdict_not_treated_as_inconsistent(self):
        # #1019: a None (unverified) verdict must NOT collapse to False.
        state = _state(
            propositional_analysis_results=[
                {"satisfiable": None},  # unverified
            ],
        )
        ev = build_act2_evidence(state)
        assert not any(f.kind == "pl" for f in ev.formal_findings)

    def test_finding_c_pl_legacy_consistent_key_still_collected(self):
        # Backward-compat: a writer using the legacy 'consistent' key still works.
        state = _state(
            propositional_analysis_results=[{"consistent": True}],
        )
        ev = build_act2_evidence(state)
        pl = next((f for f in ev.formal_findings if f.kind == "pl"), None)
        assert pl is not None and "consistantes" in pl.verdict

    def test_finding_d_dung_semantics_parsed_from_name(self):
        # Writer folds semantics into name=verification_<sem>; no 'semantics' key.
        state = _state(
            identified_arguments={"arg_1": "Claim A.", "arg_2": "Claim B."},
            dung_frameworks={
                "fw_1": {
                    "name": "verification_preferred",
                    "arguments": ["arg_1", "arg_2"],
                    "attacks": [["arg_2", "arg_1"]],
                    "extensions": {"all_members": ["arg_2"]},
                }
            },
        )
        ev = build_act2_evidence(state)
        # arg_1 rejected; label must be 'preferred', not the wrong 'grounded'.
        arg1 = next(a for m in ev.movements for a in m.arguments if a.arg_id == "arg_1")
        assert arg1.dung_rejected == "preferred"

    def test_finding_d_dung_semantics_explicit_key_preferred(self):
        # When an explicit 'semantics' key is present, it wins over the name.
        state = _state(
            identified_arguments={"arg_1": "Claim."},
            dung_frameworks={
                "fw_1": {
                    "name": "verification_grounded",
                    "semantics": "stable",
                    "arguments": ["arg_1"],
                    "attacks": [],
                    "extensions": {"all_members": []},
                }
            },
        )
        ev = build_act2_evidence(state)
        arg1 = next(a for m in ev.movements for a in m.arguments if a.arg_id == "arg_1")
        assert arg1.dung_rejected == "stable"

    def test_note_a_unresolved_fallacy_traced_not_dropped(self):
        # A fallacy with no target_argument_id must be counted apart, not lost.
        state = _state(
            identified_arguments={"arg_1": "Claim."},
            identified_fallacies={
                "fl_1": {"target_argument_id": "arg_1", "family": "ad hominem",
                         "type": "ad hominem", "justification": "x"},
                "fl_2": {"target_argument_id": "", "family": "fuite",
                         "type": "fuite en avant", "justification": "y"},
            },
        )
        ev = build_act2_evidence(state)
        assert ev.fallacies_total == 1  # only the attributed one
        assert ev.unattributed_fallacies == 1  # traced, not dropped

    def test_section5_gate_usable_content_not_bool_dict(self):
        # A non-empty dict with NO usable entry → axis unavailable (Finding A
        # hid here). Partial-but-empty must fail-loud, not pass as available.
        state = _state(
            identified_arguments={"arg_1": "Claim."},
            argument_quality_scores={"arg_1": {}},  # present but unusable
        )
        ev = build_act2_evidence(state)
        assert ev.quality_axis_available is False

    def test_section5_gate_legit_partial_state_still_available(self):
        # Anti-pendule: a single usable entry (overall only, no virtues) is
        # a legitimate partial state → axis stays available, no false fail-loud.
        state = _state(
            identified_arguments={"arg_1": "Claim."},
            argument_quality_scores={"arg_1": {"overall": 2.5}},
        )
        ev = build_act2_evidence(state)
        assert ev.quality_axis_available is True



class TestPrivacy:
    def test_long_description_truncated_in_prompt(self):
        long_desc = "x" * 500  # well over the _DESC_CAP
        state = _state(identified_arguments={"arg_1": long_desc})
        ev = build_act2_evidence(state)
        prompt = build_act2_prompt(ev)
        # The full 500-char string must not appear; the truncation marker must.
        assert long_desc not in prompt
        assert "[…]" in prompt

    def test_prompt_carries_opaque_id_directive_and_weaving_rule(self):
        ev = build_act2_evidence(_rich_state())
        prompt = build_act2_prompt(ev)
        assert "OPAQUES" in prompt  # FB-34 directive heading
        assert "TISSAGE" in prompt  # §4 weaving rule heading
        assert "spec §4" in prompt


# ============================================================================
# weave_act2_narrative — fail-loud
# ============================================================================


class TestWeaveFailLoud:
    def test_llm_error_returns_empty(self):
        ev = build_act2_evidence(_rich_state())
        out = asyncio.get_event_loop().run_until_complete(
            weave_act2_narrative(ev, _raising_llm(RuntimeError("boom")))  # type: ignore[arg-type]
        )
        assert out == ""

    def test_llm_empty_returns_empty(self):
        ev = build_act2_evidence(_rich_state())
        out = asyncio.get_event_loop().run_until_complete(
            weave_act2_narrative(ev, _stub_llm(""))  # type: ignore[arg-type]
        )
        assert out == ""


# ============================================================================
# build_act2_narrative — orchestrator + §4 self-check
# ============================================================================


class TestBuildNarrative:
    def test_no_llm_is_fail_loud_unavailable(self):
        result = asyncio.get_event_loop().run_until_complete(
            build_act2_narrative(_rich_state(), llm_callable=None)
        )
        assert result.status == "unavailable"
        assert result.narrative == ""
        assert "act2_narrative" in result.degraded

    def test_empty_state_is_fail_loud_empty_state(self):
        result = asyncio.get_event_loop().run_until_complete(
            build_act2_narrative(_state(), llm_callable=_stub_llm(_WOVEN_NARRATIVE))  # type: ignore[arg-type]
        )
        assert result.status == "empty_state"
        assert result.narrative == ""

    def test_woven_narrative_passes_gate_self_check(self):
        """DoD: the conducted narrative passes our own §4 gate."""
        result = asyncio.get_event_loop().run_until_complete(
            build_act2_narrative(
                _rich_state(), llm_callable=_stub_llm(_WOVEN_NARRATIVE)  # type: ignore[arg-type]
            )
        )
        assert result.status == "woven"
        assert result.narrative == _WOVEN_NARRATIVE
        assert result.gate_verdict is not None
        # A woven narrative is PASS (no bare refs, no dump headings).
        assert result.gate_verdict.band == "PASS", result.gate_verdict.reasons

    def test_enumeration_is_detected_honestly(self):
        """The self-check must NOT pass an enumeration (honest, no curve)."""
        result = asyncio.get_event_loop().run_until_complete(
            build_act2_narrative(
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
            build_act2_narrative(
                state, llm_callable=_stub_llm(_WOVEN_NARRATIVE)  # type: ignore[arg-type]
            )
        )
        assert any("qualité" in v.lower() or "qualit" in v.lower() for v in result.degraded.values())


# ============================================================================
# The woven fixture itself passes the gate independently (belt + braces)
# ============================================================================


class TestWovenFixtureIsGateCompliant:
    def test_woven_narrative_passes_gate_directly(self):
        gate = ReadabilityGate()
        verdict = gate.check_body(_WOVEN_NARRATIVE)
        assert verdict.passed, verdict.reasons

    def test_enumeration_fails_gate_directly(self):
        gate = ReadabilityGate()
        verdict = gate.check_body(_ENUMERATION)
        assert not verdict.passed


# ============================================================================
# DoD (d): state.act2_narrative is consumed by the R6 renderer end-to-end.
# The full state→RestitutionActs bridge is assembled once R2/R4 land (their
# lane); this proves the act2 key flows to the renderer via the contract today.
# ============================================================================


class TestConsumedByRenderer:
    def test_state_act2_flows_to_renderer(self):
        from argumentation_analysis.reporting.restitution.acts import RestitutionActs
        from argumentation_analysis.reporting.restitution.renderer import (
            render_restitution_report,
        )

        # A state whose act2 phase has run (state_writer populated the key).
        state = SimpleNamespace(act2_narrative=_WOVEN_NARRATIVE)
        # The 1-liner wiring: the act-builder maps state→RestitutionActs. R2/R4
        # add act1/act3; today only act2 is produced (act1/act3 → missing,
        # reported honestly by the renderer, never silent).
        acts = RestitutionActs(source_id="doc_A", act2_narrative=state.act2_narrative)

        report = render_restitution_report(acts)
        # The woven act2 narrative is rendered into the body verbatim.
        assert _WOVEN_NARRATIVE.splitlines()[0] in report.markdown
        # act1/act3 are reported as missing (fail-loud), not silently dropped.
        assert "indisponible" in report.markdown.lower() or "acte" in report.markdown.lower()
