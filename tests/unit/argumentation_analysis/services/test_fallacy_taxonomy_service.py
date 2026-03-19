# tests/unit/argumentation_analysis/services/test_fallacy_taxonomy_service.py
"""Tests for ClassifiedFallacy dataclass, FallacyFamily enum, and FallacyTaxonomyManager."""

import pytest
from unittest.mock import patch, MagicMock

from argumentation_analysis.services.fallacy_taxonomy_service import (
    ClassifiedFallacy,
    FallacyFamily,
    FallacyTaxonomyManager,
    get_taxonomy_manager,
)

# ── FallacyFamily Enum ──


class TestFallacyFamily:
    def test_has_eight_families(self):
        assert len(FallacyFamily) == 8

    def test_values(self):
        expected = {
            "authority_popularity",
            "emotional_appeals",
            "generalization_causality",
            "diversion_attack",
            "false_dilemma_simplification",
            "language_ambiguity",
            "statistical_probabilistic",
            "audio_oral_context",
        }
        actual = {f.value for f in FallacyFamily}
        assert actual == expected

    def test_by_value(self):
        assert (
            FallacyFamily("authority_popularity") == FallacyFamily.AUTHORITY_POPULARITY
        )
        assert FallacyFamily("emotional_appeals") == FallacyFamily.EMOTIONAL_APPEALS

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            FallacyFamily("nonexistent")


# ── ClassifiedFallacy ──


class TestClassifiedFallacy:
    @pytest.fixture
    def fallacy(self):
        return ClassifiedFallacy(
            taxonomy_key=101,
            name="Ad Hominem",
            nom_vulgarise="Attaque personnelle",
            family=FallacyFamily.DIVERSION_ATTACK,
            confidence=0.85,
            description="Attacking the person",
            severity="Élevée",
            context_relevance=0.7,
            family_pattern_score=0.9,
            detection_method="pattern",
        )

    def test_init(self, fallacy):
        assert fallacy.taxonomy_key == 101
        assert fallacy.name == "Ad Hominem"
        assert fallacy.nom_vulgarise == "Attaque personnelle"
        assert fallacy.family == FallacyFamily.DIVERSION_ATTACK
        assert fallacy.confidence == 0.85
        assert fallacy.severity == "Élevée"

    def test_to_dict(self, fallacy):
        d = fallacy.to_dict()
        assert d["taxonomy_key"] == 101
        assert d["name"] == "Ad Hominem"
        assert d["family"] == "diversion_attack"  # enum .value
        assert d["confidence"] == 0.85
        assert d["detection_method"] == "pattern"

    def test_to_dict_string_family(self):
        f = ClassifiedFallacy(
            taxonomy_key=1,
            name="n",
            nom_vulgarise="nv",
            family="string_family",
            confidence=0.5,
            description="d",
            severity="Moyenne",
            context_relevance=0.5,
            family_pattern_score=0.5,
            detection_method="m",
        )
        d = f.to_dict()
        assert d["family"] == "string_family"  # no .value call

    def test_to_dict_all_keys(self, fallacy):
        d = fallacy.to_dict()
        expected_keys = {
            "taxonomy_key",
            "name",
            "nom_vulgarise",
            "family",
            "confidence",
            "description",
            "severity",
            "context_relevance",
            "family_pattern_score",
            "detection_method",
        }
        assert set(d.keys()) == expected_keys


# ── FallacyTaxonomyManager ──


class TestFallacyTaxonomyManager:
    @pytest.fixture
    def mock_detector(self):
        detector = MagicMock()
        detector.detect_sophisms_from_taxonomy.return_value = []
        return detector

    @pytest.fixture
    def manager(self, mock_detector):
        with patch(
            "argumentation_analysis.services.fallacy_taxonomy_service.get_global_detector",
            return_value=mock_detector,
        ):
            return FallacyTaxonomyManager()

    def test_init(self, manager):
        assert len(manager.families) == 8
        assert manager.detector is not None

    def test_families_are_enum(self, manager):
        for f in manager.families:
            assert isinstance(f, FallacyFamily)

    def test_detect_empty_text(self, manager):
        results = manager.detect_fallacies_with_families("")
        assert isinstance(results, list)

    def test_detect_returns_classified_list(self, manager, mock_detector):
        mock_detector.detect_sophisms_from_taxonomy.return_value = [
            {
                "taxonomy_key": 1,
                "name": "Test Fallacy",
                "nom_vulgarise": "Sophisme test",
                "confidence": 0.8,
                "description": "A test fallacy",
            }
        ]
        results = manager.detect_fallacies_with_families("Texte de test.")
        assert len(results) == 1
        assert isinstance(results[0], ClassifiedFallacy)
        assert results[0].name == "Test Fallacy"
        assert results[0].confidence == 0.8

    def test_detect_default_values(self, manager, mock_detector):
        mock_detector.detect_sophisms_from_taxonomy.return_value = [{}]
        results = manager.detect_fallacies_with_families("test")
        assert results[0].taxonomy_key == 0
        assert results[0].name == ""
        assert results[0].severity == "Moyenne"
        assert results[0].detection_method == "taxonomy_service"


# ── get_taxonomy_manager singleton ──


class TestGetTaxonomyManager:
    def test_returns_manager(self):
        import argumentation_analysis.services.fallacy_taxonomy_service as mod

        mod._global_taxonomy_manager = None
        with patch(
            "argumentation_analysis.services.fallacy_taxonomy_service.get_global_detector",
            return_value=MagicMock(),
        ):
            mgr = get_taxonomy_manager()
            assert isinstance(mgr, FallacyTaxonomyManager)

    def test_singleton(self):
        import argumentation_analysis.services.fallacy_taxonomy_service as mod

        mod._global_taxonomy_manager = None
        with patch(
            "argumentation_analysis.services.fallacy_taxonomy_service.get_global_detector",
            return_value=MagicMock(),
        ):
            m1 = get_taxonomy_manager()
            m2 = get_taxonomy_manager()
            assert m1 is m2
