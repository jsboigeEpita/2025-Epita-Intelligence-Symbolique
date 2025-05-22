#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de test pour vérifier le fonctionnement du mock JPype1.
"""

import os
import sys
import traceback

# Ajouter le répertoire racine du projet au chemin de recherche
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
print(f"Répertoire racine du projet ajouté au chemin de recherche : {project_root}")

def test_jpype_mock():
    """
    Teste le fonctionnement du mock JPype1.
    """
    print(f"Version de Python : {sys.version}")
    
    # Importer le mock JPype1
    try:
        print("Importation du mock JPype1...")
        
        # Vérifier si le module existe
        import importlib.util
        spec = importlib.util.find_spec("tests.mocks.jpype_mock")
        if spec is None:
            print("Le module tests.mocks.jpype_mock n'existe pas")
            print("Chemins de recherche Python :")
            for path in sys.path:
                print(f"  {path}")
            
            # Vérifier si le répertoire tests/mocks existe
            mocks_dir = os.path.join(project_root, "tests", "mocks")
            if os.path.exists(mocks_dir):
                print(f"Le répertoire {mocks_dir} existe")
                print("Contenu du répertoire :")
                for file in os.listdir(mocks_dir):
                    print(f"  {file}")
            else:
                print(f"Le répertoire {mocks_dir} n'existe pas")
            
            return False
        
        # Importer le module
        from tests.mocks import jpype_mock
        print("Mock JPype1 importé avec succès")
        
        # Tester les fonctionnalités de base du mock
        import jpype
        
        print("Test de startJVM...")
        jpype.startJVM()
        
        print("Test de isJVMStarted...")
        is_started = jpype.isJVMStarted()
        print(f"JVM démarrée : {is_started}")
        
        print("Test de JClass...")
        String = jpype.JClass("java.lang.String")
        string_instance = String("Hello, World!")
        print(f"Instance de String créée : {string_instance}")
        
        print("Tous les tests ont réussi !")
        return True
    except Exception as e:
        print(f"Erreur lors du test du mock JPype1 : {e}")
        print("Traceback :")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Début du test...")
    result = test_jpype_mock()
    print(f"Résultat du test : {'Succès' if result else 'Échec'}")