#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour exécuter les tests embed_all_sources sans pytest.
"""

import sys
import os
from pathlib import Path
import traceback

# Ajouter le répertoire racine au path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent # MODIFIÉ: Remonter à la racine du projet
sys.path.insert(0, str(PROJECT_ROOT))

def run_tests():
    """Exécute les tests embed_all_sources."""
    print("=== Exécution des tests embed_all_sources ===")
    
    try:
        # Importer le module de test
        from tests.scripts.test_embed_all_sources import *
        
        # Créer un répertoire temporaire pour les tests
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # Créer les fixtures nécessaires
            test_passphrase_val = "Propaganda"  # Passphrase de test
            
            # Configuration des données de test
            minimal_config_data_no_text_val = [
                {
                    "source_name": "Minimal Source",
                    "source_type": "direct_download",
                    "schema": "http",
                    "host_parts": ["testserver"],
                    "path": "/file1.txt",
                    "extracts": [{"extract_name": "e1", "start_marker": "START1", "end_marker": "END1"}],
                }
            ]
            
            minimal_config_data_with_text_val = [
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
            
            # Fonction pour créer des fichiers chiffrés
            def create_encrypted_config_file_func(filename: str, data: list, passphrase_override=None):
                from argumentation_analysis.ui import file_operations
                input_file = tmp_path / filename
                should_embed = any("full_text" in item for item in data)
                
                file_operations.save_extract_definitions(
                    data,
                    input_file,
                    passphrase_override or test_passphrase_val,
                    embed_full_text=should_embed,
                    config={}
                )
                return input_file
            
            # Liste des tests à exécuter
            tests_to_run = [
                ("test_embed_script_success_no_text_initially", test_embed_script_success_no_text_initially),
                ("test_embed_script_text_already_present", test_embed_script_text_already_present),
                ("test_embed_script_force_overwrite", test_embed_script_force_overwrite),
                ("test_embed_script_output_exists_no_force", test_embed_script_output_exists_no_force),
                ("test_embed_script_passphrase_from_env", test_embed_script_passphrase_from_env),
                ("test_embed_script_missing_passphrase", test_embed_script_missing_passphrase),
                ("test_embed_script_input_file_not_found", test_embed_script_input_file_not_found),
                ("test_embed_script_incorrect_passphrase", test_embed_script_incorrect_passphrase),
                ("test_embed_script_source_fetch_error", test_embed_script_source_fetch_error),
                ("test_embed_script_empty_input_config", test_embed_script_empty_input_config),
            ]
            
            passed_tests = 0
            failed_tests = 0
            
            for test_name, test_func in tests_to_run:
                print(f"\n--- Exécution de {test_name} ---")
                try:
                    # Préparer les arguments selon le test
                    if test_name == "test_embed_script_success_no_text_initially":
                        # Mock les appels réseau
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
                            
                            test_func(tmp_path, create_encrypted_config_file_func, minimal_config_data_no_text_val, test_passphrase_val, (mock_get_text, mock_load_extract_sources))
                    
                    elif test_name == "test_embed_script_text_already_present":
                        with patch('argumentation_analysis.ui.utils.get_full_text_for_source') as mock_get_text, \
                             patch('argumentation_analysis.ui.utils.load_from_cache', return_value=None), \
                             patch('argumentation_analysis.ui.utils.save_to_cache', return_value=None), \
                             patch('argumentation_analysis.ui.config.load_extract_sources') as mock_load_extract_sources:
                            
                            mock_app_config_instance = MagicMock()
                            mock_load_extract_sources.return_value = mock_app_config_instance
                            
                            test_func(tmp_path, create_encrypted_config_file_func, minimal_config_data_with_text_val, test_passphrase_val, (mock_get_text, mock_load_extract_sources))
                    
                    elif test_name == "test_embed_script_force_overwrite":
                        test_func(tmp_path, create_encrypted_config_file_func, minimal_config_data_no_text_val, test_passphrase_val)
                    
                    elif test_name == "test_embed_script_output_exists_no_force":
                        test_func(tmp_path, create_encrypted_config_file_func, minimal_config_data_no_text_val, test_passphrase_val)
                    
                    elif test_name == "test_embed_script_passphrase_from_env":
                        test_func(tmp_path, create_encrypted_config_file_func, minimal_config_data_no_text_val, test_passphrase_val)
                    
                    elif test_name == "test_embed_script_missing_passphrase":
                        test_func(tmp_path, create_encrypted_config_file_func, minimal_config_data_no_text_val)
                    
                    elif test_name == "test_embed_script_input_file_not_found":
                        test_func(tmp_path, test_passphrase_val)
                    
                    elif test_name == "test_embed_script_incorrect_passphrase":
                        test_func(tmp_path, create_encrypted_config_file_func, minimal_config_data_no_text_val, test_passphrase_val)
                    
                    elif test_name == "test_embed_script_source_fetch_error":
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
                            
                            test_func(tmp_path, create_encrypted_config_file_func, test_passphrase_val, (mock_get_text, mock_load_extract_sources))
                    
                    elif test_name == "test_embed_script_empty_input_config":
                        test_func(tmp_path, create_encrypted_config_file_func, test_passphrase_val)
                    
                    print(f"✅ {test_name} - RÉUSSI")
                    passed_tests += 1
                    
                except Exception as e:
                    print(f"❌ {test_name} - ÉCHEC")
                    print(f"Erreur: {e}")
                    print(f"Traceback: {traceback.format_exc()}")
                    failed_tests += 1
            
            print(f"\n=== RÉSULTATS ===")
            print(f"Tests réussis: {passed_tests}")
            print(f"Tests échoués: {failed_tests}")
            print(f"Total: {passed_tests + failed_tests}")
            
            return failed_tests == 0
            
    except Exception as e:
        print(f"Erreur lors de l'exécution des tests: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)