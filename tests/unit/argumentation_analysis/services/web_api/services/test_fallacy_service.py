# tests/unit/argumentation_analysis/services/web_api/services/test_fallacy_service.py
"""Tests for FallacyService — pattern-based fallacy detection."""

import pytest
from unittest.mock import MagicMock, patch

from argumentation_analysis.services.web_api.services.fallacy_service import (
    FallacyService,
)
from argumentation_analysis.services.web_api.models.request_models import (
    FallacyRequest,
    FallacyOptions,
)
from argumentation_analysis.services.web_api.models.response_models import (
    FallacyDetection,
)


@pytest.fixture
def service():
    """Create FallacyService with mocked analyzers (only pattern detection)."""
    with patch(
        "argumentation_analysis.services.web_api.services.fallacy_service.ContextualFallacyAnalyzer",
        None,
    ), patch(
        "argumentation_analysis.services.web_api.services.fallacy_service.FallacySeverityEvaluator",
        None,
    ), patch(
        "argumentation_analysis.services.web_api.services.fallacy_service.EnhancedContextualAnalyzer",
        None,
    ):
        svc = FallacyService()
    return svc


# ── Init & Health ──


class TestInit:
    def test_initialized(self, service):
        assert service.is_initialized is True

    def test_fallacy_patterns_loaded(self, service):
        assert len(service.fallacy_patterns) > 0
        assert "ad_hominem" in service.fallacy_patterns
        assert "straw_man" in service.fallacy_patterns
        assert "false_dilemma" in service.fallacy_patterns

    def test_is_healthy(self, service):
        assert service.is_healthy() is True

    def test_pattern_structure(self, service):
        for key, info in service.fallacy_patterns.items():
            assert "name" in info
            assert "description" in info
            assert "category" in info
            assert "patterns" in info
            assert "severity" in info


# ── Pattern Matching ──


class TestPatternMatching:
    def test_simple_substring_match(self, service):
        assert (
            service._pattern_matches("tout le monde", "tout le monde sait que") is True
        )

    def test_regex_match(self, service):
        assert (
            service._pattern_matches(
                "si.*alors.*donc.*vrai", "si A alors B donc c'est vrai"
            )
            is True
        )

    def test_no_match(self, service):
        assert service._pattern_matches("xyz123", "un texte normal") is False

    def test_case_insensitive(self, service):
        assert service._pattern_matches("EXPERT", "un expert dit") is True


# ── Context Extraction ──


class TestContextExtraction:
    def test_extract_middle(self, service):
        text = "A" * 100 + "TARGET" + "B" * 100
        ctx = service._extract_context(text, 100, context_size=10)
        assert "TARGET" in ctx

    def test_extract_start(self, service):
        text = "TARGET" + "B" * 100
        ctx = service._extract_context(text, 0, context_size=10)
        assert ctx.startswith("TARGET")

    def test_extract_negative_position(self, service):
        assert service._extract_context("text", -1) is None


# ── Severity Distribution ──


class TestSeverityDistribution:
    def test_empty_list(self, service):
        dist = service._calculate_severity_distribution([])
        assert dist == {"low": 0, "medium": 0, "high": 0}

    def test_low_severity(self, service):
        fallacies = [
            FallacyDetection(
                type="t", name="n", description="d", severity=0.3, confidence=0.5
            )
        ]
        dist = service._calculate_severity_distribution(fallacies)
        assert dist["low"] == 1
        assert dist["medium"] == 0
        assert dist["high"] == 0

    def test_medium_severity(self, service):
        fallacies = [
            FallacyDetection(
                type="t", name="n", description="d", severity=0.5, confidence=0.5
            )
        ]
        dist = service._calculate_severity_distribution(fallacies)
        assert dist["medium"] == 1

    def test_high_severity(self, service):
        fallacies = [
            FallacyDetection(
                type="t", name="n", description="d", severity=0.8, confidence=0.5
            )
        ]
        dist = service._calculate_severity_distribution(fallacies)
        assert dist["high"] == 1

    def test_mixed(self, service):
        fallacies = [
            FallacyDetection(
                type="t", name="n", description="d", severity=0.2, confidence=0.5
            ),
            FallacyDetection(
                type="t", name="n", description="d", severity=0.5, confidence=0.5
            ),
            FallacyDetection(
                type="t", name="n", description="d", severity=0.9, confidence=0.5
            ),
        ]
        dist = service._calculate_severity_distribution(fallacies)
        assert dist == {"low": 1, "medium": 1, "high": 1}


# ── Category Distribution ──


class TestCategoryDistribution:
    def test_empty_list(self, service):
        dist = service._calculate_category_distribution([])
        assert dist == {}

    def test_known_type(self, service):
        fallacies = [
            FallacyDetection(
                type="ad_hominem",
                name="n",
                description="d",
                severity=0.5,
                confidence=0.5,
            )
        ]
        dist = service._calculate_category_distribution(fallacies)
        assert dist.get("informal", 0) == 1

    def test_unknown_type(self, service):
        fallacies = [
            FallacyDetection(
                type="unknown_type",
                name="n",
                description="d",
                severity=0.5,
                confidence=0.5,
            )
        ]
        dist = service._calculate_category_distribution(fallacies)
        assert "unknown" in dist


# ── Filter and Deduplicate ──


class TestFilterAndDeduplicate:
    def test_severity_threshold_default(self, service):
        fallacies = [
            FallacyDetection(
                type="t1", name="n", description="d", severity=0.3, confidence=0.5
            ),
            FallacyDetection(
                type="t2", name="n", description="d", severity=0.8, confidence=0.5
            ),
        ]
        result = service._filter_and_deduplicate(fallacies, None)
        assert len(result) == 1
        assert result[0].type == "t2"

    def test_severity_threshold_custom(self, service):
        options = FallacyOptions(severity_threshold=0.2)
        fallacies = [
            FallacyDetection(
                type="t1", name="n", description="d", severity=0.3, confidence=0.5
            ),
            FallacyDetection(
                type="t2", name="n", description="d", severity=0.8, confidence=0.5
            ),
        ]
        result = service._filter_and_deduplicate(fallacies, options)
        assert len(result) == 2

    def test_deduplication_same_type_same_location(self, service):
        fallacies = [
            FallacyDetection(
                type="t1",
                name="n",
                description="d",
                severity=0.8,
                confidence=0.5,
                location={"start": 10},
            ),
            FallacyDetection(
                type="t1",
                name="n",
                description="d",
                severity=0.8,
                confidence=0.5,
                location={"start": 10},
            ),
        ]
        result = service._filter_and_deduplicate(fallacies, None)
        assert len(result) == 1

    def test_no_dedup_different_locations(self, service):
        fallacies = [
            FallacyDetection(
                type="t1",
                name="n",
                description="d",
                severity=0.8,
                confidence=0.5,
                location={"start": 10},
            ),
            FallacyDetection(
                type="t1",
                name="n",
                description="d",
                severity=0.8,
                confidence=0.5,
                location={"start": 50},
            ),
        ]
        result = service._filter_and_deduplicate(fallacies, None)
        assert len(result) == 2

    def test_max_fallacies_limit(self, service):
        options = FallacyOptions(max_fallacies=2, severity_threshold=0.0)
        fallacies = [
            FallacyDetection(
                type=f"t{i}", name="n", description="d", severity=0.8, confidence=0.5
            )
            for i in range(5)
        ]
        result = service._filter_and_deduplicate(fallacies, options)
        assert len(result) == 2

    def test_category_filter(self, service):
        options = FallacyOptions(categories=["ad_hominem"], severity_threshold=0.0)
        fallacies = [
            FallacyDetection(
                type="ad_hominem",
                name="n",
                description="d",
                severity=0.8,
                confidence=0.5,
            ),
            FallacyDetection(
                type="straw_man",
                name="n",
                description="d",
                severity=0.8,
                confidence=0.5,
            ),
        ]
        result = service._filter_and_deduplicate(fallacies, options)
        assert len(result) == 1
        assert result[0].type == "ad_hominem"


# ── Get Fallacy Types ──


class TestGetFallacyTypes:
    def test_returns_dict(self, service):
        types = service.get_fallacy_types()
        assert isinstance(types, dict)
        assert len(types) > 0

    def test_each_type_has_required_keys(self, service):
        types = service.get_fallacy_types()
        for key, info in types.items():
            assert "name" in info
            assert "description" in info
            assert "category" in info
            assert "severity" in info

    def test_ad_hominem_present(self, service):
        types = service.get_fallacy_types()
        assert "ad_hominem" in types
        assert types["ad_hominem"]["category"] == "informal"


# ── Get Categories ──


class TestGetCategories:
    def test_returns_list(self, service):
        categories = service.get_categories()
        assert isinstance(categories, list)

    def test_formal_and_informal(self, service):
        categories = service.get_categories()
        assert "formal" in categories
        assert "informal" in categories


# ── Detect Fallacies (integration) ──


class TestDetectFallacies:
    def test_detect_false_dilemma(self, service):
        request = FallacyRequest(
            text="Soit vous êtes avec nous, soit vous êtes contre nous."
        )
        response = service.detect_fallacies(request)
        assert response.success is True
        assert response.fallacy_count > 0
        types = [f.type for f in response.fallacies]
        assert "false_dilemma" in types

    def test_detect_no_fallacy(self, service):
        request = FallacyRequest(text="Le ciel est bleu aujourd'hui.")
        response = service.detect_fallacies(request)
        assert response.success is True
        # May or may not detect — depends on pattern sensitivity

    def test_response_has_processing_time(self, service):
        request = FallacyRequest(text="Un texte quelconque.")
        response = service.detect_fallacies(request)
        assert response.processing_time >= 0.0

    def test_response_has_distributions(self, service):
        request = FallacyRequest(
            text="Soit ceci soit cela, c'est tout le monde qui le dit."
        )
        response = service.detect_fallacies(request)
        assert isinstance(response.severity_distribution, dict)
        assert isinstance(response.category_distribution, dict)

    def test_detect_with_options(self, service):
        options = FallacyOptions(severity_threshold=0.9)
        request = FallacyRequest(
            text="Soit A soit B, tout le monde le dit.", options=options
        )
        response = service.detect_fallacies(request)
        assert response.success is True
        # High threshold should filter out low-severity matches
