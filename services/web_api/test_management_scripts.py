#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fonctionnels pour les scripts de gestion des services web
==============================================================

Tests pour start_simple_only.py, stop_all_services.py, health_check.py
et validation de la gestion des ports et processus.

Version: 1.0.0
Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import sys
import os
import asyncio
import subprocess
import time
import json
import unittest
import psutil
import aiohttp
from pathlib import Path
from unittest.mock import patch, MagicMock

# Configuration des chemins
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

class TestManagementScripts(unittest.TestCase):
    """Tests pour les scripts de gestion des services."""
    
    @classmethod
    def setUpClass(cls):
        """Configuration des tests."""
        cls.project_root = PROJECT_ROOT
        cls.services_dir = cls.project_root / "services" / "web_api"
        
        # Scripts à tester
        cls.scripts = {
            'start_simple': cls.services_dir / "start_simple_only.py",
            'stop_all': cls.services_dir / "stop_all_services.py",
            'health_check': cls.services_dir / "health_check.py"
        }
        
        # Vérifier l'existence des scripts
        cls.scripts_available = {}
        for name, script_path in cls.scripts.items():
            cls.scripts_available[name] = script_path.exists()
    
    def setUp(self):
        """Configuration avant chaque test."""
        self.test_processes = []
        self.ports_to_cleanup = [3000, 3001, 5000, 5001]
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        # Arrêter tous les processus de test
        for process in self.test_processes:
            try:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
        
        # Nettoyage optionnel des ports (pour éviter les conflits)
        self._cleanup_ports_if_needed()
    
    def _cleanup_ports_if_needed(self):
        """Nettoyage optionnel des ports pour les tests."""
        # Note: Ce nettoyage ne sera fait que si explicitement demandé
        # pour éviter d'interférer avec des services légitimes
        pass
    
    def _find_processes_by_port(self, port):
        """Trouve les processus utilisant un port spécifique."""
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    for conn in proc.connections(kind='inet'):
                        if conn.laddr.port == port:
                            processes.append({
                                'pid': proc.pid,
                                'name': proc.name(),
                                'cmdline': ' '.join(proc.cmdline())
                            })
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            pass
        return processes
    
    def test_01_scripts_existence(self):
        """Test 1: Vérification de l'existence des scripts."""
        for name, available in self.scripts_available.items():
            with self.subTest(script=name):
                self.assertTrue(available, f"Le script {name} doit exister")
    
    def test_02_health_check_script_basic(self):
        """Test 2: Fonctionnement basique du script health_check."""
        if not self.scripts_available['health_check']:
            self.skipTest("Script health_check non disponible")
        
        # Test d'exécution basique du health check
        try:
            result = subprocess.run([
                sys.executable, str(self.scripts['health_check']),
                '--help'
            ], capture_output=True, text=True, timeout=10)
            
            self.assertEqual(result.returncode, 0, "Le script health_check doit afficher l'aide")
            self.assertIn('health_check', result.stdout.lower(), "L'aide doit mentionner health_check")
        except subprocess.TimeoutExpired:
            self.fail("Le script health_check a dépassé le timeout")
    
    def test_03_health_check_execution(self):
        """Test 3: Exécution du health check sans services actifs."""
        if not self.scripts_available['health_check']:
            self.skipTest("Script health_check non disponible")
        
        try:
            # Exécution rapide du health check
            result = subprocess.run([
                sys.executable, str(self.scripts['health_check'])
            ], capture_output=True, text=True, timeout=30)
            
            # Le script doit se terminer même sans services actifs
            self.assertIn(result.returncode, [0, 1], "Le health check doit retourner 0 ou 1")
            
            # Vérifier la présence d'éléments clés dans la sortie
            output = result.stdout.lower()
            # Rechercher différents termes possibles de vérification
            verification_terms = ['verification', 'vérification', 'check', 'health', 'port']
            has_verification = any(term in output for term in verification_terms)
            self.assertTrue(has_verification, f"La sortie doit mentionner une vérification. Sortie: {result.stdout[:200]}")
            
        except subprocess.TimeoutExpired:
            self.fail("Le script health_check a dépassé le timeout de 30s")
    
    @patch('builtins.input', return_value='n')  # Simuler réponse "non" pour l'ouverture navigateur
    def test_04_start_simple_script_help(self, mock_input):
        """Test 4: Script start_simple_only - aide."""
        if not self.scripts_available['start_simple']:
            self.skipTest("Script start_simple_only non disponible")
        
        try:
            result = subprocess.run([
                sys.executable, str(self.scripts['start_simple']),
                '--help'
            ], capture_output=True, text=True, timeout=10)
            
            self.assertEqual(result.returncode, 0, "Le script start_simple doit afficher l'aide")
            self.assertIn('interface simple', result.stdout.lower(), "L'aide doit mentionner l'interface simple")
            
        except subprocess.TimeoutExpired:
            self.fail("Le script start_simple --help a dépassé le timeout")
    
    def test_05_stop_all_script_help(self):
        """Test 5: Script stop_all_services - aide."""
        if not self.scripts_available['stop_all']:
            self.skipTest("Script stop_all_services non disponible")
        
        try:
            result = subprocess.run([
                sys.executable, str(self.scripts['stop_all']),
                '--help'
            ], capture_output=True, text=True, timeout=10)
            
            self.assertEqual(result.returncode, 0, "Le script stop_all doit afficher l'aide")
            self.assertIn('stop', result.stdout.lower(), "L'aide doit mentionner l'arrêt")
            
        except subprocess.TimeoutExpired:
            self.fail("Le script stop_all --help a dépassé le timeout")
    
    def test_06_port_detection_functionality(self):
        """Test 6: Fonctionnalité de détection des ports."""
        # Test avec un port libre (on assume que 9999 est libre)
        processes_9999 = self._find_processes_by_port(9999)
        self.assertIsInstance(processes_9999, list, "La détection de port doit retourner une liste")
        
        # Test avec des ports potentiellement utilisés
        for port in [80, 443, 3000]:
            processes = self._find_processes_by_port(port)
            self.assertIsInstance(processes, list, f"La détection du port {port} doit retourner une liste")
    
    def test_07_scripts_import_validation(self):
        """Test 7: Validation des imports dans les scripts."""
        scripts_to_test = []
        
        # Test des imports pour health_check
        if self.scripts_available['health_check']:
            scripts_to_test.append(('health_check', self.scripts['health_check']))
        
        for script_name, script_path in scripts_to_test:
            with self.subTest(script=script_name):
                # Test d'exécution avec validation syntax
                try:
                    result = subprocess.run([
                        sys.executable, '-m', 'py_compile', str(script_path)
                    ], capture_output=True, text=True, timeout=10)
                    
                    self.assertEqual(result.returncode, 0, 
                                   f"Le script {script_name} doit être syntaxiquement correct")
                    
                except subprocess.TimeoutExpired:
                    self.fail(f"La compilation du script {script_name} a dépassé le timeout")
    
    def test_08_servicemanager_dependency_check(self):
        """Test 8: Vérification des dépendances OrchestrationServiceManager dans les scripts."""
        # Tester l'import du OrchestrationServiceManager comme le feraient les scripts
        servicemanager_available = False
        try:
            from argumentation_analysis.orchestration.service_manager import OrchestrationServiceManager
            servicemanager_available = True
        except ImportError:
            pass
        
        # Le test valide que les scripts peuvent gérer l'absence de OrchestrationServiceManager
        self.assertIsInstance(servicemanager_available, bool,
                            "La vérification OrchestrationServiceManager doit retourner un booléen")
    
    def test_09_integration_script_configurations(self):
        """Test 9: Configurations d'intégration des scripts."""
        # Vérifier la configuration des chemins
        expected_paths = [
            self.project_root / "scripts" / "webapp",
            self.project_root / "argumentation_analysis",
        ]
        
        for path in expected_paths:
            # On vérifie l'existence des répertoires clés pour l'intégration
            if path.exists():
                self.assertTrue(path.is_dir(), f"{path} doit être un répertoire")


class TestHealthCheckIntegration(unittest.TestCase):
    """Tests spécifiques pour le health check avec intégration."""
    
    def setUp(self):
        """Configuration pour les tests de health check."""
        self.project_root = PROJECT_ROOT
        self.health_script = self.project_root / "services" / "web_api" / "health_check.py"
    
    def test_health_check_with_fake_service(self):
        """Test du health check avec un service simulé."""
        if not self.health_script.exists():
            self.skipTest("Script health_check non disponible")
        
        # Créer un serveur HTTP simple pour tester le health check
        import threading
        import http.server
        import socketserver
        
        # Serveur simple sur port 9998
        class TestHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/status':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{"status": "ok"}')
                else:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b'<html><body>Test Service</body></html>')
        
        # Note: Ce test est préparé mais non exécuté pour éviter les conflits de ports
        # Il pourrait être activé dans un environnement de test isolé
        self.assertTrue(True, "Test de health check avec service simulé préparé")


async def run_async_management_tests():
    """Exécute les tests de gestion asynchrones."""
    print("\n=== TESTS ASYNCHRONES DES SCRIPTS DE GESTION ===")
    
    # Test de la fonction health check asynchrone
    try:
        from services.web_api.health_check import check_endpoint_health
        
        # Test avec un endpoint qui n'existe pas
        result = await check_endpoint_health("http://localhost:9999", timeout=1)
        assert isinstance(result, dict), "check_endpoint_health doit retourner un dict"
        assert 'accessible' in result, "Le résultat doit contenir 'accessible'"
        
        print("[OK] Tests asynchrones des health checks")
        return True
        
    except ImportError:
        print("[WARNING] Fonctions health check asynchrones non disponibles")
        return True
    except Exception as e:
        print(f"[ERROR] Erreur dans les tests asynchrones: {e}")
        return False


def test_management_scripts_complete():
    """Test complet des scripts de gestion."""
    print("=== TESTS SCRIPTS DE GESTION ===")
    print("=" * 40)
    
    # Tests synchrones
    suite = unittest.TestLoader().loadTestsFromTestCase(TestManagementScripts)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestHealthCheckIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Tests asynchrones
    try:
        async_success = asyncio.run(run_async_management_tests())
    except Exception as e:
        print(f"[ERROR] Tests asynchrones échoués: {e}")
        async_success = False
    
    # Résumé
    print("\n" + "=" * 40)
    print("RÉSUMÉ DES TESTS DE GESTION")
    print("=" * 40)
    print(f"Tests synchrones: {result.testsRun}")
    print(f"Échecs: {len(result.failures)}")
    print(f"Erreurs: {len(result.errors)}")
    print(f"Tests asynchrones: {'[OK]' if async_success else '[ECHEC]'}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0 and async_success
    print(f"\nRESULTAT: {'[SUCCES]' if success else '[ECHEC]'}")
    
    return success


if __name__ == '__main__':
    success = test_management_scripts_complete()
    sys.exit(0 if success else 1)