# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.agents.tools.analysis.rhetorical_result_visualizer
Covers RhetoricalResultVisualizer: argument graph, fallacy distribution,
quality heatmap, all visualizations, HTML report.
"""

import pytest

from argumentation_analysis.agents.tools.analysis.rhetorical_result_visualizer import (
    RhetoricalResultVisualizer,
)


@pytest.fixture
def viz():
    return RhetoricalResultVisualizer()


@pytest.fixture
def sample_state():
    return {
        "identified_arguments": {
            "arg_1": "Les experts affirment que le produit est efficace.",
            "arg_2": "Des millions de personnes l'utilisent déjà.",
            "arg_3": "Sans ce produit, des conséquences graves sont inévitables.",
        },
        "identified_fallacies": {
            "fallacy_1": {
                "type": "Appel à l'autorité",
                "target_argument_id": "arg_1",
            },
            "fallacy_2": {
                "type": "Appel à la popularité",
                "target_argument_id": "arg_2",
            },
            "fallacy_3": {
                "type": "Faux dilemme",
                "target_argument_id": "arg_3",
            },
        },
    }


@pytest.fixture
def empty_state():
    return {}


# ============================================================
# __init__
# ============================================================

class TestInit:
    def test_creates_instance(self, viz):
        assert viz is not None
        assert viz.logger is not None


# ============================================================
# generate_argument_graph
# ============================================================

class TestGenerateArgumentGraph:
    def test_empty_state(self, viz, empty_state):
        graph = viz.generate_argument_graph(empty_state)
        assert "graph TD" in graph
        assert "Aucun argument identifié" in graph

    def test_no_arguments_key(self, viz):
        graph = viz.generate_argument_graph({"identified_fallacies": {}})
        assert "Aucun argument identifié" in graph

    def test_arguments_only(self, viz):
        state = {"identified_arguments": {"arg_1": "Texte argument"}}
        graph = viz.generate_argument_graph(state)
        assert "graph TD" in graph
        assert "arg_1" in graph
        assert "Texte argument" in graph

    def test_with_fallacies_linked(self, viz, sample_state):
        graph = viz.generate_argument_graph(sample_state)
        assert "graph TD" in graph
        assert "arg_1" in graph
        assert "fallacy_1" in graph
        assert "arg_1 --> fallacy_1" in graph

    def test_fallacy_without_target(self, viz):
        state = {
            "identified_arguments": {"arg_1": "Some argument"},
            "identified_fallacies": {
                "fallacy_1": {"type": "Ad hominem"},  # No target_argument_id
            },
        }
        graph = viz.generate_argument_graph(state)
        assert "fallacy_1" in graph
        assert "-->" not in graph  # No link

    def test_fallacy_with_nonexistent_target(self, viz):
        state = {
            "identified_arguments": {"arg_1": "Argument"},
            "identified_fallacies": {
                "fallacy_1": {"type": "Ad hominem", "target_argument_id": "arg_999"},
            },
        }
        graph = viz.generate_argument_graph(state)
        assert "fallacy_1" in graph
        assert "-->" not in graph  # Target not in arguments

    def test_long_argument_truncated(self, viz):
        long_text = "A" * 100
        state = {"identified_arguments": {"arg_1": long_text}}
        graph = viz.generate_argument_graph(state)
        assert "..." in graph
        # Should contain first 50 chars
        assert "A" * 50 in graph

    def test_quotes_escaped(self, viz):
        state = {"identified_arguments": {"arg_1": 'He said "hello"'}}
        graph = viz.generate_argument_graph(state)
        assert '\\"' in graph

    def test_multiple_fallacies_same_target(self, viz):
        state = {
            "identified_arguments": {"arg_1": "Argument text"},
            "identified_fallacies": {
                "f1": {"type": "Type A", "target_argument_id": "arg_1"},
                "f2": {"type": "Type B", "target_argument_id": "arg_1"},
            },
        }
        graph = viz.generate_argument_graph(state)
        assert "arg_1 --> f1" in graph
        assert "arg_1 --> f2" in graph


# ============================================================
# generate_fallacy_distribution
# ============================================================

class TestGenerateFallacyDistribution:
    def test_empty_state(self, viz, empty_state):
        dist = viz.generate_fallacy_distribution(empty_state)
        assert "pie" in dist
        assert "Aucun sophisme identifié" in dist

    def test_single_fallacy(self, viz):
        state = {
            "identified_fallacies": {
                "f1": {"type": "Ad hominem"},
            },
        }
        dist = viz.generate_fallacy_distribution(state)
        assert "pie" in dist
        assert '"Ad hominem" : 1' in dist

    def test_multiple_same_type(self, viz):
        state = {
            "identified_fallacies": {
                "f1": {"type": "Ad hominem"},
                "f2": {"type": "Ad hominem"},
                "f3": {"type": "Faux dilemme"},
            },
        }
        dist = viz.generate_fallacy_distribution(state)
        assert '"Ad hominem" : 2' in dist
        assert '"Faux dilemme" : 1' in dist

    def test_unknown_type(self, viz):
        state = {
            "identified_fallacies": {
                "f1": {},  # No type key
            },
        }
        dist = viz.generate_fallacy_distribution(state)
        assert "Type inconnu" in dist

    def test_title_present(self, viz, sample_state):
        dist = viz.generate_fallacy_distribution(sample_state)
        assert "title Distribution des sophismes" in dist


# ============================================================
# generate_argument_quality_heatmap
# ============================================================

class TestGenerateHeatmap:
    def test_empty_state(self, viz, empty_state):
        hm = viz.generate_argument_quality_heatmap(empty_state)
        assert "heatmap" in hm
        assert "Aucun argument identifié" in hm

    def test_no_fallacies_max_quality(self, viz):
        state = {"identified_arguments": {"arg_1": "Good argument"}}
        hm = viz.generate_argument_quality_heatmap(state)
        assert ": 10" in hm  # Max quality

    def test_one_fallacy_reduces_quality(self, viz):
        state = {
            "identified_arguments": {"arg_1": "Argument"},
            "identified_fallacies": {
                "f1": {"type": "X", "target_argument_id": "arg_1"},
            },
        }
        hm = viz.generate_argument_quality_heatmap(state)
        assert ": 8" in hm  # 10 - 2*1 = 8

    def test_many_fallacies_zero_quality(self, viz):
        state = {
            "identified_arguments": {"arg_1": "Argument"},
            "identified_fallacies": {
                f"f{i}": {"type": "X", "target_argument_id": "arg_1"}
                for i in range(10)
            },
        }
        hm = viz.generate_argument_quality_heatmap(state)
        assert ": 0" in hm  # max(0, 10-20) = 0

    def test_long_text_truncated(self, viz):
        long_text = "B" * 50
        state = {"identified_arguments": {"arg_1": long_text}}
        hm = viz.generate_argument_quality_heatmap(state)
        assert "..." in hm

    def test_title_present(self, viz, sample_state):
        hm = viz.generate_argument_quality_heatmap(sample_state)
        assert "title" in hm


# ============================================================
# generate_all_visualizations
# ============================================================

class TestGenerateAllVisualizations:
    def test_keys_present(self, viz, sample_state):
        result = viz.generate_all_visualizations(sample_state)
        assert "argument_graph" in result
        assert "fallacy_distribution" in result
        assert "argument_quality_heatmap" in result

    def test_all_strings(self, viz, sample_state):
        result = viz.generate_all_visualizations(sample_state)
        for v in result.values():
            assert isinstance(v, str)

    def test_empty_state(self, viz, empty_state):
        result = viz.generate_all_visualizations(empty_state)
        assert len(result) == 3


# ============================================================
# generate_html_report
# ============================================================

class TestGenerateHtmlReport:
    def test_html_structure(self, viz, sample_state):
        html = viz.generate_html_report(sample_state)
        assert "<!DOCTYPE html>" in html
        assert "<html>" in html
        assert "</html>" in html
        assert "mermaid" in html

    def test_contains_title(self, viz, sample_state):
        html = viz.generate_html_report(sample_state)
        assert "Rapport d'Analyse Rhétorique" in html

    def test_contains_visualizations(self, viz, sample_state):
        html = viz.generate_html_report(sample_state)
        assert "Graphe des Arguments" in html
        assert "Distribution des Sophismes" in html
        assert "Qualité des Arguments" in html

    def test_mermaid_script_included(self, viz, sample_state):
        html = viz.generate_html_report(sample_state)
        assert "mermaid.min.js" in html

    def test_empty_state(self, viz, empty_state):
        html = viz.generate_html_report(empty_state)
        assert "<!DOCTYPE html>" in html
        # Should still produce valid HTML even with empty data
        assert "</html>" in html
