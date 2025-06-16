#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour exécuter les tests du projet en utilisant le mock JPype1.
"""

import project_core.core_from_scripts.auto_env
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
        # Importer le mock JPype1
        from tests.mocks import jpype_mock
        print("Mock JPype1 importé avec succès")
        
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

def run_tests():
    """
    Exécute les tests du projet.
    """
    print("\nExécution des tests...")
    
    try:
        # Exécuter pytest avec le mock JPype1
        cmd = [sys.executable, "-m", "pytest", "tests", "-v"]
        print(f"Commande : {' '.join(cmd)}")
        
        result = subprocess.run(cmd, cwd=project_root)
        
        if result.returncode == 0:
            print("Tous les tests ont réussi !")
            return True
        else:
            print(f"Certains tests ont échoué (code de retour : {result.returncode})")
            return False
    except Exception as e:
        print(f"Erreur lors de l'exécution des tests : {e}")
        print("Traceback :")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print(f"Exécution des tests avec le mock JPype1 (Python {sys.version})")
    
    # Configurer le mock
    if not setup_mock():
        print("Échec de la configuration du mock JPype1")
        sys.exit(1)
    
    # Exécuter les tests
    if not run_tests():
        print("Échec de l'exécution des tests")
        sys.exit(1)
    
    print("\nTous les tests ont été exécutés avec succès en utilisant le mock JPype1")