"""#1907 — tri-state virtue outcomes: evaluated / not applicable / unavailable.

Context (measured firsthand on 142 real quality records, R871):

    virtue                    %zero   max    verdict
    refutation_constructive   100%    0.00   constant — 0 bit
    structure_logique         100%    0.00   constant — 0 bit
    analogie_pertinente       100%    0.00   constant — 0 bit
    fiabilite_sources         100%    0.00   constant — 0 bit
    presence_sources           94%    0.50   near-constant
    exhaustivite               93%    0.50   near-constant
    clarte                      0%    1.00   real signal
    pertinence                  0%    0.50   real signal
    redondance_faible           0%    1.00   constant *at 1.0* — 0 bit, +1.0 to every score

    note_finale: min 1.40 max 2.50 mean 1.76 — rendered on a "/10" surface
    input unit: median 94 chars, 1 sentence, 88% under 5 sentences

Seven of nine virtues were not measuring anything: they were asserting a
default. ``detect_exhaustivite`` says so in its own comment — "Texte trop
court pour juger de l'exhaustivite" — and then returns ``0.0`` anyway. That
is the invalid inference #1907 asks to remove *first*: an isolated extracted
claim cannot carry a bibliography, a rebuttal, or essay-level coverage, so
scoring those dimensions zero grades the extractor's slicing, not the speaker.

The contract under test: a virtue declares the *context level* it requires
(claim / local passage / whole document); the evaluator declares the level it
received; ``required > received`` yields NOT_APPLICABLE, never 0.0. A detector
that raises yields UNAVAILABLE, also never 0.0.
"""

import pytest

from argumentation_analysis.agents.core.quality.quality_evaluator import (
    VERTUES,
    ArgumentQualityEvaluator,
    ContextLevel,
    VirtueStatus,
    VIRTUE_CONTEXT_REQUIREMENTS,
    infer_context_level,
)

# A single extracted claim — the unit the real corpus actually feeds (median
# 94 chars, 1 sentence). Synthetic, no corpus content.
ISOLATED_CLAIM = "La hausse des prix de l'énergie provient de la spéculation."

# A full-document unit. Every marker below is verbatim from
# ``ressources_argumentatives.json`` so the lexical detectors can actually
# fire: "selon"/"comme le montre" (citation_patterns), OMS/OCDE
# (credible_sources), "on pourrait objecter" (marqueurs_refutation),
# "comparable à" (patterns_analogies).
DOCUMENT = (
    "Selon l'OMS, la pollution de l'air cause sept millions de décès par an. "
    "D'abord, les particules fines pénètrent le système respiratoire ; ainsi, "
    "elles provoquent des inflammations chroniques. "
    "Comme le montre l'OCDE, le coût sanitaire dépasse le coût réglementaire. "
    "On pourrait objecter que la charge économique serait prohibitive, car les "
    "industries devraient investir. "
    "Cependant ce raisonnement est comparable à celui d'un propriétaire qui "
    "diffère une réparation : le report coûte plus cher. "
    "Donc la réglementation doit être renforcée, puisque l'inaction reste le "
    "scénario le plus onéreux."
)


class TestVirtueContextTaxonomy:
    """The taxonomy itself — every virtue declares a context requirement."""

    def test_every_virtue_declares_a_context_requirement(self):
        assert set(VIRTUE_CONTEXT_REQUIREMENTS) == set(VERTUES), (
            "#1907: a virtue with no declared context requirement would fall "
            "back to being scored at any input size — the exact invalid "
            "inference this issue removes."
        )

    def test_claim_level_virtues_are_the_two_with_real_variance(self):
        """Derived from the issue prose, cross-checked against 142 records.

        Only ``clarte`` and ``pertinence`` showed non-degenerate distributions
        on real isolated claims. If a third virtue is declared CLAIM-level,
        it must be because it genuinely varies at that unit.
        """
        claim_level = {
            v
            for v, lvl in VIRTUE_CONTEXT_REQUIREMENTS.items()
            if lvl == ContextLevel.CLAIM
        }
        assert claim_level == {"clarte", "pertinence"}


class TestInapplicableIsNotZero:
    """DoD 1 + 3 — the core of #1907."""

    def test_isolated_claim_marks_document_virtues_not_applicable(self):
        result = ArgumentQualityEvaluator().evaluate(
            ISOLATED_CLAIM, context_level=ContextLevel.CLAIM
        )
        statuses = result["statuts_par_vertu"]
        for vertu in ("exhaustivite", "presence_sources", "refutation_constructive"):
            assert statuses[vertu] == VirtueStatus.NOT_APPLICABLE, (
                f"#1907: {vertu} requires document-level context; on an isolated "
                f"claim it must be honestly absent, got {statuses[vertu]!r}."
            )

    def test_inapplicable_virtues_carry_no_score_at_all(self):
        """Absence must be absence — not a zero that averages like a failure."""
        result = ArgumentQualityEvaluator().evaluate(
            ISOLATED_CLAIM, context_level=ContextLevel.CLAIM
        )
        scores = result["scores_par_vertu"]
        assert "exhaustivite" not in scores
        assert scores.get("exhaustivite") != 0.0
        # ...while the applicable ones are present and real.
        assert "clarte" in scores and "pertinence" in scores

    def test_aggregate_denominator_excludes_inapplicable(self):
        """DoD 3 — the /9 denominator is what made every argument look terrible."""
        result = ArgumentQualityEvaluator().evaluate(
            ISOLATED_CLAIM, context_level=ContextLevel.CLAIM
        )
        scores = result["scores_par_vertu"]
        assert result["note_moyenne"] == pytest.approx(
            sum(scores.values()) / len(scores)
        )
        assert result["note_max_applicable"] == pytest.approx(float(len(scores))), (
            "#1907: the reader needs the ceiling that was actually reachable, "
            "otherwise a perfect claim still reads as a low grade."
        )

    def test_document_unit_unlocks_the_document_virtues(self):
        """The discriminator: the SAME evaluator, a richer unit, more evaluated
        dimensions. If everything were marked N/A regardless of input, this
        test would fail — that is what makes the one above meaningful."""
        result = ArgumentQualityEvaluator().evaluate(
            DOCUMENT, context_level=ContextLevel.DOCUMENT
        )
        statuses = result["statuts_par_vertu"]
        assert all(
            s == VirtueStatus.EVALUATED for s in statuses.values()
        ), f"at document level every virtue is applicable, got {statuses}"
        assert len(result["scores_par_vertu"]) == len(VERTUES)


class TestGenuineZeroStaysZero:
    """Anti-pendulum — #1907 forbids replacing low numbers with flattering prose.

    The tri-state must not become a machine for relabelling every zero as
    "not applicable". A document that *could* cite sources and does not has
    genuinely failed that dimension, and must still be scored 0.0.
    """

    # Five plain sentences: document-level, yet carrying no citation, no
    # credible-source name, no rebuttal marker and no analogy pattern.
    UNSUPPORTED_DOCUMENT = (
        "Le prix du logement augmente dans les grandes villes. "
        "Les loyers pèsent lourdement sur les ménages modestes. "
        "La construction neuve reste insuffisante depuis dix ans. "
        "Les délais administratifs allongent chaque projet immobilier. "
        "Le parc social ne se renouvelle plus assez vite."
    )

    def test_absence_that_the_unit_could_have_carried_is_still_a_zero(self):
        result = ArgumentQualityEvaluator().evaluate(self.UNSUPPORTED_DOCUMENT)
        assert result["contexte_evalue"] == ContextLevel.DOCUMENT
        statuses = result["statuts_par_vertu"]
        scores = result["scores_par_vertu"]

        assert statuses["presence_sources"] == VirtueStatus.EVALUATED, (
            "#1907 anti-pendulum: a document-level unit CAN carry citations; "
            "finding none is a verdict, not an inapplicability."
        )
        assert scores["presence_sources"] == 0.0
        assert statuses["refutation_constructive"] == VirtueStatus.EVALUATED
        assert scores["refutation_constructive"] == 0.0

    def test_dependency_rule_fires_when_there_is_nothing_to_assess(self):
        """``fiabilite_sources`` over a text that cites nothing is undefined,
        not zero: there are no sources whose reliability could be wrong."""
        result = ArgumentQualityEvaluator().evaluate(self.UNSUPPORTED_DOCUMENT)
        assert result["scores_par_vertu"]["presence_sources"] == 0.0
        assert (
            result["statuts_par_vertu"]["fiabilite_sources"]
            == VirtueStatus.NOT_APPLICABLE
        )
        assert "fiabilite_sources" not in result["scores_par_vertu"]


class TestUnavailableIsNotZeroEither:
    """DoD 1, third state — a failed dependency is not a measured zero."""

    def test_raising_detector_yields_unavailable_not_a_zero_score(self):
        def _broken(text):
            raise ValueError("dependency down")

        evaluator = ArgumentQualityEvaluator(
            detectors={"clarte": _broken, "pertinence": lambda t: (0.5, "ok")}
        )
        result = evaluator.evaluate(ISOLATED_CLAIM, context_level=ContextLevel.CLAIM)
        assert result["statuts_par_vertu"]["clarte"] == VirtueStatus.UNAVAILABLE
        assert "clarte" not in result["scores_par_vertu"], (
            "#1907: a detector that crashed contributes no measurement; "
            "recording 0.0 makes an outage indistinguishable from a verdict."
        )
        # The surviving virtue still aggregates honestly over itself alone.
        assert result["note_moyenne"] == pytest.approx(0.5)
        assert result["note_max_applicable"] == pytest.approx(1.0)


class TestContextInference:
    """Callers that pass only text must not silently get DOCUMENT treatment."""

    def test_short_claim_infers_claim_level(self):
        assert infer_context_level(ISOLATED_CLAIM) == ContextLevel.CLAIM

    def test_document_infers_document_level(self):
        assert infer_context_level(DOCUMENT) == ContextLevel.DOCUMENT

    def test_legacy_single_argument_call_does_not_assume_document(self):
        """The ~40 existing call sites pass text only. Before #1907 they got
        nine scores including seven fabricated zeros."""
        result = ArgumentQualityEvaluator().evaluate(ISOLATED_CLAIM)
        assert result["contexte_evalue"] == ContextLevel.CLAIM
        assert len(result["scores_par_vertu"]) < len(VERTUES)


class TestPopulationBand:
    """DoD 7 — a degenerate corpus-wide band must not silently return."""

    def test_reported_band_is_not_degenerate_across_a_population(self):
        claims = [
            "Le chômage baisse.",
            "La hausse des prix provient de la spéculation, car les stocks "
            "restent au plus haut.",
            "Il faut donc réformer, puisque le système est à bout de souffle, "
            "et ainsi agir vite.",
            "Ce texte-ci répète, répète, répète et répète encore la même chose.",
        ]
        evaluator = ArgumentQualityEvaluator()
        normalised = []
        for claim in claims:
            r = evaluator.evaluate(claim)
            ceiling = r["note_max_applicable"]
            assert (
                ceiling > 0
            ), "a unit with zero applicable virtues must be reported, not scored"
            normalised.append(r["note_finale"] / ceiling)

        assert max(normalised) - min(normalised) > 0.15, (
            "#1907 DoD 7: the normalised score band collapsed — the instrument "
            f"is not discriminating between visibly different claims: {normalised}. "
            "A constant dimension inflates every score without ranking anything."
        )
        assert max(normalised) <= 1.0
