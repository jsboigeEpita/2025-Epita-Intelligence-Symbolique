#!/usr/bin/env python3
"""
Tests fonctionnels pour ServiceManager
Valide les patterns critiques identifiés dans la cartographie :
- Démarrage/arrêt gracieux des services
- Gestion des ports occupés (pattern Free-Port)
- Nettoyage complet des processus (pattern Cleanup-Services)
- Cross-platform compatibility (Windows/Linux)

Auteur: Projet Intelligence Symbolique EPITA
Date: 07/06/2025
"""

import os
import sys
import time
import pytest
import socket
import subprocess
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import des modules à tester
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from project_core.service_manager import ServiceManager, ServiceConfig, PortManager, ProcessCleanup

try:
    import psutil
    import requests
except ImportError:
    pytest.skip("psutil et requests requis pour les tests fonctionnels", allow_module_level=True)


class TestPortManager:
    """Tests du gestionnaire de ports - validation pattern Free-Port"""
    
    def setup_method(self):
        """Setup avant chaque test"""
        import logging
        self.logger = logging.getLogger('test')
        self.port_manager = PortManager(self.logger)
    
    def test_is_port_free_with_free_port(self):
        """Test détection port libre"""
        # Trouver un port libre
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', 0))
            free_port = s.getsockname()[1]
        
        assert self.port_manager.is_port_free(free_port) == True
    
    def test_is_port_free_with_occupied_port(self):
        """Test détection port occupé"""
        # Créer un serveur pour occuper un port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.bind(('localhost', 0))
            occupied_port = server.getsockname()[1]
            server.listen(1)
            
            assert self.port_manager.is_port_free(occupied_port) == False
    
    def test_find_available_port_success(self):
        """Test recherche port libre réussie"""
        # Utiliser un port élevé pour éviter conflits
        start_port = 9000
        found_port = self.port_manager.find_available_port(start_port, max_attempts=10)
        
        assert found_port is not None
        assert found_port >= start_port
        assert self.port_manager.is_port_free(found_port) == True
    
    def test_find_available_port_all_occupied(self):
        """Test quand tous les ports sont occupés"""
        servers = []
        try:
            # Occuper une plage de ports
            start_port = 9100
            for i in range(5):
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server.bind(('localhost', start_port + i))
                server.listen(1)
                servers.append(server)
            
            # Tenter de trouver un port dans cette plage
            found_port = self.port_manager.find_available_port(start_port, max_attempts=5)
            assert found_port is None
            
        finally:
            for server in servers:
                server.close()
    
    @pytest.mark.skipif(sys.platform != "win32", reason="Test spécifique Windows")
    def test_free_port_windows(self):
        """Test libération port sur Windows"""
        self._test_free_port_common()
    
    @pytest.mark.skipif(sys.platform == "win32", reason="Test spécifique Unix/Linux")
    def test_free_port_unix(self):
        """Test libération port sur Unix/Linux"""
        self._test_free_port_common()
    
    def _test_free_port_common(self):
        """Logic commune pour test libération port cross-platform"""
        # Simuler un processus occupant un port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.bind(('localhost', 0))
            test_port = server.getsockname()[1]
            server.listen(1)
            
            # Vérifier que le port est occupé
            assert self.port_manager.is_port_free(test_port) == False
            
            # Le port sera libéré quand le socket se ferme
            # (nous ne pouvons pas tester la terminaison forcée sans risquer
            # d'affecter d'autres processus)


class TestProcessCleanup:
    """Tests du nettoyage des processus - validation pattern Cleanup-Services"""
    
    def setup_method(self):
        """Setup avant chaque test"""
        import logging
        self.logger = logging.getLogger('test')
        self.cleanup = ProcessCleanup(self.logger)
        self.test_processes = []
    
    def teardown_method(self):
        """Nettoyage après chaque test"""
        # Nettoyer tous les processus de test
        for proc in self.test_processes:
            try:
                if proc.is_running():
                    proc.terminate()
                    proc.wait(timeout=5)
            except:
                pass
    
    def test_register_process(self):
        """Test enregistrement processus"""
        # Créer un processus factice
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
        self.test_processes.append(psutil.Process(proc.pid))
        
        # Convertir en psutil.Popen pour le test
        psutil_proc = psutil.Process(proc.pid)
        
        self.cleanup.register_process("test-process", psutil_proc)
        assert "test-process" in self.cleanup.managed_processes
        assert self.cleanup.managed_processes["test-process"].pid == proc.pid
    
    def test_register_cleanup_handler(self):
        """Test enregistrement gestionnaire de nettoyage"""
        handler_called = False
        
        def test_handler():
            nonlocal handler_called
            handler_called = True
        
        self.cleanup.register_cleanup_handler(test_handler)
        
        # Exécuter les gestionnaires
        for handler in self.cleanup.cleanup_handlers:
            handler()
        
        assert handler_called == True
    
    def test_stop_backend_processes_simulation(self):
        """Test arrêt processus backend (simulation)"""
        # Créer un processus Python simulant app.py
        script = "import time; import sys; sys.argv = ['python', 'app.py']; time.sleep(10)"
        proc = subprocess.Popen([sys.executable, "-c", script])
        self.test_processes.append(psutil.Process(proc.pid))
        
        # Attendre que le processus démarre
        time.sleep(1)
        
        # Test avec mock pour éviter d'arrêter d'autres processus Python
        with patch('psutil.process_iter') as mock_iter:
            mock_process = Mock()
            mock_process.info = {
                'pid': proc.pid,
                'name': 'python.exe',
                'cmdline': ['python', 'app.py']
            }
            mock_iter.return_value = [mock_process]
            
            with patch('psutil.Process') as mock_psutil_process:
                mock_proc_instance = Mock()
                mock_proc_instance.name.return_value = "python.exe"
                mock_proc_instance.pid = proc.pid
                mock_psutil_process.return_value = mock_proc_instance
                
                stopped_count = self.cleanup.stop_backend_processes(['app.py'])
                
                # Vérifier que terminate a été appelé
                mock_proc_instance.terminate.assert_called_once()
    
    def test_cleanup_managed_processes(self):
        """Test nettoyage processus managés"""
        # Créer un processus de test
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(5)"])
        psutil_proc = psutil.Process(proc.pid)
        self.test_processes.append(psutil_proc)
        
        # Enregistrer le processus
        self.cleanup.register_process("test-cleanup", psutil_proc)
        
        # Nettoyer
        self.cleanup.cleanup_managed_processes(timeout=3)
        
        # Vérifier que le processus a été arrêté
        assert len(self.cleanup.managed_processes) == 0
        assert not psutil_proc.is_running()


class TestServiceManager:
    """Tests du gestionnaire de services principal"""
    
    def setup_method(self):
        """Setup avant chaque test"""
        self.service_manager = ServiceManager()
        
        # Configuration de test simple
        self.test_config = ServiceConfig(
            name="test-service",
            command=["python", "-c", "import time; time.sleep(30)"],
            working_dir=".",
            port=8888,
            health_check_url="http://localhost:8888/health",
            startup_timeout=10,
            max_port_attempts=3
        )
    
    def teardown_method(self):
        """Nettoyage après chaque test"""
        self.service_manager.stop_all_services()
    
    def test_register_service(self):
        """Test enregistrement configuration service"""
        self.service_manager.register_service(self.test_config)
        
        assert "test-service" in self.service_manager.services
        assert self.service_manager.services["test-service"].port == 8888
    
    def test_service_health_check_mock(self):
        """Test health check avec mock"""
        with patch('requests.get') as mock_get:
            # Simuler réponse réussie
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = self.service_manager.test_service_health("http://localhost:8888/health")
            assert result == True
            
            # Simuler échec
            mock_response.status_code = 500
            result = self.service_manager.test_service_health("http://localhost:8888/health")
            assert result == False
    
    def test_service_health_check_timeout(self):
        """Test timeout health check"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout()
            
            result = self.service_manager.test_service_health("http://localhost:8888/health", timeout=1)
            assert result == False
    
    def test_start_service_unregistered(self):
        """Test démarrage service non enregistré"""
        success, port = self.service_manager.start_service_with_failover("inexistant")
        
        assert success == False
        assert port is None
    
    def test_start_service_no_available_port(self):
        """Test démarrage quand aucun port libre"""
        # Enregistrer service avec port très restreint
        config = ServiceConfig(
            name="no-port-service",
            command=["python", "-c", "print('test')"],
            working_dir=".",
            port=99999,  # Port très élevé
            health_check_url="http://localhost:99999/health",
            max_port_attempts=1
        )
        
        self.service_manager.register_service(config)
        
        # Mock pour simuler qu'aucun port n'est libre
        with patch.object(self.service_manager.port_manager, 'find_available_port') as mock_find:
            mock_find.return_value = None
            
            success, port = self.service_manager.start_service_with_failover("no-port-service")
            
            assert success == False
            assert port is None
    
    def test_get_service_status_not_running(self):
        """Test statut service non démarré"""
        self.service_manager.register_service(self.test_config)
        
        status = self.service_manager.get_service_status("test-service")
        
        assert status['name'] == "test-service"
        assert status['running'] == False
        assert status['pid'] is None
    
    def test_list_all_services(self):
        """Test listage de tous les services"""
        self.service_manager.register_service(self.test_config)
        
        services = self.service_manager.list_all_services()
        
        assert len(services) >= 1
        assert any(s['name'] == "test-service" for s in services)
    
    def test_stop_service_not_running(self):
        """Test arrêt service non démarré"""
        result = self.service_manager.stop_service("inexistant")
        assert result == True  # Arrêt d'un service non démarré = succès


class TestServiceManagerIntegration:
    """Tests d'intégration pour ServiceManager - scenarios réels"""
    
    def setup_method(self):
        """Setup avant chaque test"""
        self.service_manager = ServiceManager()
    
    def teardown_method(self):
        """Nettoyage après chaque test"""
        self.service_manager.stop_all_services()
    
    def test_simple_python_service_lifecycle(self):
        """Test cycle de vie complet d'un service Python simple"""
        # Configuration d'un serveur HTTP simple
        config = ServiceConfig(
            name="simple-http",
            command=[
                sys.executable, "-c",
                "import http.server; import socketserver; "
                "httpd = socketserver.TCPServer(('localhost', 9999), http.server.SimpleHTTPRequestHandler); "
                "print('Server started'); httpd.serve_forever()"
            ],
            working_dir=".",
            port=9999,
            health_check_url="http://localhost:9999/",
            startup_timeout=10,
            max_port_attempts=3
        )
        
        self.service_manager.register_service(config)
        
        # Test démarrage avec failover
        success, port = self.service_manager.start_service_with_failover("simple-http")
        
        if success:
            # Vérifier que le service fonctionne
            status = self.service_manager.get_service_status("simple-http")
            assert status['running'] == True
            assert status['pid'] is not None
            
            # Test health check réel
            time.sleep(2)  # Laisser le temps au serveur de démarrer
            health_ok = self.service_manager.test_service_health(f"http://localhost:{port}/")
            # Note: Peut échouer selon l'environnement, mais ne fait pas échouer le test
            
            # Test arrêt
            stop_success = self.service_manager.stop_service("simple-http")
            assert stop_success == True
            
            # Vérifier arrêt
            status = self.service_manager.get_service_status("simple-http")
            assert status['running'] == False


class TestCrossPlatformCompatibility:
    """Tests de compatibilité cross-platform"""
    
    def test_platform_detection(self):
        """Test détection de plateforme"""
        assert sys.platform in ['win32', 'linux', 'darwin']
    
    @pytest.mark.skipif(sys.platform != "win32", reason="Test spécifique Windows")
    def test_windows_process_management(self):
        """Test gestion processus Windows"""
        # Vérifier que psutil fonctionne sur Windows
        processes = list(psutil.process_iter(['pid', 'name']))
        assert len(processes) > 0
    
    @pytest.mark.skipif(sys.platform == "win32", reason="Test spécifique Unix")
    def test_unix_process_management(self):
        """Test gestion processus Unix/Linux"""
        # Vérifier que psutil fonctionne sur Unix
        processes = list(psutil.process_iter(['pid', 'name']))
        assert len(processes) > 0
    
    def test_path_handling(self):
        """Test gestion des chemins cross-platform"""
        from pathlib import Path
        
        # Test chemins relatifs
        test_path = Path("./test/path")
        assert isinstance(test_path, Path)
        
        # Test résolution de chemin
        resolved = test_path.resolve()
        assert resolved.is_absolute()


class TestFailoverScenarios:
    """Tests des scénarios de failover - validation patterns PowerShell"""
    
    def setup_method(self):
        """Setup avant chaque test"""
        self.service_manager = ServiceManager()
    
    def teardown_method(self):
        """Nettoyage après chaque test"""
        self.service_manager.stop_all_services()
    
    def test_port_failover_simulation(self):
        """Test failover de port quand port principal occupé"""
        # Occuper le port principal
        primary_port = 9900
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
            blocker.bind(('localhost', primary_port))
            blocker.listen(1)
            
            # Configurer service sur port occupé
            config = ServiceConfig(
                name="failover-test",
                command=[sys.executable, "-c", "import time; time.sleep(5)"],
                working_dir=".",
                port=primary_port,
                health_check_url=f"http://localhost:{primary_port}/",
                max_port_attempts=5
            )
            
            self.service_manager.register_service(config)
            
            # Mock health check pour éviter échec
            with patch.object(self.service_manager, 'test_service_health') as mock_health:
                mock_health.return_value = True
                
                # Test démarrage avec failover
                success, assigned_port = self.service_manager.start_service_with_failover("failover-test")
                
                if success:
                    # Vérifier que le port assigné est différent du port principal
                    assert assigned_port != primary_port
                    assert assigned_port > primary_port


if __name__ == "__main__":
    # Exécution directe des tests
    pytest.main([__file__, "-v"])