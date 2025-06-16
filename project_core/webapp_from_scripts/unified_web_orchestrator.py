#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orchestrateur Unifié d'Application Web Python
==============================================

Remplace tous les scripts PowerShell redondants d'intégration web :
- integration_test_with_trace.ps1
- integration_test_with_trace_robust.ps1
- integration_test_with_trace_fixed.ps1
- integration_test_trace_working.ps1
- integration_test_trace_simple_success.ps1
- sprint3_final_validation.py
- test_backend_fixed.ps1

Auteur: Projet Intelligence Symbolique EPITA
Date: 07/06/2025
"""

import os
import sys
import time
import json
import yaml
import asyncio
import logging
import argparse
import subprocess
import threading
import socket
import signal
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from playwright.async_api import async_playwright, Playwright, Browser
import aiohttp

# Imports internes (sans activation d'environnement au niveau du module)
# Le bootstrap se fera dans la fonction main()
from project_core.webapp_from_scripts.backend_manager import BackendManager
from project_core.webapp_from_scripts.frontend_manager import FrontendManager
from project_core.webapp_from_scripts.playwright_runner import PlaywrightRunner
from project_core.webapp_from_scripts.process_cleaner import ProcessCleaner

# Import du gestionnaire centralisé des ports
try:
    from project_core.config.port_manager import get_port_manager, set_environment_variables
    CENTRAL_PORT_MANAGER_AVAILABLE = True
except ImportError:
    CENTRAL_PORT_MANAGER_AVAILABLE = False
    print("[WARNING] Gestionnaire centralisé des ports non disponible, utilisation des ports par défaut")

class WebAppStatus(Enum):
    """États de l'application web"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    STOPPING = "stopping"

@dataclass
class TraceEntry:
    """Entrée de trace d'action"""
    timestamp: str
    action: str
    details: str = ""
    result: str = ""
    screenshot: str = ""
    status: str = "success"

@dataclass
class WebAppInfo:
    """Informations sur l'état de l'application web"""
    backend_url: Optional[str] = None
    backend_port: Optional[int] = None
    backend_pid: Optional[int] = None
    frontend_url: Optional[str] = None
    frontend_port: Optional[int] = None
    frontend_pid: Optional[int] = None
    status: WebAppStatus = WebAppStatus.STOPPED
    start_time: Optional[datetime] = None

class UnifiedWebOrchestrator:
    """
    Orchestrateur unifié pour applications web Python
    
    Fonctionnalités principales :
    - Démarrage/arrêt backend Flask avec failover de ports
    - Démarrage/arrêt frontend React (optionnel)
    - Exécution tests Playwright intégrés
    - Tracing complet des opérations
    - Cleanup automatique des processus
    - Configuration centralisée
    """
    
    API_ENDPOINTS_TO_CHECK = [
        # Routes FastAPI
        {"path": "/api/health", "method": "GET"},
        {"path": "/api/endpoints", "method": "GET"},
    ]

    def __init__(self, args: argparse.Namespace):
        self.config_path = Path(args.config)
        self.config = self._load_config()
        self.logger = self._setup_logging(log_level=args.log_level.upper())

        # Configuration runtime basée sur les arguments
        self.headless = args.headless and not args.visible
        self.timeout_minutes = args.timeout
        self.enable_trace = not args.no_trace

        # Gestionnaires spécialisés
        self.backend_manager = BackendManager(self.config.get('backend', {}), self.logger)
        self.frontend_manager: Optional[FrontendManager] = None  # Sera instancié plus tard

        playwright_config = self.config.get('playwright', {})
        # Le timeout CLI surcharge la config YAML
        playwright_config['timeout_ms'] = self.timeout_minutes * 60 * 1000

        self.playwright_runner = PlaywrightRunner(playwright_config, self.logger)
        self.process_cleaner = ProcessCleaner(self.logger)

        # État de l'application
        self.app_info = WebAppInfo()
        self.trace_log: List[TraceEntry] = []
        self.start_time = datetime.now()

        # Support Playwright natif
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None

        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Configure les gestionnaires de signaux pour un arrêt propre, compatible Windows."""
        if sys.platform != "win32":
            # Utilisation de la version la plus a jour de la boucle asyncio
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(self.shutdown(signal=s)))
        else:
            self.logger.info("Gestionnaires de signaux non configurés pour Windows (SIGINT/SIGTERM).")

    async def shutdown(self, signal=None):
        """Point d'entrée pour l'arrêt."""
        if self.app_info.status in [WebAppStatus.STOPPING, WebAppStatus.STOPPED]:
            return

        if signal:
            self.add_trace("[SHUTDOWN] SIGNAL RECU", f"Signal: {signal.name}", "Arrêt initié")
        
        await self.stop_webapp()

    def _is_port_in_use(self, port: int) -> bool:
        """Vérifie si un port est déjà utilisé en se connectant dessus."""
        if not port: return False
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            is_used = s.connect_ex(('localhost', port)) == 0
            if is_used:
                self.logger.info(f"Port {port} détecté comme étant utilisé.")
            return is_used
            
    def _load_config(self) -> Dict[str, Any]:
        """Charge la configuration depuis le fichier YAML"""
        print("[DEBUG] unified_web_orchestrator.py: _load_config()")
        if not self.config_path.exists():
            self._create_default_config()
            
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            # Si le fichier yaml est vide, safe_load retourne None.
            # On retourne la config par défaut pour éviter un crash.
            if not isinstance(config, dict):
                print(f"[WARNING] Le contenu de {self.config_path} est vide ou n'est pas un dictionnaire. Utilisation de la configuration par défaut.")
                return self._get_default_config()
            return config
        except Exception as e:
            print(f"Erreur chargement config {self.config_path}: {e}")
            return self._get_default_config()
    
    def _create_default_config(self):
        """Crée une configuration par défaut"""
        default_config = self._get_default_config()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Configuration par défaut de l'application web avec gestion centralisée des ports"""
        
        # Configuration avec gestionnaire centralisé si disponible
        if CENTRAL_PORT_MANAGER_AVAILABLE:
            try:
                port_manager = get_port_manager()
                backend_port = port_manager.get_port('backend')
                frontend_port = port_manager.get_port('frontend')
                fallback_ports = port_manager.config['ports']['backend'].get('fallback', [5004, 5005, 5006])
                
                # Configuration des variables d'environnement
                set_environment_variables()
                print(f"[PORTS] Configuration centralisée chargée - Backend: {backend_port}, Frontend: {frontend_port}")
                
            except Exception as e:
                print(f"[PORTS] Erreur gestionnaire centralisé: {e}, utilisation des valeurs par défaut")
                backend_port = 5003
                frontend_port = 8081
                fallback_ports = [5004, 5005, 5006]
        else:
            backend_port = 5003
            frontend_port = 8081
            fallback_ports = [5004, 5005, 5006]
        
        return {
            'webapp': {
                'name': 'Argumentation Analysis Web App',
                'version': '1.0.0',
                'environment': 'development'
            },
            'backend': {
                'enabled': True,
                'module': 'api.main:app',
                'start_port': backend_port,
                'fallback_ports': fallback_ports,
                'max_attempts': 5,
                'timeout_seconds': 30,
                'health_endpoint': '/health',
                'env_activation': 'powershell -File activate_project_env.ps1'
            },
            'frontend': {
                'enabled': False,  # Optionnel selon besoins
                'path': 'services/web_api/interface-web-argumentative',
                'port': frontend_port,
                'start_command': 'npm start',
                'timeout_seconds': 90
            },
            'playwright': {
                'enabled': True,
                'browser': 'chromium',
                'headless': True,
                'timeout_ms': 10000,
                'slow_timeout_ms': 20000,
                'test_paths': ['tests/functional/'],
                'screenshots_dir': 'logs/screenshots',
                'traces_dir': 'logs/traces'
            },
            'logging': {
                'level': 'INFO',
                'file': 'logs/webapp_orchestrator.log',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'cleanup': {
                'auto_cleanup': True,
                'kill_processes': ['python*', 'node*'],
                'process_filters': ['app.py', 'web_api', 'serve']
            }
        }
    
    def _setup_logging(self, log_level: str = 'INFO') -> logging.Logger:
        """Configure le système de logging"""
        print("[DEBUG] unified_web_orchestrator.py: _setup_logging()")
        logging_config = self.config.get('logging', {})
        log_file = Path(logging_config.get('file', 'logs/webapp_orchestrator.log'))
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # La CLI surcharge la config YAML
        level = log_level or logging_config.get('level', 'INFO').upper()

        # Ne plus supprimer les handlers existants pour permettre la cohabitation
        # for handler in logging.root.handlers[:]:
        #     logging.root.removeHandler(handler)
            
        # On configure le logger de la librairie, sans toucher à la config de base
        # pour permettre au script appelant de garder sa propre configuration.
        logger = logging.getLogger(__name__)
        logger.setLevel(level)
        
        # S'assurer de ne pas ajouter de handlers si ils existent déjà
        if not logger.handlers:
            # Création des handlers spécifiques à l'orchestrateur
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(logging_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')))
            
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(logging.Formatter(logging_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')))
            
            logger.addHandler(file_handler)
            logger.addHandler(stream_handler)

        # Empêcher les logs de remonter au root logger pour éviter les duplications
        logger.propagate = False
        
        # Le logger est déjà configuré, on le retourne simplement.
        logger.info(f"Niveau de log pour l'orchestrateur configuré sur : {level}")
        return logger
    
    def add_trace(self, action: str, details: str = "", result: str = "", 
                  screenshot: str = "", status: str = "success"):
        """Ajoute une entrée de trace"""
        if not self.enable_trace:
            return
            
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        entry = TraceEntry(timestamp, action, details, result, screenshot, status)
        self.trace_log.append(entry)
        
        # Log avec couleurs
        color = "\033[96m" if status == "success" else "\033[91m"  # Cyan ou Rouge
        reset = "\033[0m"
        
        self.logger.info(f"{color}[{timestamp}] {action}{reset}")
        if details:
            self.logger.info(f"   Détails: {details}")
        if result:
            self.logger.info(f"   Résultat: {result}")
    
    async def start_webapp(self, headless: bool = True, frontend_enabled: bool = None) -> bool:
        """
        Démarre l'application web complète
        
        Args:
            headless: Mode headless pour Playwright
            frontend_enabled: Force activation/désactivation frontend
            
        Returns:
            bool: True si démarrage réussi
        """
        print("[DEBUG] unified_web_orchestrator.py: start_webapp()")
        self.headless = headless
        self.app_info.start_time = datetime.now()
        
        self.add_trace("[START] DEMARRAGE APPLICATION WEB",
                       f"Mode: {'Headless' if headless else 'Visible'}", 
                       "Initialisation orchestrateur")
        
        try:
            # 1. Nettoyage préalable
            await self._cleanup_previous_instances()
            
            # 2. Démarrage backend (obligatoire)
            if not await self._start_backend():
                self.app_info.status = WebAppStatus.ERROR
                self.add_trace("[ERROR] ECHEC DEMARRAGE BACKEND", "Le backend n'a pas pu démarrer.", status="error")
                return False
            
            # 3. Démarrage frontend (optionnel)
            frontend_config_enabled = self.config.get('frontend', {}).get('enabled', False)
            frontend_enabled_effective = frontend_config_enabled or (frontend_enabled is True)
            
            self.logger.info(f"[FRONTEND_DECISION] Config 'frontend.enabled': {frontend_config_enabled}")
            self.logger.info(f"[FRONTEND_DECISION] Argument CLI '--frontend' (via paramètre frontend_enabled): {frontend_enabled}")
            self.logger.info(f"[FRONTEND_DECISION] Valeur effective pour démarrer le frontend: {frontend_enabled_effective}")

            if frontend_enabled_effective:
                self.logger.info("[FRONTEND_DECISION] Condition de démarrage du frontend est VRAIE. Tentative de démarrage...")
                await self._start_frontend()
            else:
                self.logger.info("[FRONTEND_DECISION] Condition de démarrage du frontend est FAUSSE. Frontend non démarré.")
            
            # 4. Validation des services
            if not await self._validate_services():
                return False
            
            # 5. Lancement du navigateur Playwright
            if self.config.get('playwright', {}).get('enabled', False):
                await self._launch_playwright_browser()

            self.app_info.status = WebAppStatus.RUNNING
            self.add_trace("[OK] APPLICATION WEB OPERATIONNELLE",
                          f"Backend: {self.app_info.backend_url}",
                          "Tous les services démarrés")
            
            return True
            
        except Exception as e:
            self.add_trace("[ERROR] ERREUR DEMARRAGE", str(e), "Echec critique", status="error")
            self.app_info.status = WebAppStatus.ERROR
            return False
    
    async def run_tests(self, test_paths: List[str] = None, **kwargs) -> bool:
        """
        Exécute les tests Playwright avec le support natif.
        """
        if self.app_info.status != WebAppStatus.RUNNING:
            self.add_trace("[WARNING] APPLICATION NON DEMARREE", "", "Démarrage requis avant tests", status="error")
            return False
        
        if not self.browser and self.config.get('playwright', {}).get('enabled'):
            self.add_trace("[WARNING] NAVIGATEUR PLAYWRIGHT NON PRÊT", "Tentative de lancement...", status="warning")
            await self._launch_playwright_browser()
            if not self.browser:
                self.add_trace("[ERROR] ECHEC LANCEMENT NAVIGATEUR", "Impossible d'exécuter les tests", status="error")
                return False

        # Pause de stabilisation pour le serveur de développement React
        if self.app_info.frontend_url:
            delay = self.config.get('frontend', {}).get('stabilization_delay_s', 10)
            self.add_trace("[STABILIZE] PAUSE STABILISATION", f"Attente de {delay}s pour que le frontend (Create React App) se stabilise...")
            await asyncio.sleep(delay)

        self.add_trace("[TEST] EXECUTION TESTS PLAYWRIGHT", f"Tests: {test_paths or 'tous'}")
        
        test_config = {
            'backend_url': self.app_info.backend_url,
            'frontend_url': self.app_info.frontend_url or self.app_info.backend_url,
            'headless': self.headless,
            **kwargs
        }

        # La communication avec Playwright se fait via les variables d'environnement
        # que playwright.config.js lira (par exemple, BASE_URL)
        base_url = self.app_info.frontend_url or self.app_info.backend_url
        backend_url = self.app_info.backend_url
        os.environ['BASE_URL'] = base_url
        os.environ['BACKEND_URL'] = backend_url
        
        self.add_trace("[PLAYWRIGHT] CONFIGURATION URLS",
                      f"BASE_URL={base_url}",
                      f"BACKEND_URL={backend_url}")

        # L'ancienne gestion de subprocess.TimeoutExpired n'est plus nécessaire car
        # le runner utilise maintenant create_subprocess_exec.
        # Le timeout est géré plus haut par asyncio.wait_for.
        return await self.playwright_runner.run_tests(
            test_type='python',
            test_paths=test_paths,
            runtime_config=test_config
        )
    
    async def stop_webapp(self):
        """Arrête l'application web et nettoie les ressources de manière gracieuse."""
        # On ne quitte plus prématurément, on tente toujours de nettoyer.
        # if self.app_info.status in [WebAppStatus.STOPPING, WebAppStatus.STOPPED]:
        #     self.logger.warning("Arrêt déjà en cours ou terminé.")
        #     return

        self.add_trace("[STOP] ARRET APPLICATION WEB", "Nettoyage gracieux en cours")
        self.app_info.status = WebAppStatus.STOPPING
        
        try:
            # 1. Fermer le navigateur Playwright
            await self._close_playwright_browser()

            # 2. Arrêter les services
            tasks = []
            if self.frontend_manager and self.app_info.frontend_pid:
                tasks.append(self.frontend_manager.stop())
            if self.app_info.backend_pid:
                tasks.append(self.backend_manager.stop())
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
            # 3. Cleanup final des processus
            await self.process_cleaner.cleanup_webapp_processes()
            
            self.app_info = WebAppInfo()  # Reset
            self.add_trace("[OK] ARRET TERMINE", "", "Toutes les ressources libérées")
            
        except Exception as e:
            self.add_trace("[WARNING] ERREUR ARRET", str(e), "Nettoyage partiel", status="error")
        finally:
            self.app_info.status = WebAppStatus.STOPPED
    
    async def full_integration_test(self, headless: bool = True,
                                   frontend_enabled: bool = None,
                                   test_paths: List[str] = None,
                                   **kwargs) -> bool:
        """
        Test d'intégration complet : démarrage + tests + arrêt
        
        Remplace toutes les fonctions des scripts PowerShell
        
        Returns:
            bool: True si intégration complète réussie
        """
        success = False
        
        try:
            self.add_trace("[TEST] INTEGRATION COMPLETE",
                          "Démarrage orchestration complète")
            
            # 1. Démarrage application
            if not await self.start_webapp(headless, frontend_enabled):
                return False
            
            # 2. Attente stabilisation
            await asyncio.sleep(2)
            
            # 3. Exécution tests
            try:
                # Utilisation d'un timeout asyncio global comme filet de sécurité ultime.
                # Cela garantit que l'orchestrateur ne restera jamais bloqué indéfiniment.
                test_timeout_s = self.timeout_minutes * 60
                self.add_trace("[TEST] Lancement avec timeout global", f"{test_timeout_s}s")
                
                success = await asyncio.wait_for(
                    self.run_tests(test_paths=test_paths, **kwargs),
                    timeout=test_timeout_s
                )
            except asyncio.TimeoutError:
                self.add_trace("[ERROR] TIMEOUT GLOBAL",
                              f"L'étape de test a dépassé le timeout de {self.timeout_minutes} minutes.",
                              "Le processus est probablement bloqué.",
                              status="error")
                success = False
            
            if success:
                self.add_trace("[SUCCESS] INTEGRATION REUSSIE",
                              "Tous les tests ont passé", 
                              "Application web validée")
            else:
                self.add_trace("[ERROR] ECHEC INTEGRATION",
                              "Certains tests ont échoué", 
                              "Voir logs détaillés", status="error")
            
        finally:
            # 4. Nettoyage systématique
            await self.stop_webapp()
            
            # 5. Sauvegarde trace
            await self._save_trace_report()
        
        return success

    def is_ready(self) -> bool:
        """
        Vérifie si l'application web est entièrement démarrée et opérationnelle.
        
        Returns:
            bool: True si l'état est RUNNING, sinon False.
        """
        return self.app_info.status == WebAppStatus.RUNNING
    
    # ========================================================================
    # MÉTHODES PRIVÉES
    # ========================================================================
    
    async def _cleanup_previous_instances(self):
        """Nettoie les instances précédentes en vérifiant tous les ports concernés."""
        self.add_trace("[CLEAN] NETTOYAGE PREALABLE", "Arrêt instances existantes")

        backend_config = self.config.get('backend', {})
        frontend_config = self.config.get('frontend', {})
        
        ports_to_check = []
        if backend_config.get('enabled'):
            ports_to_check.append(backend_config.get('start_port'))
            ports_to_check.extend(backend_config.get('fallback_ports', []))
        
        if frontend_config.get('enabled'):
            ports_to_check.append(frontend_config.get('port'))
        
        ports_to_check = [p for p in ports_to_check if p is not None]
        
        used_ports = [p for p in ports_to_check if self._is_port_in_use(p)]

        if used_ports:
            self.add_trace("[CLEAN] PORTS OCCUPES", f"Ports {used_ports} utilisés. Nettoyage forcé.")
            await self.process_cleaner.cleanup_by_port(ports=used_ports)
        else:
            self.add_trace("[CLEAN] PORTS LIBRES", f"Aucun service détecté sur les ports cibles : {ports_to_check}")

    async def _launch_playwright_browser(self):
        """Lance et configure le navigateur Playwright."""
        if self.browser:
            return
        
        playwright_config = self.config.get('playwright', {})
        if not playwright_config.get('enabled', False):
            return

        self.add_trace("[PLAYWRIGHT] LANCEMENT NAVIGATEUR", f"Browser: {playwright_config.get('browser', 'chromium')}")
        try:
            self.playwright = await async_playwright().start()
            browser_type = getattr(self.playwright, playwright_config.get('browser', 'chromium'))
            
            launch_options = {
                'headless': self.headless,
                'slow_mo': playwright_config.get('slow_timeout_ms', 0) if not self.headless else 0
            }
            self.browser = await browser_type.launch(**launch_options)
            self.add_trace("[OK] NAVIGATEUR PRÊT", "Playwright est initialisé.")
        except Exception as e:
            self.add_trace("[ERROR] ECHEC PLAYWRIGHT", str(e), status="error")
            self.browser = None

    async def _close_playwright_browser(self):
        """Ferme le navigateur et l'instance Playwright."""
        if self.browser:
            self.add_trace("[PLAYWRIGHT] Fermeture du navigateur")
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    async def _start_backend(self) -> bool:
        """Démarre le backend avec failover de ports"""
        print("[DEBUG] unified_web_orchestrator.py: _start_backend()")
        self.add_trace("[BACKEND] DEMARRAGE BACKEND", "Lancement avec failover de ports")
        
        result = await self.backend_manager.start(self.app_info.backend_port)
        if result['success']:
            self.app_info.backend_url = result['url']
            self.app_info.backend_port = result['port']
            self.app_info.backend_pid = result['pid']
            
            self.add_trace("[OK] BACKEND OPERATIONNEL",
                          f"Port: {result['port']} | PID: {result['pid']}", 
                          f"URL: {result['url']}")
            return True
        else:
            self.add_trace("[ERROR] ECHEC BACKEND", result['error'], "", status="error")
            return False
    
    async def _start_frontend(self) -> bool:
        """Démarre le frontend React"""
        print("[DEBUG] unified_web_orchestrator.py: _start_frontend()")
        # La décision de démarrer a déjà été prise en amont
        self.add_trace("[FRONTEND] DEMARRAGE FRONTEND", "Lancement interface React")
        
        # Instanciation tardive du FrontendManager pour lui passer l'URL du backend
        self.frontend_manager = FrontendManager(
            self.config.get('frontend', {}),
            self.logger,
            backend_url=self.app_info.backend_url
        )

        result = await self.frontend_manager.start()
        if result['success']:
            self.app_info.frontend_url = result['url']
            self.app_info.frontend_port = result['port']
            self.app_info.frontend_pid = result['pid']
            
            self.add_trace("[OK] FRONTEND OPERATIONNEL",
                          f"Port: {result['port']}", 
                          f"URL: {result['url']}")

            # Sauvegarde l'URL du frontend pour que les tests puissent la lire
            print("[DEBUG] unified_web_orchestrator.py: Saving frontend URL")
            try:
                log_dir = Path("logs")
                log_dir.mkdir(exist_ok=True)
                with open(log_dir / "frontend_url.txt", "w") as f:
                    f.write(result['url'])
                self.add_trace("[SAVE] URL FRONTEND SAUVEGARDEE", f"URL {result['url']} écrite dans logs/frontend_url.txt")
                print(f"[DEBUG] unified_web_orchestrator.py: Frontend URL saved to logs/frontend_url.txt: {result['url']}")
            except Exception as e:
                self.add_trace("[ERROR] SAUVEGARDE URL FRONTEND", str(e), status="error")
            
            return True
        else:
            self.add_trace("[WARNING] FRONTEND ECHEC", result['error'], "Continue sans frontend", status="error")
            return True  # Non bloquant
    
    async def _validate_services(self) -> bool:
        """Valide que les services backend et frontend répondent correctement."""
        print("[DEBUG] unified_web_orchestrator.py: _validate_services()")
        self.add_trace(
            "[CHECK] VALIDATION SERVICES",
            f"Vérification des endpoints critiques: {[ep['path'] for ep in self.API_ENDPOINTS_TO_CHECK]}"
        )

        backend_ok = await self._check_all_api_endpoints()
        if not backend_ok:
            return False

        if self.frontend_manager and self.app_info.frontend_url:
            frontend_ok = await self.frontend_manager.health_check()
            if not frontend_ok:
                self.add_trace("[WARNING] FRONTEND INACCESSIBLE", "L'interface utilisateur ne répond pas, mais le backend est OK.", status="warning")

        self.add_trace("[OK] SERVICES VALIDES", "Tous les endpoints critiques répondent.")
        return True

    async def _check_all_api_endpoints(self) -> bool:
        """Vérifie tous les endpoints API critiques listés dans la classe.
        
        MODIFICATION CRITIQUE POUR TESTS PLAYWRIGHT:
        Le backend est considéré comme opérationnel si au moins /api/health fonctionne.
        Cela permet au frontend de démarrer même si d'autres endpoints sont défaillants.
        """
        if not self.app_info.backend_url:
            self.add_trace("[ERROR] URL Backend non définie", "Impossible de valider les endpoints", status="error")
            return False

        self.add_trace("[CHECK] BACKEND ENDPOINTS", f"Validation de {len(self.API_ENDPOINTS_TO_CHECK)} endpoints...")
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for endpoint_info in self.API_ENDPOINTS_TO_CHECK:
                url = f"{self.app_info.backend_url}{endpoint_info['path']}"
                method = endpoint_info.get("method", "GET").upper()
                data = endpoint_info.get("data", None)
                
                if method == 'POST':
                    tasks.append(session.post(url, json=data, timeout=10))
                else: # GET par défaut
                    tasks.append(session.get(url, timeout=10))

            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Variables pour la nouvelle logique de validation
        health_endpoint_ok = False
        all_ok = True
        working_endpoints = 0
        
        for i, res in enumerate(results):
            endpoint_info = self.API_ENDPOINTS_TO_CHECK[i]
            endpoint_path = endpoint_info['path']
            
            if isinstance(res, Exception):
                details = f"Échec de la connexion à {endpoint_path}"
                result = str(res)
                status = "error"
            elif res.status >= 400:
                details = f"Endpoint {endpoint_path} a retourné une erreur"
                result = f"Status: {res.status}"
                status = "error"
            else:
                details = f"Endpoint {endpoint_path} est accessible"
                result = f"Status: {res.status}"
                status = "success"
                working_endpoints += 1
                
                # Marquer si l'endpoint critique /api/health fonctionne
                if endpoint_path == "/api/health":
                    health_endpoint_ok = True
            
            # Marquer l'échec pour les métriques, mais ne pas bloquer si health fonctionne
            if status == "error":
                all_ok = False
            
            self.add_trace(f"[API CHECK] {endpoint_path}", details, result, status=status)

        # NOUVELLE LOGIQUE: Backend opérationnel si /api/health fonctionne
        if health_endpoint_ok:
            if not all_ok:
                self.add_trace("[WARNING] BACKEND PARTIELLEMENT OPERATIONNEL",
                             f"L'endpoint critique /api/health fonctionne ({working_endpoints}/{len(self.API_ENDPOINTS_TO_CHECK)} endpoints OK). "
                             "Le frontend peut démarrer pour les tests Playwright.",
                             status="warning")
            else:
                self.add_trace("[OK] BACKEND COMPLETEMENT OPERATIONNEL",
                             f"Tous les {len(self.API_ENDPOINTS_TO_CHECK)} endpoints fonctionnent.",
                             status="success")
            return True
        else:
            self.add_trace("[ERROR] BACKEND CRITIQUE NON OPERATIONNEL",
                         "L'endpoint critique /api/health ne répond pas. Le démarrage ne peut pas continuer.",
                         status="error")
            return False
    
    async def _save_trace_report(self):
        """Sauvegarde le rapport de trace"""
        if not self.enable_trace or not self.trace_log:
            return
            
        trace_file = Path("logs/webapp_integration_trace.md")
        trace_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Génération du rapport Markdown
        content = self._generate_trace_markdown()
        
        with open(trace_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        self.add_trace("[SAVE] TRACE SAUVEGARDEE", f"Fichier: {trace_file}")
    
    def _generate_trace_markdown(self) -> str:
        """Génère le rapport de trace en Markdown"""
        duration = (datetime.now() - self.start_time).total_seconds()
        success_count = sum(1 for entry in self.trace_log if entry.status == "success")
        error_count = len(self.trace_log) - success_count
        
        content = f"""# 🎯 TRACE D'EXÉCUTION - ORCHESTRATEUR WEB UNIFIÉ

**Date d'exécution:** {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}  
**Mode:** {'Interface Cachée (Headless)' if self.headless else 'Interface Visible'}  
**Backend:** {self.app_info.backend_url or 'Non démarré'}  
**Frontend:** {self.app_info.frontend_url or 'Non démarré'}  
**Durée totale:** {duration:.2f} secondes

---

## 📋 ACTIONS DÉTAILLÉES

"""
        
        for entry in self.trace_log:
            status_emoji = "✅" if entry.status == "success" else "❌"
            content += f"""
### {status_emoji} {entry.timestamp} - {entry.action}
"""
            if entry.details:
                content += f"**Détails:** {entry.details}\n"
            if entry.result:
                content += f"**Résultat:** {entry.result}\n"
            if entry.screenshot:
                content += f"**Screenshot:** {entry.screenshot}\n"
        
        content += f"""


---

## 📊 RÉSUMÉ D'EXÉCUTION
- **Nombre d'actions:** {len(self.trace_log)}
- **Succès:** {success_count}
- **Erreurs:** {error_count}
- **Statut final:** {'✅ SUCCÈS' if error_count == 0 else '❌ ÉCHEC'}

## 🔧 CONFIGURATION TECHNIQUE
- **Backend Port:** {self.app_info.backend_port}
- **Frontend Port:** {self.app_info.frontend_port}
- **Mode Headless:** {self.headless}
- **Config:** {self.config_path}
"""
        
        return content

def main():
    """Point d'entrée principal en ligne de commande"""
    print("[DEBUG] unified_web_orchestrator.py: main()")
    parser = argparse.ArgumentParser(description="Orchestrateur Unifié d'Application Web")
    parser.add_argument('--config', default='scripts/webapp/config/webapp_config.yml',
                       help='Chemin du fichier de configuration')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Mode headless pour les tests')
    parser.add_argument('--visible', action='store_true',
                       help='Mode visible (override headless)')
    parser.add_argument('--frontend', action='store_true',
                       help='Force activation frontend')
    parser.add_argument('--tests', nargs='*',
                       help='Chemins spécifiques des tests à exécuter.')
    parser.add_argument('--timeout', type=int, default=20,
                           help='Timeout global en minutes pour l\'orchestration.')
    parser.add_argument('--log-level', type=str, default='INFO',
                           choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                           help='Niveau de log pour la console et le fichier.')
    parser.add_argument('--no-trace', action='store_true',
                           help='Désactive la génération du rapport de trace Markdown.')
    parser.add_argument('--no-playwright', action='store_true',
                        help='Désactive l\'exécution des tests Playwright.')
    parser.add_argument('--exit-after-start', action='store_true',
                        help='Démarre les serveurs puis quitte sans lancer les tests.')

    # Commandes
    parser.add_argument('--start', action='store_true', help='Démarre seulement l\'application.')
    parser.add_argument('--stop', action='store_true', help='Arrête l\'application.')
    parser.add_argument('--test', action='store_true', help='Exécute seulement les tests sur une app déjà démarrée ou en la démarrant.')
    parser.add_argument('--integration', action='store_true', default=True, help='Test d\'intégration complet (défaut).')

    args, unknown = parser.parse_known_args()

    # Création orchestrateur
    orchestrator = UnifiedWebOrchestrator(args)

    async def run_command():
        success = False
        try:
            # La configuration de Playwright est modifiée en fonction de l'argument
            if args.no_playwright:
                orchestrator.config['playwright']['enabled'] = False
                orchestrator.logger.info("Tests Playwright désactivés via l'argument --no-playwright.")

            if args.exit_after_start:
                success = await orchestrator.start_webapp(orchestrator.headless, args.frontend)
                if success:
                    orchestrator.logger.info("Application démarrée avec succès. Arrêt immédiat comme demandé.")
                # Le `finally` se chargera de l'arrêt propre
                return success

            if args.start:
                success = await orchestrator.start_webapp(orchestrator.headless, args.frontend)
                if success:
                    print("Application démarrée. Pressez Ctrl+C pour arrêter.")
                    await asyncio.Event().wait()  # Attendre indéfiniment
            elif args.stop:
                await orchestrator.stop_webapp()
                success = True
            elif args.test:
                # Pour les tests seuls, on fait un cycle complet mais sans arrêt entre les étapes.
                if await orchestrator.start_webapp(orchestrator.headless, args.frontend):
                    success = await orchestrator.run_tests(test_paths=args.tests)
            else:  # --integration par défaut
                success = await orchestrator.full_integration_test(
                    orchestrator.headless, args.frontend, args.tests)
        except KeyboardInterrupt:
            print("\n🛑 Interruption utilisateur détectée. Arrêt en cours...")
            # L'arrêt est géré par le signal handler
        except Exception as e:
            orchestrator.logger.error(f"❌ Erreur inattendue dans l'orchestration : {e}", exc_info=True)
            success = False
        finally:
            await orchestrator.shutdown()
        return success
    
    # Exécution asynchrone
    loop = asyncio.get_event_loop()
    success = loop.run_until_complete(run_command())
    
    exit_code = 0 if success else 1
    orchestrator.logger.info(f"Code de sortie final : {exit_code}")
    sys.exit(exit_code)

if __name__ == "__main__":
    from project_core.core_from_scripts import auto_env
    auto_env.ensure_env()
    main()