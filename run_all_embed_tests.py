#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour exécuter tous les 10 tests embed_all_sources.py.
"""

import sys
import os
import subprocess
import tempfile
import traceback
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ajouter le répertoire racine au path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

def setup_environment():
    """Configure l'environnement de test."""
    try:
        from tests.mocks.extract_definitions_mock import setup_extract_definitions_mock
        from argumentation_analysis.ui import file_operations
        
        # Configurer le mock
        setup_result = setup_extract_definitions_mock()
        print(f"Configuration du mock: {'[OK] Reussi' if setup_result else '[ERREUR] Echec'}")
        
        return setup_result
    except Exception as e:
        print(f"[ERREUR] Configuration environnement: {e}")
        return False

def create_test_data():
    """Crée les données de test."""
    minimal_config_data_no_text = [
        {
            "source_name": "Minimal Source",
            "source_type": "direct_download",
            "schema": "http",
            "host_parts": ["testserver"],
            "path": "/file1.txt",
            "extracts": [{"extract_name": "e1", "start_marker": "START1", "end_marker": "END1"}],
        }
    ]
    
    minimal_config_data_with_text = [
        {
            "source_name": "Minimal Source With Text",
            "source_type": "direct_download",
            "schema": "http",
            "host_parts": ["testserver"],
            "path": "/file2.txt",
            "extracts": [],
            "full_text": "This text is already here."
        }
    ]
    
    source_error_data = [
        {
            "source_name": "Source Error",
            "source_type": "direct_download",
            "schema": "http",
            "host_parts": ["error"],
            "path": "/error.txt",
            "extracts": []
        }
    ]
    
    return minimal_config_data_no_text, minimal_config_data_with_text, source_error_data

def create_encrypted_file(tmp_path, filename, data, passphrase):
    """Crée un fichier chiffré avec les données spécifiées."""
    from argumentation_analysis.ui import file_operations
    
    input_file = tmp_path / filename
    should_embed = any("full_text" in item for item in data)
    
    file_operations.save_extract_definitions(
        data,
        input_file,
        passphrase,
        embed_full_text=should_embed,
        config={}
    )
    return input_file

def run_script_with_args(args_list, env_vars=None):
    """Exécute le script embed_all_sources.py avec les arguments donnés."""
    script_path = PROJECT_ROOT / "scripts" / "embed_all_sources.py"
    
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    
    cmd = [sys.executable, str(script_path)] + args_list
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
            check=False
        )
        return result
    except subprocess.TimeoutExpired:
        print("[ERREUR] Timeout lors de l'execution du script")
        return None
    except Exception as e:
        print(f"[ERREUR] Exception lors de l'execution: {e}")
        return None

def decrypt_and_load_json(file_path, passphrase):
    """Déchiffre et charge un fichier JSON."""
    from argumentation_analysis.ui import file_operations
    
    try:
        loaded_data = file_operations.load_extract_definitions(
            config_file=file_path,
            key=passphrase
        )
        return loaded_data
    except Exception as e:
        print(f"[ERREUR] Dechiffrement: {e}")
        return None

def test_1_success_no_text_initially(tmp_path, test_passphrase):
    """Test 1: Script réussit sans texte initial."""
    print("\n--- Test 1: Success no text initially ---")
    
    minimal_config_data_no_text, _, _ = create_test_data()
    
    with patch('argumentation_analysis.ui.utils.get_full_text_for_source') as mock_get_text, \
         patch('argumentation_analysis.ui.utils.load_from_cache', return_value=None), \
         patch('argumentation_analysis.ui.utils.save_to_cache', return_value=None), \
         patch('argumentation_analysis.ui.config.load_extract_sources') as mock_load_extract_sources:
        
        def side_effect_get_text(source_info, app_config=None):
            if source_info["source_name"] == "Minimal Source":
                return f"Fetched content for {source_info['path']}"
            return None
        
        mock_get_text.side_effect = side_effect_get_text
        
        mock_app_config_instance = MagicMock()
        config_values_for_get = {
            'JINA_READER_PREFIX': "mock_jina_prefix_via_get",
            'TIKA_SERVER_URL': "mock_tika_url_via_get",
            'PLAINTEXT_EXTENSIONS': ['.mocktxt'],
            'TEMP_DOWNLOAD_DIR': tmp_path / "mock_temp_dir_via_get"
        }
        
        def app_config_get_side_effect(key, default=None):
            return config_values_for_get.get(key, default)
        
        mock_app_config_instance.get.side_effect = app_config_get_side_effect
        mock_load_extract_sources.return_value = mock_app_config_instance
        
        input_file = create_encrypted_file(tmp_path, "input1.enc", minimal_config_data_no_text, test_passphrase)
        output_file = tmp_path / "output1.enc"
        
        args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase]
        result = run_script_with_args(args)
        
        if result is None:
            return False
        
        success = (result.returncode == 0 and 
                  output_file.exists() and
                  mock_get_text.called)
        
        if success:
            output_data = decrypt_and_load_json(output_file, test_passphrase)
            success = (output_data and len(output_data) == 1 and 
                      output_data[0]["source_name"] == "Minimal Source")
        
        print(f"Test 1: {'[OK] REUSSI' if success else '[ERREUR] ECHEC'}")
        return success

def test_2_text_already_present(tmp_path, test_passphrase):
    """Test 2: Texte déjà présent."""
    print("\n--- Test 2: Text already present ---")
    
    _, minimal_config_data_with_text, _ = create_test_data()
    
    with patch('argumentation_analysis.ui.utils.get_full_text_for_source') as mock_get_text, \
         patch('argumentation_analysis.ui.utils.load_from_cache', return_value=None), \
         patch('argumentation_analysis.ui.utils.save_to_cache', return_value=None), \
         patch('argumentation_analysis.ui.config.load_extract_sources') as mock_load_extract_sources:
        
        mock_app_config_instance = MagicMock()
        mock_load_extract_sources.return_value = mock_app_config_instance
        
        input_file = create_encrypted_file(tmp_path, "input2.enc", minimal_config_data_with_text, test_passphrase)
        output_file = tmp_path / "output2.enc"
        
        args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase]
        result = run_script_with_args(args)
        
        if result is None:
            return False
        
        success = (result.returncode == 0 and 
                  output_file.exists() and
                  not mock_get_text.called)
        
        if success:
            output_data = decrypt_and_load_json(output_file, test_passphrase)
            success = (output_data and len(output_data) == 1 and 
                      output_data[0]["full_text"] == "This text is already here.")
        
        print(f"Test 2: {'[OK] REUSSI' if success else '[ERREUR] ECHEC'}")
        return success

def test_3_force_overwrite(tmp_path, test_passphrase):
    """Test 3: Force overwrite."""
    print("\n--- Test 3: Force overwrite ---")
    
    minimal_config_data_no_text, _, _ = create_test_data()
    
    input_file = create_encrypted_file(tmp_path, "input3.enc", minimal_config_data_no_text, test_passphrase)
    output_file = tmp_path / "output3.enc"
    output_file.write_text("pre_existing_content")
    
    args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase, "--force"]
    result = run_script_with_args(args)
    
    if result is None:
        return False
    
    success = (result.returncode == 0 and 
              output_file.exists() and
              output_file.read_text() != "pre_existing_content")
    
    print(f"Test 3: {'[OK] REUSSI' if success else '[ERREUR] ECHEC'}")
    return success

def test_4_output_exists_no_force(tmp_path, test_passphrase):
    """Test 4: Output exists no force."""
    print("\n--- Test 4: Output exists no force ---")
    
    minimal_config_data_no_text, _, _ = create_test_data()
    
    input_file = create_encrypted_file(tmp_path, "input4.enc", minimal_config_data_no_text, test_passphrase)
    output_file = tmp_path / "output4.enc"
    output_file.write_text("pre_existing_content")
    
    args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase]
    result = run_script_with_args(args)
    
    if result is None:
        return False
    
    success = (result.returncode == 1 and
              output_file.read_text() == "pre_existing_content")
    
    print(f"Test 4: {'[OK] REUSSI' if success else '[ERREUR] ECHEC'}")
    return success

def test_5_passphrase_from_env(tmp_path, test_passphrase):
    """Test 5: Passphrase from environment."""
    print("\n--- Test 5: Passphrase from env ---")
    
    minimal_config_data_no_text, _, _ = create_test_data()
    
    input_file = create_encrypted_file(tmp_path, "input5.enc", minimal_config_data_no_text, test_passphrase)
    output_file = tmp_path / "output5.enc"
    
    env_vars = {"TEXT_CONFIG_PASSPHRASE": test_passphrase}
    args = ["--input-config", str(input_file), "--output-config", str(output_file)]
    result = run_script_with_args(args, env_vars=env_vars)
    
    if result is None:
        return False
    
    success = (result.returncode == 0 and output_file.exists())
    
    print(f"Test 5: {'[OK] REUSSI' if success else '[ERREUR] ECHEC'}")
    return success

def test_6_missing_passphrase(tmp_path, test_passphrase):
    """Test 6: Missing passphrase."""
    print("\n--- Test 6: Missing passphrase ---")
    
    minimal_config_data_no_text, _, _ = create_test_data()
    
    input_file = create_encrypted_file(tmp_path, "input6.enc", minimal_config_data_no_text, test_passphrase)
    output_file = tmp_path / "output6.enc"
    
    # S'assurer que la variable d'env n'est pas définie
    env_vars = os.environ.copy()
    if "TEXT_CONFIG_PASSPHRASE" in env_vars:
        del env_vars["TEXT_CONFIG_PASSPHRASE"]
    
    args = ["--input-config", str(input_file), "--output-config", str(output_file)]
    result = run_script_with_args(args, env_vars=env_vars)
    
    if result is None:
        return False
    
    success = result.returncode == 1
    
    print(f"Test 6: {'[OK] REUSSI' if success else '[ERREUR] ECHEC'}")
    return success

def test_7_input_file_not_found(tmp_path, test_passphrase):
    """Test 7: Input file not found."""
    print("\n--- Test 7: Input file not found ---")
    
    non_existent_input = tmp_path / "ghost.enc"
    output_file = tmp_path / "output7.enc"
    
    args = ["--input-config", str(non_existent_input), "--output-config", str(output_file), "--passphrase", test_passphrase]
    result = run_script_with_args(args)
    
    if result is None:
        return False
    
    success = result.returncode == 1
    
    print(f"Test 7: {'[OK] REUSSI' if success else '[ERREUR] ECHEC'}")
    return success

def test_8_incorrect_passphrase(tmp_path, test_passphrase):
    """Test 8: Incorrect passphrase."""
    print("\n--- Test 8: Incorrect passphrase ---")
    
    minimal_config_data_no_text, _, _ = create_test_data()
    
    input_file = create_encrypted_file(tmp_path, "input8.enc", minimal_config_data_no_text, test_passphrase)
    output_file = tmp_path / "output8.enc"
    wrong_passphrase = "thisiswrong"
    
    args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", wrong_passphrase]
    result = run_script_with_args(args)
    
    if result is None:
        return False
    
    success = result.returncode == 1
    
    print(f"Test 8: {'[OK] REUSSI' if success else '[ERREUR] ECHEC'}")
    return success

def test_9_source_fetch_error(tmp_path, test_passphrase):
    """Test 9: Source fetch error."""
    print("\n--- Test 9: Source fetch error ---")
    
    _, _, source_error_data = create_test_data()
    
    with patch('argumentation_analysis.ui.utils.get_full_text_for_source') as mock_get_text, \
         patch('argumentation_analysis.ui.utils.load_from_cache', return_value=None), \
         patch('argumentation_analysis.ui.utils.save_to_cache', return_value=None), \
         patch('argumentation_analysis.ui.config.load_extract_sources') as mock_load_extract_sources:
        
        def side_effect_get_text(source_info, app_config=None):
            if source_info["source_name"] == "Source Error":
                raise ConnectionError("Simulated network error")
            return None
        
        mock_get_text.side_effect = side_effect_get_text
        
        mock_app_config_instance = MagicMock()
        mock_load_extract_sources.return_value = mock_app_config_instance
        
        input_file = create_encrypted_file(tmp_path, "input9.enc", source_error_data, test_passphrase)
        output_file = tmp_path / "output9.enc"
        
        args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase]
        result = run_script_with_args(args)
        
        if result is None:
            return False
        
        success = (result.returncode == 0 and 
                  output_file.exists() and
                  mock_get_text.called)
        
        if success:
            output_data = decrypt_and_load_json(output_file, test_passphrase)
            success = (output_data and len(output_data) == 1 and 
                      "full_text" not in output_data[0])
        
        print(f"Test 9: {'[OK] REUSSI' if success else '[ERREUR] ECHEC'}")
        return success

def test_10_empty_input_config(tmp_path, test_passphrase):
    """Test 10: Empty input config."""
    print("\n--- Test 10: Empty input config ---")
    
    input_file = create_encrypted_file(tmp_path, "input10.enc", [], test_passphrase)
    output_file = tmp_path / "output10.enc"
    
    args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase]
    result = run_script_with_args(args)
    
    if result is None:
        return False
    
    success = (result.returncode == 0 and output_file.exists())
    
    if success:
        output_data = decrypt_and_load_json(output_file, test_passphrase)
        success = (output_data is not None and len(output_data) == 0)
    
    print(f"Test 10: {'[OK] REUSSI' if success else '[ERREUR] ECHEC'}")
    return success

def main():
    """Fonction principale."""
    print("=== Execution des 10 tests embed_all_sources ===")
    
    # Configuration de l'environnement
    if not setup_environment():
        print("[ERREUR] Impossible de configurer l'environnement")
        return False
    
    test_passphrase = "Propaganda"
    
    # Liste des tests à exécuter
    tests = [
        ("Test 1: Success no text initially", test_1_success_no_text_initially),
        ("Test 2: Text already present", test_2_text_already_present),
        ("Test 3: Force overwrite", test_3_force_overwrite),
        ("Test 4: Output exists no force", test_4_output_exists_no_force),
        ("Test 5: Passphrase from env", test_5_passphrase_from_env),
        ("Test 6: Missing passphrase", test_6_missing_passphrase),
        ("Test 7: Input file not found", test_7_input_file_not_found),
        ("Test 8: Incorrect passphrase", test_8_incorrect_passphrase),
        ("Test 9: Source fetch error", test_9_source_fetch_error),
        ("Test 10: Empty input config", test_10_empty_input_config),
    ]
    
    passed_tests = 0
    failed_tests = 0
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        for test_name, test_func in tests:
            try:
                print(f"\n=== {test_name} ===")
                success = test_func(tmp_path, test_passphrase)
                if success:
                    passed_tests += 1
                else:
                    failed_tests += 1
            except Exception as e:
                print(f"[ERREUR] Exception dans {test_name}: {e}")
                print(f"Traceback: {traceback.format_exc()}")
                failed_tests += 1
    
    print(f"\n=== RESULTATS FINAUX ===")
    print(f"Tests reussis: {passed_tests}/10")
    print(f"Tests echoues: {failed_tests}/10")
    
    if passed_tests == 10:
        print("[OK] TOUS LES TESTS ONT REUSSI - La logique de chiffrement est harmonisee")
    else:
        print(f"[ERREUR] {failed_tests} tests ont echoue - Corrections necessaires")
    
    return passed_tests == 10

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)