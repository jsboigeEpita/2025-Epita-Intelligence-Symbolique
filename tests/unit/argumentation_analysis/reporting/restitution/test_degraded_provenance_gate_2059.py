"""Degraded-act provenance must reach the gate verdict, not just the appendix (#2059).

``RestitutionActs.degraded`` carries ``{act_key -> reason}`` — honest provenance
written by the act generators and already printed under the act by the renderer.
The gate, however, judged the three acts on forms only: a degraded but well-formed
act passed as a full ``PASS`` with zero reasons. These tests pin the corrected
contract — a degraded act caps the band at ``WARN`` (never ``FAIL``: degraded is
a documented, legitimate mode) and cites the stored motif verbatim in ``reasons``.

No JVM, no LLM, no network — deterministic structural checks only (CI-safe).
"""

from __future__ import annotations

from argumentation_analysis.reporting.restitution.acts import RestitutionActs
from argumentation_analysis.reporting.restitution.readability_gate import (
    ReadabilityGate,
)

# Woven act bodies (well-anchored, no bare refs, no taxonomy codes, no dump
# headings) — the same canonical fixtures as test_readability_gate.py.
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

_MOTIF = "générateur LLM indisponible — repli gabarit"


def _woven_acts() -> RestitutionActs:
    return RestitutionActs(
        act1_framing=_WOVEN_ACT1,
        act2_narrative=_WOVEN_ACT2,
        act3_conclusion=_WOVEN_ACT3,
        source_id="doc_A",
    )


class TestDegradedProvenance:
    def test_degraded_act_is_not_a_pass_and_cites_the_stored_motif(self):
        acts = _woven_acts()
        acts.degraded = {RestitutionActs.act_key(1): _MOTIF}

        verdict = ReadabilityGate().check_acts(acts)

        assert verdict.band != "PASS", verdict.reasons
        assert any(_MOTIF in reason for reason in verdict.reasons)

    def test_degraded_act_caps_at_warn_not_fail(self):
        # Anti-pendule: a degraded act was still emitted and stays readable —
        # the verdict must say "diminished", not block the report.
        acts = _woven_acts()
        acts.degraded = {RestitutionActs.act_key(2): _MOTIF}

        verdict = ReadabilityGate().check_acts(acts)

        assert verdict.band == "WARN", verdict.reasons
        assert verdict.passed is True

    def test_negative_control_clean_acts_still_pass_silent(self):
        # The same three acts with no degradation must keep the exact PASS/[]
        # verdict — the new control cannot redden on its own.
        acts = _woven_acts()
        acts.degraded = {}

        verdict = ReadabilityGate().check_acts(acts)

        assert verdict.band == "PASS"
        assert verdict.reasons == []

    def test_full_verdict_inherits_the_degraded_warn(self):
        acts = _woven_acts()
        acts.degraded = {RestitutionActs.act_key(3): _MOTIF}

        verdict = ReadabilityGate().check(acts)

        assert verdict.band == "WARN", verdict.reasons
        assert any(_MOTIF in reason for reason in verdict.reasons)

    def test_missing_act_still_dominates_as_fail(self):
        # Absence stays the worse verdict: an act that never ran is FAIL, with
        # or without a degradation entry — the new WARN control cannot soften it.
        acts = _woven_acts()
        acts.act1_framing = ""
        acts.degraded = {RestitutionActs.act_key(1): _MOTIF}

        verdict = ReadabilityGate().check_acts(acts)

        assert verdict.band == "FAIL"
        assert not verdict.passed
