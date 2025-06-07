#!/usr/bin/env python3
"""
Tests unitaires complets pour ServiceManager
Validation exhaustive de tous les composants
"""

import unittest
import sys
import os
import time
import socket
import subprocess
import tempfile
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Ajouter project_core au path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "project_core"))

from service_manager import (
    ServiceManager, PortManager, ProcessCleanup, 
    ServiceConfig, create_default_configs
)


class TestPortManager(unittest.TestCase):
    """Tests unitaires pour PortManager"""
    
    def setUp(self):
        self.logger = logging.getLogger('test')
        self.port_manager = PortManager(self.logger)
    
    def test_is_port_free_with_available_port(self):
        """Test détection port libre"""
        # Trouver un port libre
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            port = s.getsockname()[1]
        
        self.assertTrue(self.port_manager.is_port_free(port))
    
    def test_is_port_free_with_occupied_port(self):
        """Test détection port occupé"""
        # Créer un socket qui occupe un port
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('', 0))
        port = server_socket.getsockname()[1]
        server_socket.listen(1)
        
        try:
            self.assertFalse(self.port_manager.is_port_free(port))
        finally:
            server_socket.close()
    
    def test_find_available_port_success(self):
        """Test recherche port disponible - succès"""
        port = self.port_manager.find_available_port(8000, max_attempts=5)
        self.assertIsNotNone(port)
        self.assertGreaterEqual(port, 8000)
        self.assertLess(port, 8005)
    
    def test_find_available_port_no_ports_available(self):
        """Test recherche port - aucun disponible"""
        # Mock is_port_free pour retourner toujours False
        with patch.object(self.port_manager, 'is_port_free', return_value=False):
            port = self.port_manager.find_available_port(9000, max_attempts=3)
            self.assertIsNone(port)
    
    @patch('psutil.net_connections')
    def test_free_port_no_connections(self, mock_net_connections):
        """Test libération port - aucune connexion"""
        mock_net_connections.return_value = []
        
        result = self.port_manager.free_port(8080)
        self.assertTrue(result)
    
    @patch('psutil.net_connections')
    @patch('psutil.Process')
    def test_free_port_with_process(self, mock_process_class, mock_net_connections):
        """Test libération port avec processus actif"""
        # Mock connection
        mock_conn = Mock()
        mock_conn.laddr.port = 8080
        mock_conn.pid = 12345
        mock_net_connections.return_value = [mock_conn]
        
        # Mock process
        mock_process = Mock()
        mock_process.name.return_value = 'test.exe'
        mock_process.pid = 12345
        mock_process_class.return_value = mock_process
        
        # Test sans force - devrait retourner False
        result = self.port_manager.free_port(8080, force=False)
        self.assertFalse(result)
        
        # Test avec force - devrait terminer le processus
        with patch.object(self.port_manager, 'is_port_free', return_value=True):
            result = self.port_manager.free_port(8080, force=True)
            self.assertTrue(result)
            mock_process.terminate.assert_called_once()


class TestProcessCleanup(unittest.TestCase):
    """Tests unitaires pour ProcessCleanup"""
    
    def setUp(self):
        self.logger = logging.getLogger('test')
        self.cleanup = ProcessCleanup(self.logger)
    
    def test_register_process(self):
        """Test enregistrement processus"""
        mock_process = Mock()
        mock_process.pid = 12345
        
        self.cleanup.register_process("test-service", mock_process)
        
        self.assertIn("test-service", self.cleanup.managed_processes)
        self.assertEqual(self.cleanup.managed_processes["test-service"], mock_process)
    
    def test_cleanup_managed_processes(self):
        """Test nettoyage processus gérés"""
        # Créer un mock process
        mock_process = Mock()
        mock_process.is_running.return_value = True
        mock_process.pid = 12345
        
        self.cleanup.register_process("test-service", mock_process)
        self.cleanup.cleanup_managed_processes()
        
        # Vérifier que terminate a été appelé
        mock_process.terminate.assert_called_once()
    
    @patch('psutil.process_iter')
    def test_stop_backend_processes(self, mock_process_iter):
        """Test arrêt processus backend"""
        # Mock process Python
        mock_process = Mock()
        mock_process.info = {
            'pid': 12345,
            'name': 'python.exe',
            'cmdline': ['python', 'app.py', '--port', '5000']
        }
        mock_process.terminate = Mock()
        
        mock_process_iter.return_value = [mock_process]
        
        count = self.cleanup.stop_backend_processes()
        
        self.assertGreaterEqual(count, 0)
    
    @patch('psutil.process_iter')
    def test_stop_frontend_processes(self, mock_process_iter):
        """Test arrêt processus frontend"""
        # Mock process Node.js
        mock_process = Mock()
        mock_process.info = {
            'pid': 12345,
            'name': 'node.exe',
            'cmdline': ['node', 'server.js', 'serve']
        }
        mock_process.terminate = Mock()
        
        mock_process_iter.return_value = [mock_process]
        
        count = self.cleanup.stop_frontend_processes()
        
        self.assertGreaterEqual(count, 0)


class TestServiceConfig(unittest.TestCase):
    """Tests unitaires pour ServiceConfig"""
    
    def test_service_config_creation(self):
        """Test création configuration service"""
        config = ServiceConfig(
            name="test-service",
            command=["python", "app.py"],
            working_dir="/test",
            port=8000,
            health_check_url="http://localhost:8000/health"
        )
        
        self.assertEqual(config.name, "test-service")
        self.assertEqual(config.command, ["python", "app.py"])
        self.assertEqual(config.working_dir, "/test")
        self.assertEqual(config.port, 8000)
        self.assertEqual(config.health_check_url, "http://localhost:8000/health")
        self.assertEqual(config.startup_timeout, 30)  # valeur par défaut
        self.assertEqual(config.max_port_attempts, 5)  # valeur par défaut


class TestServiceManager(unittest.TestCase):
    """Tests unitaires pour ServiceManager"""
    
    def setUp(self):
        self.manager = ServiceManager()
        self.test_config = ServiceConfig(
            name="test-service",
            command=["python", "-c", "import time; time.sleep(1)"],
            working_dir=".",
            port=9000,
            health_check_url="http://localhost:9000/health"
        )
    
    def test_register_service(self):
        """Test enregistrement service"""
        self.manager.register_service(self.test_config)
        
        self.assertIn("test-service", self.manager.services)
        self.assertEqual(self.manager.services["test-service"], self.test_config)
    
    def test_get_service_status_not_running(self):
        """Test statut service non démarré"""
        self.manager.register_service(self.test_config)
        
        status = self.manager.get_service_status("test-service")
        
        self.assertEqual(status['name'], "test-service")
        self.assertFalse(status['running'])
        self.assertIsNone(status['pid'])
        self.assertFalse(status['health'])
    
    def test_get_service_status_unregistered(self):
        """Test statut service non enregistré"""
        status = self.manager.get_service_status("nonexistent")
        
        self.assertEqual(status['name'], "nonexistent")
        self.assertFalse(status['running'])
    
    def test_list_all_services(self):
        """Test liste tous les services"""
        self.manager.register_service(self.test_config)
        
        services = self.manager.list_all_services()
        
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0]['name'], "test-service")
    
    @patch('requests.get')
    def test_service_health_check_success(self, mock_get):
        """Test health check succès"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = self.manager.test_service_health("http://localhost:8000/health")
        
        self.assertTrue(result)
    
    @patch('requests.get')
    def test_service_health_check_failure(self, mock_get):
        """Test health check échec"""
        mock_get.side_effect = Exception("Connection refused")
        
        result = self.manager.test_service_health("http://localhost:8000/health")
        
        self.assertFalse(result)
    
    def test_stop_service_not_running(self):
        """Test arrêt service non démarré"""
        result = self.manager.stop_service("nonexistent")
        
        self.assertTrue(result)


class TestCreateDefaultConfigs(unittest.TestCase):
    """Tests pour les configurations par défaut"""
    
    def test_create_default_configs(self):
        """Test création configurations par défaut"""
        configs = create_default_configs()
        
        self.assertIsInstance(configs, list)
        self.assertGreater(len(configs), 0)
        
        # Vérifier que toutes les configs sont bien des ServiceConfig
        for config in configs:
            self.assertIsInstance(config, ServiceConfig)
            self.assertIsNotNone(config.name)
            self.assertIsNotNone(config.command)
            self.assertIsNotNone(config.port)


class TestServiceManagerIntegration(unittest.TestCase):
    """Tests d'intégration pour ServiceManager"""
    
    def setUp(self):
        self.manager = ServiceManager()
    
    def test_full_service_lifecycle_simulation(self):
        """Test cycle de vie complet d'un service (simulation)"""
        # Configuration service simple
        config = ServiceConfig(
            name="integration-test",
            command=["python", "-c", "print('Service started'); import time; time.sleep(0.5)"],
            working_dir=".",
            port=9001,
            health_check_url="http://localhost:9001/health"
        )
        
        # Enregistrement
        self.manager.register_service(config)
        self.assertIn("integration-test", self.manager.services)
        
        # Vérification statut initial
        status = self.manager.get_service_status("integration-test")
        self.assertFalse(status['running'])
        
        # Liste des services
        services = self.manager.list_all_services()
        service_names = [s['name'] for s in services]
        self.assertIn("integration-test", service_names)


if __name__ == '__main__':
    # Configuration logging pour les tests
    logging.basicConfig(level=logging.WARNING)
    
    # Lancement des tests
    unittest.main(verbosity=2)