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
import shutil # Ajout pour shutil.which

# Import pour l'activation de l'environnement et la recherche de Python
# from scripts.core.environment_manager import auto_activate_env # auto_activate_env est appelé par le script parent start_webapp.py

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
    
    async def _get_conda_env_python_executable(self, env_name: str) -> Optional[str]:
        """Tente de trouver l'exécutable Python pour un environnement Conda donné."""
        try:
            # Essayer de trouver conda d'abord
            conda_exe = shutil.which("conda")
            if not conda_exe:
                self.logger.warning("Exécutable Conda non trouvé via shutil.which('conda').")
                conda_exe = os.environ.get("CONDA_EXE")
                if not conda_exe or not Path(conda_exe).exists():
                    self.logger.error("CONDA_EXE non trouvé ou invalide dans l'environnement.")
                    return None

            # Obtenir les informations sur les environnements Conda
            # Utilisation de asyncio.to_thread pour exécuter la commande bloquante subprocess.run
            result = await asyncio.to_thread(
                subprocess.run,
                [conda_exe, "info", "--envs", "--json"],
                capture_output=True,
                text=True,
                check=True, # Lève une exception si la commande échoue
                timeout=30
            )
            envs_info = json.loads(result.stdout)
            
            for env_path_str in envs_info.get("envs", []):
                env_path = Path(env_path_str)
                if env_path.name == env_name:
                    # Construire le chemin vers python.exe (Windows) ou python (Unix)
                    python_exe = env_path / "python.exe" # Pour Windows
                    if not python_exe.exists():
                        python_exe = env_path / "bin" / "python" # Pour Unix-like
                    
                    if python_exe.exists():
                        self.logger.info(f"Exécutable Python trouvé pour l'env '{env_name}': {python_exe}")
                        return str(python_exe)
                    else:
                        self.logger.warning(f"Exécutable Python non trouvé dans le chemin de l'env '{env_name}': {env_path}")
                        break
            
            self.logger.error(f"Impossible de trouver le chemin de l'exécutable Python pour l'environnement Conda '{env_name}'.")
            return None
        except FileNotFoundError:
            self.logger.error("La commande 'conda' n'a pas été trouvée. Assurez-vous que Conda est installé et dans le PATH.")
            return None
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Erreur lors de l'exécution de 'conda info --envs --json': {e.stderr}")
            return None
        except subprocess.TimeoutExpired:
            self.logger.error("Timeout lors de l'exécution de 'conda info --envs --json'.")
            return None
        except json.JSONDecodeError:
            self.logger.error("Erreur lors du parsing de la sortie JSON de 'conda info --envs --json'.")
            return None
        except Exception as e:
            self.logger.error(f"Erreur inattendue lors de la recherche de l'exécutable Python de Conda: {e}")
            return None

    async def _start_on_port(self, port: int) -> Dict[str, Any]:
        """Démarre le backend sur un port spécifique"""
        try:
            conda_env_name = "projet-is" # Nom de l'environnement cible
            
            # Obtenir l'exécutable Python de l'environnement Conda cible
            python_exe_path = await self._get_conda_env_python_executable(conda_env_name)
            
            if not python_exe_path:
                self.logger.error(f"Impossible de démarrer le backend: exécutable Python pour '{conda_env_name}' non trouvé.")
                return {
                    'success': False,
                    'error': f"Exécutable Python pour l'environnement '{conda_env_name}' introuvable.",
                    'url': None, 'port': port, 'pid': None
                }
            
            self.logger.info(f"Utilisation de l'interpréteur Python de l'environnement Conda '{conda_env_name}': {python_exe_path}")

            # Commande de démarrage pour FastAPI avec Uvicorn
            # S'assurer que l'attribut de l'application (généralement 'app') est spécifié
            # Vérifier si self.module contient déjà l'attribut de l'application (ex: "module:app_instance")
            if ':' in self.module:
                app_module_with_attribute = self.module
            else:
                app_module_with_attribute = f"{self.module}:app"
            backend_host = self.config.get('host', '127.0.0.1')
            
            # Construction de la commande pour uvicorn.main()
            # Cela permet d'insérer un log de test avant l'appel à uvicorn
            uvicorn_args_list = [
                app_module_with_attribute,
                f"--host={backend_host}",
                f"--port={str(port)}"
                # Ajoutez d'autres options uvicorn ici si nécessaire (ex: --log-level)
            ]
            # Formatter les arguments pour la chaîne de commande Python
            # Ex: "['module:app', '--host=127.0.0.1', '--port=5003']"
            uvicorn_args_str_for_python = str(uvicorn_args_list)

            python_command_str = (
                f"import sys; sys.stderr.write('--- PYTHON EXEC TEST IN UVICORN LOG OK ---\\n'); "
                f"sys.stderr.flush(); import uvicorn; "
                f"uvicorn.main({uvicorn_args_str_for_python})"
            )

            cmd = [
                python_exe_path, '-c', python_command_str
            ]
            
            self.logger.info(f"Démarrage backend FastAPI via uvicorn.main(): {python_exe_path} -c \"...uvicorn.main(...)\"")
            self.logger.debug(f"Commande Python détaillée pour uvicorn.main(): {python_command_str}")
            
            # Créer le répertoire de logs s'il n'existe pas
            log_dir = Path.cwd() / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            stdout_log_file = log_dir / f"uvicorn_stdout_{port}.log"
            stderr_log_file = log_dir / f"uvicorn_stderr_{port}.log"

            self.logger.info(f"Logging stdout de Uvicorn dans: {stdout_log_file}")
            self.logger.info(f"Logging stderr de Uvicorn dans: {stderr_log_file}")

            # Démarrage processus en arrière-plan
            env = os.environ.copy()
            
            # Définir PYTHONPATH pour inclure la racine du projet.
            # Path.cwd() devrait être la racine du projet si start_webapp.py est à la racine.
            project_root = str(Path.cwd())
            
            # Construire PYTHONPATH : s'assurer que project_root est le premier élément.
            # Cela permet aux imports relatifs à la racine du projet de fonctionner.
            existing_pythonpath = env.get('PYTHONPATH', '')
            if existing_pythonpath:
                env['PYTHONPATH'] = project_root + os.pathsep + existing_pythonpath
            else:
                env['PYTHONPATH'] = project_root
            
            self.logger.info(f"PYTHONPATH pour Uvicorn: {env['PYTHONPATH']}")
            self.logger.info(f"CWD pour Uvicorn: {project_root}")

            # Ouvrir les fichiers de log pour la redirection
            with open(stdout_log_file, 'wb') as f_stdout, open(stderr_log_file, 'wb') as f_stderr:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=f_stdout, # Rediriger stdout vers le fichier
                    stderr=f_stderr, # Rediriger stderr vers le fichier
                    cwd=project_root, # Exécuter depuis la racine du projet
                    env=env,
                    shell=False
                )
            
            # Attente démarrage
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
            else:
                # Échec - cleanup processus
                if self.process:
                    self.process.terminate()
                    self.process = None
                    
                return {
                    'success': False,
                    'error': f'Backend non accessible sur port {port} après {self.timeout_seconds}s',
                    'url': None,
                    'port': None,
                    'pid': None
                }
                
        except Exception as e:
            self.logger.error(f"Erreur démarrage backend port {port}: {e}")
            return {
                'success': False,
                'error': str(e),
                'url': None,
                'port': None,
                'pid': None
            }

    async def _wait_for_backend(self, port: int) -> bool:
        """Attend que le backend soit accessible via health check"""
        # S'assurer que l'URL de health check utilise aussi 127.0.0.1 si c'est l'hôte d'écoute
        backend_host_for_url = self.config.get('host', '127.0.0.1')
        # Si backend_host_for_url est 0.0.0.0, le client doit utiliser localhost ou 127.0.0.1
        if backend_host_for_url == "0.0.0.0":
            connect_host = "127.0.0.1"
        else:
            connect_host = backend_host_for_url

        url = f"http://{connect_host}:{port}{self.health_endpoint}"
        start_time = time.time()
        
        self.logger.info(f"Attente backend sur {url} (timeout: {self.timeout_seconds}s)")
        
        self.logger.info("Pause initiale de 20 secondes avant de commencer les health checks...") # Augmentation de la pause
        await asyncio.sleep(20) # Pause initiale plus longue

        while time.time() - start_time < self.timeout_seconds:
            try:
                # Vérifier d'abord si le processus est toujours vivant
                if self.process and self.process.poll() is not None:
                    return_code = self.process.returncode
                    self.logger.error(f"Processus backend terminé prématurément (code: {return_code})")
                    
                    # Lire stdout et stderr du processus terminé
                    # Note: la lecture directe des pipes après la fin du processus peut être délicate.
                    # Les logs fichiers sont plus fiables.
                    # stdout_output, stderr_output = self.process.communicate(timeout=1) # Ne peut être appelé qu'une fois
                    # Pour l'instant, on se fie aux logs fichiers qui sont créés.
                    return False # Processus mort, donc backend pas prêt
                
                async with aiohttp.ClientSession() as session:
                    self.logger.info(f"Tentative de connexion GET à {url}...")
                    sys.stdout.flush() # Forcer le flush pour voir ce log immédiatement
                    # Augmentation du timeout pour chaque requête individuelle
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        self.logger.info(f"Réponse reçue de {url} avec statut: {response.status}")
                        if response.status == 200:
                            self.logger.info(f"Backend accessible sur {url}")
                            return True
            except aiohttp.ClientConnectorError as e_conn:
                elapsed = time.time() - start_time
                self.logger.debug(f"Tentative health check (connexion) après {elapsed:.1f}s: {type(e_conn).__name__} - {e_conn}")
            except asyncio.TimeoutError as e_timeout_req: # Spécifique pour le timeout de la requête aiohttp
                elapsed = time.time() - start_time
                self.logger.debug(f"Tentative health check (timeout requête) après {elapsed:.1f}s: {type(e_timeout_req).__name__}")
            except Exception as e_other: # Autres exceptions aiohttp ou génériques
                elapsed = time.time() - start_time
                self.logger.debug(f"Tentative health check (autre erreur) après {elapsed:.1f}s: {type(e_other).__name__} - {e_other}")
                
            await asyncio.sleep(5) # Intervalle augmenté
        
        self.logger.error(f"Timeout - Backend non accessible sur {url}")
        # Si timeout et le processus est toujours là mais ne répond pas, logguer sa sortie aussi
        if self.process and self.process.poll() is None: # Processus encore en cours
            self.logger.info("Le processus backend est toujours en cours mais ne répond pas au health check.")
            # Tenter de lire la sortie non bloquante (peut être vide si rien n'a été écrit récemment)
            # Note: Cela est délicat avec Popen en mode non bloquant sans threads séparés pour lire les pipes.
            # Les modifications ci-dessus pour la terminaison prématurée sont plus fiables pour obtenir la sortie.
        return False
    
    async def _is_port_occupied(self, port: int) -> bool:
        """Vérifie si un port est déjà occupé"""
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                    return True
        except (psutil.AccessDenied, AttributeError):
            # Fallback - tentative connexion
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://localhost:{port}", 
                                         timeout=aiohttp.ClientTimeout(total=1)) as response:
                        return True  # Port répond
            except:
                pass
                
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
                
                # Terminaison progressive
                self.process.terminate()
                
                # Attente arrêt propre (5s max)
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill si nécessaire
                    self.process.kill()
                    self.process.wait()
                    
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
            'job_id': result['pid'],  # Compatibilité scripts PowerShell
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