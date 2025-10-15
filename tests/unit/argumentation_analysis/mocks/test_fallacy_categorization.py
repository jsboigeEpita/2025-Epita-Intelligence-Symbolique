# -*- coding: utf-8 -*-
"""Tests pour le MockFallacyCategorizer."""

import pytest
import logging
from argumentation_analysis.mocks.fallacy_categorization import MockFallacyCategorizer


@pytest.fixture
def categorizer_default() -> MockFallacyCategorizer:
    """Instance de MockFallacyCategorizer avec config par défaut."""
    return MockFallacyCategorizer()


@pytest.fixture
def categorizer_custom_config() -> MockFallacyCategorizer:
    """Instance avec une configuration personnalisée."""
    config = {
        "fallacy_categories": {
            "Custom Cat 1 (Mock)": ["CustomTypeA", "CustomTypeB"],
            "Custom Cat 2 (Mock)": ["CustomTypeC"],
        }
    }
    return MockFallacyCategorizer(config=config)


def test_initialization_default(categorizer_default: MockFallacyCategorizer):
    """Teste l'initialisation avec la configuration par défaut."""
    assert categorizer_default.get_config() == {}
    assert "Sophismes de Pertinence (Mock)" in categorizer_default.fallacy_categories
    assert (
        "Ad Hominem (Mock)"
        in categorizer_default.fallacy_categories["Sophismes de Pertinence (Mock)"]
    )
    assert (
        categorizer_default.type_to_category_map["ad hominem (mock)"]
        == "Sophismes de Pertinence (Mock)"
    )


def test_initialization_custom_config(
    categorizer_custom_config: MockFallacyCategorizer,
):
    """Teste l'initialisation avec une configuration personnalisée."""
    expected_categories = {
        "Custom Cat 1 (Mock)": ["CustomTypeA", "CustomTypeB"],
        "Custom Cat 2 (Mock)": ["CustomTypeC"],
    }
    assert categorizer_custom_config.fallacy_categories == expected_categories
    assert (
        categorizer_custom_config.type_to_category_map["customtypea"]
        == "Custom Cat 1 (Mock)"
    )  # Test case insensitivity


def test_categorize_fallacies_invalid_input(
    categorizer_default: MockFallacyCategorizer, caplog
):
    """Teste la catégorisation avec une entrée invalide."""
    with caplog.at_level(logging.WARNING):
        result_none = categorizer_default.categorize_fallacies(None)  # type: ignore
    assert "error" in result_none
    assert result_none["error"] == "Entrée non-liste"
    assert (
        "MockFallacyCategorizer.categorize_fallacies a reçu une entrée non-liste."
        in caplog.text
    )

    caplog.clear()
    fallacies_invalid_dict = [{"type": "AdHominem"}, {"nom_sophisme": "PenteGlissante"}]  # type: ignore
    with caplog.at_level(logging.WARNING):
        result_invalid_dict = categorizer_default.categorize_fallacies(
            fallacies_invalid_dict
        )
    # Devrait logguer pour le deuxième élément invalide.
    # Le premier est valide (même si "type" au lieu de "fallacy_type", le mock ne le gère pas strictement)
    # Le mock actuel ne gère pas "type", il attend "fallacy_type". Donc les deux sont invalides.
    assert "Sophisme invalide ou sans 'fallacy_type'" in caplog.text
    # Le résultat sera probablement vide ou avec "Autres" vide.
    assert not result_invalid_dict.get("Sophismes de Pertinence (Mock)")


def test_categorize_fallacies_empty_list(categorizer_default: MockFallacyCategorizer):
    """Teste avec une liste vide de sophismes."""
    result = categorizer_default.categorize_fallacies([])
    # Le mock retourne un dict vide si aucune catégorie n'a de types après traitement.
    assert result == {}


def test_categorize_fallacies_known_types(categorizer_default: MockFallacyCategorizer):
    """Teste la catégorisation de types de sophismes connus."""
    fallacies = [
        {"fallacy_type": "Ad Hominem (Mock)", "description": "..."},
        {"fallacy_type": "Généralisation Hâtive (Mock)", "description": "..."},
    ]
    result = categorizer_default.categorize_fallacies(fallacies)
    assert "Sophismes de Pertinence (Mock)" in result
    assert "Ad Hominem (Mock)" in result["Sophismes de Pertinence (Mock)"]
    assert "Sophismes de Présomption (Mock)" in result
    assert "Généralisation Hâtive (Mock)" in result["Sophismes de Présomption (Mock)"]


def test_categorize_fallacies_case_insensitivity(
    categorizer_default: MockFallacyCategorizer,
):
    """Teste la sensibilité à la casse pour fallacy_type."""
    fallacies = [{"fallacy_type": "ad hominem (mock)"}]  # En minuscules
    result = categorizer_default.categorize_fallacies(fallacies)
    assert "Sophismes de Pertinence (Mock)" in result
    # Le mock stocke le type original, donc on vérifie avec la casse originale de la config
    assert "Ad Hominem (Mock)" in result["Sophismes de Pertinence (Mock)"]


def test_categorize_fallacies_duplicate_types_in_input(
    categorizer_default: MockFallacyCategorizer,
):
    """Teste que les types dupliqués en entrée n'apparaissent qu'une fois par catégorie."""
    fallacies = [
        {"fallacy_type": "Ad Hominem (Mock)"},
        {"fallacy_type": "Ad Hominem (Mock)"},
    ]
    result = categorizer_default.categorize_fallacies(fallacies)
    assert len(result["Sophismes de Pertinence (Mock)"]) == 1
    assert result["Sophismes de Pertinence (Mock)"][0] == "Ad Hominem (Mock)"


def test_categorize_fallacies_unknown_type(categorizer_default: MockFallacyCategorizer):
    """Teste un type de sophisme inconnu."""
    fallacies = [{"fallacy_type": "Sophisme Inexistant (Mock)"}]
    result = categorizer_default.categorize_fallacies(fallacies)
    assert "Autres Sophismes (Mock)" in result
    assert "Sophisme Inexistant (Mock)" in result["Autres Sophismes (Mock)"]


def test_categorize_fallacies_mixed_known_and_unknown(
    categorizer_default: MockFallacyCategorizer,
):
    """Teste un mélange de sophismes connus et inconnus."""
    fallacies = [
        {"fallacy_type": "Ad Hominem (Mock)"},
        {"fallacy_type": "Sophisme Inconnu A (Mock)"},
        {"fallacy_type": "Équivocation (Mock)"},
        {"fallacy_type": "Sophisme Inconnu B (Mock)"},
    ]
    result = categorizer_default.categorize_fallacies(fallacies)
    assert "Sophismes de Pertinence (Mock)" in result
    assert "Ad Hominem (Mock)" in result["Sophismes de Pertinence (Mock)"]
    assert "Sophismes d'Ambiguïté (Mock)" in result
    assert "Équivocation (Mock)" in result["Sophismes d'Ambiguïté (Mock)"]
    assert "Autres Sophismes (Mock)" in result
    assert "Sophisme Inconnu A (Mock)" in result["Autres Sophismes (Mock)"]
    assert "Sophisme Inconnu B (Mock)" in result["Autres Sophismes (Mock)"]


def test_categorize_fallacies_empty_categories_removed(
    categorizer_default: MockFallacyCategorizer,
):
    """Teste que les catégories vides sont retirées (sauf "Autres" si elle a du contenu)."""
    # On utilise une config custom où certaines catégories par défaut n'existeront pas
    custom_cats = {
        "Cat A": ["Type1"],
    }
    categorizer_temp = MockFallacyCategorizer(
        config={"fallacy_categories": custom_cats}
    )

    fallacies_type1 = [{"fallacy_type": "Type1"}]
    result1 = categorizer_temp.categorize_fallacies(fallacies_type1)
    assert "Cat A" in result1
    assert len(result1) == 1  # Seule Cat A devrait être là

    fallacies_unknown = [{"fallacy_type": "TypeInconnu"}]
    result2 = categorizer_temp.categorize_fallacies(fallacies_unknown)
    assert "Autres Sophismes (Mock)" in result2
    assert "TypeInconnu" in result2["Autres Sophismes (Mock)"]
    assert len(result2) == 1  # Seule Autres devrait être là

    # Si on donne un type qui n'est dans aucune catégorie de la config custom,
    # et que la liste de fallacies est vide, le résultat doit être vide.
    result_empty_input_custom = categorizer_temp.categorize_fallacies([])
    assert result_empty_input_custom == {}


def test_categorize_fallacies_with_custom_config(
    categorizer_custom_config: MockFallacyCategorizer,
):
    """Teste la catégorisation avec une configuration personnalisée."""
    fallacies = [
        {"fallacy_type": "CustomTypeA"},
        {"fallacy_type": "customtypeb"},  # Test case insensitivity
        {"fallacy_type": "UnmappedType"},
    ]
    result = categorizer_custom_config.categorize_fallacies(fallacies)
    assert "Custom Cat 1 (Mock)" in result
    assert "CustomTypeA" in result["Custom Cat 1 (Mock)"]
    assert (
        "CustomTypeB" in result["Custom Cat 1 (Mock)"]
    )  # Doit stocker la casse originale
    assert len(result["Custom Cat 1 (Mock)"]) == 2

    assert "Custom Cat 2 (Mock)" not in result  # Car CustomTypeC n'est pas dans l'input

    assert "Autres Sophismes (Mock)" in result
    assert "UnmappedType" in result["Autres Sophismes (Mock)"]
