#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le mock JPype1.
"""

import os
import sys
import unittest

# Ajouter le répertoire racine du projet au chemin de recherche
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Importer le mock JPype1
from tests.mocks import jpype_mock

class TestJPypeMock(unittest.TestCase):
    """Tests pour le mock JPype1."""
    
    def setUp(self):
        """Configuration avant chaque test."""
        """Configuration avant chaque test."""
        # La gestion de la JVM est maintenant centralisée dans conftest.py.
        # Plus besoin de shutdownJVM ici.
        pass
    
    # test_start_jvm supprimé car la gestion de la JVM est centralisée
    # et ne doit plus être testée au niveau unitaire des mocks de cette manière.

    def test_jclass(self):
        """Tester la création de classes Java."""
        from tests.mocks import jpype_mock as jpype # MODIFIÉ
        
        # La JVM est supposée être démarrée par conftest.py
        # jpype.startJVM() # Supprimé
        
        # Créer une classe Java
        String = jpype.JClass("java.lang.String")
        
        # Vérifier que la classe a été créée
        self.assertEqual(String.class_name, "java.lang.String")
        
        # Créer une instance de la classe
        string_instance = String("Hello, World!")
        
        # Vérifier que l'instance a été créée
        self.assertIsNotNone(string_instance)
    
    def test_jexception(self):
        """Tester les exceptions Java."""
        from tests.mocks import jpype_mock as jpype # MODIFIÉ
        
        # Créer une exception Java
        exception = jpype.JException("Mock Java Exception")
        
        # Vérifier les propriétés de l'exception
        self.assertEqual(exception.message, "Mock Java Exception")
        self.assertEqual(exception.getClass().getName(), "org.mockexception.MockException")
        self.assertEqual(exception.getMessage(), "Mock Java Exception")

if __name__ == "__main__":
    unittest.main()