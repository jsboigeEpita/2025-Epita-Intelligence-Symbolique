#!/usr/bin/env python3
"""
ServiceManager - Module unifié pour la gestion des services backend/frontend
Élimine les redondances critiques identifiées dans la cartographie des scripts.

Patterns intégrés :
- Pattern Cleanup-Services de integration_tests_with_failover.ps1
- Pattern Free-Port de backend_failover_non_interactive.ps1
- Logique de failover intelligent multi-ports
- Timeouts et health checks systématiques

Auteur: Projet Intelligence Symbolique EPITA
Date: 07/06/2025
"""

import os
import sys
import time
import signal
import socket
import logging
import subprocess
import threading
from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass
from pathlib import Path

try:
    import psutil
    import requests
except ImportError as e:
    print(f"Dépendances manquantes: {e}")
    print("Installation requise: pip install psutil requests")
    sys.exit(1)


@dataclass
class ServiceConfig:
    """Configuration d'un service"""
    name: str
    command: List[str]
    working_dir: str
    port: int
    health_check_url: str
    startup_timeout: int = 30
    shutdown_timeout: int = 10
    max_port_attempts: int = 5


class PortManager:
    """Gestionnaire intelligent des ports - reprend pattern Free-Port"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        
    def is_port_free(self, port: int) -> bool:
        """Vérifie si un port est libre"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result != 0
        except Exception as e:
            self.logger.warning(f"Erreur test port {port}: {e}")
            return False
    
    def find_available_port(self, start_port: int, max_attempts: int = 10) -> Optional[int]:
        """Trouve un port libre à partir du port de départ"""
        for i in range(max_attempts):
            port = start_port + i
            if self.is_port_free(port):
                self.logger.info(f"Port libre trouvé: {port}")
                return port
        return None
    
    def free_port(self, port: int, force: bool = False) -> bool:
        """Libère un port occupé - adaptation du pattern PowerShell Free-Port"""
        try:
            processes_killed = []
            
            # Recherche des connexions sur le port
            for conn in psutil.net_connections():
                if conn.laddr.port == port:
                    try:
                        process = psutil.Process(conn.pid)
                        proc_info = f"{process.name()} (PID: {process.pid})"
                        
                        if force:
                            process.terminate()
                            processes_killed.append(proc_info)
                            self.logger.info(f"Processus terminé sur port {port}: {proc_info}")
                        else:
                            self.logger.warning(f"Port {port} occupé par: {proc_info}")
                            return False
                            
                    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        self.logger.warning(f"Impossible d'accéder au processus PID {conn.pid}: {e}")
            
            if processes_killed:
                time.sleep(2)  # Délai de grâce pour arrêt propre
                
            return self.is_port_free(port)
            
        except Exception as e:
            self.logger.error(f"Erreur libération port {port}: {e}")
            return False


class ProcessCleanup:
    """Nettoyage gracieux ciblé - adaptation pattern Cleanup-Services"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.managed_processes: Dict[str, psutil.Popen] = {}
        self.cleanup_handlers: List[Callable] = []
        
        # Enregistrer gestionnaire de signal pour nettoyage automatique
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def register_process(self, name: str, process: psutil.Popen):
        """Enregistre un processus pour nettoyage automatique"""
        self.managed_processes[name] = process
        self.logger.info(f"Processus enregistré: {name} (PID: {process.pid})")
    
    def register_cleanup_handler(self, handler: Callable):
        """Enregistre un gestionnaire de nettoyage personnalisé"""
        self.cleanup_handlers.append(handler)
    
    def stop_backend_processes(self, target_scripts: List[str] = None) -> int:
        """Arrêt ciblé processus Python backend - adaptation pattern PowerShell"""
        if target_scripts is None:
            target_scripts = ["app.py", "web_api", "flask"]
        
        stopped_count = 0
        
        for process in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(process.info['cmdline'] or [])
                
                # Vérification si c'est un processus Python ciblé
                if (process.info['name'] and 'python' in process.info['name'].lower() and
                    any(script in cmdline for script in target_scripts)):
                    
                    proc = psutil.Process(process.info['pid'])
                    proc_info = f"{proc.name()} (PID: {proc.pid}) - {cmdline[:100]}"
                    
                    proc.terminate()
                    stopped_count += 1
                    self.logger.info(f"Processus backend arrêté: {proc_info}")
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        return stopped_count
    
    def stop_frontend_processes(self, target_scripts: List[str] = None) -> int:
        """Arrêt ciblé processus Node.js frontend - adaptation pattern PowerShell"""
        if target_scripts is None:
            target_scripts = ["serve", "dev", "start", "react-scripts"]
        
        stopped_count = 0
        
        for process in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(process.info['cmdline'] or [])
                
                # Vérification si c'est un processus Node.js ciblé
                if (process.info['name'] and 'node' in process.info['name'].lower() and
                    any(script in cmdline for script in target_scripts)):
                    
                    proc = psutil.Process(process.info['pid'])
                    proc_info = f"{proc.name()} (PID: {proc.pid}) - {cmdline[:100]}"
                    
                    proc.terminate()
                    stopped_count += 1
                    self.logger.info(f"Processus frontend arrêté: {proc_info}")
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        return stopped_count
    
    def cleanup_managed_processes(self, timeout: int = 10):
        """Nettoyage de tous les processus managés"""
        for name, process in self.managed_processes.items():
            try:
                if process.is_running():
                    self.logger.info(f"Arrêt du processus managé: {name}")
                    process.terminate()
                    
                    # Attendre arrêt gracieux
                    try:
                        process.wait(timeout=timeout)
                    except psutil.TimeoutExpired:
                        self.logger.warning(f"Arrêt forcé du processus: {name}")
                        process.kill()
                        
            except Exception as e:
                self.logger.error(f"Erreur arrêt processus {name}: {e}")
        
        self.managed_processes.clear()
    
    def cleanup_all(self):
        """Nettoyage complet - executé lors des signaux d'arrêt"""
        self.logger.info("Début du nettoyage complet des services...")
        
        # Exécuter gestionnaires personnalisés
        for handler in self.cleanup_handlers:
            try:
                handler()
            except Exception as e:
                self.logger.error(f"Erreur gestionnaire de nettoyage: {e}")
        
        # Nettoyer processus managés
        self.cleanup_managed_processes()
        
        # Arrêter processus backend/frontend
        backend_stopped = self.stop_backend_processes()
        frontend_stopped = self.stop_frontend_processes()
        
        self.logger.info(f"Nettoyage terminé - Backend: {backend_stopped}, Frontend: {frontend_stopped}")
    
    def _signal_handler(self, signum, frame):
        """Gestionnaire de signal pour nettoyage automatique"""
        self.logger.info(f"Signal reçu ({signum}), nettoyage en cours...")
        self.cleanup_all()
        sys.exit(0)


class ServiceManager:
    """Gestionnaire centralisé des services backend/frontend"""
    
    def __init__(self, log_level: int = logging.INFO):
        self.logger = self._setup_logging(log_level)
        self.port_manager = PortManager(self.logger)
        self.process_cleanup = ProcessCleanup(self.logger)
        self.services: Dict[str, ServiceConfig] = {}
        self.running_services: Dict[str, psutil.Popen] = {}
        
    def _setup_logging(self, level: int) -> logging.Logger:
        """Configuration du logging"""
        logger = logging.getLogger('ServiceManager')
        logger.setLevel(level)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def register_service(self, config: ServiceConfig):
        """Enregistre une configuration de service"""
        self.services[config.name] = config
        self.logger.info(f"Service enregistré: {config.name} sur port {config.port}")
    
    def test_service_health(self, url: str, timeout: int = 5) -> bool:
        """Test de santé d'un service via HTTP"""
        try:
            response = requests.get(url, timeout=timeout)
            return response.status_code == 200
        except Exception as e:
            self.logger.debug(f"Health check échoué pour {url}: {e}")
            return False
    
    def start_service_with_failover(self, service_name: str) -> Tuple[bool, Optional[int]]:
        """
        Démarre un service avec failover intelligent sur les ports
        Adaptation du pattern backend_failover_non_interactive.ps1
        """
        if service_name not in self.services:
            self.logger.error(f"Service non enregistré: {service_name}")
            return False, None
        
        config = self.services[service_name]
        
        # Recherche d'un port libre
        available_port = self.port_manager.find_available_port(
            config.port, config.max_port_attempts
        )
        
        if not available_port:
            self.logger.error(f"Aucun port libre trouvé pour {service_name}")
            return False, None
        
        # Si port différent, libérer le port original si nécessaire
        if available_port != config.port:
            self.logger.info(f"Failover port {config.port} → {available_port} pour {service_name}")
            self.port_manager.free_port(config.port, force=True)
        
        # Préparation de la commande avec port dynamique
        command = []
        for arg in config.command:
            if f":{config.port}" in arg:
                arg = arg.replace(f":{config.port}", f":{available_port}")
            elif str(config.port) == arg:
                arg = str(available_port)
            command.append(arg)
        
        try:
            # Démarrage du processus
            self.logger.info(f"Démarrage {service_name}: {' '.join(command)}")
            
            process = psutil.Popen(
                command,
                cwd=config.working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Enregistrement pour nettoyage automatique
            self.running_services[service_name] = process
            self.process_cleanup.register_process(service_name, process)
            
            # Attente démarrage avec health check
            health_url = config.health_check_url.replace(f":{config.port}", f":{available_port}")
            
            for attempt in range(config.startup_timeout):
                if not process.is_running():
                    self.logger.error(f"Processus {service_name} arrêté prématurément")
                    return False, None
                
                if self.test_service_health(health_url):
                    self.logger.info(f"Service {service_name} démarré avec succès sur port {available_port}")
                    return True, available_port
                
                time.sleep(1)
            
            self.logger.error(f"Timeout démarrage {service_name} après {config.startup_timeout}s")
            self.stop_service(service_name)
            return False, None
            
        except Exception as e:
            self.logger.error(f"Erreur démarrage {service_name}: {e}")
            return False, None
    
    def stop_service(self, service_name: str) -> bool:
        """Arrête un service spécifique"""
        if service_name not in self.running_services:
            self.logger.warning(f"Service non en cours d'exécution: {service_name}")
            return True
        
        process = self.running_services[service_name]
        config = self.services.get(service_name)
        timeout = config.shutdown_timeout if config else 10
        
        try:
            if process.is_running():
                self.logger.info(f"Arrêt du service: {service_name}")
                process.terminate()
                
                try:
                    process.wait(timeout=timeout)
                    self.logger.info(f"Service {service_name} arrêté proprement")
                except psutil.TimeoutExpired:
                    self.logger.warning(f"Arrêt forcé du service: {service_name}")
                    process.kill()
            
            del self.running_services[service_name]
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur arrêt service {service_name}: {e}")
            return False
    
    def stop_all_services(self):
        """Arrête tous les services en cours"""
        self.logger.info("Arrêt de tous les services...")
        
        service_names = list(self.running_services.keys())
        for service_name in service_names:
            self.stop_service(service_name)
        
        # Nettoyage complet pour éliminer les processus fantômes
        self.process_cleanup.cleanup_all()
    
    def get_service_status(self, service_name: str) -> Dict:
        """Obtient le statut d'un service"""
        status = {
            'name': service_name,
            'running': False,
            'pid': None,
            'port': None,
            'health': False
        }
        
        if service_name in self.running_services:
            process = self.running_services[service_name]
            status['running'] = process.is_running()
            status['pid'] = process.pid if status['running'] else None
            
            if service_name in self.services:
                config = self.services[service_name]
                if status['running']:
                    status['health'] = self.test_service_health(config.health_check_url)
        
        return status
    
    def list_all_services(self) -> List[Dict]:
        """Liste le statut de tous les services enregistrés"""
        return [self.get_service_status(name) for name in self.services.keys()]


def create_default_configs() -> List[ServiceConfig]:
    """Crée les configurations par défaut pour les services standards"""
    return [
        ServiceConfig(
            name="backend-flask",
            command=["python", "-c", "from flask import Flask; app = Flask(__name__); @app.route('/health'); def health(): return {'status': 'ok'}; app.run(host='0.0.0.0', port=5000, debug=True)"],
            working_dir=".",
            port=5000,
            health_check_url="http://localhost:5000/health",
            startup_timeout=30,
            max_port_attempts=5
        ),
        ServiceConfig(
            name="frontend-react",
            command=["npm", "start"],
            working_dir="services/web_api/interface-web-argumentative",
            port=3000,
            health_check_url="http://localhost:3000",
            startup_timeout=45,
            max_port_attempts=5
        )
    ]


if __name__ == "__main__":
    # Test rapide du ServiceManager
    manager = ServiceManager()
    
    # Enregistrement des configurations par défaut
    for config in create_default_configs():
        manager.register_service(config)
    
    print("ServiceManager initialisé avec succès")
    print("Services enregistrés:", list(manager.services.keys()))
    
    # Test nettoyage
    manager.process_cleanup.cleanup_all()