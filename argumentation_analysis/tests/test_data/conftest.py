#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fixtures pour les données de test.

Ce module contient des fixtures pytest qui permettent d'accéder facilement
aux données de test préparées pour les tests unitaires et d'intégration.
"""

import pytest
import json
import os
from pathlib import Path

# Chemin de base pour les données de test
TEST_DATA_DIR = Path(__file__).parent


# --- Fixtures pour les définitions d'extraits ---

@pytest.fixture
def valid_extract_definitions_file():
    """Fixture pour le chemin du fichier de définitions d'extraits valides."""
    return TEST_DATA_DIR / "extract_definitions" / "valid" / "valid_extract_definitions.json"


@pytest.fixture
def valid_extract_definitions():
    """Fixture pour les définitions d'extraits valides."""
    file_path = TEST_DATA_DIR / "extract_definitions" / "valid" / "valid_extract_definitions.json"
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture
def partial_extract_definitions_file():
    """Fixture pour le chemin du fichier de définitions d'extraits partiellement valides."""
    return TEST_DATA_DIR / "extract_definitions" / "partial" / "partial_extract_definitions.json"


@pytest.fixture
def partial_extract_definitions():
    """Fixture pour les définitions d'extraits partiellement valides."""
    file_path = TEST_DATA_DIR / "extract_definitions" / "partial" / "partial_extract_definitions.json"
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture
def invalid_extract_definitions_file():
    """Fixture pour le chemin du fichier de définitions d'extraits invalides."""
    return TEST_DATA_DIR / "extract_definitions" / "invalid" / "invalid_extract_definitions.json"


@pytest.fixture
def invalid_extract_definitions():
    """Fixture pour les définitions d'extraits invalides."""
    file_path = TEST_DATA_DIR / "extract_definitions" / "invalid" / "invalid_extract_definitions.json"
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# --- Fixtures pour les textes sources ---

@pytest.fixture
def discours_politique_text():
    """Fixture pour le texte source du discours politique avec marqueurs."""
    file_path = TEST_DATA_DIR / "source_texts" / "with_markers" / "discours_politique.txt"
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


@pytest.fixture
def discours_avec_template_text():
    """Fixture pour le texte source du discours avec template."""
    file_path = TEST_DATA_DIR / "source_texts" / "with_markers" / "discours_avec_template.txt"
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


@pytest.fixture
def article_scientifique_text():
    """Fixture pour le texte source de l'article scientifique avec marqueurs partiels."""
    file_path = TEST_DATA_DIR / "source_texts" / "partial_markers" / "article_scientifique.txt"
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


@pytest.fixture
def texte_sans_marqueurs_text():
    """Fixture pour le texte source sans marqueurs."""
    file_path = TEST_DATA_DIR / "source_texts" / "no_markers" / "texte_sans_marqueurs.txt"
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


# --- Fixtures pour les configurations de services ---

@pytest.fixture
def llm_config():
    """Fixture pour la configuration du service LLM."""
    file_path = TEST_DATA_DIR / "service_configs" / "llm" / "llm_config.json"
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture
def cache_config():
    """Fixture pour la configuration du service de cache."""
    file_path = TEST_DATA_DIR / "service_configs" / "cache" / "cache_config.json"
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture
def crypto_config():
    """Fixture pour la configuration du service de cryptographie."""
    file_path = TEST_DATA_DIR / "service_configs" / "crypto" / "crypto_config.json"
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# --- Fixtures pour les cas d'erreur ---

@pytest.fixture
def network_error_scenarios():
    """Fixture pour les scénarios d'erreur réseau."""
    file_path = TEST_DATA_DIR / "error_cases" / "network_error.json"
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)["error_scenarios"]


@pytest.fixture
def service_error_scenarios():
    """Fixture pour les scénarios d'erreur de service."""
    file_path = TEST_DATA_DIR / "error_cases" / "service_error.json"
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)["error_scenarios"]


@pytest.fixture
def validation_error_scenarios():
    """Fixture pour les scénarios d'erreur de validation."""
    file_path = TEST_DATA_DIR / "error_cases" / "validation_error.json"
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)["error_scenarios"]


# --- Fixtures pour les cas de test spécifiques ---

@pytest.fixture
def extract_with_template_missing_first_letter():
    """Fixture pour un extrait avec template mais sans première lettre."""
    return {
        "extract_name": "Introduction avec template mais sans première lettre",
        "start_marker": "commence mon discours",
        "end_marker": "Passons maintenant",
        "template_start": "I{0}"
    }


@pytest.fixture
def extract_with_missing_end_marker():
    """Fixture pour un extrait avec marqueur de fin manquant."""
    return {
        "extract_name": "Extrait avec marqueur de fin manquant",
        "start_marker": "En matière d'économie, nous proposons",
        "end_marker": "",
        "template_start": ""
    }