#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le modèle ExtractDefinition

Ce module contient les tests unitaires pour le modèle ExtractDefinition
qui représente les définitions d'extraits et de sources.
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
from models.extract_definition import (
    ExtractDefinitions, SourceDefinition, Extract
)


class TestExtractDefinition(unittest.TestCase):
    """Tests pour le modèle ExtractDefinition."""

    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer un extrait de test
        self.extract = Extract(
            extract_name="Test Extract",
            start_marker="DEBUT_EXTRAIT",
            end_marker="FIN_EXTRAIT",
            template_start="T{0}"
        )
        
        # Créer une source de test
        self.source = SourceDefinition(
            source_name="Test Source",
            source_type="url",
            schema="https",
            host_parts=["example", "com"],
            path="/test",
            extracts=[self.extract]
        )
        
        # Créer des définitions d'extraits de test
        self.extract_definitions = ExtractDefinitions(
            sources=[self.source]
        )

    def test_extract_to_dict(self):
        """Test de conversion d'un extrait en dictionnaire."""
        extract_dict = self.extract.to_dict()
        
        # Vérifier les propriétés du dictionnaire
        self.assertEqual(extract_dict["extract_name"], "Test Extract")
        self.assertEqual(extract_dict["start_marker"], "DEBUT_EXTRAIT")
        self.assertEqual(extract_dict["end_marker"], "FIN_EXTRAIT")
        self.assertEqual(extract_dict["template_start"], "T{0}")

    def test_source_definition_to_dict(self):
        """Test de conversion d'une définition de source en dictionnaire."""
        source_dict = self.source.to_dict()
        
        # Vérifier les propriétés du dictionnaire
        self.assertEqual(source_dict["source_name"], "Test Source")
        self.assertEqual(source_dict["source_type"], "url")
        self.assertEqual(source_dict["schema"], "https")
        self.assertEqual(source_dict["host_parts"], ["example", "com"])
        self.assertEqual(source_dict["path"], "/test")
        self.assertEqual(len(source_dict["extracts"]), 1)
        
        # Vérifier l'extrait dans la source
        extract_dict = source_dict["extracts"][0]
        self.assertEqual(extract_dict["extract_name"], "Test Extract")

    def test_extract_definitions_to_dict_list(self):
        """Test de conversion des définitions d'extraits en liste de dictionnaires."""
        definitions_list = self.extract_definitions.to_dict_list()
        
        # Vérifier les propriétés de la liste
        self.assertEqual(len(definitions_list), 1)
        
        # Vérifier la source dans les définitions
        source_dict = definitions_list[0]
        self.assertEqual(source_dict["source_name"], "Test Source")

    def test_extract_from_dict(self):
        """Test de création d'un extrait à partir d'un dictionnaire."""
        extract_dict = {
            "extract_name": "New Extract",
            "start_marker": "START",
            "end_marker": "END",
            "template_start": "N{0}"
        }
        
        extract = Extract.from_dict(extract_dict)
        
        # Vérifier les propriétés de l'extrait
        self.assertEqual(extract.extract_name, "New Extract")
        self.assertEqual(extract.start_marker, "START")
        self.assertEqual(extract.end_marker, "END")
        self.assertEqual(extract.template_start, "N{0}")

    def test_source_definition_from_dict(self):
        """Test de création d'une définition de source à partir d'un dictionnaire."""
        source_dict = {
            "source_name": "New Source",
            "source_type": "file",
            "schema": "file",
            "host_parts": [],
            "path": "/path/to/file.txt",
            "extracts": [
                {
                    "extract_name": "New Extract",
                    "start_marker": "START",
                    "end_marker": "END"
                }
            ]
        }
        
        source = SourceDefinition.from_dict(source_dict)
        
        # Vérifier les propriétés de la source
        self.assertEqual(source.source_name, "New Source")
        self.assertEqual(source.source_type, "file")
        self.assertEqual(source.schema, "file")
        self.assertEqual(source.host_parts, [])
        self.assertEqual(source.path, "/path/to/file.txt")
        self.assertEqual(len(source.extracts), 1)
        
        # Vérifier l'extrait dans la source
        extract = source.extracts[0]
        self.assertEqual(extract.extract_name, "New Extract")
        self.assertEqual(extract.start_marker, "START")
        self.assertEqual(extract.end_marker, "END")

    def test_extract_definitions_from_dict_list(self):
        """Test de création des définitions d'extraits à partir d'une liste de dictionnaires."""
        definitions_list = [
            {
                "source_name": "New Source",
                "source_type": "url",
                "schema": "https",
                "host_parts": ["example", "com"],
                "path": "/new",
                "extracts": [
                    {
                        "extract_name": "New Extract",
                        "start_marker": "START",
                        "end_marker": "END"
                    }
                ]
            }
        ]
        
        definitions = ExtractDefinitions.from_dict_list(definitions_list)
        
        # Vérifier les propriétés des définitions
        self.assertEqual(len(definitions.sources), 1)
        
        # Vérifier la source dans les définitions
        source = definitions.sources[0]
        self.assertEqual(source.source_name, "New Source")
        self.assertEqual(source.source_type, "url")
        self.assertEqual(source.schema, "https")
        self.assertEqual(source.host_parts, ["example", "com"])
        self.assertEqual(source.path, "/new")
        
        # Vérifier l'extrait dans la source
        extract = source.extracts[0]
        self.assertEqual(extract.extract_name, "New Extract")
        self.assertEqual(extract.start_marker, "START")
        self.assertEqual(extract.end_marker, "END")

    def test_json_serialization(self):
        """Test de sérialisation/désérialisation JSON."""
        # Sérialiser en JSON
        json_str = json.dumps(self.extract_definitions.to_dict_list())
        
        # Désérialiser depuis JSON
        definitions_list = json.loads(json_str)
        definitions = ExtractDefinitions.from_dict_list(definitions_list)
        
        # Vérifier les propriétés des définitions
        self.assertEqual(len(definitions.sources), 1)
        
        # Vérifier la source dans les définitions
        source = definitions.sources[0]
        self.assertEqual(source.source_name, "Test Source")
        
        # Vérifier l'extrait dans la source
        extract = source.extracts[0]
        self.assertEqual(extract.extract_name, "Test Extract")
        self.assertEqual(extract.start_marker, "DEBUT_EXTRAIT")
        self.assertEqual(extract.end_marker, "FIN_EXTRAIT")


if __name__ == "__main__":
    unittest.main()


# Tests utilisant les fixtures pytest

@pytest.mark.parametrize("template_start,expected", [
    ("T{0}", "T{0}"),
    ("", ""),
    ("Prefix_{0}_Suffix", "Prefix_{0}_Suffix"),
])
def test_extract_template_start(sample_extract_dict, template_start, expected):
    """Test paramétré pour le champ template_start de l'extrait."""
    sample_extract_dict["template_start"] = template_start
    extract = Extract.from_dict(sample_extract_dict)
    assert extract.template_start == expected


def test_source_definition_add_extract(sample_source):
    """Test de la méthode add_extract."""
    new_extract = Extract(
        extract_name="New Extract",
        start_marker="START",
        end_marker="END"
    )
    
    initial_count = len(sample_source.extracts)
    sample_source.add_extract(new_extract)
    
    assert len(sample_source.extracts) == initial_count + 1
    assert sample_source.extracts[-1] == new_extract


def test_source_definition_get_extract_by_name(sample_source, sample_extract):
    """Test de la méthode get_extract_by_name."""
    # Test avec un nom existant
    extract = sample_source.get_extract_by_name("Test Extract")
    assert extract == sample_extract
    
    # Test avec un nom inexistant
    extract = sample_source.get_extract_by_name("Nonexistent Extract")
    assert extract is None


def test_source_definition_get_extract_by_index(sample_source, sample_extract):
    """Test de la méthode get_extract_by_index."""
    # Test avec un index valide
    extract = sample_source.get_extract_by_index(0)
    assert extract == sample_extract
    
    # Test avec un index invalide (négatif)
    extract = sample_source.get_extract_by_index(-1)
    assert extract is None
    
    # Test avec un index invalide (trop grand)
    extract = sample_source.get_extract_by_index(100)
    assert extract is None


def test_extract_definitions_add_source(sample_definitions):
    """Test de la méthode add_source."""
    new_source = SourceDefinition(
        source_name="New Source",
        source_type="file",
        schema="file",
        host_parts=[],
        path="/path/to/file.txt",
        extracts=[]
    )
    
    initial_count = len(sample_definitions.sources)
    sample_definitions.add_source(new_source)
    
    assert len(sample_definitions.sources) == initial_count + 1
    assert sample_definitions.sources[-1] == new_source


def test_extract_definitions_get_source_by_name(sample_definitions, sample_source):
    """Test de la méthode get_source_by_name."""
    # Test avec un nom existant
    source = sample_definitions.get_source_by_name("Test Source")
    assert source == sample_source
    
    # Test avec un nom inexistant
    source = sample_definitions.get_source_by_name("Nonexistent Source")
    assert source is None


def test_extract_definitions_get_source_by_index(sample_definitions, sample_source):
    """Test de la méthode get_source_by_index."""
    # Test avec un index valide
    source = sample_definitions.get_source_by_index(0)
    assert source == sample_source
    
    # Test avec un index invalide (négatif)
    source = sample_definitions.get_source_by_index(-1)
    assert source is None
    
    # Test avec un index invalide (trop grand)
    source = sample_definitions.get_source_by_index(100)
    assert source is None