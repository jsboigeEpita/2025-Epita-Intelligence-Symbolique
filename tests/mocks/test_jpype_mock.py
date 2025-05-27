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
        # Réinitialiser l'état du mock via shutdownJVM
        import jpype
        if hasattr(jpype, 'shutdownJVM'):
            jpype.shutdownJVM()
    
    def test_start_jvm(self):
        """Tester le démarrage de la JVM."""
        import jpype
        
        # Vérifier que la JVM n'est pas démarrée initialement
        self.assertFalse(jpype.isJVMStarted())
        
        # Démarrer la JVM
        jpype.startJVM()
        
        # Vérifier que la JVM est démarrée
        self.assertTrue(jpype.isJVMStarted())
    
    def test_jclass(self):
        """Tester la création de classes Java."""
        import jpype
        
        # Démarrer la JVM
        jpype.startJVM()
        
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
        import jpype
        
        # Créer une exception Java
        exception = jpype.JException("Mock Java Exception")
        
        # Vérifier les propriétés de l'exception
        self.assertEqual(exception.message, "Mock Java Exception")
        self.assertEqual(exception.getClass().getName(), "org.mockexception.MockException")
        self.assertEqual(exception.getMessage(), "Mock Java Exception")

if __name__ == "__main__":
    unittest.main()