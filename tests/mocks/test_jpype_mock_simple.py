#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test simple pour le mock JPype1.
"""

import os
import sys

print("Début du test simple pour le mock JPype1")

# Ajouter le répertoire racine du projet au chemin de recherche
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
print(f"Répertoire racine du projet : {project_root}")

try:
    print("Importation du mock JPype1...")
    from tests.mocks import jpype_mock
    print("Mock JPype1 importé avec succès")
    
    print("Importation de jpype...")
    import jpype
    print("jpype importé avec succès")
    
    print("Test de startJVM...")
    jpype.startJVM()
    print("startJVM exécuté")
    
    print("Test de isJVMStarted...")
    is_started = jpype.isJVMStarted()
    print(f"JVM démarrée : {is_started}")
    
    print("Test de JClass...")
    String = jpype.JClass("java.lang.String")
    print(f"Classe créée : {String.class_name}")
    
    print("Test de création d'instance...")
    string_instance = String("Hello, World!")
    print(f"Instance créée : {string_instance}")
    
    print("Tous les tests ont réussi !")
except Exception as e:
    print(f"Erreur : {e}")
    import traceback
    traceback.print_exc()