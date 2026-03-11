# tests/unit/argumentation_analysis/services/web_api/services/test_validation_service.py
"""Tests for ValidationService — heuristic argument validation."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from argumentation_analysis.services.web_api.services.validation_service import (
    ValidationService,
)
from argumentation_analysis.services.web_api.models.request_models import (
    ValidationRequest,
)


@pytest.fixture
def mock_logic_service():
    svc = MagicMock()
    svc.is_healthy.return_value = True
    return svc


@pytest.fixture
def service(mock_logic_service):
    return ValidationService(logic_service=mock_logic_service)


# ── Init & Health ──

class TestInit:
    def test_init(self, service):
        assert service.is_initialized is True
        assert len(service.logical_connectors) > 0
        assert len(service.premise_indicators) > 0

    def test_is_healthy(self, service):
        assert service.is_healthy() is True

    def test_is_unhealthy_when_logic_unhealthy(self, mock_logic_service):
        mock_logic_service.is_healthy.return_value = False
        svc = ValidationService(logic_service=mock_logic_service)
        assert svc.is_healthy() is False


# ── Clarity ──

class TestClarity:
    def test_short_text_low_clarity(self, service):
        assert service._assess_clarity("ab") == 0.3

    def test_medium_text_good_clarity(self, service):
        assert service._assess_clarity("Ceci est une phrase de taille moyenne") == 0.8

    def test_long_text_reduced_clarity(self, service):
        text = " ".join(["mot"] * 35)
        assert service._assess_clarity(text) == 0.6


# ── Specificity ──

class TestSpecificity:
    def test_vague_term_lowers_specificity(self, service):
        assert service._assess_specificity("certains pensent que c'est vrai") == 0.4

    def test_no_vague_terms_higher_specificity(self, service):
        assert service._assess_specificity("Le fer fond à 1538 degrés") == 0.7


# ── Credibility ──

class TestCredibility:
    def test_source_indicator_high_credibility(self, service):
        assert service._assess_credibility("selon une étude récente") == 0.8

    def test_no_indicators_moderate_credibility(self, service):
        assert service._assess_credibility("il fait beau aujourd'hui") == 0.6


# ── Qualifiers ──

class TestQualifiers:
    def test_contains_qualifier(self, service):
        assert service._contains_qualifiers("c'est probablement vrai") is True

    def test_no_qualifier(self, service):
        assert service._contains_qualifiers("c'est vrai") is False


# ── Factual Claim ──

class TestFactualClaim:
    def test_factual(self, service):
        assert service._is_factual_claim("La terre tourne autour du soleil") is True

    def test_opinion(self, service):
        assert service._is_factual_claim("je crois que c'est bien") is False

    def test_modal(self, service):
        assert service._is_factual_claim("il devrait venir demain") is False


# ── Conclusion Strength ──

class TestConclusionStrength:
    def test_reasonable_conclusion(self, service):
        strength = service._assess_conclusion_strength(
            "Donc la terre tourne autour du soleil"
        )
        assert 0.0 < strength < 1.0


# ── Logical Connectors ──

class TestLogicalConnectors:
    def test_has_connector(self, service):
        assert service._has_logical_connectors("donc il pleut") is True

    def test_no_connector(self, service):
        assert service._has_logical_connectors("il pleut") is False

    def test_par_consequent(self, service):
        assert service._has_logical_connectors("par conséquent nous partons") is True


# ── Premise Relevance ──

class TestPremiseRelevance:
    def test_relevant_premises(self, service):
        score = service._assess_premise_relevance(
            ["la pluie est froide", "l'eau tombe du ciel"],
            "il tombe de l'eau froide",
        )
        assert score > 0.0

    def test_irrelevant_premises(self, service):
        score = service._assess_premise_relevance(
            ["les chats sont mignons"],
            "la terre est ronde",
        )
        assert score < 0.5

    def test_empty_premises(self, service):
        assert service._assess_premise_relevance([], "conclusion") == 0.0


# ── Logical Flow ──

class TestLogicalFlow:
    def test_good_flow(self, service):
        score = service._assess_logical_flow(
            ["prémisse 1", "prémisse 2"],
            "donc la conclusion suit",
        )
        assert score == 1.0  # 0.5 + 0.3 (connector) + 0.2 (2 premises)

    def test_no_connector_one_premise(self, service):
        score = service._assess_logical_flow(
            ["une seule prémisse"],
            "conclusion sans connecteur",
        )
        assert score == 0.5


# ── Completeness ──

class TestCompleteness:
    def test_complete_argument(self, service):
        score = service._assess_completeness(
            ["p1", "p2", "p3"],
            "une conclusion de taille raisonnable avec plusieurs mots",
        )
        assert score > 0.5

    def test_minimal_argument(self, service):
        score = service._assess_completeness(["p1"], "ok")
        assert score < 0.5


# ── Consistency ──

class TestConsistency:
    def test_single_premise_full_consistency(self, service):
        assert service._assess_consistency(["une prémisse"]) == 1.0

    def test_multiple_premises_reduced(self, service):
        assert service._assess_consistency(["p1", "p2"]) == 0.7


# ── Logical Gaps ──

class TestLogicalGaps:
    def test_no_gaps(self, service):
        gaps = service._identify_logical_gaps(
            ["la terre est ronde", "la terre tourne"],
            "donc la terre est ronde et tourne",
        )
        # With connector and 2 premises and shared words, no gaps
        assert "Nombre insuffisant" not in gaps
        assert "Absence de connecteurs" not in gaps

    def test_gap_low_relevance(self, service):
        gaps = service._identify_logical_gaps(
            ["les chats dorment"],
            "la météo est mauvaise",
        )
        assert any("pertinence" in g.lower() for g in gaps)

    def test_gap_insufficient_premises(self, service):
        gaps = service._identify_logical_gaps(
            ["une seule prémisse"],
            "conclusion quelconque",
        )
        assert any("insuffisant" in g.lower() for g in gaps)


# ── Premise Analysis ──

class TestPremiseAnalysis:
    def test_analyze_premises(self, service):
        analysis = service._analyze_premises([
            "Selon une étude, la terre est ronde",
            "ok",
        ])
        assert len(analysis) == 2
        assert analysis[0]["index"] == 0
        assert analysis[0]["credibility_score"] == 0.8  # "étude"
        assert analysis[0]["strength"] > 0
        assert analysis[1]["clarity_score"] == 0.3  # short text


# ── Conclusion Analysis ──

class TestConclusionAnalysis:
    def test_analyze_conclusion(self, service):
        result = service._analyze_conclusion("Donc le phénomène est expliqué")
        assert result["text"] == "Donc le phénomène est expliqué"
        assert result["word_count"] > 0
        assert "clarity_score" in result
        assert "strength" in result
        assert result["follows_logically"] == 0.5  # default


# ── Logical Structure ──

class TestLogicalStructure:
    def test_analyze_structure(self, service):
        result = service._analyze_logical_structure(
            ["p1", "p2"], "donc c'est vrai", "deductive",
        )
        assert result["argument_type"] == "deductive"
        assert result["premise_count"] == 2
        assert result["has_logical_connectors"] is True
        assert "premise_relevance" in result
        assert "gap_analysis" in result


# ── Validity Score ──

class TestValidityScore:
    def test_no_premises_returns_zero(self, service):
        assert service._calculate_validity_score([], {}, {}) == 0.0

    def test_reasonable_score(self, service):
        premise_analysis = [{"strength": 0.7}]
        conclusion_analysis = {"strength": 0.6}
        structure = {"premise_relevance": 0.5, "logical_flow": 0.6, "completeness": 0.5}
        score = service._calculate_validity_score(
            premise_analysis, conclusion_analysis, structure,
        )
        assert 0.0 <= score <= 1.0


# ── Soundness Score ──

class TestSoundnessScore:
    def test_no_premises_returns_zero(self, service):
        assert service._calculate_soundness_score([], 0.8) == 0.0

    def test_soundness_depends_on_validity(self, service):
        premise_analysis = [{"credibility_score": 0.8}]
        score = service._calculate_soundness_score(premise_analysis, 0.9)
        assert score == pytest.approx(0.72, abs=0.01)  # 0.9 * 0.8


# ── Issues ──

class TestIdentifyIssues:
    def test_no_premises_issue(self, service):
        issues = service._identify_issues(
            [], {"text": "conclusion", "clarity_score": 0.8}, {},
        )
        assert any("prémisse" in i.lower() for i in issues)

    def test_low_clarity_premise(self, service):
        issues = service._identify_issues(
            [{"clarity_score": 0.3, "credibility_score": 0.7}],
            {"text": "ok", "clarity_score": 0.8},
            {"premise_relevance": 0.8, "logical_flow": 0.8, "completeness": 0.8, "consistency": 0.8, "gap_analysis": []},
        )
        assert any("clarté" in i for i in issues)

    def test_gaps_included(self, service):
        issues = service._identify_issues(
            [{"clarity_score": 0.9, "credibility_score": 0.9}],
            {"text": "conclusion", "clarity_score": 0.9},
            {"premise_relevance": 0.8, "logical_flow": 0.8, "completeness": 0.8, "consistency": 0.8,
             "gap_analysis": ["gap1"]},
        )
        assert any("gap1" in i for i in issues)


# ── Suggestions ──

class TestSuggestions:
    def test_no_issues_positive_suggestion(self, service):
        suggestions = service._generate_suggestions([], {"argument_type": None})
        assert len(suggestions) >= 1
        assert any("bien structuré" in s for s in suggestions)

    def test_premise_clarity_suggestion(self, service):
        suggestions = service._generate_suggestions(
            ["la prémisse manque de clarté"], {},
        )
        assert any("clarté" in s for s in suggestions)

    def test_premise_credibility_suggestion(self, service):
        suggestions = service._generate_suggestions(
            ["prémisse manque de crédibilité"], {},
        )
        assert any("crédibilité" in s for s in suggestions)

    def test_deductive_suggestion(self, service):
        suggestions = service._generate_suggestions(
            ["un problème"], {"argument_type": "deductive"},
        )
        assert any("déductif" in s for s in suggestions)

    def test_inductive_suggestion(self, service):
        suggestions = service._generate_suggestions(
            ["un problème"], {"argument_type": "inductive"},
        )
        assert any("inductif" in s for s in suggestions)


# ── validate_argument (async) ──

class TestValidateArgument:
    async def test_valid_argument(self, service):
        request = ValidationRequest(
            premises=["La terre est ronde selon les données scientifiques",
                       "Les données proviennent d'une étude approfondie"],
            conclusion="Donc la terre est ronde selon ces données",
        )
        response = await service.validate_argument(request)
        assert response.success is True
        assert response.result.validity_score > 0
        assert response.processing_time >= 0.0

    async def test_no_premises_pydantic_rejects(self, service):
        """Pydantic model enforces min 1 premise."""
        from pydantic import ValidationError as PydanticValidationError
        with pytest.raises(PydanticValidationError):
            ValidationRequest(premises=[], conclusion="conclusion")

    async def test_empty_conclusion_pydantic_rejects(self, service):
        """Pydantic model enforces non-empty conclusion."""
        from pydantic import ValidationError as PydanticValidationError
        with pytest.raises(PydanticValidationError):
            ValidationRequest(premises=["premise"], conclusion="")

    async def test_argument_type_preserved(self, service):
        request = ValidationRequest(
            premises=["tous les hommes sont mortels"],
            conclusion="donc Socrate est mortel",
            argument_type="deductive",
        )
        response = await service.validate_argument(request)
        assert response.argument_type == "deductive"

    async def test_heuristic_method_used(self, service):
        request = ValidationRequest(
            premises=["prémisse 1"],
            conclusion="donc conclusion",
        )
        response = await service.validate_argument(request)
        assert response.result.logical_structure.get("method") == "heuristic"
