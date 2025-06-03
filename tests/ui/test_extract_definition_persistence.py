# -*- coding: utf-8 -*-
import pytest
import json
from pathlib import Path
from cryptography.fernet import InvalidToken
import gzip

from argumentation_analysis.models.extract_definition import ExtractDefinitions, SourceDefinition, Extract
from argumentation_analysis.ui.file_operations import load_extract_definitions, save_extract_definitions
from argumentation_analysis.services.crypto_service import CryptoService

@pytest.fixture
def sample_extract_data():
    return {
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

@pytest.fixture
def crypto_service_instance(): # Renommé pour éviter conflit avec le module crypto_service
    return CryptoService()

@pytest.fixture
def test_env(tmp_path, crypto_service_instance, sample_extract_data):
    test_dir = tmp_path / "test_definitions_dir"
    test_dir.mkdir()
    definitions_file = test_dir / "extract_definitions.json"
    encrypted_definitions_file = test_dir / "extract_definitions.json.enc"
    key_file = test_dir / "definitions_key.key"

    # Sauvegarder un fichier de définitions non chiffré pour certains tests
    with open(definitions_file, 'w') as f:
        json.dump(sample_extract_data, f)

    # Générer une clé et sauvegarder un fichier chiffré pour d'autres tests
    key = crypto_service_instance.generate_key() # key is bytes
    crypto_service_instance.save_key(key, key_file)
    
    crypto_service_instance.set_encryption_key(key)
    # Créer des données correctement formatées : JSON -> compression gzip -> chiffrement
    json_data = json.dumps(sample_extract_data["sources"]).encode('utf-8')
    compressed_data = gzip.compress(json_data)
    encrypted_content = crypto_service_instance.encrypt_data(compressed_data) # Uses key (bytes)
    if encrypted_content:
        with open(encrypted_definitions_file, 'wb') as f:
            f.write(encrypted_content)
            
    return {
        "test_dir": test_dir,
        "definitions_file": definitions_file,
        "encrypted_definitions_file": encrypted_definitions_file,
        "key_file": key_file,
        "key": key, # This is a raw Fernet key (bytes)
        "crypto_service": crypto_service_instance, 
        "sample_data": sample_extract_data
    }

def test_load_encrypted_definitions_from_fixture(test_env):
    # Ce test utilise le fichier chiffré (extract_definitions.json.enc)
    # et la clé préparés par la fixture test_env.
    # load_extract_definitions expects b64_derived_key as str
    # test_env['key'] is raw bytes.
    # The functions in file_operations now use crypto_utils functions that handle raw bytes or b64 str.
    definitions = load_extract_definitions(
        config_file=test_env['encrypted_definitions_file'], 
        b64_derived_key=test_env['key'].decode('utf-8') # Pass raw Fernet key as str
    )
    assert definitions is not None
    assert len(definitions) == 1
    assert definitions[0]["source_name"] == "Test Source 1"

def test_load_definitions_encrypted(test_env):
    key = test_env['crypto_service'].load_key(test_env['key_file']) # key is bytes
    definitions = load_extract_definitions(
        config_file=test_env['encrypted_definitions_file'],
        b64_derived_key=key.decode('utf-8') if isinstance(key, bytes) else key
    )
    assert definitions is not None
    assert len(definitions) == 1
    assert definitions[0]["source_name"] == "Test Source 1"

def test_load_definitions_no_file(test_env):
    non_existent_file = test_env['test_dir'] / "non_existent.json"
    if non_existent_file.exists(): non_existent_file.unlink()
    
    definitions = load_extract_definitions(config_file=non_existent_file, b64_derived_key=test_env['key'].decode('utf-8'))
    assert definitions is not None

def test_load_definitions_encrypted_no_key(test_env):
    # Le fichier est chiffré. Si on tente de le lire sans clé,
    # file_operations.py essaiera de le parser comme JSON, ce qui échouera.
    with pytest.raises(json.JSONDecodeError):
        load_extract_definitions(config_file=test_env['encrypted_definitions_file'], b64_derived_key=None)

def test_load_definitions_encrypted_wrong_key(test_env):
    wrong_key = test_env['crypto_service'].generate_key() # bytes
    
    with pytest.raises(InvalidToken):
        load_extract_definitions(
            config_file=test_env['encrypted_definitions_file'],
            b64_derived_key=wrong_key.decode('utf-8')
        )

@pytest.mark.skip("La fonction save_extract_definitions chiffre toujours ; ce test pour la sauvegarde non chiffrée est obsolète.")
def test_save_definitions_unencrypted(test_env):
    new_definitions_file = test_env['test_dir'] / "new_extract_definitions.json"
    definitions_obj = ExtractDefinitions.model_validate(test_env['sample_data'])
    
    save_extract_definitions(definitions_obj.to_dict_list(), config_file=new_definitions_file, b64_derived_key=test_env['key'].decode('utf-8'))
    assert new_definitions_file.exists()
    
    with open(new_definitions_file, 'r') as f:
        pass 
    # assert loaded_data["sources"][0]["source_name"] == "Test Source 1"

def test_save_definitions_encrypted(test_env):
    new_encrypted_file = test_env['test_dir'] / "new_extract_definitions.json.enc"
    definitions_obj = ExtractDefinitions.model_validate(test_env['sample_data'])
    
    new_key = test_env['crypto_service'].generate_key() # bytes

    save_extract_definitions(definitions_obj.to_dict_list(), config_file=new_encrypted_file, b64_derived_key=new_key.decode('utf-8'))
    assert new_encrypted_file.exists()
    
    with open(new_encrypted_file, 'rb') as f:
        encrypted_data_read = f.read()
    
    # CryptoService.decrypt_data expects bytes key
    decrypted_data_bytes = test_env['crypto_service'].decrypt_data(encrypted_data_read, new_key)
    assert decrypted_data_bytes is not None
    
    decompressed_data = gzip.decompress(decrypted_data_bytes)
    loaded_data = json.loads(decompressed_data.decode('utf-8'))
    assert loaded_data[0]["source_name"] == "Test Source 1"

def test_load_default_if_path_none(test_env):
    non_existent_default_path = test_env['test_dir'] / "non_existent_default.json"
    definitions = load_extract_definitions(config_file=non_existent_default_path, b64_derived_key=None)
    assert definitions is not None 
    assert isinstance(definitions, list) 
    if not definitions: 
        pass
    elif definitions: 
        assert 'source_name' in definitions[0]

def test_load_malformed_json(test_env):
    malformed_json_file = test_env['test_dir'] / "malformed.json"
    
    with open(malformed_json_file, 'w') as f:
        f.write("{'sources': [}") 

    with pytest.raises(json.JSONDecodeError):
         load_extract_definitions(config_file=malformed_json_file, b64_derived_key=None)

    malformed_encrypted_file = test_env['test_dir'] / "malformed_encrypted.json.enc"
    with open(malformed_encrypted_file, 'wb') as f:
        f.write(b"this is not encrypted data")

    with pytest.raises(InvalidToken):
        load_extract_definitions(config_file=malformed_encrypted_file, b64_derived_key=test_env['key'].decode('utf-8'))