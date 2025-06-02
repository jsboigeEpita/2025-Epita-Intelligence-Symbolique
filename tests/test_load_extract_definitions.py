# -*- coding: utf-8 -*-
import unittest
import pytest # Ajout de l'import pytest
import os
import json
import base64
from unittest.mock import patch, mock_open
from pathlib import Path
from cryptography.fernet import InvalidToken

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
        # self.key est la clé Fernet brute (bytes, déjà encodée en base64url)
        self.key = self.crypto_service.generate_key() 
        self.crypto_service.save_key(self.key, self.key_file)
        
        self.crypto_service.set_encryption_key(self.key)
        # Créer des données correctement formatées : JSON -> compression gzip -> chiffrement
        import gzip
        json_data = json.dumps(self.sample_data["sources"]).encode('utf-8')  # Utiliser directement la liste des sources
        compressed_data = gzip.compress(json_data)
        # CryptoService.encrypt_data attend la clé brute (bytes)
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
        
        # Nettoyer les fichiers créés dans le répertoire de test avant de le supprimer
        other_files = ["test_encrypted.json.enc", "wrong_key.key", "new_extract_definitions.json", "new_extract_definitions.json.enc", "new_key.key", "malformed.json"]
        for f_name in other_files:
            f_path = self.test_dir / f_name
            if f_path.exists():
                f_path.unlink()

        if self.test_dir.exists():
            # S'assurer que le répertoire est vide avant de le supprimer
            # Cela peut échouer sur Windows si un fichier est encore verrouillé, mais on essaie.
            try:
                for item in self.test_dir.iterdir(): # Devrait être vide maintenant
                    item.unlink() 
                self.test_dir.rmdir()
            except OSError as e:
                print(f"Warning: Could not completely remove test directory {self.test_dir}: {e}")


    def test_load_definitions_unencrypted(self):
        # Ce test est un peu redondant avec setUp, mais vérifie explicitement le chiffrement/déchiffrement
        import gzip
        json_data = json.dumps(self.sample_data["sources"]).encode('utf-8')
        compressed_data = gzip.compress(json_data)
        
        self.crypto_service.set_encryption_key(self.key) # Assure que crypto_service utilise self.key
        encrypted_data = self.crypto_service.encrypt_data(compressed_data) # Chiffre avec self.key (bytes bruts)
        
        test_encrypted_file = self.test_dir / "test_encrypted.json.enc"
        with open(test_encrypted_file, 'wb') as f:
            f.write(encrypted_data)
        
        # load_extract_definitions attend la version string de la clé Fernet (qui est déjà b64)
        definitions = load_extract_definitions(config_file=test_encrypted_file, b64_derived_key=self.key.decode('utf-8') if self.key else None)
        self.assertIsNotNone(definitions)
        self.assertEqual(len(definitions), 1)
        self.assertEqual(definitions[0]["source_name"], "Test Source 1")

    def test_load_definitions_encrypted(self):
        key_bytes = self.crypto_service.load_key(self.key_file) # key_bytes sont les bytes bruts de la clé Fernet
        self.assertIsNotNone(key_bytes)
        definitions = load_extract_definitions(
            config_file=self.encrypted_definitions_file,
            b64_derived_key=key_bytes.decode('utf-8') if key_bytes else None
        )
        self.assertIsNotNone(definitions)
        self.assertEqual(len(definitions), 1)
        self.assertEqual(definitions[0]["source_name"], "Test Source 1")

    def test_load_definitions_no_file(self):
        if self.definitions_file.exists(): self.definitions_file.unlink() 
        key_bytes = self.key 
        definitions = load_extract_definitions(config_file=self.definitions_file, b64_derived_key=key_bytes.decode('utf-8') if key_bytes else None)
        self.assertIsNotNone(definitions) 

    def test_load_definitions_encrypted_no_key(self):
        if self.key_file.exists(): self.key_file.unlink() 
        key_bytes = self.crypto_service.load_key(self.key_file) if self.key_file.exists() else None
        b64_derived_key_str = key_bytes.decode('utf-8') if key_bytes else None
        definitions = load_extract_definitions(config_file=self.encrypted_definitions_file, b64_derived_key=b64_derived_key_str)
        self.assertIsNotNone(definitions) 

    def test_load_definitions_encrypted_wrong_key(self):
        wrong_key_bytes = self.crypto_service.generate_key() # Clé Fernet brute (bytes)
        wrong_key_file = self.test_dir / "wrong_key.key"
        self.crypto_service.save_key(wrong_key_bytes, wrong_key_file)
        
        loaded_wrong_key_bytes = self.crypto_service.load_key(wrong_key_file)
        
        # load_extract_definitions attrape InvalidToken et retourne les définitions par défaut
        # si le déchiffrement échoue à cause d'une mauvaise clé.
        # crypto_utils.decrypt_data_with_fernet retourne None en cas d'InvalidToken.
        # file_operations.load_extract_definitions retourne alors les définitions par défaut.
        definitions = load_extract_definitions(
            config_file=self.encrypted_definitions_file,
            b64_derived_key=loaded_wrong_key_bytes.decode('utf-8') if loaded_wrong_key_bytes else None
        )
        self.assertIsNotNone(definitions)
        # Vérifier que ce sont les définitions par défaut (ou une structure attendue en cas d'échec)
        # Par exemple, si le fallback est une liste vide ou une liste avec un item spécifique:
        from argumentation_analysis.ui import config as ui_config_module
        fallback_definitions = ui_config_module.EXTRACT_SOURCES if ui_config_module.EXTRACT_SOURCES else ui_config_module.DEFAULT_EXTRACT_SOURCES
        self.assertEqual(definitions, [item.copy() for item in fallback_definitions])

        if wrong_key_file.exists(): wrong_key_file.unlink()


    @unittest.skip("La fonction save_extract_definitions chiffre toujours ; ce test pour la sauvegarde non chiffrée est obsolète.")
    def test_save_definitions_unencrypted(self, config={}):
        new_definitions_file = self.test_dir / "new_extract_definitions.json"
        definitions_obj = ExtractDefinitions.model_validate(self.sample_data)
        
        key_bytes = self.key
        save_extract_definitions(definitions_obj.to_dict_list(), config_file=new_definitions_file, b64_derived_key=key_bytes.decode('utf-8') if key_bytes else None)
        self.assertTrue(new_definitions_file.exists())
        
        with open(new_definitions_file, 'r') as f:
            loaded_data = json.load(f)
        self.assertEqual(loaded_data["sources"][0]["source_name"], "Test Source 1")
        
        if new_definitions_file.exists(): new_definitions_file.unlink()

    def test_save_definitions_encrypted(self, embed_full_text=True):
        new_encrypted_file = self.test_dir / "new_extract_definitions.json.enc"
        new_key_file = self.test_dir / "new_key.key"
        definitions_obj = ExtractDefinitions.model_validate(self.sample_data)
        
        new_key_bytes = self.crypto_service.generate_key() # Clé Fernet brute (bytes)
        self.crypto_service.save_key(new_key_bytes, new_key_file)

        save_extract_definitions(definitions_obj.to_dict_list(), config_file=new_encrypted_file, b64_derived_key=new_key_bytes.decode('utf-8') if new_key_bytes else None)
        self.assertTrue(new_encrypted_file.exists())
        
        with open(new_encrypted_file, 'rb') as f:
            encrypted_data_read = f.read()
        
        # CryptoService.decrypt_data attend la clé brute (bytes)
        decrypted_compressed_bytes = self.crypto_service.decrypt_data(encrypted_data_read, new_key_bytes)
        self.assertIsNotNone(decrypted_compressed_bytes)
        if decrypted_compressed_bytes:
            import gzip
            decompressed_data = gzip.decompress(decrypted_compressed_bytes)
            loaded_data = json.loads(decompressed_data.decode('utf-8'))
            self.assertEqual(loaded_data[0]["source_name"], "Test Source 1")
        
        if new_encrypted_file.exists(): new_encrypted_file.unlink()
        if new_key_file.exists(): new_key_file.unlink()

    def test_load_default_if_path_none(self):
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = False 
            definitions = load_extract_definitions(config_file=Path("nonexistent"), b64_derived_key=None) 
            self.assertIsNotNone(definitions) 
            self.assertIsInstance(definitions, list) 
            if definitions:
                self.assertIn('source_name', definitions[0])

    def test_load_malformed_json(self):
        malformed_json_file = self.test_dir / "malformed.json"
        # Écrire des données qui ne sont PAS chiffrées mais qui sont du JSON malformé
        # Pour que ce test soit pertinent, il faut que le déchiffrement réussisse (ou soit bypassé)
        # et que l'erreur vienne du json.loads.
        # Actuellement, si on passe des données non chiffrées à decrypt_data_with_fernet,
        # cela lèvera InvalidToken (ou une autre erreur crypto), et load_extract_definitions
        # retournera les définitions par défaut sans jamais essayer de parser le JSON.
        # Pour tester json.JSONDecodeError, il faudrait mocker decrypt_data_with_fernet
        # pour qu'il retourne des données décompressées mais malformées.
        
        # Ce test, dans sa forme actuelle, va probablement échouer car InvalidToken sera levée avant JSONDecodeError.
        # Il est conservé pour illustrer le comportement actuel.
        with open(malformed_json_file, 'wb') as f: # wb pour simuler des données "chiffrées"
            f.write(b"{'sources': [}") # JSON malformé en bytes

        key_bytes = self.key
        definitions = load_extract_definitions(config_file=malformed_json_file, b64_derived_key=key_bytes.decode('utf-8') if key_bytes else None)
        
        # Comme decrypt_data_with_fernet va échouer (InvalidToken), on s'attend aux définitions par défaut.
        from argumentation_analysis.ui import config as ui_config_module
        fallback_definitions = ui_config_module.EXTRACT_SOURCES if ui_config_module.EXTRACT_SOURCES else ui_config_module.DEFAULT_EXTRACT_SOURCES
        self.assertEqual(definitions, [item.copy() for item in fallback_definitions])
        
        if malformed_json_file.exists(): malformed_json_file.unlink()

if __name__ == '__main__': 
    unittest.main()