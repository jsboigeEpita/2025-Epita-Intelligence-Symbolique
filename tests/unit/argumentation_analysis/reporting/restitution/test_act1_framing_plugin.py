"""Tests for the Acte I generator — mise en situation / framing (R2 #1136).

Pins the spec §1.1 contract (4 framing beats, before the microscope; the only
act that may anticipate) and the §4 weaving contract. The load-bearing DoD for
the expected spectrum: it is **derived** from the taxonomy ``common_contexts``
matching the discourse genre — never hardcoded.

Deterministic — no JVM, no LLM service, no network: the LLM is an injectable
async stub and the state is a ``SimpleNamespace``.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    Act1Result,
    _derive_expected_spectrum,
    _derive_genre,
    _load_families,
    build_act1_evidence,
    build_act1_framing,
    build_act1_prompt,
    reset_taxonomy_cache,
    weave_act1_framing,
)
from argumentation_analysis.reporting.restitution.readability_gate import (
    ReadabilityGate,
)


# --- state stubs -------------------------------------------------------------


def _state(**fields: object) -> SimpleNamespace:
    base = dict(
        source_metadata={},
        stakes_and_stakeholders={
            "stakes": [],
            "stakeholders": [],
            "rhetorical_register": "",
            "discursive_arena": "",
        },
        identified_arguments={},
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _political_state() -> SimpleNamespace:
    return _state(
        source_metadata={
            "genre": "discours politique",
            "speaker_role": "locuteur en autorité",
            "channel": "arène publique",
        },
        stakes_and_stakeholders={
            "rhetorical_register": "délibératif",
            "discursive_arena": "politique",
            "stakes": [
                {"stake_type": "décision", "description": "Mobiliser l'auditoire sur une décision controversée."},
            ],
            "stakeholders": [
                {"role": "locuteur", "interest": "Faire adopter la décision."},
                {"role": "adversaire", "interest": "Bloquer la décision."},
            ],
        },
        identified_arguments={"arg_1": "thèse", "arg_2": "support"},
    )


# --- async LLM stubs ---------------------------------------------------------


def _stub_llm(return_value: str) -> object:
    async def _call(_prompt: str) -> str:
        return return_value

    return _call


def _raising_llm(exc: BaseException) -> object:
    async def _call(_prompt: str) -> str:
        raise exc

    return _call


# A §4-compliant woven Acte I (4 thematic beats, families anchored to the
# genre, no isolated score, no dump heading). Must PASS the readability gate.
_WOVEN_FRAMING = (
    "### Le texte\n\n"
    "Le discours analysé (source doc_A) est un propos politique prononcé par "
    "un locuteur en position d'autorité dans une arène publique. Le registre "
    "délibératif borne ce qu'on peut attendre de la suite.\n\n"
    "### Les enjeux\n\n"
    "Ce qui se joue est l'adoption d'une décision controversée; l'asymétrie "
    "d'information joue en faveur du locuteur, qui dispose de cadres que "
    "l'auditoire ne peut vérifier immédiatement.\n\n"
    "### Le spectre attendu\n\n"
    "Pour un discours politique, un auditeur averti doit guetter l'appel à "
    "l'autorité et l'attaque personnelle, typiques de l'arène où la "
    "disqualification prime sur le raisonnement. L'appel à la peur y est aussi "
    "probable, car l'émotion fait levier sur une décision controversée. C'est "
    "une anticipation, non une détection : l'Acte II dira ce qui a été "
    "réellement trouvé.\n\n"
    "### La lecture game-theoretic\n\n"
    "Les joueurs sont le locuteur, l'auditoire cible et un adversaire implicite; "
    "leurs intérêts divergent sur la décision, et le coup attendu du locuteur "
    "est la disqualification de l'adversaire. L'information asymétrique est son "
    "atout principal."
)

# An enumeration (bare refs + dump headings) — must NOT pass the gate.
_ENUMERATION = (
    "Argument 1: Speaker_A\n"
    "Sophisme 1: ad verecundiam (0.8)\n"
    "Sophisme 2: ad populum (0.7)\n"
)


# ============================================================================
# spectrum derivation (load-bearing DoD: derived, not hardcoded)
# ============================================================================


class TestSpectrumDerivation:
    def test_political_genre_matches_four_families(self):
        families = _load_families()
        spectrum, general = _derive_expected_spectrum(families, "politique")
        ids = {f.family_id for f in spectrum}
        assert general is False
        # All four families whose common_contexts include "politique".
        assert ids == {
            "authority_popularity",
            "emotional_appeals",
            "diversion_attack",
            "false_dilemma_simplification",
        }

    def test_unknown_genre_falls_back_to_general_full_taxonomy(self):
        families = _load_families()
        spectrum, general = _derive_expected_spectrum(families, "__unknown__")
        assert general is True
        assert len(spectrum) == len(families)  # full watch-list
        # ordered by severity descending
        weights = [f.severity_weight for f in spectrum]
        assert weights == sorted(weights, reverse=True)

    def test_specific_genre_matching_nothing_falls_back_to_general(self):
        families = _load_families()
        spectrum, general = _derive_expected_spectrum(
            families, "quantique_inédit_genre"
        )
        assert general is True
        assert len(spectrum) == len(families)

    def test_matched_spectrum_ordered_by_severity(self):
        families = _load_families()
        spectrum, _ = _derive_expected_spectrum(families, "scientifique")
        weights = [f.severity_weight for f in spectrum]
        assert weights == sorted(weights, reverse=True)


class TestGenreDerivation:
    def test_arena_takes_precedence(self):
        # The arena (concrete domain) wins over the register (Aristotelian mode)
        # because taxonomy common_contexts encode domains — a register alone
        # never narrows the expected spectrum.
        state = _state(
            stakes_and_stakeholders={
                "rhetorical_register": "Polémique",
                "discursive_arena": "marketing",
            }
        )
        genre, src = _derive_genre(state)
        assert genre == "marketing"
        assert src == "discursive_arena"

    def test_register_used_when_arena_absent(self):
        state = _state(
            stakes_and_stakeholders={"rhetorical_register": "Délibératif", "discursive_arena": ""}
        )
        genre, src = _derive_genre(state)
        assert genre == "délibératif"
        assert src == "rhetorical_register"

    def test_metadata_fallback(self):
        state = _state(
            source_metadata={"genre": "Plaidoyer"},
            stakes_and_stakeholders={"rhetorical_register": "", "discursive_arena": ""},
        )
        genre, src = _derive_genre(state)
        assert genre == "plaidoyer"
        assert "source_metadata" in src

    def test_unknown_when_nothing_present(self):
        genre, src = _derive_genre(_state())
        assert genre == "__unknown__"
        assert src == ""


# ============================================================================
# build_act1_evidence — deterministic framing bundle
# ============================================================================


class TestBuildEvidence:
    def test_metadata_is_opaque_view(self):
        ev = build_act1_evidence(_political_state())
        assert ev.metadata["speaker_role"] == "locuteur en autorité"
        assert ev.genre in ("politique", "délibératif")

    def test_stakes_and_stakeholders_populated(self):
        ev = build_act1_evidence(_political_state())
        assert ev.has_stakes is True
        assert ev.stakeholders[0].role == "locuteur"
        assert ev.arg_count == 2

    def test_long_stake_truncated(self):
        long_stake = "y" * 500
        state = _state(
            stakes_and_stakeholders={
                "rhetorical_register": "politique",
                "stakes": [{"description": long_stake}],
                "stakeholders": [],
            }
        )
        ev = build_act1_evidence(state)
        assert ev.stakes[0].endswith("[…]")
        assert len(ev.stakes[0]) <= 205

    def test_no_stakes_flag(self):
        ev = build_act1_evidence(_state())
        assert ev.has_stakes is False

    def test_spectrum_derived_not_general_for_known_genre(self):
        ev = build_act1_evidence(_political_state())
        assert ev.spectrum_available is True
        assert ev.spectrum_general is False
        assert any(f.family_id == "authority_popularity" for f in ev.expected_spectrum)


class TestPrivacy:
    def test_prompt_carries_directives(self):
        ev = build_act1_evidence(_political_state())
        prompt = build_act1_prompt(ev)
        assert "OPAQUES" in prompt  # FB-34 directive
        assert "TISSAGE" in prompt  # §4 weaving rule
        assert "HONNÊTETÉ" in prompt  # fail-loud instruction

    def test_long_metadata_truncated_in_prompt(self):
        state = _state(source_metadata={"genre": "x" * 500})
        ev = build_act1_evidence(state)
        prompt = build_act1_prompt(ev)
        assert "x" * 500 not in prompt


# ============================================================================
# weave_act1_framing — fail-loud
# ============================================================================


class TestWeaveFailLoud:
    def test_llm_error_returns_empty(self):
        ev = build_act1_evidence(_political_state())
        out = asyncio.get_event_loop().run_until_complete(
            weave_act1_framing(ev, _raising_llm(RuntimeError("boom")))  # type: ignore[arg-type]
        )
        assert out == ""

    def test_llm_empty_returns_empty(self):
        ev = build_act1_evidence(_political_state())
        out = asyncio.get_event_loop().run_until_complete(
            weave_act1_framing(ev, _stub_llm(""))  # type: ignore[arg-type]
        )
        assert out == ""


# ============================================================================
# build_act1_framing — orchestrator + §4 self-check
# ============================================================================


class TestBuildFraming:
    def test_no_llm_is_fail_loud_unavailable(self):
        result = asyncio.get_event_loop().run_until_complete(
            build_act1_framing(_political_state(), llm_callable=None)
        )
        assert result.status == "unavailable"
        assert result.narrative == ""
        assert "act1_framing" in result.degraded

    def test_woven_framing_passes_gate_self_check(self):
        """DoD: the conducted framing passes our own §4 gate."""
        result = asyncio.get_event_loop().run_until_complete(
            build_act1_framing(
                _political_state(), llm_callable=_stub_llm(_WOVEN_FRAMING)  # type: ignore[arg-type]
            )
        )
        assert result.status == "woven"
        assert result.narrative == _WOVEN_FRAMING
        assert result.gate_verdict is not None
        assert result.gate_verdict.band == "PASS", result.gate_verdict.reasons

    def test_enumeration_is_detected_honestly(self):
        result = asyncio.get_event_loop().run_until_complete(
            build_act1_framing(
                _political_state(), llm_callable=_stub_llm(_ENUMERATION)  # type: ignore[arg-type]
            )
        )
        assert result.status == "woven"
        assert result.gate_verdict is not None
        assert result.gate_verdict.band == "FAIL"
        assert result.degraded

    def test_no_stakes_recorded_as_degraded(self):
        state = _political_state()
        state.stakes_and_stakeholders = {
            "stakes": [],
            "stakeholders": [],
            "rhetorical_register": "",
            "discursive_arena": "",
        }
        result = asyncio.get_event_loop().run_until_complete(
            build_act1_framing(state, llm_callable=_stub_llm(_WOVEN_FRAMING))  # type: ignore[arg-type]
        )
        assert any("enjeux" in v.lower() for v in result.degraded.values())


# ============================================================================
# The woven fixture passes the gate independently (belt + braces)
# ============================================================================


class TestWovenFixtureIsGateCompliant:
    def test_woven_framing_passes_gate_directly(self):
        gate = ReadabilityGate()
        verdict = gate.check_body(_WOVEN_FRAMING)
        assert verdict.passed, verdict.reasons

    def test_enumeration_fails_gate_directly(self):
        gate = ReadabilityGate()
        verdict = gate.check_body(_ENUMERATION)
        assert not verdict.passed


# ============================================================================
# DoD (d): state.act1_framing is consumed by the R6 renderer end-to-end.
# ============================================================================


class TestConsumedByRenderer:
    def test_state_act1_flows_to_renderer(self):
        from argumentation_analysis.reporting.restitution.acts import RestitutionActs
        from argumentation_analysis.reporting.restitution.renderer import (
            render_restitution_report,
        )

        state = SimpleNamespace(act1_framing=_WOVEN_FRAMING)
        acts = RestitutionActs(source_id="doc_A", act1_framing=state.act1_framing)
        report = render_restitution_report(acts)
        assert _WOVEN_FRAMING.splitlines()[0] in report.markdown
        # act2/act3 are missing → reported honestly, not silently dropped.
        assert "indisponible" in report.markdown.lower() or "acte" in report.markdown.lower()
