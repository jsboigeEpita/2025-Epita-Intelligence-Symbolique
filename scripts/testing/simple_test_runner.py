#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script simple pour exécuter les tests embed_all_sources.
"""

import sys
import os
import subprocess
from pathlib import Path

# Ajouter le répertoire racine au path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent # MODIFIÉ: Remonter à la racine du projet
sys.path.insert(0, str(PROJECT_ROOT))

def run_single_test():
    """Exécute un test simple pour vérifier la logique de chiffrement."""
    print("=== Test simple de la logique de chiffrement ===")
    
    try:
        # Importer les modules nécessaires
        from tests.mocks.extract_definitions_mock import setup_extract_definitions_mock
        from argumentation_analysis.ui import file_operations
        from cryptography.fernet import Fernet
        import tempfile
        import json
        
        # Configurer le mock
        setup_result = setup_extract_definitions_mock()
        print(f"Configuration du mock: {'[OK] Reussi' if setup_result else '[ERREUR] Echec'}")
        
        # Créer des données de test
        test_data = [
            {
                "source_name": "Test Source",
                "source_type": "direct_download",
                "schema": "http",
                "host_parts": ["testserver"],
                "path": "/test.txt",
                "extracts": [],
                "full_text": "Test content"
            }
        ]
        
        test_passphrase = "Propaganda"
        
        # Test de sauvegarde et chargement
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.enc"
            
            # Sauvegarder avec le mock
            print("Test de sauvegarde...")
            save_result = file_operations.save_extract_definitions(
                test_data,
                test_file,
                test_passphrase,
                embed_full_text=True,
                config={}
            )
            print(f"Sauvegarde: {'[OK] Reussi' if save_result else '[ERREUR] Echec'}")
            print(f"Fichier cree: {'[OK] Oui' if test_file.exists() else '[ERREUR] Non'}")
            
            # Charger avec le mock
            print("Test de chargement...")
            loaded_data = file_operations.load_extract_definitions(
                config_file=test_file,
                key=test_passphrase
            )
            print(f"Chargement: {'[OK] Reussi' if loaded_data else '[ERREUR] Echec'}")
            print(f"Donnees chargees: {len(loaded_data) if loaded_data else 0} elements")
            
            if loaded_data and len(loaded_data) > 0:
                print(f"Premier élément: {loaded_data[0].get('source_name', 'N/A')}")
                print(f"Texte complet present: {'[OK] Oui' if 'full_text' in loaded_data[0] else '[ERREUR] Non'}")
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] Erreur: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def run_script_test():
    """Teste l'exécution du script embed_all_sources.py."""
    print("\n=== Test d'exécution du script embed_all_sources.py ===")
    
    try:
        import tempfile
        from tests.mocks.extract_definitions_mock import setup_extract_definitions_mock
        from argumentation_analysis.ui import file_operations
        
        # Configurer le mock
        setup_extract_definitions_mock()
        
        # Créer des données de test
        test_data = [
            {
                "source_name": "Script Test Source",
                "source_type": "direct_download",
                "schema": "http",
                "host_parts": ["testserver"],
                "path": "/script_test.txt",
                "extracts": []
                # Pas de full_text pour forcer le script à le récupérer
            }
        ]
        
        test_passphrase = "Propaganda"
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_file = Path(tmp_dir) / "input.enc"
            output_file = Path(tmp_dir) / "output.enc"
            
            # Créer le fichier d'entrée
            file_operations.save_extract_definitions(
                test_data,
                input_file,
                test_passphrase,
                embed_full_text=False,
                config={}
            )
            
            print(f"Fichier d'entree cree: {'[OK] Oui' if input_file.exists() else '[ERREUR] Non'}")
            
            # Exécuter le script
            script_path = PROJECT_ROOT / "scripts" / "embed_all_sources.py"
            cmd = [
                sys.executable, str(script_path),
                "--input-config", str(input_file),
                "--output-config", str(output_file),
                "--passphrase", test_passphrase
            ]
            
            print(f"Commande: {' '.join(cmd)}")
            
            # Mock get_full_text_for_source pour éviter les appels réseau
            import unittest.mock
            with unittest.mock.patch('argumentation_analysis.ui.utils.get_full_text_for_source') as mock_get_text:
                mock_get_text.return_value = "Mocked full text content"
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                print(f"Code de retour: {result.returncode}")
                print(f"STDOUT: {result.stdout}")
                if result.stderr:
                    print(f"STDERR: {result.stderr}")
                
                print(f"Fichier de sortie cree: {'[OK] Oui' if output_file.exists() else '[ERREUR] Non'}")
                
                if output_file.exists():
                    # Vérifier le contenu du fichier de sortie
                    output_data = file_operations.load_extract_definitions(
                        config_file=output_file,
                        key=test_passphrase
                    )
                    print(f"Donnees de sortie: {len(output_data) if output_data else 0} elements")
                    if output_data and len(output_data) > 0:
                        has_full_text = 'full_text' in output_data[0]
                        print(f"Texte complet ajoute: {'[OK] Oui' if has_full_text else '[ERREUR] Non'}")
                
                return result.returncode == 0
        
    except Exception as e:
        print(f"[ERREUR] Erreur: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Fonction principale."""
    print("=== Validation des tests embed script ===")
    
    # Test 1: Logique de chiffrement
    test1_success = run_single_test()
    
    # Test 2: Exécution du script
    test2_success = run_script_test()
    
    print(f"\n=== RESULTATS FINAUX ===")
    print(f"Test logique de chiffrement: {'[OK] REUSSI' if test1_success else '[ERREUR] ECHEC'}")
    print(f"Test execution script: {'[OK] REUSSI' if test2_success else '[ERREUR] ECHEC'}")
    
    overall_success = test1_success and test2_success
    print(f"Resultat global: {'[OK] TOUS LES TESTS REUSSIS' if overall_success else '[ERREUR] CERTAINS TESTS ONT ECHOUE'}")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)