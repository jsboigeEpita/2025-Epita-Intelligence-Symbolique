#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le modèle ExtractResult

Ce module contient les tests unitaires pour le modèle ExtractResult
qui représente le résultat d'une opération d'extraction de texte.
"""

import unittest
import os
import sys
import json
import pytest
from pathlib import Path

# Utiliser des imports absolus pour éviter les problèmes de chemin
from argumentation_analysis.models.extract_result import ExtractResult


def test_init(valid_extract_result):
    """Test d'initialisation d'un résultat d'extraction."""
    assert valid_extract_result.source_name == "Test Source"
    assert valid_extract_result.extract_name == "Test Extract"
    assert valid_extract_result.status == "valid"
    assert valid_extract_result.message == "Extraction réussie"
    assert valid_extract_result.start_marker == "DEBUT_EXTRAIT"
    assert valid_extract_result.end_marker == "FIN_EXTRAIT"
    assert valid_extract_result.template_start == "T{0}"
    assert valid_extract_result.explanation == "Explication de l'extraction"
    assert valid_extract_result.extracted_text == "Texte extrait de test"


def test_to_dict(valid_extract_result):
    """Test de conversion d'un résultat d'extraction en dictionnaire."""
    result_dict = valid_extract_result.to_dict()
    assert result_dict["source_name"] == "Test Source"
    assert result_dict["extract_name"] == "Test Extract"
    assert result_dict["status"] == "valid"
    assert result_dict["message"] == "Extraction réussie"
    assert result_dict["start_marker"] == "DEBUT_EXTRAIT"
    assert result_dict["end_marker"] == "FIN_EXTRAIT"
    assert result_dict["template_start"] == "T{0}"
    assert result_dict["explanation"] == "Explication de l'extraction"
    assert result_dict["extracted_text"] == "Texte extrait de test"


def test_from_dict():
    """Test de création d'un résultat d'extraction à partir d'un dictionnaire."""
    result_dict = {
        "source_name": "New Source",
        "extract_name": "New Extract",
        "status": "valid",
        "message": "Nouvelle extraction",
        "start_marker": "START",
        "end_marker": "END",
        "template_start": "N{0}",
        "explanation": "Nouvelle explication",
        "extracted_text": "Nouveau texte extrait",
    }
    result = ExtractResult.from_dict(result_dict)
    assert result.source_name == "New Source"
    assert result.extract_name == "New Extract"
    assert result.status == "valid"
    assert result.message == "Nouvelle extraction"
    assert result.start_marker == "START"
    assert result.end_marker == "END"
    assert result.template_start == "N{0}"
    assert result.explanation == "Nouvelle explication"
    assert result.extracted_text == "Nouveau texte extrait"


def test_from_dict_with_missing_fields():
    """Test de création d'un résultat avec des champs manquants."""
    result_dict = {
        "source_name": "Minimal Source",
        "extract_name": "Minimal Extract",
        "status": "valid",
        "message": "Extraction minimale",
    }
    result = ExtractResult.from_dict(result_dict)
    assert result.source_name == "Minimal Source"
    assert result.extract_name == "Minimal Extract"
    assert result.status == "valid"
    assert result.message == "Extraction minimale"
    assert result.start_marker == ""
    assert result.end_marker == ""
    assert result.template_start == ""
    assert result.explanation == ""
    assert result.extracted_text == ""


def test_is_valid(valid_extract_result, error_extract_result, rejected_extract_result):
    """Test de la méthode is_valid."""
    assert valid_extract_result.is_valid()
    assert not error_extract_result.is_valid()
    assert not rejected_extract_result.is_valid()


def test_is_error(valid_extract_result, error_extract_result, rejected_extract_result):
    """Test de la méthode is_error."""
    assert not valid_extract_result.is_error()
    assert error_extract_result.is_error()
    assert not rejected_extract_result.is_error()


def test_is_rejected(
    valid_extract_result, error_extract_result, rejected_extract_result
):
    """Test de la méthode is_rejected."""
    assert not valid_extract_result.is_rejected()
    assert not error_extract_result.is_rejected()
    assert rejected_extract_result.is_rejected()


def test_str_representation(
    valid_extract_result, error_extract_result, rejected_extract_result
):
    """Test de la représentation sous forme de chaîne."""
    assert str(valid_extract_result) == "ExtractResult(valid): Extraction réussie"
    assert (
        str(error_extract_result) == "ExtractResult(error): Erreur lors de l'extraction"
    )
    assert str(rejected_extract_result) == "ExtractResult(rejected): Extraction rejetée"


def test_json_serialization(valid_extract_result):
    """Test de sérialisation/désérialisation JSON."""
    json_str = json.dumps(valid_extract_result.to_dict())
    result_dict = json.loads(json_str)
    result = ExtractResult.from_dict(result_dict)
    assert result.source_name == "Test Source"
    assert result.extract_name == "Test Extract"
    assert result.status == "valid"
    assert result.message == "Extraction réussie"
    assert result.start_marker == "DEBUT_EXTRAIT"
    assert result.end_marker == "FIN_EXTRAIT"
    assert result.template_start == "T{0}"
    assert result.explanation == "Explication de l'extraction"
    assert result.extracted_text == "Texte extrait de test"


# Tests paramétrés pour les différents statuts
@pytest.mark.parametrize(
    "status,expected_valid,expected_error,expected_rejected",
    [
        ("valid", True, False, False),
        ("error", False, True, False),
        ("rejected", False, False, True),
        ("unknown", False, False, False),
    ],
)
def test_status_methods(status, expected_valid, expected_error, expected_rejected):
    """Test paramétré pour les méthodes de vérification de statut."""
    result = ExtractResult(
        source_name="Test Source",
        extract_name="Test Extract",
        status=status,
        message="Test message",
    )
    assert result.is_valid() == expected_valid
    assert result.is_error() == expected_error
    assert result.is_rejected() == expected_rejected


# Tests utilisant les fixtures pytest
def test_extract_result_init_with_fixture(valid_extract_result):
    """Test d'initialisation d'un résultat d'extraction avec fixture."""
    assert valid_extract_result.source_name == "Test Source"
    assert valid_extract_result.extract_name == "Test Extract"
    assert valid_extract_result.status == "valid"
    assert valid_extract_result.message == "Extraction réussie"
    assert valid_extract_result.start_marker == "DEBUT_EXTRAIT"
    assert valid_extract_result.end_marker == "FIN_EXTRAIT"
    assert valid_extract_result.template_start == "T{0}"
    assert valid_extract_result.explanation == "Explication de l'extraction"
    assert valid_extract_result.extracted_text == "Texte extrait de test"


def test_extract_result_to_dict_with_fixture(valid_extract_result, extract_result_dict):
    """Test de conversion d'un résultat d'extraction en dictionnaire avec fixture."""
    result_dict = valid_extract_result.to_dict()
    for key, value in extract_result_dict.items():
        assert result_dict[key] == value


def test_extract_result_from_dict_with_fixture(extract_result_dict):
    """Test de création d'un résultat d'extraction à partir d'un dictionnaire avec fixture."""
    result = ExtractResult.from_dict(extract_result_dict)
    for key, value in extract_result_dict.items():
        assert getattr(result, key) == value


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_name", "Custom Source"),
        ("extract_name", "Custom Extract"),
        ("status", "custom_status"),
        ("message", "Custom message"),
        ("start_marker", "CUSTOM_START"),
        ("end_marker", "CUSTOM_END"),
        ("template_start", "C{0}"),
        ("explanation", "Custom explanation"),
        ("extracted_text", "Custom extracted text"),
    ],
)
def test_extract_result_field_customization(extract_result_dict, field, value):
    """Test paramétré pour la personnalisation des champs d'un résultat d'extraction."""
    extract_result_dict[field] = value
    result = ExtractResult.from_dict(extract_result_dict)
    assert getattr(result, field) == value


def test_extract_result_status_methods_with_fixtures(
    valid_extract_result, error_extract_result, rejected_extract_result
):
    """Test des méthodes de vérification de statut avec fixtures."""
    assert valid_extract_result.is_valid() is True
    assert valid_extract_result.is_error() is False
    assert valid_extract_result.is_rejected() is False

    assert error_extract_result.is_valid() is False
    assert error_extract_result.is_error() is True
    assert error_extract_result.is_rejected() is False

    assert rejected_extract_result.is_valid() is False
    assert rejected_extract_result.is_error() is False
    assert rejected_extract_result.is_rejected() is True


def test_extract_result_str_with_fixtures(
    valid_extract_result, error_extract_result, rejected_extract_result
):
    """Test de la représentation sous forme de chaîne avec fixtures."""
    assert str(valid_extract_result) == "ExtractResult(valid): Extraction réussie"
    assert (
        str(error_extract_result) == "ExtractResult(error): Erreur lors de l'extraction"
    )
    assert str(rejected_extract_result) == "ExtractResult(rejected): Extraction rejetée"


@pytest.mark.parametrize(
    "extracted_text",
    [
        "",
        "Texte court",
        "Texte avec des caractères spéciaux: é, è, à, ç, ù",
        "Texte\nmulti-ligne\navec\ndes\nretours\nà\nla\nligne",
        "Texte très long " + "a" * 1000,
    ],
)
def test_extract_result_with_different_extracted_texts(
    extract_result_dict, extracted_text
):
    """Test paramétré pour différents types de textes extraits."""
    extract_result_dict["extracted_text"] = extracted_text
    result = ExtractResult.from_dict(extract_result_dict)
    assert result.extracted_text == extracted_text
