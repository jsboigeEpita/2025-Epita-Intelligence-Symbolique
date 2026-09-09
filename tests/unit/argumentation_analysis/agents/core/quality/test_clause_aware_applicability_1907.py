"""#1907 — clause-aware applicability, rule R2 (coordinator arbitration, R950).

Measured background (R952/R961, gitignored artifacts, aggregates only): the
sub-30-word single-sentence region of the real corpus holds 47 units, and 12
of them (25.5%) carry local structure — a refutation, an analogy or a causal
chain — that the CLAIM band makes unevaluable. Nine of the twelve sit in the
20-29 word band, exactly where the word threshold decides. A deterministic
clause proxy captures 11 of the 12.

The arbitration (R950): admit those units for the three structural virtues
only, with rule R2 — at least one strong separator (";", ":" or a connector
from the existing ``connecteurs_structure_logique`` resource; no second
taxonomy) OR at least two commas. The admission lives in the per-virtue
applicability decision, never as a third gate of ``infer_context_level``, so
``redondance_faible`` keeps its measured >= 30-word floor: it scored a flat
1.00 on 47/47 sub-30-word units, and admitting it would reopen the degenerate
band the tri-state closed.

Honest bounds carried by this rule, by construction of the measured
calibration:

- recall bound 11/12: the one structure-bearing unit that carries no
  punctuation at all stays NOT_APPLICABLE. That is a family bound of any
  punctuation-based rule — assumed, not repaired (anti-pendulum: no
  threshold tuning to pass one example).
- cost 11/35: non-bearing units admitted by R2 are *evaluated*; when no
  chain fires they produce a legitimate evaluated 0.0 (tri-state), never a
  fabricated score. The denominator changes; the honesty does not.
"""

import pytest

from argumentation_analysis.agents.core.quality.quality_evaluator import (
    ArgumentQualityEvaluator,
    ContextLevel,
    VirtueStatus,
    infer_context_level,
    is_multi_clause,
)

STRUCTURAL_VIRTUES = (
    "refutation_constructive",
    "analogie_pertinente",
    "structure_logique",
)

# All fixtures below are synthetic. Word counts stay in the CLAIM band
# (< 2 sentences AND < 30 words) so the admission rule — not the word gate
# of ``infer_context_level`` — is what decides applicability.
R2_CONNECTOR = "Le rapport met en cause la règle car elle date de 1990."
R2_SEMICOLON = "L'urgence est réelle ; reporter coûtera plus cher."
R2_COLON = "Un seul choix reste : tenir le cap jusqu'à l'hiver."
R2_TWO_COMMAS = "Si le prix monte, la demande baisse, et l'emploi suit."
ENUMERATION_TWO_COMMAS = "Les États-Unis, la Chine, et l'Inde signent l'accord."
SINGLE_COMMA = "Malgré tout, la courbe reste plate."
NO_PUNCTUATION = "La commission valide le texte sans débattre"
# >= 30 words, single sentence, no clause marker: the existing word gate
# already makes this LOCAL_CONTEXT — behavior there must not change.
WORDY_SINGLE_SENTENCE = (
    "Le conseil régional a publié ce matin un communiqué détaillant les "
    "prochaines étapes de la réforme annoncée la semaine dernière lors de la "
    "conférence de presse sur le budget partagé de l'année prochaine."
)


class TestR2Predicate:
    """The deterministic clause test itself."""

    @pytest.mark.parametrize(
        "text",
        [R2_CONNECTOR, R2_SEMICOLON, R2_COLON, R2_TWO_COMMAS, ENUMERATION_TWO_COMMAS],
    )
    def test_multi_clause_units_pass(self, text):
        assert is_multi_clause(text)

    @pytest.mark.parametrize(
        "text", [SINGLE_COMMA, NO_PUNCTUATION, WORDY_SINGLE_SENTENCE]
    )
    def test_non_carriers_fail(self, text):
        assert not is_multi_clause(text)


class TestR2AdmitsStructuralVirtues:
    """Born-red: on main these units are NOT_APPLICABLE — the measured false
    negatives (12/47 structure-bearing units locked out by the word gate)."""

    @pytest.mark.parametrize(
        "text", [R2_CONNECTOR, R2_SEMICOLON, R2_COLON, R2_TWO_COMMAS]
    )
    def test_structural_virtues_become_applicable(self, text):
        assert infer_context_level(text) == ContextLevel.CLAIM, (
            "fixture must sit in the CLAIM band so the clause rule, not the "
            "word gate, is under test"
        )
        result = ArgumentQualityEvaluator().evaluate(text)
        statuses = result["statuts_par_vertu"]
        for vertu in STRUCTURAL_VIRTUES:
            assert statuses[vertu] == VirtueStatus.EVALUATED, (
                f"#1907 R2: a multi-clause unit carries judgeable structure; "
                f"{vertu} must be evaluated, got {statuses[vertu]!r} on {text!r}"
            )
            assert vertu in result["scores_par_vertu"]

    def test_denominator_grows_with_the_admitted_virtues(self):
        """clarte + pertinence (CLAIM virtues) + the three structural ones:
        the ceiling the reader is shown must reflect what was actually judged."""
        result = ArgumentQualityEvaluator().evaluate(R2_CONNECTOR)
        assert result["note_max_applicable"] == pytest.approx(5.0)

    def test_declared_claim_level_gets_the_same_admission(self):
        """Applicability is a property of the input unit, not of who declared
        the level: an explicitly-declared CLAIM is admitted the same way."""
        result = ArgumentQualityEvaluator().evaluate(
            R2_CONNECTOR, context_level=ContextLevel.CLAIM
        )
        assert (
            result["statuts_par_vertu"]["structure_logique"] == VirtueStatus.EVALUATED
        )


class TestR2KeepsNonCarriersHonest:
    """The negatives of the calibration — what must NOT be admitted."""

    def test_single_comma_stays_not_applicable(self):
        result = ArgumentQualityEvaluator().evaluate(SINGLE_COMMA)
        for vertu in STRUCTURAL_VIRTUES:
            assert result["statuts_par_vertu"][vertu] == VirtueStatus.NOT_APPLICABLE, (
                "#1907 R2: one comma is the weak enumeration signal R0 was "
                f"rejected for; {vertu} must stay absent."
            )

    def test_no_punctuation_stays_not_applicable(self):
        """The 1/12 family bound: adversative content without any punctuation
        is not catchable by a punctuation-based rule. Assumed NA, not repaired."""
        result = ArgumentQualityEvaluator().evaluate(NO_PUNCTUATION)
        for vertu in STRUCTURAL_VIRTUES:
            assert result["statuts_par_vertu"][vertu] == VirtueStatus.NOT_APPLICABLE
            assert vertu not in result["scores_par_vertu"]

    def test_enumeration_commas_admit_and_produce_an_evaluated_zero(self):
        """The declared cost (11/35): enumeration commas are not clauses, so
        the unit is admitted and honestly scored 0.0 — an evaluated verdict,
        distinct from NOT_APPLICABLE. This pins the tri-state distinction."""
        result = ArgumentQualityEvaluator().evaluate(ENUMERATION_TWO_COMMAS)
        assert (
            result["statuts_par_vertu"]["structure_logique"] == VirtueStatus.EVALUATED
        )
        assert result["scores_par_vertu"]["structure_logique"] == 0.0


class TestRedondanceFloorUnchanged:
    """``redondance_faible`` is deliberately NOT clause-aware: its sub-30-word
    band is degenerate (flat 1.00 on 47/47 measured units)."""

    @pytest.mark.parametrize(
        "text",
        [R2_CONNECTOR, R2_SEMICOLON, R2_COLON, R2_TWO_COMMAS, ENUMERATION_TWO_COMMAS],
    )
    def test_redondance_faible_stays_not_applicable_on_admitted_units(self, text):
        result = ArgumentQualityEvaluator().evaluate(text)
        assert (
            result["statuts_par_vertu"]["redondance_faible"]
            == VirtueStatus.NOT_APPLICABLE
        ), (
            "#1907: the clause admission must stay per-virtue; opening "
            "redondance_faible below 30 words reopens the flat +1.0 band."
        )
        assert "redondance_faible" not in result["scores_par_vertu"]


class TestNoThirdGate:
    """Design guard: the admission must not leak into ``infer_context_level``."""

    @pytest.mark.parametrize("text", [R2_CONNECTOR, R2_SEMICOLON, R2_TWO_COMMAS])
    def test_inference_unchanged_on_multi_clause_claims(self, text):
        assert infer_context_level(text) == ContextLevel.CLAIM, (
            "#1907 design guard: a third clause gate in infer_context_level "
            "would also admit redondance_faible and the DOCUMENT virtues' "
            "taxonomy neighbour — the admission is per-virtue only."
        )


class TestUnchangedRegions:
    """Everything outside the arbitration stays byte-for-byte the same."""

    def test_wordy_single_sentence_stays_local_by_word_gate(self):
        result = ArgumentQualityEvaluator().evaluate(WORDY_SINGLE_SENTENCE)
        assert result["contexte_evalue"] == ContextLevel.LOCAL_CONTEXT
        assert (
            result["statuts_par_vertu"]["structure_logique"] == VirtueStatus.EVALUATED
        )
        assert (
            result["statuts_par_vertu"]["redondance_faible"] == VirtueStatus.EVALUATED
        )

    def test_document_virtues_stay_not_applicable_on_admitted_units(self):
        result = ArgumentQualityEvaluator().evaluate(R2_CONNECTOR)
        for vertu in ("exhaustivite", "presence_sources", "fiabilite_sources"):
            assert result["statuts_par_vertu"][vertu] == VirtueStatus.NOT_APPLICABLE

    def test_claim_virtues_unchanged(self):
        result = ArgumentQualityEvaluator().evaluate(R2_CONNECTOR)
        for vertu in ("clarte", "pertinence"):
            assert result["statuts_par_vertu"][vertu] == VirtueStatus.EVALUATED
