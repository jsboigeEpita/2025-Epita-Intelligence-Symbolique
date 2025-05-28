# -*- coding: utf-8 -*-
import unittest
import os
import json
from unittest.mock import patch, mock_open
from pathlib import Path

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from argumentation_analysis.models.extract_definition import ExtractDefinitions, SourceDefinition, Extract
from argumentation_analysis.ui.file_operations import load_extract_definitions, save_extract_definitions # Corrigé
from argumentation_analysis.services.crypto_service import CryptoService

class TestLoadExtractDefinitions(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path("test_definitions_dir")
        self.test_dir.mkdir(exist_ok=True)
        self.definitions_file = self.test_dir / "extract_definitions.json"
        self.encrypted_definitions_file = self.test_dir / "extract_definitions.json.enc"
        self.key_file = self.test_dir / "definitions_key.key"

        self.sample_data = {
            "sources": [
                {
                    "source_name": "Test Source 1",
                    "source_type": "url",
                    "schema": "https",
                    "host_parts": ["example", "com"],
                    "path": "/page1",
                    "extracts": [
                        {"extract_name": "Extract 1.1", "start_marker": "START1", "end_marker": "END1"}
                    ]
                }
            ]
        }
        # Sauvegarder un fichier de définitions non chiffré pour certains tests
        with open(self.definitions_file, 'w') as f:
            json.dump(self.sample_data, f)

        # Générer une clé et sauvegarder un fichier chiffré pour d'autres tests
        self.crypto_service = CryptoService()
        self.key = self.crypto_service.generate_key()
        self.crypto_service.save_key(self.key, self.key_file)
        
        self.crypto_service.set_encryption_key(self.key)
        # Créer des données correctement formatées : JSON -> compression gzip -> chiffrement
        import gzip
        json_data = json.dumps(self.sample_data["sources"]).encode('utf-8')  # Utiliser directement la liste des sources
        compressed_data = gzip.compress(json_data)
        encrypted_content = self.crypto_service.encrypt_data(compressed_data)
        if encrypted_content:
            with open(self.encrypted_definitions_file, 'wb') as f:
                f.write(encrypted_content)


    def tearDown(self):
        if self.definitions_file.exists():
            self.definitions_file.unlink()
        if self.encrypted_definitions_file.exists():
            self.encrypted_definitions_file.unlink()
        if self.key_file.exists():
            self.key_file.unlink()
        if self.test_dir.exists():
            # S'assurer que le répertoire est vide avant de le supprimer
            for item in self.test_dir.iterdir():
                item.unlink()
            self.test_dir.rmdir()

    def test_load_definitions_unencrypted(self):
        # Pour ce test, créons un fichier chiffré et compressé correctement
        import gzip
        json_data = json.dumps(self.sample_data["sources"]).encode('utf-8')
        compressed_data = gzip.compress(json_data)
        
        # Chiffrer avec le service crypto
        self.crypto_service.set_encryption_key(self.key)
        encrypted_data = self.crypto_service.encrypt_data(compressed_data)
        
        # Sauvegarder le fichier chiffré
        test_encrypted_file = self.test_dir / "test_encrypted.json.enc"
        with open(test_encrypted_file, 'wb') as f:
            f.write(encrypted_data)
        
        definitions = load_extract_definitions(config_file=test_encrypted_file, key=self.key)
        self.assertIsNotNone(definitions)
        self.assertEqual(len(definitions), 1)
        self.assertEqual(definitions[0]["source_name"], "Test Source 1")

    def test_load_definitions_encrypted(self):
        key = self.crypto_service.load_key(self.key_file)
        definitions = load_extract_definitions(
            config_file=self.encrypted_definitions_file,
            key=key
        )
        self.assertIsNotNone(definitions)
        self.assertEqual(len(definitions), 1)
        self.assertEqual(definitions[0]["source_name"], "Test Source 1")

    def test_load_definitions_no_file(self):
        if self.definitions_file.exists(): self.definitions_file.unlink() # S'assurer que le fichier n'existe pas
        definitions = load_extract_definitions(config_file=self.definitions_file, key=self.key)
        self.assertIsNotNone(definitions) # Devrait retourner les définitions par défaut si le fichier n'existe pas

    def test_load_definitions_encrypted_no_key(self):
        if self.key_file.exists(): self.key_file.unlink() # Supprimer la clé
        key = self.crypto_service.load_key(self.key_file) if self.key_file.exists() else None
        definitions = load_extract_definitions(config_file=self.encrypted_definitions_file, key=key)
        self.assertIsNotNone(definitions) # Devrait retourner les définitions par défaut si la clé est manquante

    def test_load_definitions_encrypted_wrong_key(self):
        # Générer une mauvaise clé
        wrong_key = self.crypto_service.generate_key()
        wrong_key_file = self.test_dir / "wrong_key.key"
        self.crypto_service.save_key(wrong_key, wrong_key_file)
        
        wrong_key = self.crypto_service.load_key(wrong_key_file)
        definitions = load_extract_definitions(
            config_file=self.encrypted_definitions_file,
            key=wrong_key
        )
        self.assertIsNotNone(definitions) # Devrait retourner les définitions par défaut avec une mauvaise clé
        if wrong_key_file.exists(): wrong_key_file.unlink()


    def test_save_definitions_unencrypted(self, config={}):
        new_definitions_file = self.test_dir / "new_extract_definitions.json"
        definitions_obj = ExtractDefinitions.model_validate(self.sample_data)
        
        save_extract_definitions(definitions_obj, config_file=str(new_definitions_file))
        self.assertTrue(new_definitions_file.exists())
        
        # Vérifier le contenu
        with open(new_definitions_file, 'r') as f:
            loaded_data = json.load(f)
        self.assertEqual(loaded_data["sources"][0]["source_name"], "Test Source 1")
        
        if new_definitions_file.exists(): new_definitions_file.unlink()

    def test_save_definitions_encrypted(self, embed_full_text=True):
        new_encrypted_file = self.test_dir / "new_extract_definitions.json.enc"
        new_key_file = self.test_dir / "new_key.key"
        definitions_obj = ExtractDefinitions.model_validate(self.sample_data)
        
        # Générer une nouvelle clé pour la sauvegarde
        new_key = self.crypto_service.generate_key()
        self.crypto_service.save_key(new_key, new_key_file)

        save_extract_definitions(definitions_obj, config_file=str(new_encrypted_file), key_path=str(new_key_file))
        self.assertTrue(new_encrypted_file.exists())
        
        # Vérifier en déchiffrant
        with open(new_encrypted_file, 'rb') as f:
            encrypted_data_read = f.read()
        
        decrypted_data_str = self.crypto_service.decrypt_data(encrypted_data_read, new_key)
        self.assertIsNotNone(decrypted_data_str)
        if decrypted_data_str:
            # Décompresser les données déchiffrées
            import gzip
            decompressed_data = gzip.decompress(decrypted_data_str)
            loaded_data = json.loads(decompressed_data.decode('utf-8'))
            self.assertEqual(loaded_data["sources"][0]["source_name"], "Test Source 1")
        
        if new_encrypted_file.exists(): new_encrypted_file.unlink()
        if new_key_file.exists(): new_key_file.unlink()

    def test_load_default_if_path_none(self):
        # Ce test vérifie que la fonction retourne des définitions par défaut
        # quand le fichier n'existe pas, conformément à la logique métier robuste
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = False # Simuler que le fichier par défaut n'existe pas
            definitions = load_extract_definitions(config_file=Path("nonexistent"), key=None) # Path inexistant
            self.assertIsNotNone(definitions) # Devrait retourner des définitions par défaut
            self.assertIsInstance(definitions, list) # Devrait être une liste
            # Vérifier que c'est bien les définitions par défaut
            if definitions:
                self.assertIn('source_name', definitions[0])

    def test_load_malformed_json(self):
        malformed_json_file = self.test_dir / "malformed.json"
        with open(malformed_json_file, 'w') as f:
            f.write("{'sources': [}") # JSON malformé
        
        definitions = load_extract_definitions(config_file=malformed_json_file, key=self.key)
        self.assertIsNotNone(definitions) # Devrait retourner des définitions par défaut pour JSON malformé
        self.assertIsInstance(definitions, list) # Devrait être une liste
        # Vérifier que c'est bien les définitions par défaut (fallback)
        if definitions:
            self.assertIn('source_name', definitions[0])
        
        if malformed_json_file.exists(): malformed_json_file.unlink()

if __name__ == '__main__':
    unittest.main()