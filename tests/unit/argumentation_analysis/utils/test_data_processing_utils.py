#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module data_processing_utils.py.
"""

import pytest
from argumentation_analysis.utils.data_processing_utils import group_results_by_corpus

# Fixtures pour les données de test

@pytest.fixture
def sample_results_various_sources():
    """Retourne un échantillon de résultats avec diverses sources."""
    return [
        {"id": 1, "text": "Texte A", "source_name": "Discours d'Hitler - 1933"},
        {"id": 2, "text": "Texte B", "source_name": "Débat Lincoln-Douglas - 1"},
        {"id": 3, "text": "Texte C", "source_name": "Article de Blog X"},
        {"id": 4, "text": "Texte D", "source_name": "Discours d'Hitler - 1939"},
        {"id": 5, "text": "Texte E", "source_name": "Autre source Lincoln"},
        {"id": 6, "text": "Texte F", "source_name": "Document Y"},
        {"id": 7, "text": "Texte G", "source_name": "Analyse Douglas"},
    ]

@pytest.fixture
def results_with_missing_source_name():
    """Retourne des résultats où 'source_name' est manquant pour certains."""
    return [
        {"id": 1, "text": "Texte A", "source_name": "Discours d'Hitler - 1933"},
        {"id": 2, "text": "Texte B"}, # source_name manquant
        {"id": 3, "text": "Texte C", "source_name": "Article de Blog X"},
    ]

@pytest.fixture
def results_with_non_dict_elements():
    """Retourne une liste contenant des éléments qui ne sont pas des dictionnaires."""
    return [
        {"id": 1, "text": "Texte A", "source_name": "Discours d'Hitler - 1933"},
        "ceci n'est pas un dict",
        {"id": 3, "text": "Texte C", "source_name": "Article de Blog X"},
    ]

# Tests pour group_results_by_corpus

def test_group_results_nominal_case(sample_results_various_sources):
    """Teste le regroupement nominal des résultats."""
    grouped = group_results_by_corpus(sample_results_various_sources)
    
    assert "Discours d'Hitler" in grouped
    assert len(grouped["Discours d'Hitler"]) == 2
    assert any(r["id"] == 1 for r in grouped["Discours d'Hitler"])
    assert any(r["id"] == 4 for r in grouped["Discours d'Hitler"])

    assert "Débats Lincoln-Douglas" in grouped
    assert len(grouped["Débats Lincoln-Douglas"]) == 3
    assert any(r["id"] == 2 for r in grouped["Débats Lincoln-Douglas"])
    assert any(r["id"] == 5 for r in grouped["Débats Lincoln-Douglas"])
    assert any(r["id"] == 7 for r in grouped["Débats Lincoln-Douglas"])

    assert "Autres corpus" in grouped
    assert len(grouped["Autres corpus"]) == 2
    assert any(r["id"] == 3 for r in grouped["Autres corpus"])
    assert any(r["id"] == 6 for r in grouped["Autres corpus"])

def test_group_results_empty_list():
    """Teste le regroupement avec une liste de résultats vide."""
    grouped = group_results_by_corpus([])
    assert grouped == {}

def test_group_results_missing_source_name(results_with_missing_source_name):
    """Teste le regroupement quand 'source_name' est manquant."""
    grouped = group_results_by_corpus(results_with_missing_source_name)
    
    assert "Discours d'Hitler" in grouped
    assert len(grouped["Discours d'Hitler"]) == 1
    assert grouped["Discours d'Hitler"][0]["id"] == 1

    assert "Autres corpus" in grouped  # Le résultat sans source_name va ici par défaut
    assert len(grouped["Autres corpus"]) == 2 # Un pour "Article de Blog X", un pour celui sans source_name (classé "Inconnu" puis "Autres corpus")
    assert any(r["id"] == 3 for r in grouped["Autres corpus"])
    assert any(r.get("source_name") == "Inconnu" for r in grouped["Autres corpus"])


def test_group_results_with_non_dict_elements(results_with_non_dict_elements):
    """Teste le regroupement avec des éléments non-dictionnaires dans la liste."""
    grouped = group_results_by_corpus(results_with_non_dict_elements)
    
    assert "Discours d'Hitler" in grouped
    assert len(grouped["Discours d'Hitler"]) == 1
    assert grouped["Discours d'Hitler"][0]["id"] == 1

    assert "Autres corpus" in grouped
    assert len(grouped["Autres corpus"]) == 1
    assert grouped["Autres corpus"][0]["id"] == 3
    
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

def test_group_results_all_other_corpus():
    """Teste le cas où tous les résultats vont dans 'Autres corpus'."""
    results = [
        {"id": 1, "text": "Texte A", "source_name": "Source Inconnue 1"},
        {"id": 2, "text": "Texte B", "source_name": "Source Inconnue 2"},
    ]
    grouped = group_results_by_corpus(results)
    assert "Autres corpus" in grouped
    assert len(grouped["Autres corpus"]) == 2
    assert "Discours d'Hitler" not in grouped
    assert "Débats Lincoln-Douglas" not in grouped

def test_group_results_specific_corpus_names():
    """Teste des noms de source qui pourraient être ambigus mais doivent être correctement classés."""
    results = [
        {"id": 1, "text": "Texte H", "source_name": "Un document sur Hitler et la guerre"},
        {"id": 2, "text": "Texte LD", "source_name": "Notes sur Lincoln"},
        {"id": 3, "text": "Texte D", "source_name": "Commentaire de Douglas"},
    ]
    grouped = group_results_by_corpus(results)
    assert "Discours d'Hitler" in grouped
    assert len(grouped["Discours d'Hitler"]) == 1
    assert "Débats Lincoln-Douglas" in grouped
    assert len(grouped["Débats Lincoln-Douglas"]) == 2
    assert "Autres corpus" not in grouped