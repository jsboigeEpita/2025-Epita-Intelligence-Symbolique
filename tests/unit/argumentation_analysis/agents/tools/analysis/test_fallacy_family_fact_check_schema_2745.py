"""#2745 — one fact-check implication schema, producer to consumer.

The producer (``ExternalVerificationPlugin._analyze_fallacy_implications``)
names a fallacy species when a claim verifies false; the consumer
(``FallacyFamilyAnalyzer._integrate_fact_checking``) integrates those
implications per family. Before #2745 the producer omitted the
``fallacy_family`` field the consumer matches on, so real producer-shaped
implications matched no family: 0 relevant checks, 0 credibility impact —
only the test mock emitted the field. These tests drive the real producer
shape end to end.
"""

import pytest

from argumentation_analysis.agents.tools.analysis.fact_claim_extractor import (
    ClaimType,
    ClaimVerifiability,
    FactualClaim,
)
from argumentation_analysis.agents.tools.analysis.fallacy_family_analyzer import (
    FallacyFamily,
    FallacyFamilyAnalyzer,
)
from argumentation_analysis.plugin_framework.core.plugins.standard.external_verification.plugin import (
    ExternalVerificationPlugin,
)
from argumentation_analysis.services.fact_verification_service import (
    VerificationStatus,
)


def _make_claim(text: str, claim_type: ClaimType = ClaimType.CAUSAL) -> FactualClaim:
    return FactualClaim(
        claim_text=text,
        claim_type=claim_type,
        verifiability=ClaimVerifiability.HIGHLY_VERIFIABLE,
        confidence=0.9,
        context="",
        start_pos=0,
        end_pos=len(text),
        entities=[],
        keywords=[],
        temporal_references=[],
        numerical_values=[],
        sources_mentioned=[],
        extraction_method="test_2745",
    )


@pytest.fixture
def producer() -> ExternalVerificationPlugin:
    return ExternalVerificationPlugin()


@pytest.fixture
def analyzer() -> FallacyFamilyAnalyzer:
    return FallacyFamilyAnalyzer()


class TestProducerSchema:
    """The implication records the family the species belongs to (#2745)."""

    def test_sweeping_false_claim_names_generalization_family(self, producer):
        implications = producer._analyze_fallacy_implications(
            _make_claim("Tous les politiciens mentent toujours"),
            VerificationStatus.VERIFIED_FALSE,
            [],
        )
        assert any(
            i.get("fallacy_family") == FallacyFamily.GENERALIZATION_CAUSALITY.value
            and i.get("potential_fallacy")
            for i in implications
        )

    def test_false_statistical_claim_names_statistical_family(self, producer):
        implications = producer._analyze_fallacy_implications(
            _make_claim("50% des français utilisent internet", ClaimType.STATISTICAL),
            VerificationStatus.VERIFIED_FALSE,
            [],
        )
        assert any(
            i.get("fallacy_family") == FallacyFamily.STATISTICAL_PROBABILISTIC.value
            and i.get("potential_fallacy")
            for i in implications
        )

    def test_non_false_status_asserts_nothing(self, producer):
        """#1019: a claim that is not verified false carries no implication —
        the producer does not guess a fallacy the status does not warrant."""
        for status in (
            VerificationStatus.DISPUTED,
            VerificationStatus.VERIFIED_TRUE,
            VerificationStatus.UNVERIFIABLE,
        ):
            implications = producer._analyze_fallacy_implications(
                _make_claim("Tous les politiciens mentent", ClaimType.STATISTICAL),
                status,
                [],
            )
            assert implications == []


class TestFamilyIntegration:
    """Real producer-shaped results actually integrate (#2745)."""

    def _fact_result(self, producer, claim: FactualClaim) -> dict:
        implications = producer._analyze_fallacy_implications(
            claim, VerificationStatus.VERIFIED_FALSE, []
        )
        # The shape the analyzer sees: FactVerificationResult.to_dict()
        return {"status": "verified_false", "fallacy_implications": implications}

    def test_relevant_checks_and_credibility_impact(self, producer, analyzer):
        claim = _make_claim("Tous les politiciens mentent toujours")
        integration = analyzer._integrate_fact_checking(
            FallacyFamily.GENERALIZATION_CAUSALITY,
            [self._fact_result(producer, claim)],
        )
        assert integration["relevant_fact_checks"] == 1
        assert integration["verified_false_claims"] == 1
        assert integration["disputed_claims"] == 0
        assert integration["credibility_impact"] > 0

    def test_wrong_family_matches_nothing(self, producer, analyzer):
        """The match is on the family the producer named — an implication
        never counts for every family."""
        claim = _make_claim("Tous les politiciens mentent toujours")
        integration = analyzer._integrate_fact_checking(
            FallacyFamily.STATISTICAL_PROBABILISTIC,
            [self._fact_result(producer, claim)],
        )
        assert integration["relevant_fact_checks"] == 0
        assert integration["credibility_impact"] == 0.0

    def test_disputed_result_without_implication_integrates_nothing(
        self, producer, analyzer
    ):
        """Real producer shape for a disputed claim carries no implication:
        the counters stay at zero rather than guessing (#1019)."""
        fact_result = {"status": "disputed", "fallacy_implications": []}
        integration = analyzer._integrate_fact_checking(
            FallacyFamily.GENERALIZATION_CAUSALITY, [fact_result]
        )
        assert integration["relevant_fact_checks"] == 0
        assert integration["credibility_impact"] == 0.0

    def test_family_recommendations_follow_integration(self, producer, analyzer):
        """A relevant fact check is what unlocks family recommendations —
        zero relevance means zero recommendations, nonzero means some."""
        claim = _make_claim("Tous les politiciens mentent toujours")
        integration = analyzer._integrate_fact_checking(
            FallacyFamily.GENERALIZATION_CAUSALITY,
            [self._fact_result(producer, claim)],
        )
        recommendations = analyzer._generate_family_recommendations(
            FallacyFamily.GENERALIZATION_CAUSALITY, [], integration
        )
        assert recommendations  # real producer shape unlocks them

        empty = analyzer._integrate_fact_checking(
            FallacyFamily.GENERALIZATION_CAUSALITY,
            [{"status": "disputed", "fallacy_implications": []}],
        )
        assert (
            analyzer._generate_family_recommendations(
                FallacyFamily.GENERALIZATION_CAUSALITY, [], empty
            )
            == []
        )
