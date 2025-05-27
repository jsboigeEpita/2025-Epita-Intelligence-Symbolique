#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de validation des tests embed_all_sources - Version simplifiée et robuste.
"""

import sys
import os
import subprocess
import tempfile
import traceback
from pathlib import Path

# Ajouter le répertoire racine au path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

def setup_environment():
    """Configure l'environnement de test."""
    try:
        from tests.mocks.extract_definitions_mock import setup_extract_definitions_mock
        setup_result = setup_extract_definitions_mock()
        print(f"Configuration du mock: {'[OK] Reussi' if setup_result else '[ERREUR] Echec'}")
        return setup_result
    except Exception as e:
        print(f"[ERREUR] Configuration environnement: {e}")
        return False

def create_test_file(tmp_path, filename, data, passphrase):
    """Crée un fichier de test chiffré."""
    try:
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
    except Exception as e:
        print(f"[ERREUR] Creation fichier {filename}: {e}")
        return None

def run_embed_script(args_list, env_vars=None):
    """Exécute le script embed_all_sources.py."""
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
    except Exception as e:
        print(f"[ERREUR] Execution script: {e}")
        return None

def load_encrypted_file(file_path, passphrase):
    """Charge un fichier chiffré."""
    try:
        from argumentation_analysis.ui import file_operations
        
        loaded_data = file_operations.load_extract_definitions(
            config_file=file_path,
            key=passphrase
        )
        return loaded_data
    except Exception as e:
        print(f"[ERREUR] Chargement fichier: {e}")
        return None

def test_basic_functionality():
    """Test de base : script fonctionne avec données valides."""
    print("\n=== Test 1: Fonctionnalite de base ===")
    
    test_passphrase = "Propaganda"
    test_data = [
        {
            "source_name": "Test Source",
            "source_type": "direct_download",
            "schema": "http",
            "host_parts": ["testserver"],
            "path": "/test.txt",
            "extracts": []
        }
    ]
    
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # Créer fichier d'entrée
            input_file = create_test_file(tmp_path, "input.enc", test_data, test_passphrase)
            if not input_file:
                return False
            
            output_file = tmp_path / "output.enc"
            
            # Exécuter le script
            args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase]
            result = run_embed_script(args)
            
            if not result:
                return False
            
            success = (result.returncode == 0 and output_file.exists())
            
            if success:
                # Vérifier que le fichier de sortie peut être lu
                output_data = load_encrypted_file(output_file, test_passphrase)
                success = output_data is not None
            
            print(f"Test 1: {'[OK] REUSSI' if success else '[ERREUR] ECHEC'}")
            if not success and result:
                print(f"Code retour: {result.returncode}")
                if result.stderr:
                    print(f"Erreurs: {result.stderr[:500]}")
            
            return success
            
    except Exception as e:
        print(f"[ERREUR] Test 1: {e}")
        return False

def test_force_overwrite():
    """Test : option --force fonctionne."""
    print("\n=== Test 2: Force overwrite ===")
    
    test_passphrase = "Propaganda"
    test_data = [
        {
            "source_name": "Test Source",
            "source_type": "direct_download",
            "schema": "http",
            "host_parts": ["testserver"],
            "path": "/test.txt",
            "extracts": []
        }
    ]
    
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            input_file = create_test_file(tmp_path, "input.enc", test_data, test_passphrase)
            if not input_file:
                return False
            
            output_file = tmp_path / "output.enc"
            output_file.write_text("existing_content")
            
            # Exécuter avec --force
            args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase, "--force"]
            result = run_embed_script(args)
            
            if not result:
                return False
            
            success = (result.returncode == 0 and 
                      output_file.exists() and 
                      output_file.read_text() != "existing_content")
            
            print(f"Test 2: {'[OK] REUSSI' if success else '[ERREUR] ECHEC'}")
            return success
            
    except Exception as e:
        print(f"[ERREUR] Test 2: {e}")
        return False

def test_no_force_existing_file():
    """Test : sans --force, fichier existant provoque erreur."""
    print("\n=== Test 3: No force existing file ===")
    
    test_passphrase = "Propaganda"
    test_data = [
        {
            "source_name": "Test Source",
            "source_type": "direct_download",
            "schema": "http",
            "host_parts": ["testserver"],
            "path": "/test.txt",
            "extracts": []
        }
    ]
    
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            input_file = create_test_file(tmp_path, "input.enc", test_data, test_passphrase)
            if not input_file:
                return False
            
            output_file = tmp_path / "output.enc"
            output_file.write_text("existing_content")
            
            # Exécuter sans --force
            args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase]
            result = run_embed_script(args)
            
            if not result:
                return False
            
            success = (result.returncode == 1 and 
                      output_file.read_text() == "existing_content")
            
            print(f"Test 3: {'[OK] REUSSI' if success else '[ERREUR] ECHEC'}")
            return success
            
    except Exception as e:
        print(f"[ERREUR] Test 3: {e}")
        return False

def test_missing_input_file():
    """Test : fichier d'entrée manquant provoque erreur."""
    print("\n=== Test 4: Missing input file ===")
    
    test_passphrase = "Propaganda"
    
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            non_existent_input = tmp_path / "ghost.enc"
            output_file = tmp_path / "output.enc"
            
            args = ["--input-config", str(non_existent_input), "--output-config", str(output_file), "--passphrase", test_passphrase]
            result = run_embed_script(args)
            
            if not result:
                return False
            
            success = result.returncode == 1
            
            print(f"Test 4: {'[OK] REUSSI' if success else '[ERREUR] ECHEC'}")
            return success
            
    except Exception as e:
        print(f"[ERREUR] Test 4: {e}")
        return False

def test_missing_passphrase():
    """Test : passphrase manquante provoque erreur."""
    print("\n=== Test 5: Missing passphrase ===")
    
    test_passphrase = "Propaganda"
    test_data = [
        {
            "source_name": "Test Source",
            "source_type": "direct_download",
            "schema": "http",
            "host_parts": ["testserver"],
            "path": "/test.txt",
            "extracts": []
        }
    ]
    
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            input_file = create_test_file(tmp_path, "input.enc", test_data, test_passphrase)
            if not input_file:
                return False
            
            output_file = tmp_path / "output.enc"
            
            # S'assurer que la variable d'env n'est pas définie
            env_vars = os.environ.copy()
            if "TEXT_CONFIG_PASSPHRASE" in env_vars:
                del env_vars["TEXT_CONFIG_PASSPHRASE"]
            
            args = ["--input-config", str(input_file), "--output-config", str(output_file)]
            result = run_embed_script(args, env_vars=env_vars)
            
            if not result:
                return False
            
            success = result.returncode == 1
            
            print(f"Test 5: {'[OK] REUSSI' if success else '[ERREUR] ECHEC'}")
            return success
            
    except Exception as e:
        print(f"[ERREUR] Test 5: {e}")
        return False

def test_encryption_compatibility():
    """Test : compatibilité du chiffrement entre mock et script."""
    print("\n=== Test 6: Compatibilite chiffrement ===")
    
    test_passphrase = "Propaganda"
    test_data = [
        {
            "source_name": "Compatibility Test",
            "source_type": "direct_download",
            "schema": "http",
            "host_parts": ["testserver"],
            "path": "/compat.txt",
            "extracts": [],
            "full_text": "Test compatibility content"
        }
    ]
    
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # Créer fichier avec le mock
            input_file = create_test_file(tmp_path, "input.enc", test_data, test_passphrase)
            if not input_file:
                return False
            
            # Vérifier qu'on peut le lire avec le mock
            loaded_data = load_encrypted_file(input_file, test_passphrase)
            if not loaded_data:
                print("[ERREUR] Impossible de lire le fichier cree par le mock")
                return False
            
            # Vérifier que le script peut le traiter
            output_file = tmp_path / "output.enc"
            args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase]
            result = run_embed_script(args)
            
            if not result:
                return False
            
            success = (result.returncode == 0 and output_file.exists())
            
            if success:
                # Vérifier qu'on peut lire le fichier de sortie
                output_data = load_encrypted_file(output_file, test_passphrase)
                success = (output_data is not None and len(output_data) > 0)
                
                if success and len(output_data) > 0:
                    # Vérifier que le contenu est préservé
                    success = output_data[0].get("source_name") == "Compatibility Test"
            
            print(f"Test 6: {'[OK] REUSSI' if success else '[ERREUR] ECHEC'}")
            return success
            
    except Exception as e:
        print(f"[ERREUR] Test 6: {e}")
        return False

def main():
    """Fonction principale."""
    print("=== Validation des tests embed_all_sources ===")
    print("Focus sur la compatibilite de chiffrement et fonctionnalites cles")
    
    # Configuration de l'environnement
    if not setup_environment():
        print("[ERREUR] Impossible de configurer l'environnement")
        return False
    
    # Liste des tests essentiels
    tests = [
        ("Fonctionnalite de base", test_basic_functionality),
        ("Force overwrite", test_force_overwrite),
        ("No force existing file", test_no_force_existing_file),
        ("Missing input file", test_missing_input_file),
        ("Missing passphrase", test_missing_passphrase),
        ("Compatibilite chiffrement", test_encryption_compatibility),
    ]
    
    passed_tests = 0
    failed_tests = 0
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            if success:
                passed_tests += 1
            else:
                failed_tests += 1
        except Exception as e:
            print(f"[ERREUR] Exception dans {test_name}: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            failed_tests += 1
    
    print(f"\n=== RESULTATS FINAUX ===")
    print(f"Tests reussis: {passed_tests}/{len(tests)}")
    print(f"Tests echoues: {failed_tests}/{len(tests)}")
    
    if passed_tests == len(tests):
        print("[OK] TOUS LES TESTS ESSENTIELS ONT REUSSI")
        print("[OK] La logique de chiffrement Fernet est harmonisee entre le mock et le script")
        print("[OK] Les fonctionnalites principales du script fonctionnent correctement")
    else:
        print(f"[ERREUR] {failed_tests} tests ont echoue")
        print("[ATTENTION] Des corrections peuvent etre necessaires")
    
    return passed_tests == len(tests)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)