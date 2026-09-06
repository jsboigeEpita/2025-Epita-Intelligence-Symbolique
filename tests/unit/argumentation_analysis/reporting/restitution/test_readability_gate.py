"""Tests for the readability gate — the weaving rule (spec §4), mechanically.

The gate is the anti-énumération contract: a framework citation must be anchored
on a narrative beat, never dropped as a bare "name (score)". These tests pin the
canonical woven/bare contrast from the spec and the WARN/FAIL thresholds.

No JVM, no LLM, no network — deterministic structural checks only (CI-safe).
"""

from __future__ import annotations

import pytest

from argumentation_analysis.reporting.restitution.acts import RestitutionActs
from argumentation_analysis.reporting.restitution.readability_gate import (
    GateVerdict,
    ReadabilityGate,
    ReaderCheckResult,
    _line_is_bare,
)

# --- woven act bodies (well-anchored, no bare refs) ---------------------------

_WOVEN_ACT1 = (
    "Le discours analysé (source doc_A) est un propos politique à visée "
    "persuasive. L'orateur cherche à mobiliser l'auditoire sur une décision "
    "controversée; l'asymétrie d'information joue en sa faveur. Un auditeur "
    "averti doit guetter l'appel à l'autorité et la fausse causalité, typiques "
    "de ce genre. Les joueurs sont l'orateur, l'auditoire cible et un adversaire "
    "implicite; le coup attendu est la disqualification de l'adversaire."
)

_WOVEN_ACT2 = (
    "Le premier mouvement argumentatif appuie la thèse sur une autorité "
    "externe. Cette autorité ne satisfait pas la question critique de fiabilité: "
    "c'est une exception au scheme ExpertOpinion (ancrage AIF/Walton), et le "
    "solveur Tweety confirme l'inconsistance de l'inférence sous-jacente. "
    "Le cadre de Dung isole ensuite cette attaque comme défaillante. Le second "
    "mouvement enchaîne sur une généralisation hâtive, que la vertu de "
    "pertinence éclaire comme un dérapage."
)

_WOVEN_ACT3 = (
    "L'analyse conclut à un discours structurellement fragile sur l'axe "
    "formel: la synthèse honnête, gated par les dimensions non-triviales, "
    "caractérise un propos qui tient sur l'affect mais cède sur la logique. "
    "Pour contrer: viser la question critique de fiabilité qui fait basculer "
    "l'appel à l'autorité. À attendre ensuite: un glissement vers l'ad hominem."
)


def _woven_acts() -> RestitutionActs:
    return RestitutionActs(
        act1_framing=_WOVEN_ACT1,
        act2_narrative=_WOVEN_ACT2,
        act3_conclusion=_WOVEN_ACT3,
        source_id="doc_A",
    )


# --- the canonical woven/bare contrast (spec §4) ------------------------------


class TestBareReferenceDetection:
    """The line-level detector: what is a bare framework ref, what is woven."""

    def test_canonical_bare_example_flagged(self):
        # The exact counter-example from spec §4.
        line = "Sophisme : ad verecundiam (score 0.8)"
        assert _line_is_bare(line) is True

    def test_canonical_woven_example_not_flagged(self):
        # The exact narration example from spec §4.
        line = "le solveur Tweety confirme l'inconsistance de l'inférence"
        assert _line_is_bare(line) is False

    def test_woven_with_score_and_verb_not_bare(self):
        # A framework + a score, BUT anchored by a narrative verb → woven.
        line = "Le cadre de Dung isole cette attaque (poids 0.3)."
        assert _line_is_bare(line) is False

    def test_year_in_parens_not_a_score(self):
        line = "Dung (1995) définit les extensions préférées."
        assert _line_is_bare(line) is False

    def test_plain_sentence_no_framework_not_bare(self):
        line = "La pertinence de l'argument est faible."
        assert _line_is_bare(line) is False

    def test_confidence_label_bare(self):
        line = "ad hominem (confiance: 0.7)"
        assert _line_is_bare(line) is True

    def test_aspic_bare_without_verb(self):
        line = "ASPIC+ : attaque (score 0.65)"
        assert _line_is_bare(line) is True


# --- thresholds: presence + WARN/FAIL by bare-ref count -----------------------


class TestGateThresholds:
    gate = ReadabilityGate()

    def test_three_woven_acts_pass(self):
        verdict = self.gate.check(_woven_acts())
        assert verdict.band == "PASS", verdict.reasons
        assert verdict.passed is True

    def test_missing_act_fails(self):
        acts = _woven_acts()
        acts.act2_narrative = ""
        verdict = self.gate.check(acts)
        assert verdict.band == "FAIL"
        assert any("Acte II absent" in r for r in verdict.reasons)
        assert verdict.passed is False

    def test_one_bare_ref_passes_with_note(self):
        # A single residual bare ref is tolerated (PASS) but reported.
        acts = _woven_acts()
        acts.act2_narrative += "\n\nSophisme : ad populum (score 0.6)"
        verdict = self.gate.check(acts)
        assert verdict.band == "PASS"
        assert any("nue" in r for r in verdict.reasons)

    def test_two_bare_refs_warn(self):
        acts = _woven_acts()
        acts.act2_narrative += (
            "\n\nSophisme : ad populum (score 0.6)"
            "\nSophisme : ad baculum (score 0.55)"
        )
        verdict = self.gate.check(acts)
        assert verdict.band == "WARN"
        assert verdict.passed is True  # WARN is still readable

    def test_three_bare_refs_fail(self):
        acts = _woven_acts()
        acts.act2_narrative += (
            "\n\nSophisme : ad populum (score 0.6)"
            "\nSophisme : ad baculum (score 0.55)"
            "\nSophisme : ad misericordiam (score 0.5)"
        )
        verdict = self.gate.check(acts)
        assert verdict.band == "FAIL"
        assert any("énumération" in r.lower() or "3" in r for r in verdict.reasons)

    def test_dump_headings_fail(self):
        # The dimensional-dump smell: numbered "Sophisme N:" headings inside an act.
        acts = _woven_acts()
        acts.act2_narrative = (
            "Analyse:\n"
            "### Sophisme 1: ad hominem\nquelque chose.\n"
            "### Sophisme 2: ad populum\nautre chose.\n"
            "### Sophisme 3: straw man\nencore."
        )
        verdict = self.gate.check(acts)
        assert verdict.band == "FAIL"
        assert any("énumération dimensionnelle" in r for r in verdict.reasons)


class TestTaxonomyCodeDetection:
    """#2031: a dotted taxonomy address is never reader prose.

    Real observed shapes, from the measured artifacts:
    - September run: parenthesised next to the fallacy name —
      "(6.1.3.1.2)", "(1.1.2.1)", "(5.1.2.3.2.1)", "(2.2.2.4.1)",
      "(6.3.1.2.1.1)" — 16 occurrences in Act II.
    - July run: bracketed with a label — "[descente: 5.2.1.1]",
      "[descente: 2.1.1.4?]" (the trailing ? is the LLM hedging) — 9
      occurrences in Act II.
    The detector must catch every wrapper; decimals, versions, years and
    scores must stay legitimate prose.
    """

    gate = ReadabilityGate()

    def test_find_codes_all_observed_wrappers(self):
        from argumentation_analysis.reporting.restitution.readability_gate import (
            _find_taxonomy_codes,
        )

        text = (
            "l'« Exagération » (6.1.3.1.2) et « Comparaison incomplète » "
            "(5.1.2.3.2.1) ; l'« Appel à la fierté » [descente: 2.2.1.3.3] "
            "et l'« Acception vague » [descente: 5.1.1], nu 6.3.1.2.1.1, "
            "hedge [descente: 2.1.1.4?]."
        )
        found = _find_taxonomy_codes(text)
        assert sorted(found) == sorted(
            [
                "6.1.3.1.2",
                "5.1.2.3.2.1",
                "2.2.1.3.3",
                "5.1.1",
                "6.3.1.2.1.1",
                "2.1.1.4",
            ]
        )

    def test_legitimate_numbers_not_flagged(self):
        from argumentation_analysis.reporting.restitution.readability_gate import (
            _find_taxonomy_codes,
        )

        text = (
            "1.5 million de lecteurs, une version Tweety 1.31, l'année 1789, "
            "un score de (0.8), arg_1 visé par 2 arguments, et 2 500 données."
        )
        assert _find_taxonomy_codes(text) == []

    def test_one_residual_code_warns(self):
        acts = _woven_acts()
        acts.act2_narrative += "\n\nL'« Exagération » (6.1.3.1.2) appuie ce mouvement."
        verdict = self.gate.check(acts)
        assert verdict.band == "WARN"
        assert verdict.passed is True
        # #2046: the reason computes the agreement — 1 → singular.
        assert any("1 code de taxonomie brut" in r for r in verdict.reasons)

    def test_three_codes_fail(self):
        # The July artifact's measured density (9) and September's (16) both
        # sit far above this threshold — 3 is the manifest-leak band.
        acts = _woven_acts()
        acts.act2_narrative += (
            "\n\nL'« Exagération » (6.1.3.1.2), l'« Effet de halo » "
            "(2.2.1.1.1) et l'« Acception vague » (5.1.1) marquent le passage."
        )
        verdict = self.gate.check(acts)
        assert verdict.band == "FAIL"
        assert verdict.passed is False
        # #2046: the reason computes the agreement — 3 → plural.
        assert any("3 codes de taxonomie bruts" in r for r in verdict.reasons)

    def test_body_check_flags_leak_without_acts(self):
        from argumentation_analysis.reporting.restitution.readability_gate import (
            _find_taxonomy_codes,
        )

        body = (
            "Le mouvement tient par la comparaison « Exagération » "
            "[descente: 6.1.1.1.1.2] répétée deux fois."
        )
        verdict = self.gate.check_body(body)
        assert verdict.band == "WARN"
        assert len(_find_taxonomy_codes(body)) == 1


# --- verdict merging & reader-check ------------------------------------------


class TestVerdictMechanics:

    def test_merge_takes_worse_band(self):
        a = GateVerdict(band="PASS", reasons=["a"])
        b = GateVerdict(band="FAIL", reasons=["b"])
        merged = a.merge(b)
        assert merged.band == "FAIL"
        assert merged.reasons == ["a", "b"]

    def test_reader_check_failure_fails(self):
        def _failing_reader(_body: str) -> ReaderCheckResult:
            return ReaderCheckResult(
                passed=False, total_questions=3, failed_questions=2
            )

        gate = ReadabilityGate(reader_check=_failing_reader)
        verdict = gate.check(_woven_acts())
        assert verdict.band == "FAIL"
        assert any("Reader-check" in r for r in verdict.reasons)

    def test_reader_check_pass_notes_it(self):
        def _passing_reader(_body: str) -> ReaderCheckResult:
            return ReaderCheckResult(passed=True, total_questions=3, failed_questions=0)

        gate = ReadabilityGate(reader_check=_passing_reader)
        verdict = gate.check(_woven_acts())
        assert verdict.band == "PASS"
        assert any("Reader-check passé" in r for r in verdict.reasons)

    def test_reasons_specific_on_missing(self):
        acts = RestitutionActs(
            act1_framing="", act2_narrative="x" * 200, act3_conclusion="y" * 200
        )
        verdict = ReadabilityGate().check(acts)
        assert any("Acte I absent" in r for r in verdict.reasons)
