#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests unitaires pour les utilitaires de gestion de fichiers.
"""

import unittest
import json
from pathlib import Path
import tempfile # Pour créer des fichiers temporaires
import shutil # Pour supprimer le répertoire temporaire

from project_core.utils.file_utils import load_json_data

class TestFileUtils(unittest.TestCase):
    """Classe de test pour les fonctions de file_utils."""

    def setUp(self):
        """Crée un répertoire temporaire pour les fichiers de test."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_file_utils_"))

    def tearDown(self):
        """Supprime le répertoire temporaire après les tests."""
        shutil.rmtree(self.test_dir)

    def _create_test_json_file(self, filename: str, content: Any):
        """Helper pour créer un fichier JSON dans le répertoire de test."""
        file_path = self.test_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2)
        return file_path

    def test_load_json_data_valid_list(self):
        """Teste le chargement d'une liste JSON valide."""
        data = [{"id": 1, "name": "Test 1"}, {"id": 2, "name": "Test 2"}]
        file_path = self._create_test_json_file("valid_list.json", data)
        loaded_data = load_json_data(file_path)
        self.assertEqual(loaded_data, data)

    def test_load_json_data_valid_object(self):
        """
        Teste le chargement d'un objet JSON valide.
        La fonction load_json_data actuelle s'attend à une liste,
        mais elle retourne les données telles quelles. L'appelant doit vérifier le type.
        """
        data = {"id": 1, "name": "Test Object"}
        file_path = self._create_test_json_file("valid_object.json", data)
        loaded_data = load_json_data(file_path)
        self.assertEqual(loaded_data, data) # La fonction retourne l'objet, pas une liste d'objet

    def test_load_json_data_empty_list(self):
        """Teste le chargement d'une liste JSON vide."""
        data = []
        file_path = self._create_test_json_file("empty_list.json", data)
        loaded_data = load_json_data(file_path)
        self.assertEqual(loaded_data, data)

    def test_load_json_data_empty_file(self):
        """Teste le chargement d'un fichier JSON vide (contenu invalide)."""
        file_path = self.test_dir / "empty_file.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("") # Fichier vide
        loaded_data = load_json_data(file_path)
        self.assertIsNone(loaded_data) # Devrait retourner None car JSONDecodeError

    def test_load_json_data_null_content(self):
        """Teste le chargement d'un fichier JSON contenant 'null'."""
        file_path = self.test_dir / "null_content.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("null")
        loaded_data = load_json_data(file_path)
        # La fonction load_json_data a été modifiée pour retourner [] pour 'null'
        self.assertEqual(loaded_data, [])


    def test_load_json_data_invalid_json(self):
        """Teste le chargement d'un fichier avec du JSON invalide."""
        file_path = self.test_dir / "invalid.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("{'id': 1, 'name': 'Test'") # JSON invalide (manque } et guillemets simples)
        loaded_data = load_json_data(file_path)
        self.assertIsNone(loaded_data)

    def test_load_json_data_file_not_found(self):
        """Teste le chargement d'un fichier non existant."""
        file_path = self.test_dir / "non_existent.json"
        loaded_data = load_json_data(file_path)
        self.assertIsNone(loaded_data)

    def test_load_json_data_path_is_directory(self):
        """Teste le chargement lorsque le chemin est un répertoire."""
        # Le répertoire test_dir existe déjà
        loaded_data = load_json_data(self.test_dir)
        self.assertIsNone(loaded_data)

if __name__ == '__main__':
    unittest.main()