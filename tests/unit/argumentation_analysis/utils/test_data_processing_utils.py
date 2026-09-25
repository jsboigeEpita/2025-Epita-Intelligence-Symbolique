#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module data_processing_utils.py.

#2362 : le libellé de corpus n'est plus canonisé par sous-chaîne de nom —
chaque source_name passe verbatim, et un résultat sans nom reçoit un
identifiant positionnel opaque (``corpus_{idx}``).
"""

import pytest
from argumentation_analysis.utils.data_processing_utils import group_results_by_corpus

# Fixtures pour les données de test


@pytest.fixture
def sample_results_various_sources():
    """Retourne un échantillon de résultats avec diverses sources."""
    return [
        {"id": 1, "text": "Texte A", "source_name": "corpus_A"},
        {"id": 2, "text": "Texte B", "source_name": "corpus_B - 1"},
        {"id": 3, "text": "Texte C", "source_name": "Article de Blog X"},
        {"id": 4, "text": "Texte D", "source_name": "corpus_A"},
        {"id": 5, "text": "Texte E", "source_name": "Autre source corpus_B"},
        {"id": 6, "text": "Texte F", "source_name": "Document Y"},
        {"id": 7, "text": "Texte G", "source_name": "Analyse corpus_C"},
    ]


@pytest.fixture
def results_with_missing_source_name():
    """Retourne des résultats où 'source_name' est manquant pour certains."""
    return [
        {"id": 1, "text": "Texte A", "source_name": "corpus_A"},
        {"id": 2, "text": "Texte B"},  # source_name manquant
        {"id": 3, "text": "Texte C", "source_name": "Article de Blog X"},
    ]


@pytest.fixture
def results_with_non_dict_elements():
    """Retourne une liste contenant des éléments qui ne sont pas des dictionnaires."""
    return [
        {"id": 1, "text": "Texte A", "source_name": "corpus_A"},
        "ceci n'est pas un dict",
        {"id": 3, "text": "Texte C", "source_name": "Article de Blog X"},
    ]


# Tests pour group_results_by_corpus


def test_group_results_nominal_case(sample_results_various_sources):
    """Chaque source_name distinct forme son propre corpus, verbatim."""
    grouped = group_results_by_corpus(sample_results_various_sources)

    assert len(grouped["corpus_A"]) == 2
    assert any(r["id"] == 1 for r in grouped["corpus_A"])
    assert any(r["id"] == 4 for r in grouped["corpus_A"])

    assert len(grouped["corpus_B - 1"]) == 1
    assert grouped["corpus_B - 1"][0]["id"] == 2

    assert len(grouped["Autre source corpus_B"]) == 1
    assert grouped["Autre source corpus_B"][0]["id"] == 5

    assert len(grouped["Article de Blog X"]) == 1
    assert grouped["Article de Blog X"][0]["id"] == 3

    assert len(grouped["Document Y"]) == 1
    assert grouped["Document Y"][0]["id"] == 6

    assert len(grouped["Analyse corpus_C"]) == 1
    assert grouped["Analyse corpus_C"][0]["id"] == 7


def test_group_results_empty_list():
    """Teste le regroupement avec une liste de résultats vide."""
    grouped = group_results_by_corpus([])
    assert grouped == {}


def test_group_results_missing_source_name(results_with_missing_source_name):
    """Sans 'source_name', le résultat reçoit un identifiant positionnel opaque."""
    grouped = group_results_by_corpus(results_with_missing_source_name)

    assert len(grouped["corpus_A"]) == 1
    assert grouped["corpus_A"][0]["id"] == 1

    # L'item à l'index 1 n'a pas de nom : identifiant positionnel corpus_1
    assert len(grouped["corpus_1"]) == 1
    assert grouped["corpus_1"][0]["id"] == 2

    assert len(grouped["Article de Blog X"]) == 1
    assert grouped["Article de Blog X"][0]["id"] == 3


def test_group_results_missing_names_get_distinct_positional_ids():
    """Deux résultats sans nom ne fusionnent pas : chacun garde sa position."""
    grouped = group_results_by_corpus(
        [{"id": 1, "text": "Texte A"}, {"id": 2, "text": "Texte B"}]
    )
    assert set(grouped) == {"corpus_0", "corpus_1"}
    assert grouped["corpus_0"][0]["id"] == 1
    assert grouped["corpus_1"][0]["id"] == 2


def test_group_results_corpus_name_wins_over_source_name():
    """Un 'corpus_name' explicite a priorité sur le 'source_name'."""
    grouped = group_results_by_corpus(
        [{"id": 1, "corpus_name": "groupe_explicite", "source_name": "corpus_A"}]
    )
    assert set(grouped) == {"groupe_explicite"}


def test_group_results_with_non_dict_elements(results_with_non_dict_elements):
    """Teste le regroupement avec des éléments non-dictionnaires dans la liste."""
    grouped = group_results_by_corpus(results_with_non_dict_elements)

    assert len(grouped["corpus_A"]) == 1
    assert grouped["corpus_A"][0]["id"] == 1

    assert len(grouped["Article de Blog X"]) == 1
    assert grouped["Article de Blog X"][0]["id"] == 3

    # Vérifie que le nombre total d'éléments groupés est correct (ignore les non-dictionnaires)
    total_grouped_items = sum(len(items) for items in grouped.values())
    assert total_grouped_items == 2


def test_group_results_input_not_list():
    """Teste la levée de TypeError si l'entrée n'est pas une liste."""
    with pytest.raises(TypeError) as excinfo:
        group_results_by_corpus("ceci n'est pas une liste")
    assert "L'argument 'results' doit être une liste." in str(excinfo.value)

    with pytest.raises(TypeError) as excinfo:
        group_results_by_corpus({"un": "dict"})
    assert "L'argument 'results' doit être une liste." in str(excinfo.value)


def test_group_results_is_name_blind():
    """Témoin d'aveuglement (#2362) : des sources portant des mots-clés de
    noms de personnes ne sont PAS canonisées — chacune reste verbatim."""
    results = [
        {
            "id": 1,
            "text": "Texte H",
            "source_name": "Un document sur Hitler et la guerre",
        },
        {"id": 2, "text": "Texte LD", "source_name": "Notes sur Lincoln"},
        {"id": 3, "text": "Texte D", "source_name": "Commentaire de Douglas"},
    ]
    grouped = group_results_by_corpus(results)
    assert set(grouped) == {
        "Un document sur Hitler et la guerre",
        "Notes sur Lincoln",
        "Commentaire de Douglas",
    }
    for corpus in grouped.values():
        assert len(corpus) == 1
