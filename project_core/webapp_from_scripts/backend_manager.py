#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backend Manager - Gestionnaire du backend Flask avec failover
=============================================================

Gère le démarrage, l'arrêt et la surveillance du backend Flask
avec système de failover de ports automatique.

Auteur: Projet Intelligence Symbolique EPITA
Date: 07/06/2025
"""

import os
import sys
import time
import json
import asyncio
import logging
import subprocess
import psutil
from typing import Dict, List, Optional, Any
from pathlib import Path
import aiohttp
import shutil
import shlex

# Import pour la gestion des dépendances Tweety
from project_core.setup_core_from_scripts.manage_tweety_libs import download_tweety_jars

from dotenv import load_dotenv, find_dotenv

class BackendManager:
    """
    Gestionnaire du backend Flask avec failover de ports
    
    Fonctionnalités :
    - Démarrage avec activation environnement conda
    - Failover automatique sur plusieurs ports  
    - Health check des endpoints
    - Monitoring des processus
    - Arrêt propre avec cleanup
    """
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger, conda_env_path: Optional[str] = None, env: Optional[Dict[str, str]] = None):
        self.config = config
        self.logger = logger
        self.conda_env_path = conda_env_path
        self.env = env
        
        # Configuration par défaut
        self.module = config.get('module', 'argumentation_analysis.services.web_api.app')
        self.start_port = config.get('start_port', 5003)  # Peut servir de fallback si non défini dans l'env
        self.fallback_ports = config.get('fallback_ports', []) # La logique de fallback est déplacée vers l'orchestrateur
        self.max_attempts = config.get('max_attempts', 1)  # Normalement, une seule tentative sur le port fourni
        self.timeout_seconds = config.get('timeout_seconds', 180) # Augmenté à 180s pour le téléchargement du modèle
        self.health_endpoint = config.get('health_endpoint', '/api/health')
        self.health_check_timeout = config.get('health_check_timeout', 60) # Timeout pour chaque tentative de health check
        self.env_activation = config.get('env_activation',
                                       'powershell -File scripts/env/activate_project_env.ps1')
        
        # État runtime
        self.process: Optional[asyncio.subprocess.Process] = None
        self.current_port: Optional[int] = None
        self.current_url: Optional[str] = None
        self.pid: Optional[int] = None
        
    async def start(self, port_override: Optional[int] = None) -> Dict[str, Any]:
        """Démarre le backend en utilisant l'environnement et le port fournis."""
        try:
            # Déterminer l'environnement à utiliser
            if self.env:
                effective_env = self.env
                self.logger.info("Utilisation de l'environnement personnalisé fourni par l'orchestrateur.")
            else:
                effective_env = os.environ.copy()
                self.logger.info("Aucun environnement personnalisé fourni, utilisation de l'environnement système.")

            # Déterminer le port : priorité au port surchargé par l'appel
            port_to_use = port_override if port_override is not None else self.start_port
            effective_env['FLASK_RUN_PORT'] = str(port_to_use)
            self.current_port = port_to_use
            
            self.logger.info(f"Tentative de démarrage du backend sur le port {port_to_use}")

            # Vérifier si le port est déjà occupé avant de lancer
            if await self._is_port_occupied(port_to_use):
                error_msg = f"Le port {port_to_use} est déjà occupé. Le démarrage est annulé."
                self.logger.error(error_msg)
                return {'success': False, 'error': error_msg, 'url': None, 'port': None, 'pid': None}

            conda_env_name = self.config.get('conda_env', 'projet-is')
            # La logique de commande a été modifiée pour permettre soit 'module', soit 'command_list'
            command_list = self.config.get('command_list')
            
            if command_list:
                # Si une liste de commandes est fournie, on l'utilise directement
                cmd = command_list
                self.logger.info(f"Utilisation de la commande personnalisée: {' '.join(cmd)}")
            elif self.module:
                # Sinon, on construit la commande flask à partir du module
                app_module_with_attribute = f"{self.module}:app" if ':' not in self.module else self.module
                backend_host = self.config.get('host', '127.0.0.1')
                
                # Déterminer le type de serveur à partir de la configuration, avec un fallback
                server_type = self.config.get('server_type', 'uvicorn') # Par défaut à uvicorn maintenant
                
                if server_type == 'flask':
                    self.logger.info("Configuration pour un serveur Flask détectée.")
                    inner_cmd_list = [
                        "python", "-m", "flask", "--app", app_module_with_attribute, "run", "--host", backend_host, "--port", str(port_to_use)
                    ]
                elif server_type == 'uvicorn':
                    self.logger.info("Configuration pour un serveur Uvicorn (FastAPI) détectée.")
                    self.logger.info("Configuration pour un serveur Uvicorn (FastAPI) détectée. Utilisation du port 0 pour une allocation dynamique.")
                    # Utilisation explicite de "python -m" pour plus de robustesse
                    inner_cmd_list = [
                        "python", "-m", "uvicorn", app_module_with_attribute, "--host", backend_host, "--port", "0", "--reload"
                    ]
                else:
                    raise ValueError(f"Type de serveur non supporté: {server_type}. Choisissez 'flask' ou 'uvicorn'.")
                
                # Gestion de l'environnement Conda
                # Lire le nom de l'environnement depuis les variables d'environnement, avec un fallback.
                conda_env_name = os.environ.get('CONDA_ENV_NAME', self.config.get('conda_env', 'projet-is'))
                current_conda_env = os.getenv('CONDA_DEFAULT_ENV')
                python_executable = sys.executable
                
                is_already_in_target_env = (current_conda_env == conda_env_name and conda_env_name in python_executable)
                
                self.logger.warning(f"Construction de la commande via 'powershell.exe' pour garantir l'activation de l'environnement Conda '{conda_env_name}'.")
                
                # Construction de la commande interne (ex: python -m uvicorn ...)
                inner_cmd_str = " ".join(shlex.quote(arg) for arg in inner_cmd_list)
                
                # Construction de la commande complète pour PowerShell
                # La commande complète pour PowerShell inclut maintenant l'activation de l'environnement via le script dédié
                project_root_path = Path(__file__).resolve().parent.parent.parent
                activation_script_path = project_root_path / "activate_project_env.ps1"
                
                # S'assurer que le chemin est correctement formaté pour PowerShell
                # ` risolve le chemin complet
                # . ` exécute le script
                # `. ` exécute le script d'activation, puis la commande interne (qui contient déjà "python -m ...") est exécutée.
                full_command_str = f". '{activation_script_path}'; {inner_cmd_str}"
                
                cmd = [
                    "powershell.exe",
                    "-Command",
                    full_command_str
                ]
            else:
                # Cas d'erreur : ni module, ni command_list
                raise ValueError("La configuration du backend doit contenir soit 'module', soit 'command_list'.")

            # Le reste de la logique de lancement est maintenant unifié
            
            
            self.logger.info(f"Commande de lancement backend construite: {cmd}")

            project_root = str(Path(__file__).resolve().parent.parent.parent)
            log_dir = Path(project_root) / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            stdout_log_path = log_dir / f"backend_stdout_{port_to_use}.log"
            stderr_log_path = log_dir / f"backend_stderr_{port_to_use}.log"

            self.logger.info(f"Logs redirigés vers {stdout_log_path.name} et {stderr_log_path.name}")
            
            # --- GESTION DES DÉPENDANCES TWEETY ---
            self.logger.info("Vérification et téléchargement des JARs Tweety...")
            libs_dir = Path(project_root) / "libs" / "tweety"
            if 'LIBS_DIR' not in effective_env:
                try:
                    if await asyncio.to_thread(download_tweety_jars, str(libs_dir)):
                        self.logger.info(f"JARs Tweety prêts dans {libs_dir}")
                        effective_env['LIBS_DIR'] = str(libs_dir)
                    else:
                        self.logger.error("Échec du téléchargement des JARs Tweety.")
                except Exception as e:
                    self.logger.error(f"Erreur lors du téléchargement des JARs Tweety: {e}")

            with open(stdout_log_path, 'wb') as f_stdout, open(stderr_log_path, 'wb') as f_stderr:
                self.process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=f_stdout,
                    stderr=f_stderr,
                    cwd=project_root,
                    env=effective_env
                )

            
            # Attendre que le backend soit prêt. Cette méthode va maintenant trouver le port dynamique.
            backend_ready, dynamic_port = await self._wait_for_backend(stdout_log_path, stderr_log_path)

            if backend_ready and dynamic_port:
                self.current_port = dynamic_port
                self.current_url = f"http://localhost:{self.current_port}"
                self.pid = self.process.pid
                result = {'success': True, 'url': self.current_url, 'port': self.current_port, 'pid': self.pid, 'error': None}
                await self._save_backend_info(result)
                return result

            self.logger.error(f"Le backend n'a pas pu démarrer sur le port {port_to_use}.")
            await self._cleanup_failed_process(stdout_log_path, stderr_log_path)
            return {'success': False, 'error': f'Le backend a échoué à démarrer sur le port {port_to_use}', 'url': None, 'port': port_to_use, 'pid': None}

        except Exception as e:
            self.logger.error(f"Erreur majeure lors du démarrage du backend : {e}", exc_info=True)
            return {'success': False, 'error': str(e), 'url': None, 'port': self.current_port, 'pid': None}
    
    async def _cleanup_failed_process(self, stdout_log_path: Path, stderr_log_path: Path):
        """Nettoie le processus et affiche les logs en cas d'échec de démarrage."""
        await asyncio.sleep(0.5) # Laisser le temps aux logs de s'écrire

        for log_path in [stdout_log_path, stderr_log_path]:
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    log_content = f.read().strip()
                    if log_content:
                        self.logger.info(f"--- Contenu de {log_path.name} ---\n{log_content}\n--------------------")
            except FileNotFoundError:
                self.logger.warning(f"Fichier de log {log_path.name} non trouvé.")

        if self.process and self.process.returncode is None:
            self.logger.info(f"Tentative de terminaison du processus backend {self.process.pid} qui n'a pas démarré.")
            self.process.terminate()
            try:
                await self.process.wait()
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None

    async def _wait_for_backend(self, stdout_log_path: Path, stderr_log_path: Path) -> tuple[bool, Optional[int]]:
        """
        Attend que le backend soit accessible. Si le port est dynamique (0),
        le parse depuis les logs stdout.
        """
        import re
        start_time = time.time()
        self.logger.info(f"Analyse des logs backend ({stdout_log_path.name}, {stderr_log_path.name}) pour le port dynamique (timeout: {self.timeout_seconds}s)")

        dynamic_port = None
        log_paths_to_check = [stdout_log_path, stderr_log_path]
        
        #Regex pour trouver le port dans la sortie d'Uvicorn
        port_regex = re.compile(r"Uvicorn running on https?://[0-9\.]+:(?P<port>\d+)")

        # 1. Boucle pour trouver le port dans les logs
        while time.time() - start_time < self.timeout_seconds:
            if self.process and self.process.returncode is not None:
                self.logger.error(f"Processus backend terminé prématurément (code: {self.process.returncode})")
                return False, None

            for log_path in log_paths_to_check:
                if log_path.exists():
                    try:
                        log_content = await asyncio.to_thread(log_path.read_text, encoding='utf-8', errors='ignore')
                        match = port_regex.search(log_content)
                        if match:
                            dynamic_port = int(match.group('port'))
                            self.logger.info(f"Port dynamique {dynamic_port} détecté dans {log_path.name}")
                            break  # Sortir de la boucle for
                    except Exception as e:
                        self.logger.warning(f"Impossible de lire le fichier de log {log_path.name}: {e}")
            
            if dynamic_port:
                break # Sortir de la boucle while

            await asyncio.sleep(2) # Attendre avant de relire le fichier
        
        if not dynamic_port:
            self.logger.error("Timeout: Port dynamique non trouvé dans les logs du backend.")
            return False, None

        # 2. Boucle de health check une fois le port trouvé
        backend_host_for_url = self.config.get('host', '127.0.0.1')
        connect_host = "127.0.0.1" if backend_host_for_url == "0.0.0.0" else backend_host_for_url
        url = f"http://{connect_host}:{dynamic_port}{self.health_endpoint}"
        
        self.logger.info(f"Port trouvé. Attente du health check sur {url}")
        
        health_check_start_time = time.time()
        while time.time() - health_check_start_time < self.health_check_timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=5) as response:
                        if response.status == 200:
                            self.logger.info(f"Backend accessible sur {url}")
                            return True, dynamic_port
            except Exception:
                pass # Les erreurs sont attendues pendant le démarrage
            await asyncio.sleep(2)

        self.logger.error(f"Timeout dépassé - Health check inaccessible sur {url}")
        return False, None
    
    async def _is_port_occupied(self, port: int) -> bool:
        """Vérifie si un port est déjà occupé"""
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                    return True
        except (psutil.AccessDenied, psutil.NoSuchProcess, AttributeError):
             # Fallback si psutil échoue
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection('127.0.0.1', port), timeout=1.0)
                writer.close()
                await writer.wait_closed()
                return True # Le port est ouvert
            except (ConnectionRefusedError, asyncio.TimeoutError):
                return False # Le port n'est pas ouvert
        return False
    
    async def health_check(self) -> bool:
        """Vérifie l'état de santé du backend"""
        if not self.current_url:
            return False
            
        try:
            url = f"{self.current_url}{self.health_endpoint}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.health_check_timeout)) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.logger.info(f"Backend health: {data}")
                        return True
        except Exception as e:
            self.logger.error(f"Health check échec: {e}")
            
        return False
    
    async def stop(self):
        """Arrête le backend proprement"""
        if self.process:
            try:
                self.logger.info(f"Arrêt backend PID {self.process.pid}")
                
                self.process.terminate()
                try:
                    await self.process.wait()
                except asyncio.TimeoutError:
                    self.logger.warning("Timeout à l'arrêt, forçage...")
                    self.process.kill()
                    await self.process.wait()
                    
                self.logger.info("Backend arrêté")
                
            except Exception as e:
                self.logger.error(f"Erreur arrêt backend: {e}")
            finally:
                self.process = None
                self.current_port = None
                self.current_url = None
                self.pid = None
    
    async def _save_backend_info(self, result: Dict[str, Any]):
        """Sauvegarde les informations du backend"""
        info = {
            'status': 'SUCCESS',
            'port': result['port'],
            'url': result['url'],
            'pid': result['pid'],
            'job_id': result['pid'],
            'health_endpoint': f"{result['url']}{self.health_endpoint}",
            'start_time': time.time()
        }
        
        info_file = Path('backend_info.json')
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2)
            
        self.logger.info(f"Info backend sauvées: {info_file}")
    
    def get_status(self) -> Dict[str, Any]:
        """Retourne l'état actuel du backend"""
        return {
            'running': self.process is not None,
            'port': self.current_port,
            'url': self.current_url,
            'pid': self.pid,
            'process': self.process
        }