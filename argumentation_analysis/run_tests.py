#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script d'exécution des tests unitaires

Ce script exécute les tests unitaires pour les modèles et services.
"""

import unittest
import sys
import os

# Ajouter le répertoire courant au chemin de recherche des modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # Découvrir et exécuter tous les tests
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests', pattern='test_*.py')
    
    # Exécuter les tests
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Sortir avec un code d'erreur si des tests ont échoué
    sys.exit(not result.wasSuccessful())