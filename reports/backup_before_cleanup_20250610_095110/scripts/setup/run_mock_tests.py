#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour exécuter uniquement les tests du mock JPype1.
"""

import os
import sys
import subprocess
import traceback

# Ajouter le répertoire racine du projet au chemin de recherche
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

def setup_mock():
    """
    Configure l'environnement pour utiliser le mock JPype1.
    """
    print("Configuration du mock JPype1...")
    
    try:
        # Importer le mock JPype1 directement
        sys.path.insert(0, os.path.join(project_root, "tests", "mocks"))
        import jpype_mock
        print("Mock JPype1 importé avec succès")
        
        # Installer le mock dans sys.modules
        sys.modules['jpype'] = jpype_mock
        sys.modules['_jpype'] = jpype_mock._jpype
        
        # Vérifier que le mock fonctionne
        import jpype
        jpype.startJVM()
        if jpype.isJVMStarted():
            print("Mock JPype1 configuré avec succès")
            return True
        else:
            print("Erreur : Le mock JPype1 n'a pas pu démarrer la JVM")
            return False
    except Exception as e:
        print(f"Erreur lors de la configuration du mock JPype1 : {e}")
        print("Traceback :")
        traceback.print_exc()
        return False

def run_mock_tests():
    """
    Exécute uniquement les tests du mock JPype1.
    """
    print("\nExécution des tests du mock JPype1...")
    
    try:
        # Exécuter pytest uniquement sur les tests du mock JPype1
        test_files = [
            os.path.join(project_root, "tests", "mocks", "test_jpype_mock.py"),
            os.path.join(project_root, "tests", "mocks", "test_jpype_mock_simple.py")
        ]
        
        for test_file in test_files:
            if os.path.exists(test_file):
                print(f"\nExécution de {os.path.basename(test_file)}...")
                
                # Exécuter le test directement avec Python
                cmd = [sys.executable, test_file]
                print(f"Commande : {' '.join(cmd)}")
                
                result = subprocess.run(cmd, cwd=project_root)
                
                if result.returncode == 0:
                    print(f"Test {os.path.basename(test_file)} réussi !")
                else:
                    print(f"Test {os.path.basename(test_file)} échoué (code de retour : {result.returncode})")
                    return False
            else:
                print(f"Fichier de test non trouvé : {test_file}")
                return False
        
        return True
    except Exception as e:
        print(f"Erreur lors de l'exécution des tests : {e}")
        print("Traceback :")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print(f"Exécution des tests du mock JPype1 (Python {sys.version})")
    
    # Configurer le mock
    if not setup_mock():
        print("Échec de la configuration du mock JPype1")
        sys.exit(1)
    
    # Exécuter les tests
    if not run_mock_tests():
        print("Échec de l'exécution des tests du mock JPype1")
        sys.exit(1)
    
    print("\nTous les tests du mock JPype1 ont été exécutés avec succès")