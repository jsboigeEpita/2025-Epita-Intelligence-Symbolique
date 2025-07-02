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
import psutil

# Définir le chemin racine du projet pour les imports
# On suppose que ce script est dans un sous-répertoire de la racine.
# C'est une correction clé pour résoudre les ModuleNotFoundError.
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Imports internes (sans activation d'environnement au niveau du module)
# Le bootstrap se fera dans la fonction main()
# Import du gestionnaire centralisé des ports
try:
    from project_core.config.port_manager import get_port_manager, set_environment_variables
    CENTRAL_PORT_MANAGER_AVAILABLE = True
    from project_core.utils.shell import run_async, run_in_activated_env_async, ShellCommandError
except ImportError:
    CENTRAL_PORT_MANAGER_AVAILABLE = False
    print("[WARNING] Gestionnaire centralisé des ports non disponible, utilisation des ports par défaut")
    # Provide dummy implementations if the import fails
    class ShellCommandError(Exception): pass
    async def run_async(command, **kwargs): raise NotImplementedError("Shell utilities not found")
    async def run_in_activated_env_async(command, **kwargs): raise NotImplementedError("Shell utilities not found")

# --- DÉBUT DES CLASSES MINIMALES DE REMPLACEMENT ---

class MinimalProcessCleaner:
    def __init__(self, logger):
        self.logger = logger

    async def cleanup_webapp_processes(self, ports_to_check: List[int] = None):
        """Nettoie les instances précédentes de manière robuste."""
        self.logger.info("[CLEANER] Démarrage du nettoyage robuste des instances webapp.")
        ports_to_check = ports_to_check or []
        
        # --- Nettoyage radical basé sur le nom du processus (DÉSACTIVÉ) ---
        # Cette méthode peut causer des blocages (deadlocks) sur certaines plateformes (ex: Windows)
        # et n'est pas fiable. Le nettoyage par port est privilégié.
        self.logger.info("[CLEANER] Le nettoyage par nom de processus est désactivé. Passage au nettoyage par port.")
        
        # current_pid = os.getpid()
        # self.logger.info(f"Recherche de tous les processus 'python' et 'node' à terminer (sauf le PID actuel: {current_pid})...")
        # killed_pids = []
        # process_filters = self.config.get('cleanup', {}).get('process_filters', ['app.py', 'web_api', 'serve', 'uvicorn'])
        #
        # for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        #     try:
        #         cmdline = ' '.join(proc.info['cmdline'] or [])
        #         if any(f in cmdline for f in process_filters) and proc.info['pid'] != current_pid:
        #             p = psutil.Process(proc.info['pid'])
        #             p.kill()
        #             killed_pids.append(proc.info['pid'])
        #     except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        #         pass
        #
        # if killed_pids:
        #     self.logger.warning(f"[CLEANER] Processus terminés de force par filtre de commande: {killed_pids}")
        # else:
        #     self.logger.info("[CLEANER] Aucun processus correspondant aux filtres de commande trouvé.")

        # --- Nettoyage basé sur les ports ---
        if not ports_to_check:
            return

        max_retries = 3
        retry_delay_s = 2

        for i in range(max_retries):
            pids_on_ports = self._get_pids_on_ports(ports_to_check)
            
            if not pids_on_ports:
                self.logger.info(f"[CLEANER] Aucun processus détecté sur les ports cibles: {ports_to_check}.")
                return

            self.logger.info(f"[CLEANER] Tentative {i+1}/{max_retries}: PIDs {list(pids_on_ports.keys())} trouvés sur les ports {list(pids_on_ports.values())}. Terminaison...")
            for pid in pids_on_ports:
                try:
                    p = psutil.Process(pid)
                    p.kill()
                except psutil.NoSuchProcess:
                    pass
            
            await asyncio.sleep(retry_delay_s)

        final_pids = self._get_pids_on_ports(ports_to_check)
        if final_pids:
            self.logger.error(f"[CLEANER] ECHEC du nettoyage. PIDs {list(final_pids.keys())} occupent toujours les ports après {max_retries} tentatives.")
        else:
            self.logger.info("[CLEANER] SUCCES du nettoyage. Tous les ports cibles sont libres.")


    def _get_pids_on_ports(self, ports: List[int]) -> Dict[int, int]:
        """Retourne un dictionnaire {pid: port} pour les ports utilisés."""
        pids_map = {}
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port in ports and conn.status == psutil.CONN_LISTEN and conn.pid:
                pids_map[conn.pid] = conn.laddr.port
        return pids_map

class MinimalBackendManager:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.process: Optional[asyncio.subprocess.Process] = None
        self.port = 0
        self._log_tasks: List[asyncio.Task] = []

    async def _log_stream_continuously(self, stream: asyncio.StreamReader, stream_name: str, startup_event: asyncio.Event):
        """Lit et logue un flux en continu et signale un événement au démarrage."""
        while not stream.at_eof():
            try:
                line_bytes = await stream.readline()
                if not line_bytes:
                    break # Stream est fermé
                
                line = line_bytes.decode('utf-8', errors='ignore').strip()
                self.logger.info(f"[{stream_name}] {line}")
                
                # Vérifier si le message de démarrage est présent et si l'événement n'a pas déjà été défini
                if "Application startup complete" in line and not startup_event.is_set():
                    startup_event.set()
            except asyncio.CancelledError:
                self.logger.info(f"Tâche de logging pour {stream_name} annulée.")
                break
            except Exception as e:
                self.logger.error(f"[{stream_name}] Erreur lors de la lecture du flux: {e}")
                # Si une erreur se produit, on signale aussi l'événement pour ne pas bloquer indéfiniment.
                if not startup_event.is_set():
                    startup_event.set()
                break

    def _find_free_port(self) -> int:
        """Trouve un port TCP libre et le retourne."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', 0))
            return s.getsockname()[1]

    async def start(self, port_override=0):
        """Démarre le serveur backend et attend qu'il soit prêt."""
        self.port = port_override or self._find_free_port()
        self.logger.info(f"[BACKEND] Tentative de démarrage du backend sur le port {self.port}...")

        module_spec = self.config.get('module', 'api.main:app')
        
        command = [
            '-m', 'uvicorn', module_spec,
            '--host', '127.0.0.1',
            '--port', str(self.port)
        ]
        
        self.logger.info(f"[BACKEND] Commande de lancement: python {' '.join(command)}")

        try:
            project_root = str(Path(__file__).parent.parent.parent.resolve())
            env = os.environ.copy()

            python_path = env.get('PYTHONPATH', '')
            if project_root not in python_path:
                env['PYTHONPATH'] = f"{project_root}{os.pathsep}{python_path}"
            self.logger.info(f"[BACKEND] PYTHONPATH for subprocess: {env.get('PYTHONPATH')}")

            env['RUNNING_VIA_ENV_MANAGER'] = 'true'
            self.logger.info("[BACKEND] Injection de RUNNING_VIA_ENV_MANAGER=true pour éviter la double validation de l'environnement.")

            # Correction pour l'erreur "OMP: Error #15" sur Windows avec certaines librairies (numpy, torch)
            env['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
            self.logger.info("[BACKEND] Injection de KMP_DUPLICATE_LIB_OK=TRUE pour corriger le conflit OpenMP.")

            # Utilisation de la nouvelle fonction unifiée
            # Le nom de l'environnement est symbolique ici, car la fonction recherche .venv
            self.process = await run_in_activated_env_async(
                command=command,
                env_name="projet-is", # Nom symbolique
                env=env
            )
            self.logger.info(f"[BACKEND] Processus backend (PID: {self.process.pid}) lancé.")

            startup_event = asyncio.Event()

            # Lancer immédiatement les tâches de logging en arrière-plan
            self.log_tasks = [
                asyncio.create_task(self._log_stream_continuously(self.process.stdout, "SERVER STDOUT", startup_event)),
                asyncio.create_task(self._log_stream_continuously(self.process.stderr, "SERVER STDERR", startup_event))
            ]

            timeout_seconds = self.config.get('timeout_seconds', 30)
            
            try:
                # Attendre que l'événement de démarrage soit signalé par une des tâches de logging
                await asyncio.wait_for(startup_event.wait(), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                self.logger.error(f"[BACKEND] Timeout de {timeout_seconds}s atteint. Le serveur backend n'a pas signalé 'Application startup complete'.")
                await self.stop()
                return {'success': False, 'error': 'Timeout lors du démarrage du backend.'}

            # À ce stade, le serveur a signalé qu'il était prêt.
            self.logger.info("[BACKEND] Message de démarrage détecté. Le serveur est prêt.")
            
            url = f"http://localhost:{self.port}"
            self.logger.info(f"[BACKEND] Backend démarré et prêt sur {url}")
            return {
                'success': True,
                'url': url,
                'port': self.port,
                'pid': self.process.pid
            }

        except Exception as e:
            self.logger.error(f"[BACKEND] Erreur critique lors du lancement du processus backend: {e}", exc_info=True)
            await self.stop() # Assurer le nettoyage en cas d'erreur
            return {'success': False, 'error': str(e)}

    async def stop(self):
        if self.process and self.process.returncode is None:
            self.logger.info(f"[BACKEND] Arrêt du processus backend (PID: {self.process.pid})...")
            
            # Annuler les tâches de logging
            for task in self._log_tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*self._log_tasks, return_exceptions=True)
            self._log_tasks = []

            try:
                # Terminer le processus principal
                if self.process.returncode is None:
                    self.process.terminate()
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                self.logger.info(f"[BACKEND] Processus backend (PID: {self.process.pid}) arrêté.")
            except asyncio.TimeoutError:
                self.logger.warning(f"[BACKEND] Le processus backend (PID: {self.process.pid}) n'a pas répondu à terminate. Utilisation de kill.")
                if self.process.returncode is None:
                    self.process.kill()
                    await self.process.wait()
        self.process = None


class MinimalFrontendManager:
    def __init__(self, config, logger, backend_url=None):
        self.config = config
        self.logger = logger
        self.backend_url = backend_url
        self.process: Optional[asyncio.subprocess.Process] = None

    async def start(self):
        """Démarre le serveur de développement frontend."""
        if not self.config.get('enabled', False):
            return {'success': True, 'error': 'Frontend disabled in config.'}

        path = self.config.get('path')
        if not path or not Path(path).exists():
            self.logger.error(f"[FRONTEND] Chemin '{path}' non valide ou non trouvé.")
            return {'success': False, 'error': f"Path not found: {path}"}
        
        port = self.config.get('port', 3000)
        start_command_str = self.config.get('start_command', 'npm start')
        # Sur Windows, il est plus robuste d'appeler npm.cmd directement
        if sys.platform == "win32":
            start_command_str = start_command_str.replace("npm", "npm.cmd", 1)
        
        conda_env_name = os.environ.get('CONDA_DEFAULT_ENV', 'projet-is')
        self.logger.info(f"[FRONTEND] Utilisation de l'environnement Conda '{conda_env_name}' pour le démarrage.")
    
        start_command = start_command_str.split()
        
        self.logger.info(f"[FRONTEND] Tentative de démarrage du frontend dans '{path}' sur le port {port}...")
        self.logger.info(f"[FRONTEND] Commande de lancement: {' '.join(start_command)}")

        # Préparation de l'environnement pour le processus frontend
        env = os.environ.copy()
        env['BROWSER'] = 'none' # Empêche l'ouverture d'un nouvel onglet
        env['PORT'] = str(port)
        if self.backend_url:
            env['REACT_APP_BACKEND_URL'] = self.backend_url
            self.logger.info(f"[FRONTEND] Variable d'environnement REACT_APP_BACKEND_URL définie sur: {self.backend_url}")

        try:
            # Utilisation de la nouvelle fonction unifiée `run_async` avec l'environnement corrigé
            self.process = await run_async(
                command=start_command,
                cwd=path,
                env=env
            )
            self.logger.info(f"[FRONTEND] Processus frontend (PID: {self.process.pid}) lancé.")

            timeout_seconds = self.config.get('timeout_seconds', 90)
            
            try:
                startup_event = asyncio.Event()
                output_lines = []

                async def log_stream_and_set_event(stream, stream_name):
                    while not stream.at_eof():
                        line_bytes = await stream.readline()
                        if not line_bytes:
                            break
                        line = line_bytes.decode('utf-8', errors='ignore').strip()
                        output_lines.append(f"[{stream_name}] {line}")
                        self.logger.info(f"[FRONTEND_LOG] {line}")
                        if ("Compiled successfully!" in line or "Compiled with warnings" in line) and not startup_event.is_set():
                            startup_event.set()

                # Lancer les tâches de logging en arrière-plan
                log_tasks = [
                    asyncio.create_task(log_stream_and_set_event(self.process.stdout, "STDOUT")),
                    asyncio.create_task(log_stream_and_set_event(self.process.stderr, "STDERR"))
                ]

                # Attendre l'événement de démarrage ou le timeout
                await asyncio.wait_for(startup_event.wait(), timeout=timeout_seconds)

                # Annuler les tâches de logging après le démarrage pour ne pas consommer de ressources
                for task in log_tasks:
                    task.cancel()
                await asyncio.gather(*log_tasks, return_exceptions=True)

            except asyncio.TimeoutError:
                log_output = "\n".join(output_lines)
                self.logger.error(f"[FRONTEND] Timeout de {timeout_seconds}s atteint. Le serveur n'a pas signalé son démarrage. Logs:\n{log_output}")
                await self.stop()
                return {'success': False, 'error': 'Timeout lors du démarrage du frontend.'}

            url = f"http://localhost:{port}"
            self.logger.info(f"[FRONTEND] Frontend démarré et prêt sur {url}")
            return {'success': True, 'url': url, 'port': port, 'pid': self.process.pid}

        except Exception as e:
            self.logger.error(f"[FRONTEND] Erreur critique lors du lancement du processus frontend: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    async def stop(self):
         if self.process and self.process.returncode is None:
            self.logger.info(f"[FRONTEND] Arrêt du processus frontend (PID: {self.process.pid})...")
            # La logique d'arrêt pour `npm` peut être complexe car il lance des enfants.
            # On utilise psutil pour tuer l'arbre de processus.
            if not self.process: return
            try:
                parent = psutil.Process(self.process.pid)
                children = parent.children(recursive=True)
                for child in children:
                    self.logger.info(f"[FRONTEND] Arrêt du processus enfant (PID: {child.pid})...")
                    child.kill()
                self.logger.info(f"[FRONTEND] Arrêt du processus parent (PID: {parent.pid})...")
                parent.kill()
                # Attendre que le processus principal soit bien terminé
                await asyncio.wait_for(self.process.wait(), timeout=10.0)
                self.logger.info(f"[FRONTEND] Processus frontend (PID: {self.process.pid}) et ses enfants ({len(children)}) arrêtés.")
            except (psutil.NoSuchProcess, asyncio.TimeoutError) as e:
                self.logger.error(f"[FRONTEND] Erreur lors de l'arrêt du processus frontend (PID: {self.process.pid}): {e}")
                # En dernier recours, on fait un kill simple si le processus existe encore
                if self.process and self.process.returncode is None:
                    self.process.kill()
                    await self.process.wait()
            finally:
                self.process = None

    async def health_check(self) -> bool:
        """Vérifie si le serveur frontend répond."""
        url = f"http://localhost:{self.config.get('port', 3000)}"
        self.logger.info(f"[FRONTEND] Health Check sur {url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    return response.status == 200
        except aiohttp.ClientError as e:
            self.logger.warning(f"[FRONTEND] Health check a échoué: {e}")
            return False

# --- FIN DES CLASSES MINIMALES DE REMPLACEMENT ---


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
        self.backend_manager = MinimalBackendManager(self.config.get('backend', {}), self.logger)
        self.frontend_manager: Optional[MinimalFrontendManager] = None  # Sera instancié plus tard

        playwright_config = self.config.get('playwright', {})
        # Le timeout CLI surcharge la config YAML
        playwright_config['timeout_ms'] = self.timeout_minutes * 60 * 1000

        # self.playwright_runner = PlaywrightRunner(playwright_config, self.logger)
        self.process_cleaner = MinimalProcessCleaner(self.logger)
        self.process_cleaner.config = self.config # Injection de la config au moment de l'initialisation

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
            
    def _deep_merge_dicts(self, base: dict, new: dict) -> dict:
        """Fusionne récursivement deux dictionnaires."""
        merged = base.copy()
        for key, value in new.items():
            if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                merged[key] = self._deep_merge_dicts(merged[key], value)
            else:
                merged[key] = value
        return merged

    def _load_config(self) -> Dict[str, Any]:
        """Charge la configuration depuis le fichier YAML et la fusionne avec les valeurs par défaut."""
        print("[DEBUG] unified_web_orchestrator.py: _load_config()")
        
        default_config = self._get_default_config()

        if not self.config_path.exists():
            # Utilise le logger ici, qui est déjà initialisé via self.config (un dictionnaire vide au début)
            # mais qui sera reconfiguré plus tard.
            print(f"INFO: Le fichier de configuration '{self.config_path}' n'existe pas. Création avec les valeurs par défaut.")
            self._create_default_config()
            return default_config

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)

            if not isinstance(user_config, dict):
                print(f"WARNING: Le contenu de {self.config_path} est vide ou invalide. Utilisation de la configuration par défaut.")
                return default_config
            
            # Fusionner la config utilisateur sur la config par défaut
            merged_config = self._deep_merge_dicts(default_config, user_config)
            print("INFO: Configuration utilisateur chargée et fusionnée avec les valeurs par défaut.")
            return merged_config

        except Exception as e:
            print(f"ERROR: Erreur lors du chargement de la configuration {self.config_path}: {e}. Utilisation de la configuration par défaut.")
            return self._get_default_config()
    
        def _deep_merge_dicts(self, base_dict: Dict, new_dict: Dict) -> Dict:
            """Fusionne récursivement deux dictionnaires."""
            merged = base_dict.copy()
            for key, value in new_dict.items():
                if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key] = self._deep_merge_dicts(merged[key], value)
                else:
                    merged[key] = value
            return merged
    
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
                # 'module' et 'server_type' ne sont plus nécessaires car on utilise command_list
                # On les garde pour la clarté mais ils ne seront pas utilisés par le backend_manager.
                'module': 'api.main:app',
                'server_type': 'uvicorn',

                'start_port': backend_port,
                'fallback_ports': fallback_ports,
                'max_attempts': 5,
                'timeout_seconds': 180, # Timeout long pour le 1er démarrage
                'health_endpoint': '/api/health',

                # La solution robuste: on passe une commande complète qui peut être exécutée
                # directement par le système sans dépendre d'un PATH spécifique.
                # On utilise "powershell.exe -Command" pour chaîner l'activation et l'exécution.
                # Cette clé n'est plus utilisée par la nouvelle logique, mais conservée pour référence.
                'command_list': [
                    "echo",
                    "Cette commande est obsolète et remplacée par la détection automatique du chemin python."
                ]
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
            
            # Sauvegarder les URLs pour les processus externes
            self._save_urls_to_file()
            
            return True
            
        except Exception as e:
            self.add_trace("[ERROR] ERREUR DEMARRAGE", str(e), "Echec critique", status="error")
            self.app_info.status = WebAppStatus.ERROR
            return False
    
    async def run_tests(self, test_paths: List[str] = None, **kwargs) -> bool:
        """
        Exécute les tests du projet (fonctionnels, E2E) via pytest dans l'environnement Conda.
        """
        # On utilise le même flag de configuration pour activer/désactiver les tests.
        if not self.config.get('playwright', {}).get('enabled', False):
            self.add_trace("[INFO] TESTS DESACTIVES", "Les tests sont désactivés dans la configuration ('playwright.enabled: false').", "Tests non exécutés")
            return True

        # Les tests d'intégration nécessitent que l'application soit démarrée.
        if self.app_info.status != WebAppStatus.RUNNING:
            self.add_trace("[WARNING] APPLICATION NON DEMARREE", "L'application doit être démarrée pour lancer les tests d'intégration.", "Démarrage requis avant tests", status="error")
            return False
            
        # Configuration des variables d'environnement pour les tests
        base_url = self.app_info.frontend_url or self.app_info.backend_url
        backend_url = self.app_info.backend_url
        if base_url:
            os.environ['BASE_URL'] = base_url
        if backend_url:
            os.environ['BACKEND_URL'] = backend_url
        
        self.add_trace("[TEST] CONFIGURATION URLS",
                      f"BASE_URL={os.environ.get('BASE_URL')}",
                      f"BACKEND_URL={os.environ.get('BACKEND_URL')}")

        self.add_trace("[TEST] LANCEMENT DES TESTS PYTEST", f"Tests: {test_paths or 'tous'}")

        import shlex
        conda_env_name = os.environ.get('CONDA_ENV_NAME', self.config.get('backend', {}).get('conda_env', 'projet-is'))
        
        self.logger.info(f"Construction de la commande de test directe pour l'environnement '{conda_env_name}'.")

        # On utilise directement l'exécutable python courant,
        # car ce script est déjà lancé dans le bon environnement Conda.
        python_executable = sys.executable
        self.logger.info(f"Utilisation de l'exécutable Python de l'environnement courant : {python_executable}")

        command = [
            python_executable,
            "-m", "pytest"
        ]
        if test_paths:
            command.extend(test_paths)

        self.add_trace("[TEST] COMMANDE", " ".join(command))
        
        try:
            # Remplacer par run_async
            process = await run_async(command)

            # Log en temps réel
            async def log_stream(stream, logger_func):
                while not stream.at_eof():
                    line = await stream.readline()
                    if line:
                        logger_func(line.decode('utf-8', errors='ignore').strip())

            # Le 'self.logger.info' pour stdout et 'self.logger.error' pour stderr
            # permet une distinction claire dans les logs.
            await asyncio.gather(
                log_stream(process.stdout, self.logger.info),
                log_stream(process.stderr, self.logger.error)
            )

            return_code = await process.wait()

            if return_code == 0:
                self.add_trace("[TEST] SUCCES", f"Pytest a terminé avec succès (code {return_code}).", "Tests passés")
                return True
            else:
                error_message = f"Pytest a échoué avec le code de sortie {return_code}."
                self.add_trace("[TEST] ECHEC", error_message, status="error")
                # On lève une exception pour que le pipeline d'intégration échoue
                raise subprocess.CalledProcessError(return_code, command, "La sortie est dans les logs ci-dessus.")

        except FileNotFoundError:
            error_msg = "La commande 'conda' est introuvable. Assurez-vous que Conda est installé et configuré dans le PATH de l'environnement."
            self.add_trace("[ERROR] COMMANDE INTROUVABLE", error_msg, status="error")
            raise Exception(error_msg)
        except subprocess.CalledProcessError as e:
            # Cette exception a déjà été tracée, on la relance pour que le pipeline échoue.
            self.logger.error(f"L'exécution des tests a échoué. Voir les logs pour la sortie de pytest.")
            raise e
        except Exception as e:
            self.add_trace("[ERROR] ERREUR INATTENDUE TESTS", str(e), status="error")
            self.logger.error(f"Une erreur inattendue est survenue pendant l'exécution des tests: {e}", exc_info=True)
            raise e
    
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
            # La logique de nettoyage est maintenant plus robuste même si la config est vide
            backend_config = self.config.get('backend', {})
            frontend_config = self.config.get('frontend', {})
            
            ports_to_check = []
            if backend_config.get('enabled'):
                start_port = backend_config.get('start_port')
                if start_port: ports_to_check.append(start_port)
                fallback_ports = backend_config.get('fallback_ports')
                if fallback_ports: ports_to_check.extend(fallback_ports)
            if frontend_config.get('enabled'):
                frontend_port = frontend_config.get('port')
                if frontend_port: ports_to_check.append(frontend_port)
            ports_to_check = [p for p in ports_to_check if p is not None]

            await self.process_cleaner.cleanup_webapp_processes(ports_to_check=ports_to_check)
            
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
                
                try:
                    success = await asyncio.wait_for(
                        self.run_tests(test_paths=test_paths, **kwargs),
                        timeout=test_timeout_s # Utiliser le timeout défini
                    )
                except (subprocess.CalledProcessError, Exception) as e:
                    # Gère les échecs de tests (qui lèvent une exception) et autres erreurs
                    self.add_trace("[ERROR] ECHEC TESTS", f"Les tests ont échoué: {e}", status="error")
                    success = False
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
        """Nettoie les instances précédentes en utilisant le cleaner centralisé."""
        self.add_trace("[CLEAN] NETTOYAGE PREALABLE", "Arrêt robuste des instances existantes via ProcessCleaner")

        # Je dois injecter la config dans le cleaner car il en a besoin
        # L'injection de la config se fait maintenant dans le __init__
        pass

        backend_config = self.config.get('backend', {})
        frontend_config = self.config.get('frontend', {})
        
        ports_to_check = []
        if backend_config.get('enabled'):
            start_port = backend_config.get('start_port')
            if start_port: ports_to_check.append(start_port)
            
            fallback_ports = backend_config.get('fallback_ports')
            if fallback_ports: ports_to_check.extend(fallback_ports)

        if frontend_config.get('enabled'):
            frontend_port = frontend_config.get('port')
            if frontend_port: ports_to_check.append(frontend_port)

        ports_to_check = [p for p in ports_to_check if p is not None]
        
        # On passe la main au cleaner centralisé
        await self.process_cleaner.cleanup_webapp_processes(ports_to_check=ports_to_check)
        self.add_trace("[OK] NETTOYAGE PREALABLE TERMINE", f"Ports vérifiés: {ports_to_check}")

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

        # --- Etape 1: Lancement du backend ---
        self.add_trace("[BACKEND] Démarrage...", "Le setup des libs Java est maintenant géré en amont.")
        
        # Forcer le port dynamique pour éviter les conflits
        backend_config = self.config.get('backend', {})
        start_port = backend_config.get('start_port', 0)
        self.logger.info(f"Démarage du backend avec le port de la configuration: {start_port}")

        result = await self.backend_manager.start(port_override=start_port)
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
        self.frontend_manager = MinimalFrontendManager(
            self.config.get('frontend', {}),
            self.logger,
            backend_url=self.app_info.backend_url
        )

        result = await self.frontend_manager.start()
        if result and result.get('success'):
            self.app_info.frontend_url = result.get('url')
            self.app_info.frontend_port = result.get('port')
            self.app_info.frontend_pid = result.get('pid')
            
            # Vérifier que les valeurs existent avant de les utiliser
            if self.app_info.frontend_url and self.app_info.frontend_port:
                self.add_trace("[OK] FRONTEND OPERATIONNEL",
                              f"Port: {self.app_info.frontend_port}",
                              f"URL: {self.app_info.frontend_url}")

                # Sauvegarde l'URL du frontend pour que les tests puissent la lire
                print("[DEBUG] unified_web_orchestrator.py: Saving frontend URL")
                # La communication de l'URL se fait maintenant via les variables d'environnement
                # et la sortie standard de l'orchestrateur. Le fichier n'est plus nécessaire.
                self.add_trace("[INFO] URL FRONTEND DISPONIBLE", f"URL: {self.app_info.frontend_url}", status="success")
                # Afficher l-URL sur la sortie standard pour que les scripts externes puissent la capturer.
                print(f"FRONTEND_URL_READY={self.app_info.frontend_url}")
            
            return True
        else:
            error_details = result.get('error', 'Erreur inconnue') if isinstance(result, dict) else 'Résultat inattendu'
            self.add_trace("[WARNING] FRONTEND ECHEC", error_details, "Continue sans frontend", status="error")
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

    def _save_urls_to_file(self):
        """Sauvegarde les URLs des services dans un fichier temporaire pour les scripts externes."""
        project_root = Path(__file__).parent.parent.parent.resolve()
        temp_dir = project_root / "_temp"
        temp_dir.mkdir(exist_ok=True)
        urls_file = temp_dir / "service_urls.json"

        urls_data = {
            "backend_url": self.app_info.backend_url,
            "frontend_url": self.app_info.frontend_url,
        }
        
        try:
            with open(urls_file, 'w', encoding='utf-8') as f:
                json.dump(urls_data, f, indent=4)
            self.logger.info(f"[INFO] URLs des services sauvegardées dans {urls_file}")
        except Exception as e:
            self.logger.error(f"[ERROR] Impossible de sauvegarder les URLs dans {urls_file}: {e}")

def main():
    """Point d'entrée principal en ligne de commande"""
    print("[DEBUG] unified_web_orchestrator.py: main()")
    parser = argparse.ArgumentParser(description="Orchestrateur Unifié d'Application Web")
    parser.add_argument('--config', default='argumentation_analysis/webapp/config/webapp_config.yml',
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
                    # On s'assure que les URLs sont écrites même avec --exit-after-start
                    orchestrator._save_urls_to_file()
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
            # Ne pas arrêter les serveurs si on veut juste les laisser tourner
            if not args.exit_after_start:
                await orchestrator.shutdown()
        return success
    
    # Exécution asynchrone
    loop = asyncio.get_event_loop()
    success = loop.run_until_complete(run_command())
    
    exit_code = 0 if success else 1
    orchestrator.logger.info(f"Code de sortie final : {exit_code}")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()