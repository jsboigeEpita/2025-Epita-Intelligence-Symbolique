#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitaires pour l'interface web simple avec intégration ServiceManager
===========================================================================

Tests complets pour l'interface Flask intégrée avec ServiceManager réel
et les analyseurs de sophismes. Valide les nouvelles fonctionnalités.

Version: 2.0.0
Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import sys
import os
import json
import requests
import time
import subprocess
import asyncio
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Configuration des chemins
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

class TestWebAppIntegration(unittest.TestCase):
    """Tests d'intégration avec ServiceManager réel."""
    
    @classmethod
    def setUpClass(cls):
        """Configuration des tests."""
        # Import de l'app Flask
        try:
            # Import direct depuis le répertoire courant
            from app import app
            cls.app = app
            cls.app.config['TESTING'] = True
            cls.client = cls.app.test_client()
            cls.app_available = True
        except Exception as e:
            print(f"[WARNING] App Flask non disponible: {e}")
            cls.app_available = False
        
        # Test OrchestrationServiceManager
        try:
            from argumentation_analysis.orchestration.service_manager import OrchestrationServiceManager
            cls.service_manager_available = True
        except ImportError:
            cls.service_manager_available = False
        
        # Test analyseurs de sophismes
        try:
            from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import ComplexFallacyAnalyzer
            from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import ContextualFallacyAnalyzer
            cls.fallacy_analyzers_available = True
        except ImportError:
            cls.fallacy_analyzers_available = False
    
    def test_01_basic_app_import(self):
        """Test 1: Import basique de l'application Flask."""
        self.assertTrue(self.app_available, "L'application Flask doit être importable")
        if self.app_available:
            self.assertIsNotNone(self.app, "L'objet app ne doit pas être None")
            self.assertIsNotNone(self.client, "Le client de test ne doit pas être None")
    
    def test_02_service_manager_integration(self):
        """Test 2: Intégration avec OrchestrationServiceManager réel."""
        self.assertTrue(self.service_manager_available, "OrchestrationServiceManager doit être disponible")
        
        if self.service_manager_available and self.app_available:
            # Test de création d'instance OrchestrationServiceManager
            from argumentation_analysis.orchestration.service_manager import OrchestrationServiceManager
            sm = OrchestrationServiceManager()
            self.assertIsNotNone(sm, "OrchestrationServiceManager doit être instanciable")
    
    def test_03_fallacy_analyzers_availability(self):
        """Test 3: Disponibilité des analyseurs de sophismes."""
        if self.fallacy_analyzers_available:
            from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import ComplexFallacyAnalyzer
            from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import ContextualFallacyAnalyzer
            
            # Test d'instanciation
            complex_analyzer = ComplexFallacyAnalyzer()
            contextual_analyzer = ContextualFallacyAnalyzer()
            
            self.assertIsNotNone(complex_analyzer, "ComplexFallacyAnalyzer doit être instanciable")
            self.assertIsNotNone(contextual_analyzer, "ContextualFallacyAnalyzer doit être instanciable")
    
    def test_04_routes_basic_functionality(self):
        """Test 4: Fonctionnalité basique des routes."""
        if not self.app_available:
            self.skipTest("App Flask non disponible")
        
        # Test route principale
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200, "La route principale doit être accessible")
        self.assertIn(b"Argumentation Analysis", response.data, "Le titre doit être présent")
        
        # Test route status
        response = self.client.get('/status')
        self.assertEqual(response.status_code, 200, "La route status doit être accessible")
        
        status_data = json.loads(response.data)
        self.assertIn('status', status_data, "La réponse status doit contenir le champ 'status'")
        self.assertIn('webapp', status_data, "La réponse status doit contenir le champ 'webapp'")
    
    def test_05_analyze_with_real_servicemanager(self):
        """Test 5: Route d'analyse avec OrchestrationServiceManager réel."""
        if not (self.app_available and self.service_manager_available):
            self.skipTest("App Flask ou OrchestrationServiceManager non disponible")
        
        test_payload = {
            'text': 'Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée.',
            'analysis_type': 'propositional'
        }
        
        response = self.client.post('/analyze',
                                 data=json.dumps(test_payload),
                                 content_type='application/json')
        
        self.assertEqual(response.status_code, 200, "La route analyze doit être accessible")
        
        result = json.loads(response.data)
        self.assertIn('status', result, "La réponse doit contenir un statut")
        self.assertIn('analysis_id', result, "La réponse doit contenir un ID d'analyse")
        
        # Vérifier que l'analyse utilise bien OrchestrationServiceManager
        if result['status'] == 'success':
            self.assertIn('results', result, "Une analyse réussie doit contenir des résultats")
    
    def test_06_fallacy_detection_endpoint(self):
        """Test 6: Endpoint de détection de sophismes avec vrais analyseurs."""
        if not (self.app_available and self.fallacy_analyzers_available):
            self.skipTest("App Flask ou analyseurs de sophismes non disponibles")
        
        # Test avec un sophisme connu
        test_payload = {
            'text': 'Tu ne peux pas critiquer cette politique car tu n\'es pas politicien toi-même.',
            'analysis_type': 'fallacy_detection'
        }
        
        response = self.client.post('/analyze',
                                 data=json.dumps(test_payload),
                                 content_type='application/json')
        
        self.assertEqual(response.status_code, 200, "L'endpoint de détection de sophismes doit être accessible")
        
        result = json.loads(response.data)
        if result['status'] == 'success' and 'results' in result:
            # Vérifier que des sophismes sont détectés
            results = result['results']
            if 'fallacies' in results:
                self.assertIsInstance(results['fallacies'], list, "Les sophismes détectés doivent être dans une liste")
    
    def test_07_api_examples_endpoint(self):
        """Test 7: Endpoint des exemples API."""
        if not self.app_available:
            self.skipTest("App Flask non disponible")
        
        response = self.client.get('/api/examples')
        self.assertEqual(response.status_code, 200, "L'endpoint des exemples doit être accessible")
        
        examples = json.loads(response.data)
        self.assertIn('examples', examples, "La réponse doit contenir des exemples")
        self.assertIsInstance(examples['examples'], list, "Les exemples doivent être dans une liste")
        
        # Vérifier la structure des exemples
        if examples['examples']:
            example = examples['examples'][0]
            self.assertIn('text', example, "Chaque exemple doit avoir un texte")
            self.assertIn('type', example, "Chaque exemple doit avoir un type")
    
    def test_08_performance_basic(self):
        """Test 8: Performance basique des endpoints."""
        if not self.app_available:
            self.skipTest("App Flask non disponible")
        
        import time
        
        # Test de performance sur la route status
        start_time = time.time()
        response = self.client.get('/status')
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200, "Route status doit être accessible")
        response_time = end_time - start_time
        self.assertLess(response_time, 2.0, "La route status doit répondre en moins de 2 secondes")

def test_webapp_complete():
    """Test complet de l'interface web avec intégration réelle."""
    print("=== TESTS UNITAIRES INTERFACE WEB EPITA (VERSION 2.0) ===")
    print("=" * 60)
    
    # Lancer les tests unitaires
    suite = unittest.TestLoader().loadTestsFromTestCase(TestWebAppIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Résumé des résultats
    print("\n" + "=" * 60)
    print("RÉSUMÉ DES TESTS")
    print("=" * 60)
    print(f"Tests exécutés: {result.testsRun}")
    print(f"Échecs: {len(result.failures)}")
    print(f"Erreurs: {len(result.errors)}")
    
    if result.failures:
        print("\nÉCHECS:")
        for test, traceback in result.failures:
            error_msg = traceback.split('AssertionError: ')[-1].split('\n')[0]
            print(f"- {test}: {error_msg}")
    
    if result.errors:
        print("\nERREURS:")
        for test, traceback in result.errors:
            error_msg = traceback.split('\n')[-2]
            print(f"- {test}: {error_msg}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nRÉSULTAT GLOBAL: {'[OK] SUCCÈS' if success else '[ERREUR] ÉCHEC'}")
    
    return success

def test_webapp_basic():
    """Test basique maintenu pour compatibilité."""
    print("=== Test Interface Web EPITA (Version Basique) ===")
    
    # Test d'import simple avec chemin correct
    try:
        # Import direct depuis le répertoire courant
        from app import app
        app.config['TESTING'] = True
        client = app.test_client()
        
        # Test route principale
        response = client.get('/')
        if response.status_code == 200:
            print("[OK] Route principale accessible")
        else:
            print(f"[ERREUR] Route principale: {response.status_code}")
            return False
        
        # Test route status
        response = client.get('/status')
        if response.status_code == 200:
            print("[OK] Route status accessible")
        else:
            print("[ERREUR] Route status non accessible")
            return False
        
        return True
    except Exception as e:
        print(f"[ERREUR] Test basique échoué: {e}")
        return False

def test_server_startup():
    """Test rapide du démarrage serveur"""
    print("\n=== Test Démarrage Serveur ===")
    
    try:
        # Test de démarrage rapide avec timeout
        process = subprocess.Popen(
            [sys.executable, 'app.py'],
            cwd='services/web_api/interface-simple',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Attendre 3 secondes max
        time.sleep(3)
        
        if process.poll() is None:
            print("[OK] Serveur Flask demarre correctement")
            process.terminate()
            process.wait(timeout=2)
            return True
        else:
            stdout, stderr = process.communicate()
            print("[ERREUR] Serveur Flask n'a pas demarre")
            print(f"STDOUT: {stdout[:200]}...")
            print(f"STDERR: {stderr[:200]}...")
            return False
            
    except Exception as e:
        print(f"[ERREUR] Erreur lors du test de demarrage: {e}")
        return False

if __name__ == '__main__':
    success = test_webapp_basic()
    if success:
        print("\n[SUCCESS] Interface web validee avec succes!")
        test_server_startup()
    else:
        print("\n[ERROR] Problemes detectes dans l'interface web")
        sys.exit(1)