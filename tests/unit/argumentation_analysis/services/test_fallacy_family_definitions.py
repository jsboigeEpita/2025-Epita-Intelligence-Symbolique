# tests/unit/argumentation_analysis/services/test_fallacy_family_definitions.py
"""Tests for fallacy_family_definitions — data dictionaries and helper functions."""

import re
import pytest

from argumentation_analysis.services.fallacy_family_definitions import (
    FALLACY_FAMILY_SEVERITY,
    FALLACY_FAMILY_KEYWORDS,
    FALLACY_FAMILY_CONTEXTS,
    FALLACY_FAMILY_METRICS,
    get_family_severity_info,
    get_family_keywords,
    get_family_contexts,
    get_family_metrics,
)
from argumentation_analysis.services.fallacy_taxonomy_service import FallacyFamily

ALL_FAMILIES = list(FallacyFamily)


# ── FALLACY_FAMILY_SEVERITY ──


class TestSeverityDictionary:
    def test_all_families_present(self):
        for family in ALL_FAMILIES:
            assert family in FALLACY_FAMILY_SEVERITY, f"Missing {family}"

    def test_count_matches_enum(self):
        assert len(FALLACY_FAMILY_SEVERITY) == len(ALL_FAMILIES)

    def test_base_severity_range(self):
        for family, info in FALLACY_FAMILY_SEVERITY.items():
            assert (
                0.0 <= info["base_severity"] <= 1.0
            ), f"{family} base_severity out of range"

    def test_context_multipliers_range(self):
        for family, info in FALLACY_FAMILY_SEVERITY.items():
            for ctx, mult in info["context_multipliers"].items():
                assert 0.0 <= mult <= 1.0, f"{family}/{ctx} multiplier out of range"

    def test_all_have_keywords_high(self):
        for family, info in FALLACY_FAMILY_SEVERITY.items():
            assert "keywords_high_severity" in info, f"{family} missing high keywords"
            assert len(info["keywords_high_severity"]) > 0

    def test_all_have_keywords_medium(self):
        for family, info in FALLACY_FAMILY_SEVERITY.items():
            assert (
                "keywords_medium_severity" in info
            ), f"{family} missing medium keywords"
            assert len(info["keywords_medium_severity"]) > 0

    def test_all_have_keywords_low(self):
        for family, info in FALLACY_FAMILY_SEVERITY.items():
            assert "keywords_low_severity" in info, f"{family} missing low keywords"
            assert len(info["keywords_low_severity"]) > 0

    def test_specific_authority_severity(self):
        info = FALLACY_FAMILY_SEVERITY[FallacyFamily.AUTHORITY_POPULARITY]
        assert info["base_severity"] == 0.7
        assert info["context_multipliers"]["scientific"] == 0.9

    def test_specific_generalization_severity(self):
        info = FALLACY_FAMILY_SEVERITY[FallacyFamily.GENERALIZATION_CAUSALITY]
        assert info["base_severity"] == 0.9
        assert info["context_multipliers"]["scientific"] == 1.0

    def test_specific_audio_severity(self):
        info = FALLACY_FAMILY_SEVERITY[FallacyFamily.AUDIO_ORAL_CONTEXT]
        assert info["base_severity"] == 0.4  # lowest


# ── FALLACY_FAMILY_KEYWORDS ──


class TestKeywordsDictionary:
    def test_all_families_present(self):
        for family in ALL_FAMILIES:
            assert family in FALLACY_FAMILY_KEYWORDS, f"Missing {family}"

    def test_count_matches_enum(self):
        assert len(FALLACY_FAMILY_KEYWORDS) == len(ALL_FAMILIES)

    def test_all_have_primary(self):
        for family, kw in FALLACY_FAMILY_KEYWORDS.items():
            assert (
                "primary" in kw and len(kw["primary"]) > 0
            ), f"{family} missing primary"

    def test_all_have_secondary(self):
        for family, kw in FALLACY_FAMILY_KEYWORDS.items():
            assert (
                "secondary" in kw and len(kw["secondary"]) > 0
            ), f"{family} missing secondary"

    def test_all_have_patterns(self):
        for family, kw in FALLACY_FAMILY_KEYWORDS.items():
            assert (
                "patterns" in kw and len(kw["patterns"]) > 0
            ), f"{family} missing patterns"

    def test_patterns_are_valid_regex(self):
        for family, kw in FALLACY_FAMILY_KEYWORDS.items():
            for pattern in kw["patterns"]:
                try:
                    re.compile(pattern)
                except re.error as e:
                    pytest.fail(f"{family} invalid pattern '{pattern}': {e}")

    def test_authority_primary_keywords(self):
        kw = FALLACY_FAMILY_KEYWORDS[FallacyFamily.AUTHORITY_POPULARITY]
        assert "expert" in kw["primary"]
        assert "autorité" in kw["primary"]

    def test_emotional_primary_keywords(self):
        kw = FALLACY_FAMILY_KEYWORDS[FallacyFamily.EMOTIONAL_APPEALS]
        assert "peur" in kw["primary"]
        assert "colère" in kw["primary"]

    def test_statistical_primary_keywords(self):
        kw = FALLACY_FAMILY_KEYWORDS[FallacyFamily.STATISTICAL_PROBABILISTIC]
        assert "statistique" in kw["primary"]
        assert "pourcentage" in kw["primary"]

    def test_no_duplicate_primary_keywords_within_family(self):
        for family, kw in FALLACY_FAMILY_KEYWORDS.items():
            primary = kw["primary"]
            assert len(primary) == len(
                set(primary)
            ), f"{family} has duplicate primary keywords"


# ── FALLACY_FAMILY_CONTEXTS ──


class TestContextsDictionary:
    def test_all_families_present(self):
        for family in ALL_FAMILIES:
            assert family in FALLACY_FAMILY_CONTEXTS, f"Missing {family}"

    def test_count_matches_enum(self):
        assert len(FALLACY_FAMILY_CONTEXTS) == len(ALL_FAMILIES)

    def test_all_have_contexts(self):
        for family, contexts in FALLACY_FAMILY_CONTEXTS.items():
            assert len(contexts) > 0, f"{family} has no contexts"

    def test_contexts_are_strings(self):
        for family, contexts in FALLACY_FAMILY_CONTEXTS.items():
            for ctx in contexts:
                assert isinstance(ctx, str), f"{family} has non-string context: {ctx}"

    def test_authority_contexts(self):
        contexts = FALLACY_FAMILY_CONTEXTS[FallacyFamily.AUTHORITY_POPULARITY]
        assert "politique" in contexts
        assert "médias" in contexts

    def test_audio_contexts(self):
        contexts = FALLACY_FAMILY_CONTEXTS[FallacyFamily.AUDIO_ORAL_CONTEXT]
        assert "débat oral" in contexts


# ── FALLACY_FAMILY_METRICS ──


class TestMetricsDictionary:
    def test_all_families_present(self):
        for family in ALL_FAMILIES:
            assert family in FALLACY_FAMILY_METRICS, f"Missing {family}"

    def test_count_matches_enum(self):
        assert len(FALLACY_FAMILY_METRICS) == len(ALL_FAMILIES)

    def test_all_metrics_have_description_and_weight(self):
        for family, metrics in FALLACY_FAMILY_METRICS.items():
            for metric_name, metric_info in metrics.items():
                assert (
                    "description" in metric_info
                ), f"{family}/{metric_name} missing description"
                assert "weight" in metric_info, f"{family}/{metric_name} missing weight"

    def test_weights_sum_to_one(self):
        for family, metrics in FALLACY_FAMILY_METRICS.items():
            total = sum(m["weight"] for m in metrics.values())
            assert (
                abs(total - 1.0) < 0.01
            ), f"{family} weights sum to {total}, expected 1.0"

    def test_weights_positive(self):
        for family, metrics in FALLACY_FAMILY_METRICS.items():
            for name, info in metrics.items():
                assert info["weight"] > 0, f"{family}/{name} has non-positive weight"

    def test_authority_metrics(self):
        metrics = FALLACY_FAMILY_METRICS[FallacyFamily.AUTHORITY_POPULARITY]
        assert "authority_relevance" in metrics
        assert "source_credibility" in metrics
        assert "popularity_representativeness" in metrics

    def test_statistical_metrics(self):
        metrics = FALLACY_FAMILY_METRICS[FallacyFamily.STATISTICAL_PROBABILISTIC]
        assert "statistical_accuracy" in metrics


# ── Helper Functions ──


class TestGetFamilySeverityInfo:
    def test_known_family(self):
        info = get_family_severity_info(FallacyFamily.AUTHORITY_POPULARITY)
        assert "base_severity" in info
        assert info["base_severity"] == 0.7

    def test_returns_dict(self):
        info = get_family_severity_info(FallacyFamily.EMOTIONAL_APPEALS)
        assert isinstance(info, dict)


class TestGetFamilyKeywords:
    def test_known_family(self):
        kw = get_family_keywords(FallacyFamily.DIVERSION_ATTACK)
        assert "primary" in kw
        assert "secondary" in kw

    def test_returns_dict(self):
        kw = get_family_keywords(FallacyFamily.LANGUAGE_AMBIGUITY)
        assert isinstance(kw, dict)


class TestGetFamilyContexts:
    def test_known_family(self):
        contexts = get_family_contexts(FallacyFamily.FALSE_DILEMMA_SIMPLIFICATION)
        assert isinstance(contexts, list)
        assert len(contexts) > 0

    def test_returns_list(self):
        contexts = get_family_contexts(FallacyFamily.GENERALIZATION_CAUSALITY)
        assert isinstance(contexts, list)


class TestGetFamilyMetrics:
    def test_known_family(self):
        metrics = get_family_metrics(FallacyFamily.EMOTIONAL_APPEALS)
        assert "emotional_intensity" in metrics

    def test_returns_dict(self):
        metrics = get_family_metrics(FallacyFamily.AUDIO_ORAL_CONTEXT)
        assert isinstance(metrics, dict)
