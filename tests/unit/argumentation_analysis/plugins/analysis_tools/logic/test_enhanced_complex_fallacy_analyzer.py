# -*- coding: utf-8 -*-
"""Tests for argumentation_analysis.plugins.analysis_tools.logic.complex_fallacy_analyzer
Covers EnhancedComplexFallacyAnalyzer: initialization, composite fallacy
detection, combined fallacies, argument structure, circular reasoning,
vulnerabilities, composite severity, inter-argument coherence, fallacy
patterns.

Ported from the retired in-package suite (#2124) — the only one of its three
files with no canonical counterpart (audit B-04). The port follows the
CURRENT API: the constructor requires an injected fallacy_detector (#2147),
which the analyzer forwards to its internal contextual analyzer. The retired
originals errored at setup against this constructor — that error state is the
red the port resolves.
"""

import pytest

from argumentation_analysis.plugins.analysis_tools.logic.complex_fallacy_analyzer import (
    EnhancedComplexFallacyAnalyzer,
)
from argumentation_analysis.core.interfaces.fallacy_detector import (
    AbstractFallacyDetector,
)


class _ConformingDetector(AbstractFallacyDetector):
    """Détecteur minimal respectant le contrat DÉCLARÉ de l'ABC (#2149)."""

    def __init__(self, fallacies=None):
        self._fallacies = fallacies if fallacies is not None else []

    def detect(self, text: str) -> dict:
        return {"fallacies": list(self._fallacies)}


ARGUMENTS_DATA = [
    {
        "id": "arg-1",
        "text": "Tous les experts sont d'accord que le réchauffement climatique est réel, donc c'est vrai.",
        "confidence": 0.9,
    },
    {
        "id": "arg-2",
        "text": "Si nous acceptons le mariage homosexuel, bientôt les gens voudront épouser des animaux.",
        "confidence": 0.85,
    },
    {
        "id": "arg-3",
        "text": "Mon opposant n'a pas de diplôme en économie, donc son plan économique est forcément mauvais.",
        "confidence": 0.8,
    },
]


@pytest.fixture
def analyzer():
    return EnhancedComplexFallacyAnalyzer(fallacy_detector=_ConformingDetector())


def _arguments_text():
    return [arg["text"] for arg in ARGUMENTS_DATA]


# ============================================================
# __init__
# ============================================================


class TestInit:
    def test_creates_instance(self, analyzer):
        assert isinstance(analyzer, EnhancedComplexFallacyAnalyzer)

    def test_builds_internal_analyzers(self, analyzer):
        assert analyzer.contextual_analyzer is not None
        assert analyzer.severity_evaluator is not None

    def test_loads_knowledge_bases(self, analyzer):
        assert analyzer.argument_structure_patterns is not None
        assert analyzer.advanced_fallacy_combinations is not None


# ============================================================
# detect_composite_fallacies
# ============================================================


class TestDetectCompositeFallacies:
    def test_returns_expected_keys(self, analyzer):
        result = analyzer.detect_composite_fallacies(_arguments_text(), "général")
        assert isinstance(result, dict)
        for key in (
            "basic_combinations",
            "advanced_combinations",
            "fallacy_patterns",
            "composite_severity",
        ):
            assert key in result, f"missing key {key!r}"
        assert isinstance(result["basic_combinations"], list)
        assert isinstance(result["advanced_combinations"], list)
        assert isinstance(result["fallacy_patterns"], list)

    def test_composite_severity_in_unit_range(self, analyzer):
        result = analyzer.detect_composite_fallacies(_arguments_text(), "général")
        severity = result["composite_severity"]
        assert "adjusted_severity" in severity
        assert 0.0 <= severity["adjusted_severity"] <= 1.0


# ============================================================
# identify_combined_fallacies / identify_fallacy_patterns
# ============================================================


class TestFallacyIdentification:
    def test_identify_combined_fallacies_returns_list(self, analyzer):
        text = (
            "L'argument repose uniquement sur l'opinion d'experts sans preuves. "
            "L'argument suggère qu'une action mènera inévitablement à une chaîne "
            "d'événements indésirables."
        )
        assert isinstance(analyzer.identify_combined_fallacies(text), list)

    def test_identify_fallacy_patterns_returns_list(self, analyzer):
        text = " ".join(_arguments_text())
        assert isinstance(analyzer.identify_fallacy_patterns(text), list)


# ============================================================
# analyze_argument_structure
# ============================================================


class TestAnalyzeArgumentStructure:
    def test_returns_expected_keys(self, analyzer):
        result = analyzer.analyze_argument_structure(_arguments_text(), "général")
        assert isinstance(result, dict)
        for key in (
            "identified_structures",
            "argument_relations",
            "coherence_evaluation",
            "vulnerability_analysis",
        ):
            assert key in result, f"missing key {key!r}"

    def test_vulnerability_analysis_present(self, analyzer):
        result = analyzer.analyze_argument_structure(_arguments_text(), "général")
        assert "vulnerability_analysis" in result


# ============================================================
# analyze_inter_argument_coherence
# ============================================================


class TestAnalyzeInterArgumentCoherence:
    def test_returns_expected_keys(self, analyzer):
        result = analyzer.analyze_inter_argument_coherence(_arguments_text(), "général")
        assert isinstance(result, dict)
        for key in ("thematic_coherence", "logical_coherence", "overall_coherence"):
            assert key in result, f"missing key {key!r}"

    def test_circular_reasoning_scores_low_coherence(self, analyzer):
        """Deux arguments qui se citent l'un l'autre ne sont pas cohérents."""
        circular_arguments = [
            "La Bible est la parole de Dieu car elle le dit elle-même.",
            "La Bible dit qu'elle est la parole de Dieu, donc c'est vrai.",
        ]
        result = analyzer.analyze_inter_argument_coherence(
            circular_arguments, "religieux"
        )
        assert result["overall_coherence"]["overall_score"] <= 0.6
