#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module stats_calculator.py.
"""

import pytest
from argumentation_analysis.analytics.stats_calculator import calculate_average_scores

# Fixtures pour les données de test


@pytest.fixture
def sample_grouped_results():
    """Retourne un échantillon de résultats groupés pour les tests."""
    return {
        "CorpusA": [
            {
                "id": "doc1",
                "confidence_score": 0.8,
                "richness_score": 0.9,
                "length": 100,
            },
            {
                "id": "doc2",
                "confidence_score": 0.7,
                "richness_score": 0.85,
                "length": 150,
                "non_numeric": "abc",
            },
        ],
        "CorpusB": [
            {
                "id": "doc3",
                "confidence_score": 0.9,
                "richness_score": 0.95,
                "length": 120,
            },
            {
                "id": "doc4",
                "confidence_score": 0.85,
                "richness_score": 0.90,
                "length": 180,
                "another_metric": 5,
            },
        ],
        "CorpusC_Empty": [],  # Corpus sans résultats
        "CorpusD_NoNumeric": [  # Corpus avec résultats mais sans scores numériques pertinents
            {"id": "doc5", "text": "bla", "source": "web"},
            {"id": "doc6", "comment": "foo"},
        ],
        "CorpusE_Single": [{"id": "doc7", "confidence_score": 0.6}],
    }


# Tests pour calculate_average_scores


def test_calculate_average_scores_nominal_case(sample_grouped_results):
    """Teste le calcul des scores moyens dans un cas nominal."""
    averages = calculate_average_scores(sample_grouped_results)

    assert "CorpusA" in averages
    assert "average_confidence_score" in averages["CorpusA"]
    assert "average_richness_score" in averages["CorpusA"]
    assert "average_length" in averages["CorpusA"]
    assert (
        "average_non_numeric" not in averages["CorpusA"]
    )  # Doit ignorer les non-numériques
    assert averages["CorpusA"]["average_confidence_score"] == pytest.approx(
        0.75
    )  # (0.8 + 0.7) / 2
    assert averages["CorpusA"]["average_richness_score"] == pytest.approx(
        0.875
    )  # (0.9 + 0.85) / 2
    assert averages["CorpusA"]["average_length"] == pytest.approx(
        125
    )  # (100 + 150) / 2

    assert "CorpusB" in averages
    assert "average_confidence_score" in averages["CorpusB"]
    assert "average_richness_score" in averages["CorpusB"]
    assert "average_length" in averages["CorpusB"]
    assert "average_another_metric" in averages["CorpusB"]
    assert averages["CorpusB"]["average_confidence_score"] == pytest.approx(
        0.875
    )  # (0.9 + 0.85) / 2
    assert averages["CorpusB"]["average_richness_score"] == pytest.approx(
        0.925
    )  # (0.95 + 0.90) / 2
    assert averages["CorpusB"]["average_length"] == pytest.approx(
        150
    )  # (120 + 180) / 2
    assert averages["CorpusB"]["average_another_metric"] == pytest.approx(
        5.0
    )  # Une seule valeur


def test_calculate_average_scores_empty_corpus(sample_grouped_results):
    """Teste le cas d'un corpus sans résultats."""
    averages = calculate_average_scores(sample_grouped_results)
    assert "CorpusC_Empty" in averages
    assert averages["CorpusC_Empty"] == {}


def test_calculate_average_scores_no_numeric_scores(sample_grouped_results):
    """Teste le cas d'un corpus avec des résultats mais sans scores numériques."""
    averages = calculate_average_scores(sample_grouped_results)
    assert "CorpusD_NoNumeric" in averages
    assert averages["CorpusD_NoNumeric"] == {}


def test_calculate_average_scores_single_result_corpus(sample_grouped_results):
    """Teste le cas d'un corpus avec un seul résultat."""
    averages = calculate_average_scores(sample_grouped_results)
    assert "CorpusE_Single" in averages
    assert "average_confidence_score" in averages["CorpusE_Single"]
    assert averages["CorpusE_Single"]["average_confidence_score"] == pytest.approx(0.6)


def test_calculate_average_scores_empty_input():
    """Teste avec une entrée grouped_results vide."""
    averages = calculate_average_scores({})
    assert averages == {}


def test_calculate_average_scores_mixed_numeric_types():
    """Teste avec des types numériques mixtes (int, float)."""
    grouped_results = {
        "MixedCorpus": [
            {"score_a": 10, "score_b": 5.5},
            {"score_a": 20, "score_b": 4.5, "score_c": 100.0},
        ]
    }
    averages = calculate_average_scores(grouped_results)
    assert "MixedCorpus" in averages
    assert averages["MixedCorpus"]["average_score_a"] == pytest.approx(
        15.0
    )  # (10 + 20) / 2
    assert averages["MixedCorpus"]["average_score_b"] == pytest.approx(
        5.0
    )  # (5.5 + 4.5) / 2
    assert averages["MixedCorpus"]["average_score_c"] == pytest.approx(
        100.0
    )  # une seule valeur


def test_calculate_average_scores_results_not_dicts():
    """
    Teste le comportement lorsque les éléments dans la liste de résultats ne sont pas tous des dictionnaires.
    La fonction actuelle devrait ignorer les éléments non-dictionnaires.
    """
    grouped_results = {
        "CorpusWithInvalid": [
            {"id": "doc1", "score": 0.8},
            "not a dict",
            None,
            {"id": "doc2", "score": 0.7},
            123,
        ]
    }
    # La fonction actuelle ne lève pas d'erreur mais les ignore.
    # Si une gestion d'erreur stricte était ajoutée, ce test devrait être adapté.
    averages = calculate_average_scores(grouped_results)
    assert "CorpusWithInvalid" in averages
    assert averages["CorpusWithInvalid"]["average_score"] == pytest.approx(0.75)


# Il n'est pas explicitement demandé de tester les TypeError pour les entrées malformées
# car la docstring indique que cela n'est pas géré explicitement, mais cela pourrait être
# un ajout futur. Par exemple:
# def test_calculate_average_scores_malformed_input():
#     with pytest.raises(TypeError): # ou AttributeError selon l'implémentation
#         calculate_average_scores({"CorpusA": "not a list"})
#     with pytest.raises(TypeError): # ou AttributeError
#         calculate_average_scores("not a dict")
