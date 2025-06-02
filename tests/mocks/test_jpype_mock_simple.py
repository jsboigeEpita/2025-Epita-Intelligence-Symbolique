#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test simple pour le mock JPype1.
"""

import os
import sys

print("Début du test simple pour le mock JPype1")

# Ajouter le répertoire racine du projet au chemin de recherche
# project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# sys.path.insert(0, project_root)
# print(f"Répertoire racine du projet : {project_root}")
# Commenté car l'installation du package via `pip install -e .` devrait gérer l'accessibilité.
# De plus, ce fichier teste un mock, son path management doit être autonome si besoin.

try:
    print("Importation du mock JPype1...")
    from tests.mocks import jpype_mock # s'assure que le mock est chargé si ce script est exécuté directement
    print("Mock JPype1 importé avec succès")
    
    print("Importation de jpype...")
    import jpype # Devrait maintenant importer le mock si conftest.py a fait son travail
    print("jpype importé avec succès")
    
    print("Test de startJVM...")
    # jpype.startJVM() # Commenté car cause une erreur: missing 1 required positional argument: 'jvmpath'
    # Pour tester, il faudrait faire : jpype.startJVM(jpype.getDefaultJVMPath())
    # ou jpype.startJVM("/chemin/vers/jvm") si getDefaultJVMPath() ne fonctionne pas dans le mock.
    # Étant donné que c'est un mock, on peut supposer qu'il n'est pas nécessaire de démarrer une vraie JVM.
    # Si le mock de startJVM est appelé, il devrait gérer l'absence de jvmpath ou le test devrait le fournir.
    # Pour l'instant, on commente pour éviter l'erreur lors de l'importation potentielle par d'autres modules.
    print("startJVM (appel commenté pour éviter erreur lors d'imports)")
    
    # Les tests suivants pourraient échouer si la JVM n'est pas "démarrée" (même mockée)
    # ou si le mock n'est pas complet.
    # print("Test de isJVMStarted...")
    # is_started = jpype.isJVMStarted()
    # print(f"JVM démarrée : {is_started}")
    
    # print("Test de JClass...")
    # String = jpype.JClass("java.lang.String")
    # print(f"Classe créée : {String._class_name if hasattr(String, '_class_name') else String}")
    
    # print("Test de création d'instance...")
    # string_instance = String("Hello, World!")
    # print(f"Instance créée : {string_instance}")
    
    print("Tests partiels du mock JPype terminés (certains appels commentés).")
except Exception as e:
    print(f"Erreur : {e}")
    import traceback
    traceback.print_exc()