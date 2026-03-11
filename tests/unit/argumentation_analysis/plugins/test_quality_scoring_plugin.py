# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.plugins.quality_scoring_plugin
Covers QualityScoringPlugin: evaluate_argument_quality, get_quality_score,
list_virtues.
"""

import pytest
import json

from argumentation_analysis.plugins.quality_scoring_plugin import (
    QualityScoringPlugin,
)


@pytest.fixture
def plugin():
    return QualityScoringPlugin()


# ============================================================
# __init__
# ============================================================

class TestInit:
    def test_creates_evaluator(self, plugin):
        assert plugin.evaluator is not None


# ============================================================
# evaluate_argument_quality
# ============================================================

class TestEvaluateArgumentQuality:
    def test_returns_json(self, plugin):
        result = json.loads(plugin.evaluate_argument_quality("Ceci est un argument clair et bien structuré."))
        assert isinstance(result, dict)

    def test_has_note_finale(self, plugin):
        result = json.loads(plugin.evaluate_argument_quality("Un argument solide avec des sources fiables."))
        assert "note_finale" in result

    def test_has_note_moyenne(self, plugin):
        result = json.loads(plugin.evaluate_argument_quality("Argument test"))
        assert "note_moyenne" in result

    def test_empty_text(self, plugin):
        result = json.loads(plugin.evaluate_argument_quality(""))
        assert isinstance(result, dict)

    def test_long_text(self, plugin):
        text = "Cet argument est bien construit. " * 20
        result = json.loads(plugin.evaluate_argument_quality(text))
        assert "note_finale" in result


# ============================================================
# get_quality_score
# ============================================================

class TestGetQualityScore:
    def test_returns_json(self, plugin):
        result = json.loads(plugin.get_quality_score("Un bon argument."))
        assert isinstance(result, dict)

    def test_has_note_finale(self, plugin):
        result = json.loads(plugin.get_quality_score("Argument raisonnable."))
        assert "note_finale" in result

    def test_has_note_moyenne(self, plugin):
        result = json.loads(plugin.get_quality_score("Un test"))
        assert "note_moyenne" in result

    def test_scores_are_numeric(self, plugin):
        result = json.loads(plugin.get_quality_score("Texte"))
        assert isinstance(result["note_finale"], (int, float))
        assert isinstance(result["note_moyenne"], (int, float))


# ============================================================
# list_virtues
# ============================================================

class TestListVirtues:
    def test_returns_list(self, plugin):
        result = json.loads(plugin.list_virtues())
        assert isinstance(result, list)

    def test_has_nine_virtues(self, plugin):
        result = json.loads(plugin.list_virtues())
        assert len(result) == 9

    def test_virtues_are_strings(self, plugin):
        result = json.loads(plugin.list_virtues())
        assert all(isinstance(v, str) for v in result)
