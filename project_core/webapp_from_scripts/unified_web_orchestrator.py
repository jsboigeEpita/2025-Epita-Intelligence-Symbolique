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
import shutil # Ajout pour shutil.which
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
        # Récupérer le chemin de l'environnement Conda avant d'initialiser BackendManager
        self.conda_env_name = self.config.get('backend', {}).get('conda_env', 'projet-is')
        self.conda_env_path = self._find_conda_env_path(self.conda_env_name)

        self.backend_manager = BackendManager(
            self.config.get('backend', {}),
            self.logger,
            conda_env_path=self.conda_env_path # Passer le chemin ici
        )
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
                return yaml.safe_load(f)
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
                'module': 'argumentation_analysis.services.web_api.app:app',
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
                'test_type': 'python',  # Type de test par défaut
                'browser': 'chromium',
                'headless': True,
                'timeout_ms': 30000,
                'process_timeout_s': 600,
                'test_paths': {
                    'python': ['tests/e2e/python/'],
                    'javascript': ['tests/e2e/js/'],
                    'demos': ['tests/e2e/demos/']
                },
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

        # Supprimer les handlers existants pour éviter les logs dupliqués
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
            
        logging.basicConfig(
            level=level,
            format=logging_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logger = logging.getLogger(__name__)
        logger.info(f"Niveau de log configuré sur : {level}")
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
            frontend_enabled_effective = frontend_enabled if frontend_enabled is not None else frontend_config_enabled
            
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
    
    async def run_tests(self, test_type: str = None, test_paths: List[str] = None, **kwargs) -> bool:
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

        # Le test_type est passé en priorité, sinon celui de la config
        effective_test_type = test_type or self.playwright_runner.test_type

        # Si les chemins ne sont pas fournis, utiliser ceux par défaut pour le type de test
        paths_for_type = self.config.get('playwright', {}).get('test_paths', {})
        effective_paths = test_paths or paths_for_type.get(effective_test_type)

        return await self.playwright_runner.run_tests(
            test_type=effective_test_type,
            test_paths=effective_paths,
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
                                   test_type: str = None,
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
            test_success = False
            try:
                # Utilisation d'un timeout asyncio global comme filet de sécurité ultime.
                test_timeout_s = self.timeout_minutes * 60
                self.add_trace("[TEST] Lancement avec timeout global", f"{test_timeout_s}s")

                test_success = await asyncio.wait_for(
                    self.run_tests(test_type=test_type, test_paths=test_paths, **kwargs),
                    timeout=test_timeout_s
                )
            except asyncio.TimeoutError:
                self.add_trace("[ERROR] TIMEOUT GLOBAL",
                              f"L'étape de test a dépassé le timeout de {self.timeout_minutes} minutes.",
                              "Le processus est probablement bloqué.",
                              status="error")
                test_success = False

            # 4. Analyse des traces Playwright JS après l'exécution
            # Cette étape est exécutée même si les tests échouent pour fournir un rapport de débogage.
            effective_test_type = test_type or self.playwright_runner.test_type
            if effective_test_type == 'javascript':
                await self._analyze_playwright_traces()

            if test_success:
                self.add_trace("[SUCCESS] INTEGRATION REUSSIE",
                              "Tous les tests ont passé",
                              "Application web validée")
            else:
                self.add_trace("[ERROR] ECHEC INTEGRATION",
                              "Certains tests ont échoué",
                              "Voir logs détaillés", status="error")
            
            success = test_success # Le succès global dépend de la réussite des tests

        finally:
            # 5. Nettoyage systématique
            await self.stop_webapp()

            # 6. Sauvegarde trace
            await self._save_trace_report()

        return success

    def _find_conda_env_path(self, env_name: str) -> Optional[str]:
        """Trouve le chemin complet d'un environnement Conda."""
        self.logger.debug(f"Recherche du chemin pour l'environnement Conda: {env_name}")
        conda_exe = shutil.which("conda")
        if not conda_exe:
            self.logger.error("Exécutable Conda non trouvé avec shutil.which.")
            return None
        
        try:
            result = subprocess.run(
                [conda_exe, "env", "list", "--json"],
                capture_output=True, text=True, check=True, encoding='utf-8'
            )
            envs_data = json.loads(result.stdout)
            for env_path_str in envs_data.get("envs", []):
                if Path(env_path_str).name == env_name:
                    self.logger.info(f"Chemin de l'environnement Conda '{env_name}' trouvé: {env_path_str}")
                    return str(env_path_str)
            self.logger.error(f"Environnement Conda '{env_name}' non trouvé dans la liste.")
            return None
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Erreur lors de l'exécution de 'conda env list --json': {e}")
            self.logger.error(f"Stderr: {e.stderr}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Erreur de décodage JSON pour 'conda env list --json': {e}")
            return None
        except Exception as e:
            self.logger.error(f"Erreur inattendue dans _find_conda_env_path: {e}")
            return None

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
        
        result = await self.backend_manager.start_with_failover()
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
            # Assigner les URLs et ports
            if result['url']: # Cas serveur de dev
                self.app_info.frontend_url = result['url']
                self.app_info.frontend_port = result['port']
                self.app_info.frontend_pid = result['pid']
                self.add_trace("[OK] FRONTEND (DEV SERVER) OPERATIONNEL", f"URL: {result['url']}")
            else: # Cas statique servi par le backend
                self.app_info.frontend_url = self.app_info.backend_url
                self.app_info.frontend_port = self.app_info.backend_port
                self.add_trace("[OK] FRONTEND (STATIQUE) PRÊT", f"Servi par backend: {self.app_info.frontend_url}")

            # Écrire l'URL du frontend dans tous les cas pour signaler au script parent
            # self.app_info.frontend_url aura toujours une valeur ici.
            try:
                log_dir = Path("logs")
                log_dir.mkdir(exist_ok=True)
                url_to_write = self.app_info.frontend_url
                with open(log_dir / "frontend_url.txt", "w", encoding='utf-8') as f:
                    f.write(url_to_write)
                self.add_trace("[SYNC] FICHIER URL ECRIT", f"Fichier: logs/frontend_url.txt, URL: {url_to_write}")
            except Exception as e:
                self.add_trace("[ERROR] ECRITURE FICHIER URL", str(e), status="error")
            
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

    async def _analyze_playwright_traces(self):
        """Lance l'analyseur de traces en tant que sous-processus et logue le résultat."""
        self.add_trace("[ANALYZE] ANALYSE DES TRACES PLAYWRIGHT", "Lancement du script trace_analyzer.py")
        analyzer_script_path = "services/web_api/trace_analyzer.py"
        
        # Le répertoire de traces pour Playwright JS est défini dans sa config
        # et est relatif au répertoire de test, donc 'tests/e2e/test-results/'
        # Playwright génère un dossier par test qui contient 'trace.zip'
        # Le trace_analyzer.py doit être adapté pour chercher ces .zip, les extraire, et lire le contenu.
        # Pour l'instant, on pointe vers le dossier où Playwright génère ses rapports
        # La refactorisation du trace_analyzer est une tâche future
        trace_dir = Path("tests/e2e/test-results/")

        if not Path(analyzer_script_path).exists():
            self.add_trace("[ERROR] Script d'analyse non trouvé", f"Chemin: {analyzer_script_path}", status="error")
            return
            
        try:
            # Utiliser le même interpréteur Python que celui qui exécute l'orchestrateur
            python_executable = sys.executable
            
            command_to_run = [
                python_executable,
                analyzer_script_path,
                '--mode=summary',
                # On passe le répertoire où sont générés les rapports Playwright
                '--trace-dir', str(trace_dir)
            ]

            self.logger.debug(f"Lancement de l'analyseur de trace avec la commande : {' '.join(command_to_run)}")
            
            proc = await asyncio.create_subprocess_exec(
                *command_to_run,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            stdout_str = stdout.decode('utf-8', errors='ignore')
            stderr_str = stderr.decode('utf-8', errors='ignore')
            
            if proc.returncode == 0:
                self.add_trace("[OK] ANALYSE DE TRACE TERMINÉE", "Détails ci-dessous")
                # Loggue le résumé directement dans la trace de l'orchestrateur
                self.logger.info("\n--- DEBUT RAPPORT D'ANALYSE DE TRACE ---\n"
                                f"{stdout_str}"
                                "\n--- FIN RAPPORT D'ANALYSE DE TRACE ---")
            else:
                self.add_trace("[ERROR] ECHEC ANALYSE DE TRACE", "Le script a retourné une erreur.", status="error")
                self.logger.error(f"Erreur lors de l'exécution de {analyzer_script_path}:")
                self.logger.error("STDOUT:\n" + stdout_str)
                self.logger.error("STDERR:\n" + stderr_str)
                
        except Exception as e:
            self.add_trace("[ERROR] ERREUR CRITIQUE ANALYSEUR", str(e), status="error")


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
    parser.add_argument('--test-type', type=str,
                       choices=['python', 'javascript', 'demos'],
                       help='Type de tests à exécuter (python, javascript, demos).')
    parser.add_argument('--timeout', type=int, default=20,
                           help="Timeout global en minutes pour l'orchestration.")
    parser.add_argument('--log-level', type=str, default='INFO',
                           choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                           help='Niveau de log pour la console et le fichier.')
    parser.add_argument('--no-trace', action='store_true',
                           help='Désactive la génération du rapport de trace Markdown.')
    parser.add_argument('--no-playwright', action='store_true',
                        help="Désactive l'exécution des tests Playwright.")
    parser.add_argument('--exit-after-start', action='store_true',
                        help='Démarre les serveurs puis quitte sans lancer les tests.')

    # Commandes
    parser.add_argument('--start', action='store_true', help="Démarre seulement l'application.")
    parser.add_argument('--stop', action='store_true', help="Arrête l'application.")
    parser.add_argument('--test', action='store_true', help="Exécute seulement les tests sur une app déjà démarrée ou en la démarrant.")
    parser.add_argument('--integration', action='store_true', default=True, help="Test d'intégration complet (défaut).")

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
                    success = await orchestrator.run_tests(test_type=args.test_type, test_paths=args.tests)
            else:  # --integration par défaut
                success = await orchestrator.full_integration_test(
                    orchestrator.headless, args.frontend, args.test_type, args.tests)
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

    async def _analyze_playwright_traces(self):
        """Lance l'analyseur de traces en tant que sous-processus et logue le résultat."""
        self.add_trace("[ANALYZE] ANALYSE DES TRACES PLAYWRIGHT", "Lancement du script trace_analyzer.py")
        analyzer_script_path = "services/web_api/trace_analyzer.py"
        
        if not Path(analyzer_script_path).exists():
            self.add_trace("[ERROR] Script d'analyse non trouvé", f"Chemin: {analyzer_script_path}", status="error")
            return
            
        try:
            # Utiliser le même interpréteur Python que celui qui exécute l'orchestrateur
            python_executable = sys.executable
            
            self.logger.debug(f"Lancement de l'analyseur de trace avec la commande : {[python_executable, analyzer_script_path, '--mode=summary']}")
            
            proc = await asyncio.create_subprocess_exec(
                python_executable, analyzer_script_path, '--mode=summary',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            # Décoder la sortie
            stdout_str = stdout.decode('utf-8', errors='ignore')
            stderr_str = stderr.decode('utf-8', errors='ignore')
            
            if proc.returncode == 0:
                self.add_trace("[OK] ANALYSE DE TRACE TERMINÉE", "Détails ci-dessous")
                # Loggue le résumé directement dans la trace de l'orchestrateur
                self.logger.info("\n--- DEBUT RAPPORT D'ANALYSE DE TRACE ---\n"
                                f"{stdout_str}"
                                "\n--- FIN RAPPORT D'ANALYSE DE TRACE ---")
            else:
                self.add_trace("[ERROR] ECHEC ANALYSE DE TRACE", "Le script a retourné une erreur.", status="error")
                self.logger.error("Erreur lors de l'exécution de trace_analyzer.py:")
                self.logger.error("STDOUT:\n" + stdout_str)
                self.logger.error("STDERR:\n" + stderr_str)
                
        except Exception as e:
            self.add_trace("[ERROR] ERREUR CRITIQUE ANALYSEUR", str(e), status="error")

if __name__ == "__main__":
    from project_core.core_from_scripts import auto_env
    auto_env.ensure_env()
    main()