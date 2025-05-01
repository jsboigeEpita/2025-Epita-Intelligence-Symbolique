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

# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importer les modules à tester
from models.extract_result import ExtractResult


class TestExtractResult(unittest.TestCase):
    """Tests pour le modèle ExtractResult."""

    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer un résultat d'extraction valide
        self.valid_result = ExtractResult(
            source_name="Test Source",
            extract_name="Test Extract",
            status="valid",
            message="Extraction réussie",
            start_marker="DEBUT_EXTRAIT",
            end_marker="FIN_EXTRAIT",
            template_start="T{0}",
            explanation="Explication de l'extraction",
            extracted_text="Texte extrait de test"
        )
        
        # Créer un résultat d'extraction avec erreur
        self.error_result = ExtractResult(
            source_name="Test Source",
            extract_name="Test Extract",
            status="error",
            message="Erreur lors de l'extraction",
            start_marker="DEBUT_EXTRAIT",
            end_marker="FIN_EXTRAIT"
        )
        
        # Créer un résultat d'extraction rejeté
        self.rejected_result = ExtractResult(
            source_name="Test Source",
            extract_name="Test Extract",
            status="rejected",
            message="Extraction rejetée",
            start_marker="DEBUT_EXTRAIT",
            end_marker="FIN_EXTRAIT"
        )

    def test_init(self):
        """Test d'initialisation d'un résultat d'extraction."""
        # Vérifier les propriétés du résultat valide
        self.assertEqual(self.valid_result.source_name, "Test Source")
        self.assertEqual(self.valid_result.extract_name, "Test Extract")
        self.assertEqual(self.valid_result.status, "valid")
        self.assertEqual(self.valid_result.message, "Extraction réussie")
        self.assertEqual(self.valid_result.start_marker, "DEBUT_EXTRAIT")
        self.assertEqual(self.valid_result.end_marker, "FIN_EXTRAIT")
        self.assertEqual(self.valid_result.template_start, "T{0}")
        self.assertEqual(self.valid_result.explanation, "Explication de l'extraction")
        self.assertEqual(self.valid_result.extracted_text, "Texte extrait de test")

    def test_to_dict(self):
        """Test de conversion d'un résultat d'extraction en dictionnaire."""
        result_dict = self.valid_result.to_dict()
        
        # Vérifier les propriétés du dictionnaire
        self.assertEqual(result_dict["source_name"], "Test Source")
        self.assertEqual(result_dict["extract_name"], "Test Extract")
        self.assertEqual(result_dict["status"], "valid")
        self.assertEqual(result_dict["message"], "Extraction réussie")
        self.assertEqual(result_dict["start_marker"], "DEBUT_EXTRAIT")
        self.assertEqual(result_dict["end_marker"], "FIN_EXTRAIT")
        self.assertEqual(result_dict["template_start"], "T{0}")
        self.assertEqual(result_dict["explanation"], "Explication de l'extraction")
        self.assertEqual(result_dict["extracted_text"], "Texte extrait de test")

    def test_from_dict(self):
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
            "extracted_text": "Nouveau texte extrait"
        }
        
        result = ExtractResult.from_dict(result_dict)
        
        # Vérifier les propriétés du résultat
        self.assertEqual(result.source_name, "New Source")
        self.assertEqual(result.extract_name, "New Extract")
        self.assertEqual(result.status, "valid")
        self.assertEqual(result.message, "Nouvelle extraction")
        self.assertEqual(result.start_marker, "START")
        self.assertEqual(result.end_marker, "END")
        self.assertEqual(result.template_start, "N{0}")
        self.assertEqual(result.explanation, "Nouvelle explication")
        self.assertEqual(result.extracted_text, "Nouveau texte extrait")

    def test_from_dict_with_missing_fields(self):
        """Test de création d'un résultat avec des champs manquants."""
        result_dict = {
            "source_name": "Minimal Source",
            "extract_name": "Minimal Extract",
            "status": "valid",
            "message": "Extraction minimale"
        }
        
        result = ExtractResult.from_dict(result_dict)
        
        # Vérifier les propriétés du résultat
        self.assertEqual(result.source_name, "Minimal Source")
        self.assertEqual(result.extract_name, "Minimal Extract")
        self.assertEqual(result.status, "valid")
        self.assertEqual(result.message, "Extraction minimale")
        self.assertEqual(result.start_marker, "")
        self.assertEqual(result.end_marker, "")
        self.assertEqual(result.template_start, "")
        self.assertEqual(result.explanation, "")
        self.assertEqual(result.extracted_text, "")

    def test_is_valid(self):
        """Test de la méthode is_valid."""
        self.assertTrue(self.valid_result.is_valid())
        self.assertFalse(self.error_result.is_valid())
        self.assertFalse(self.rejected_result.is_valid())

    def test_is_error(self):
        """Test de la méthode is_error."""
        self.assertFalse(self.valid_result.is_error())
        self.assertTrue(self.error_result.is_error())
        self.assertFalse(self.rejected_result.is_error())

    def test_is_rejected(self):
        """Test de la méthode is_rejected."""
        self.assertFalse(self.valid_result.is_rejected())
        self.assertFalse(self.error_result.is_rejected())
        self.assertTrue(self.rejected_result.is_rejected())

    def test_str_representation(self):
        """Test de la représentation sous forme de chaîne."""
        self.assertEqual(str(self.valid_result), "ExtractResult(valid): Extraction réussie")
        self.assertEqual(str(self.error_result), "ExtractResult(error): Erreur lors de l'extraction")
        self.assertEqual(str(self.rejected_result), "ExtractResult(rejected): Extraction rejetée")

    def test_json_serialization(self):
        """Test de sérialisation/désérialisation JSON."""
        # Sérialiser en JSON
        json_str = json.dumps(self.valid_result.to_dict())
        
        # Désérialiser depuis JSON
        result_dict = json.loads(json_str)
        result = ExtractResult.from_dict(result_dict)
        
        # Vérifier les propriétés du résultat
        self.assertEqual(result.source_name, "Test Source")
        self.assertEqual(result.extract_name, "Test Extract")
        self.assertEqual(result.status, "valid")
        self.assertEqual(result.message, "Extraction réussie")
        self.assertEqual(result.start_marker, "DEBUT_EXTRAIT")
        self.assertEqual(result.end_marker, "FIN_EXTRAIT")
        self.assertEqual(result.template_start, "T{0}")
        self.assertEqual(result.explanation, "Explication de l'extraction")
        self.assertEqual(result.extracted_text, "Texte extrait de test")


# Tests paramétrés pour les différents statuts
@pytest.mark.parametrize("status,expected_valid,expected_error,expected_rejected", [
    ("valid", True, False, False),
    ("error", False, True, False),
    ("rejected", False, False, True),
    ("unknown", False, False, False)  # Test avec un statut inconnu
])
def test_status_methods(status, expected_valid, expected_error, expected_rejected):
    """Test paramétré pour les méthodes de vérification de statut."""
    result = ExtractResult(
        source_name="Test Source",
        extract_name="Test Extract",
        status=status,
        message="Test message"
    )
    
    assert result.is_valid() == expected_valid
    assert result.is_error() == expected_error
    assert result.is_rejected() == expected_rejected


if __name__ == "__main__":
    unittest.main()


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
    
    # Vérifier que tous les champs sont présents et ont les bonnes valeurs
    for key, value in extract_result_dict.items():
        assert result_dict[key] == value


def test_extract_result_from_dict_with_fixture(extract_result_dict):
    """Test de création d'un résultat d'extraction à partir d'un dictionnaire avec fixture."""
    result = ExtractResult.from_dict(extract_result_dict)
    
    # Vérifier que tous les champs ont les bonnes valeurs
    for key, value in extract_result_dict.items():
        assert getattr(result, key) == value


@pytest.mark.parametrize("field,value", [
    ("source_name", "Custom Source"),
    ("extract_name", "Custom Extract"),
    ("status", "custom_status"),
    ("message", "Custom message"),
    ("start_marker", "CUSTOM_START"),
    ("end_marker", "CUSTOM_END"),
    ("template_start", "C{0}"),
    ("explanation", "Custom explanation"),
    ("extracted_text", "Custom extracted text")
])
def test_extract_result_field_customization(extract_result_dict, field, value):
    """Test paramétré pour la personnalisation des champs d'un résultat d'extraction."""
    # Modifier le champ dans le dictionnaire
    extract_result_dict[field] = value
    
    # Créer un résultat à partir du dictionnaire modifié
    result = ExtractResult.from_dict(extract_result_dict)
    
    # Vérifier que le champ a bien été modifié
    assert getattr(result, field) == value


def test_extract_result_status_methods_with_fixtures(valid_extract_result, error_extract_result, rejected_extract_result):
    """Test des méthodes de vérification de statut avec fixtures."""
    # Résultat valide
    assert valid_extract_result.is_valid() is True
    assert valid_extract_result.is_error() is False
    assert valid_extract_result.is_rejected() is False
    
    # Résultat avec erreur
    assert error_extract_result.is_valid() is False
    assert error_extract_result.is_error() is True
    assert error_extract_result.is_rejected() is False
    
    # Résultat rejeté
    assert rejected_extract_result.is_valid() is False
    assert rejected_extract_result.is_error() is False
    assert rejected_extract_result.is_rejected() is True


def test_extract_result_str_with_fixtures(valid_extract_result, error_extract_result, rejected_extract_result):
    """Test de la représentation sous forme de chaîne avec fixtures."""
    assert str(valid_extract_result) == "ExtractResult(valid): Extraction réussie"
    assert str(error_extract_result) == "ExtractResult(error): Erreur lors de l'extraction"
    assert str(rejected_extract_result) == "ExtractResult(rejected): Extraction rejetée"


@pytest.mark.parametrize("extracted_text", [
    "",
    "Texte court",
    "Texte avec des caractères spéciaux: é, è, à, ç, ù",
    "Texte\nmulti-ligne\navec\ndes\nretours\nà\nla\nligne",
    "Texte très long " + "a" * 1000
])
def test_extract_result_with_different_extracted_texts(extract_result_dict, extracted_text):
    """Test paramétré pour différents types de textes extraits."""
    extract_result_dict["extracted_text"] = extracted_text
    result = ExtractResult.from_dict(extract_result_dict)
    assert result.extracted_text == extracted_text