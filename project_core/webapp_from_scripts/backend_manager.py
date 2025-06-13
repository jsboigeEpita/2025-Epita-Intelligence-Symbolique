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
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        
        # Configuration par défaut
        self.module = config.get('module', 'argumentation_analysis.services.web_api.app')
        self.start_port = config.get('start_port', 5003)
        self.fallback_ports = config.get('fallback_ports', [5004, 5005, 5006])
        self.max_attempts = config.get('max_attempts', 5)
        self.timeout_seconds = config.get('timeout_seconds', 60) # Augmenté à 60s
        self.health_endpoint = config.get('health_endpoint', '/api/health')
        self.env_activation = config.get('env_activation',
                                       'powershell -File scripts/env/activate_project_env.ps1')
        
        # État runtime
        self.process: Optional[subprocess.Popen] = None
        self.current_port: Optional[int] = None
        self.current_url: Optional[str] = None
        self.pid: Optional[int] = None
        
    async def start_with_failover(self) -> Dict[str, Any]:
        """
        Démarre le backend avec failover automatique sur plusieurs ports
        
        Returns:
            Dict contenant success, url, port, pid, error
        """
        ports_to_try = [self.start_port] + self.fallback_ports
        
        for attempt, port in enumerate(ports_to_try, 1):
            self.logger.info(f"Tentative {attempt}/{len(ports_to_try)} - Port {port}")
            
            if await self._is_port_occupied(port):
                self.logger.warning(f"Port {port} occupé, passage au suivant")
                continue
                
            result = await self._start_on_port(port)
            if result['success']:
                self.current_port = port
                self.current_url = result['url']
                self.pid = result['pid']
                
                # Sauvegarde info backend
                await self._save_backend_info(result)
                return result
                
        return {
            'success': False,
            'error': f'Impossible de démarrer sur les ports: {ports_to_try}',
            'url': None,
            'port': None,
            'pid': None
        }
    
    async def _find_conda_python(self) -> Optional[str]:
        """Trouve l'exécutable Python de l'environnement Conda spécifié dans .env."""
        self.logger.info("Recherche de l'exécutable Python de l'environnement Conda...")
        
        env_file = find_dotenv()
        if not env_file:
            self.logger.warning("Fichier .env non trouvé.")
            return None
        load_dotenv(dotenv_path=env_file)
        
        env_name = os.getenv("CONDA_ENV_NAME")
        if not env_name:
            self.logger.error("CONDA_ENV_NAME non défini dans le .env.")
            return None
        self.logger.info(f"Nom de l'environnement Conda cible: {env_name}")

        conda_exe = shutil.which("conda")
        if not conda_exe:
            self.logger.warning("'conda.exe' non trouvé via shutil.which. Tentative via CONDA_PATH.")
            conda_path_from_env = os.getenv("CONDA_PATH")
            if conda_path_from_env:
                self.logger.info(f"CONDA_PATH trouvé dans .env: {conda_path_from_env}")
                # Diviser la variable CONDA_PATH en plusieurs chemins
                for base_path_str in conda_path_from_env.split(os.pathsep):
                    base_path = Path(base_path_str.strip())
                    if not base_path.exists():
                        self.logger.warning(f"Le chemin '{base_path}' de CONDA_PATH n'existe pas.")
                        continue
                    
                    # CONDA_PATH est censé contenir des chemins comme C:\...\miniconda3\condabin
                    # ou C:\...\miniconda3\Scripts, où conda.exe se trouve directement.
                    potential_paths = [
                        base_path / "conda.exe",
                    ]
                    for path_to_check in potential_paths:
                        self.logger.info(f"Vérification de: {path_to_check}")
                        if path_to_check.exists():
                            conda_exe = str(path_to_check)
                            self.logger.info(f"Exécutable Conda trouvé: {conda_exe}")
                            break
                    if conda_exe:
                        break
            else:
                self.logger.warning("Variable CONDA_PATH non trouvée.")

        if not conda_exe:
            self.logger.error("Impossible de localiser conda.exe.")
            return None
            
        try:
            result = await asyncio.to_thread(
                subprocess.run, [conda_exe, "info", "--envs", "--json"],
                capture_output=True, text=True, check=True, timeout=30
            )
            envs_info = json.loads(result.stdout)
            for env_path_str in envs_info.get("envs", []):
                if Path(env_path_str).name == env_name:
                    python_exe = Path(env_path_str) / "python.exe"
                    if python_exe.exists():
                        self.logger.info(f"Exécutable Python trouvé: {python_exe}")
                        return str(python_exe)
            self.logger.error(f"Env '{env_name}' non trouvé.")
            return None
        except Exception as e:
            self.logger.error(f"Erreur lors de l'interrogation de Conda: {e}")
            return None

    async def _start_on_port(self, port: int) -> Dict[str, Any]:
        """Démarre le backend sur un port spécifique"""
        cmd: List[str] = []
        try:
            if self.config.get('command_list'):
                cmd = self.config['command_list'] + [str(port)]
                self.logger.info(f"Démarrage via command_list: {cmd}")
            elif self.config.get('command'):
                command_str = self.config['command']
                cmd = shlex.split(command_str) + [str(port)]
                self.logger.info(f"Démarrage via commande directe: {cmd}")
            else:
                if ':' in self.module:
                    app_module_with_attribute = self.module
                else:
                    app_module_with_attribute = f"{self.module}:app"
                backend_host = self.config.get('host', '127.0.0.1')
                
                uvicorn_args_list = [
                    app_module_with_attribute,
                    f"--host={backend_host}",
                    f"--port={str(port)}"
                ]
                uvicorn_args_str_for_python = str(uvicorn_args_list)

                python_command_str = (
                    f"import uvicorn; "
                    f"uvicorn.main({uvicorn_args_str_for_python})"
                )

                # Utiliser la nouvelle méthode pour trouver le bon Python
                python_exe_path = await self._find_conda_python()
                if not python_exe_path:
                    error_msg = "Impossible de trouver l'exécutable Python de l'environnement Conda."
                    self.logger.error(error_msg)
                    return {'success': False, 'error': error_msg, 'url': None, 'port': None, 'pid': None}
                
                backend_host = self.config.get('host', '127.0.0.1')
                
                cmd = [
                    python_exe_path, "-m", "uvicorn",
                    app_module_with_attribute,
                    "--host", backend_host,
                    "--port", str(port),
                    "--log-level", "info"
                ]
                self.logger.info(f"Commande de lancement du backend: {' '.join(cmd)}")

            project_root = str(Path.cwd())
            log_dir = Path(project_root) / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            stdout_log_path = log_dir / f"backend_stdout_{port}.log"
            stderr_log_path = log_dir / f"backend_stderr_{port}.log"

            self.logger.info(f"Redirection stdout -> {stdout_log_path}")
            self.logger.info(f"Redirection stderr -> {stderr_log_path}")
            
            env = os.environ.copy()
            existing_pythonpath = env.get('PYTHONPATH', '')
            if project_root not in existing_pythonpath.split(os.pathsep):
                env['PYTHONPATH'] = f"{project_root}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else project_root

            self.logger.debug(f"Commande Popen: {cmd}")
            self.logger.debug(f"CWD: {project_root}")
            self.logger.debug(f"PYTHONPATH: {env.get('PYTHONPATH')}")

            with open(stdout_log_path, 'wb') as f_stdout, open(stderr_log_path, 'wb') as f_stderr:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=f_stdout,
                    stderr=f_stderr,
                    cwd=project_root,
                    env=env,
                    shell=False
                )

            backend_ready = await self._wait_for_backend(port)

            if backend_ready:
                url = f"http://localhost:{port}"
                return {
                    'success': True,
                    'url': url,
                    'port': port,
                    'pid': self.process.pid,
                    'error': None
                }
            
            # Si le backend n'est pas prêt, on logue et on nettoie
            self.logger.error(f"Backend sur port {port} n'a pas démarré. Diagnostic des logs.")
            
            await asyncio.sleep(0.5)

            for log_path in [stdout_log_path, stderr_log_path]:
                try:
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        log_content = f.read().strip()
                        if log_content:
                            self.logger.info(f"--- Contenu {log_path.name} ---\n{log_content}\n--------------------")
                        else:
                            self.logger.info(f"Log {log_path.name} est vide.")
                except FileNotFoundError:
                    self.logger.warning(f"Log {log_path.name} non trouvé.")

            if self.process:
                if self.process.poll() is None:
                    self.logger.info(f"Processus {self.process.pid} encore actif, terminaison.")
                    self.process.terminate()
                    try:
                        await asyncio.to_thread(self.process.wait, timeout=5)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                else:
                    self.logger.info(f"Processus terminé avec code: {self.process.returncode}")
                self.process = None

            return { 'success': False, 'error': f'Backend failed on port {port}', 'url': None, 'port': None, 'pid': None }

        except Exception as e:
            self.logger.error(f"Erreur démarrage backend port {port}: {e}", exc_info=True)
            return {'success': False, 'error': str(e), 'url': None, 'port': None, 'pid': None}

    async def _wait_for_backend(self, port: int) -> bool:
        """Attend que le backend soit accessible via health check"""
        backend_host_for_url = self.config.get('host', '127.0.0.1')
        connect_host = "127.0.0.1" if backend_host_for_url == "0.0.0.0" else backend_host_for_url

        url = f"http://{connect_host}:{port}{self.health_endpoint}"
        start_time = time.time()
        
        self.logger.info(f"Attente backend sur {url} (timeout: {self.timeout_seconds}s)")
        
        # Pause initiale pour laisser le temps au serveur de démarrer
        initial_wait = 15
        self.logger.info(f"Pause initiale de {initial_wait}s avant health checks...")
        await asyncio.sleep(initial_wait)

        while time.time() - start_time < self.timeout_seconds:
            if self.process and self.process.poll() is not None:
                self.logger.error(f"Processus backend terminé prématurément (code: {self.process.returncode})")
                return False
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            self.logger.info(f"Backend accessible sur {url}")
                            return True
                        else:
                            self.logger.warning(f"Health check a échoué avec status {response.status}")
            except Exception as e:
                elapsed = time.time() - start_time
                self.logger.warning(f"Health check échoué ({elapsed:.1f}s): {type(e).__name__}")
                
            await asyncio.sleep(5)
        
        self.logger.error(f"Timeout dépassé - Backend inaccessible sur {url}")
        return False
    
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
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
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
                    await asyncio.to_thread(self.process.wait, timeout=5)
                except subprocess.TimeoutExpired:
                    self.logger.warning("Timeout à l'arrêt, forçage...")
                    self.process.kill()
                    await asyncio.to_thread(self.process.wait, timeout=5)
                    
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