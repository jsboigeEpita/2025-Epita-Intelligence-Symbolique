"""Tests for the post-render factual prose↔annexe cross-check (#1316, option A).

Pins the detector that closes the residual testability gap of the Tweety
inconsistency regression (#1297, po-2023 finding R487): the ``#1297`` fix pins
the *prompt* contract; this detector pins the *rendered prose*. It flags
*prose theatre* — a formal authority cited in the narrative as the source of an
inconsistency the appendix's formal-axis aggregates do not record.

All deterministic — no LLM, no JVM. The state is a plain dict (the renderer's
``state: Mapping`` contract); the body is a hand-written prose string.
"""

from __future__ import annotations

from typing import Any, Dict

from argumentation_analysis.reporting.restitution.factual_consistency_check import (
    check_factual_consistency,
)
from argumentation_analysis.reporting.restitution.readability_gate import GateVerdict

# --- state builders -----------------------------------------------------------


def _fol_all_consistent_state() -> Dict[str, Any]:
    """State where every FOL theory is consistent (0 inconsistantes) — the exact
    configuration under which the R485 artifacts claimed « Tweety confirme
    l'inconsistance » (the theatre)."""
    return {
        "fol_analysis_results": [
            {"consistent": True, "message": None},
            {"consistent": True, "message": None},
        ],
        "propositional_analysis_results": [],
        "modal_analysis_results": [],
    }


def _fol_with_inconsistance_state() -> Dict[str, Any]:
    """State where FOL actually records an inconsistency (1 inconsistante)."""
    return {
        "fol_analysis_results": [
            {"consistent": True, "message": None},
            {"consistent": False, "message": "unsatisfiable"},
        ],
    }


def _modal_inconsistent_mapping_state() -> Dict[str, Any]:
    """State where the modal axis (mapping shape) decided consistante=False."""
    return {
        "fol_analysis_results": [],
        "modal_analysis_results": {"valid": False},
    }


def _pl_insatisfiable_state() -> Dict[str, Any]:
    """State where the PL axis records an insatisfiable inference."""
    return {
        "fol_analysis_results": [],
        "modal_analysis_results": [],
        "propositional_analysis_results": [{"satisfiable": False}],
    }


def _fol_degraded_state() -> Dict[str, Any]:
    """State where every FOL theory degraded (consistent=None) — unverified, not
    inconsistent (#1019: None must not support an inconsistance claim)."""
    return {
        "fol_analysis_results": [{"consistent": None, "message": "parse-fail"}],
    }


# --- detection ---------------------------------------------------------------


def test_passes_when_no_inconsistance_claim_in_prose():
    verdict = check_factual_consistency(
        "L'analyse montre que l'argument repose sur une causalité non démontrée.",
        _fol_all_consistent_state(),
    )
    assert verdict.band == "PASS"


def test_flags_theatre_when_prose_claims_unsupported_inconsistance():
    """The canonical R485 bug: prose says « solveur Tweety confirme
    l'inconsistance » while the appendix records 0 inconsistantes."""
    verdict = check_factual_consistency(
        "Le solveur Tweety confirme l'inconsistance de cette inférence, "
        "ce qui invalide la thèse centrale.",
        _fol_all_consistent_state(),
    )
    assert verdict.band == "FAIL"
    assert any("Prose theatre" in r for r in verdict.reasons)
    assert any("#1316" in r for r in verdict.reasons)


def test_passes_when_inconsistance_claim_is_supported_by_fol():
    """Same prose wording, but FOL genuinely records an inconsistency → not
    theatre."""
    verdict = check_factual_consistency(
        "Le solveur Tweety confirme l'inconsistance de cette inférence.",
        _fol_with_inconsistance_state(),
    )
    assert verdict.band == "PASS"


def test_passes_when_inconsistance_claim_supported_by_modal_mapping():
    verdict = check_factual_consistency(
        "Le solveur révèle l'inconsistance de la théorie modale.",
        _modal_inconsistent_mapping_state(),
    )
    assert verdict.band == "PASS"


def test_passes_when_inconsistance_claim_supported_by_pl():
    verdict = check_factual_consistency(
        "Le solveur détecte une inférence insatisfaisable.",
        _pl_insatisfiable_state(),
    )
    assert verdict.band == "PASS"


def test_degraded_axis_does_not_support_inconsistance_claim():
    """A degraded axis (None) is unverified — it must NOT legitimise an
    inconsistency claim (anti None→False collapse, #1019)."""
    verdict = check_factual_consistency(
        "Le solveur Tweety confirme l'inconsistance de l'inférence.",
        _fol_degraded_state(),
    )
    assert verdict.band == "FAIL"


def test_detects_each_formal_authority_wording():
    """The detector must catch every authority wording the report prose uses,
    not just 'Tweety'."""
    state = _fol_all_consistent_state()
    for prose in (
        "Dung isole l'inconsistance du graphe.",
        "ASPIC+ démontre l'inconsistance de l'argument.",
        "SPASS prouve l'insatisfaisabilité de la théorie.",
        "le solveur confirme l'inconsistance.",
    ):
        verdict = check_factual_consistency(prose, state)
        assert verdict.band == "FAIL", f"undetected theatre: {prose!r}"


def test_ignores_inconsistance_mention_without_authority():
    """An informal « cet argument est inconsistant » (no formal authority cited)
    is a rhetorical judgement, not formal theatre — must not be flagged."""
    verdict = check_factual_consistency(
        "Cet argument est inconsistant dans sa propre logique interne.",
        _fol_all_consistent_state(),
    )
    assert verdict.band == "PASS"


# --- robustness --------------------------------------------------------------


def test_skips_silently_when_state_is_none():
    """No state → no source of truth → check is skipped honestly (PASS), never
    manufactures a verdict from missing data (#1019)."""
    verdict = check_factual_consistency(
        "Le solveur Tweety confirme l'inconsistance.", None
    )
    assert verdict.band == "PASS"


def test_returns_a_mergeable_gate_verdict():
    """The check yields a GateVerdict that merges correctly with the structural
    gate (the renderer relies on GateVerdict.merge)."""
    fail = check_factual_consistency(
        "Le solveur Tweety confirme l'inconsistance.",
        _fol_all_consistent_state(),
    )
    merged = GateVerdict(band="PASS").merge(fail)
    assert merged.band == "FAIL"
    assert merged.reasons  # reasons carried through the merge


# --- renderer integration ----------------------------------------------------


def test_renderer_flags_prose_theatre_in_final_verdict():
    """End-to-end: a rendered report whose Acte II prose commits theatre receives
    a FAIL verdict, even though every act is present and well-woven (the
    structural gate alone would PASS it — the R485 failure mode)."""
    from argumentation_analysis.reporting.restitution.acts import RestitutionActs
    from argumentation_analysis.reporting.restitution.renderer import (
        render_restitution_report,
    )

    acts = RestitutionActs(
        source_id="corpus_test",
        act1_framing=(
            "Mise en situation substantielle : le locuteur défend une thèse "
            "historique devant un auditoire varié, dans un contexte tendu."
        ),
        act2_narrative=(
            "L'argument central ne tient pas. En effet, le solveur Tweety "
            "confirme l'inconsistance de cette inférence, ce qui ruine la "
            "démonstration. Un mouvement ad hominem achève de le défaire."
        ),
        act3_conclusion=(
            "Le lecteur doit donc soupeser ces failles : la thèse ne résiste "
            "pas à l'examen formel, et l'appel à l'émotion reste à surveiller."
        ),
    )
    report = render_restitution_report(acts, state=_fol_all_consistent_state())
    assert report.verdict.band == "FAIL"
    assert any("Prose theatre" in r for r in report.verdict.reasons)


def test_renderer_passes_clean_prose_with_consistent_state():
    """Symmetric control: the same well-woven acts, with prose that does NOT
    claim an unsupported inconsistency, pass the full verdict."""
    from argumentation_analysis.reporting.restitution.acts import RestitutionActs
    from argumentation_analysis.reporting.restitution.renderer import (
        render_restitution_report,
    )

    acts = RestitutionActs(
        source_id="corpus_test",
        act1_framing=(
            "Mise en situation substantielle : le locuteur défend une thèse "
            "historique devant un auditoire varié, dans un contexte tendu."
        ),
        act2_narrative=(
            "L'argument central repose sur une analogie historique que les "
            "cadres formels n'invalident pas, mais que l'analyse rhétorique "
            "fragilise par un mouvement ad hominem."
        ),
        act3_conclusion=(
            "Le lecteur garde donc une lecture critique : la forme tient, le "
            "fond demande à être contre-argumenté."
        ),
    )
    report = render_restitution_report(acts, state=_fol_all_consistent_state())
    assert report.verdict.passed is True
