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
        
        encrypted_content = self.crypto_service.encrypt_data(json.dumps(self.sample_data).encode(), self.key)
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
        definitions = load_extract_definitions(definitions_path=str(self.definitions_file))
        self.assertIsNotNone(definitions)
        self.assertEqual(len(definitions.sources), 1)
        self.assertEqual(definitions.sources[0].source_name, "Test Source 1")

    def test_load_definitions_encrypted(self):
        definitions = load_extract_definitions(
            definitions_path=str(self.encrypted_definitions_file),
            key_path=str(self.key_file)
        )
        self.assertIsNotNone(definitions)
        self.assertEqual(len(definitions.sources), 1)
        self.assertEqual(definitions.sources[0].source_name, "Test Source 1")

    def test_load_definitions_no_file(self):
        if self.definitions_file.exists(): self.definitions_file.unlink() # S'assurer que le fichier n'existe pas
        definitions = load_extract_definitions(definitions_path=str(self.definitions_file))
        self.assertIsNone(definitions) # Devrait retourner None si le fichier n'existe pas

    def test_load_definitions_encrypted_no_key(self):
        if self.key_file.exists(): self.key_file.unlink() # Supprimer la clé
        definitions = load_extract_definitions(definitions_path=str(self.encrypted_definitions_file), key_path=str(self.key_file))
        self.assertIsNone(definitions) # Devrait retourner None si la clé est manquante pour un fichier chiffré

    def test_load_definitions_encrypted_wrong_key(self):
        # Générer une mauvaise clé
        wrong_key = self.crypto_service.generate_key()
        wrong_key_file = self.test_dir / "wrong_key.key"
        self.crypto_service.save_key(wrong_key, wrong_key_file)
        
        definitions = load_extract_definitions(
            definitions_path=str(self.encrypted_definitions_file),
            key_path=str(wrong_key_file)
        )
        self.assertIsNone(definitions) # Devrait retourner None avec une mauvaise clé
        if wrong_key_file.exists(): wrong_key_file.unlink()


    def test_save_definitions_unencrypted(self):
        new_definitions_file = self.test_dir / "new_extract_definitions.json"
        definitions_obj = ExtractDefinitions.model_validate(self.sample_data)
        
        save_extract_definitions(definitions_obj, definitions_path=str(new_definitions_file))
        self.assertTrue(new_definitions_file.exists())
        
        # Vérifier le contenu
        with open(new_definitions_file, 'r') as f:
            loaded_data = json.load(f)
        self.assertEqual(loaded_data["sources"][0]["source_name"], "Test Source 1")
        
        if new_definitions_file.exists(): new_definitions_file.unlink()

    def test_save_definitions_encrypted(self):
        new_encrypted_file = self.test_dir / "new_extract_definitions.json.enc"
        new_key_file = self.test_dir / "new_key.key"
        definitions_obj = ExtractDefinitions.model_validate(self.sample_data)
        
        # Générer une nouvelle clé pour la sauvegarde
        new_key = self.crypto_service.generate_key()
        self.crypto_service.save_key(new_key, new_key_file)

        save_extract_definitions(definitions_obj, definitions_path=str(new_encrypted_file), key_path=str(new_key_file))
        self.assertTrue(new_encrypted_file.exists())
        
        # Vérifier en déchiffrant
        with open(new_encrypted_file, 'rb') as f:
            encrypted_data_read = f.read()
        
        decrypted_data_str = self.crypto_service.decrypt_data(encrypted_data_read, new_key)
        self.assertIsNotNone(decrypted_data_str)
        if decrypted_data_str:
            loaded_data = json.loads(decrypted_data_str.decode())
            self.assertEqual(loaded_data["sources"][0]["source_name"], "Test Source 1")
        
        if new_encrypted_file.exists(): new_encrypted_file.unlink()
        if new_key_file.exists(): new_key_file.unlink()

    def test_load_default_if_path_none(self):
        # Ce test dépend de l'existence d'un fichier par défaut ou d'un comportement spécifique
        # si definitions_path est None. La fonction actuelle retourne None si le path n'existe pas.
        # Pour tester un "défaut", il faudrait mocker l'existence d'un fichier par défaut.
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = False # Simuler que le fichier par défaut n'existe pas
            definitions = load_extract_definitions(definitions_path=None) # Path est None
            self.assertIsNone(definitions) # S'attend à None si aucun fichier par défaut n'est trouvé

    def test_load_malformed_json(self):
        malformed_json_file = self.test_dir / "malformed.json"
        with open(malformed_json_file, 'w') as f:
            f.write("{'sources': [}") # JSON malformé
        
        definitions = load_extract_definitions(definitions_path=str(malformed_json_file))
        self.assertIsNone(definitions) # Devrait retourner None pour JSON malformé
        
        if malformed_json_file.exists(): malformed_json_file.unlink()

if __name__ == '__main__':
    unittest.main()