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
import time
import json
import asyncio
import logging
import subprocess
import psutil
import threading
from typing import Dict, List, Optional, Any, IO
from pathlib import Path
import aiohttp

from argumentation_analysis.core.jvm_setup import initialize_jvm

# Correction du chemin pour la racine du projet
project_root = Path(__file__).resolve().parents[3]


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
        self.module = config.get(
            "module", "argumentation_analysis.services.web_api.app"
        )
        self.start_port = config.get("start_port", 8095)
        self.fallback_ports = config.get("fallback_ports", [8096, 8097, 8098])
        self.max_attempts = config.get("max_attempts", 5)
        self.timeout_seconds = config.get(
            "timeout_seconds", 180
        )  # Augmentation du timeout
        self.health_endpoint = config.get("health_endpoint", "/api/health")
        # Forcer l'utilisation d'un chemin absolu pour la robustesse
        # Forcer l'utilisation d'un chemin absolu pour la robustesse et pointer vers le bon script
        # Forcer l'utilisation du script d'activation à la racine du projet, comme demandé par l'audit
        self.env_activation = 'powershell -Command ". ./activate_project_env.ps1"'

        # État runtime
        self.process: Optional[subprocess.Popen] = None
        self.current_port: Optional[int] = None
        self.current_url: Optional[str] = None
        self.pid: Optional[int] = None
        self.log_threads: List[threading.Thread] = []

    async def start_with_failover(
        self, app_module: Optional[str] = None, port_override: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Démarre le backend avec failover automatique sur plusieurs ports

        Args:
            app_module: Module applicatif à lancer (ex: 'api.main:app')
            port_override: Force l'utilisation d'un port spécifique

        Returns:
            Dict contenant success, url, port, pid, error
        """
        if port_override:
            ports_to_try = [port_override]
        else:
            ports_to_try = [self.start_port] + self.fallback_ports

        # Le module applicatif peut être surchargé, sinon on utilise celui de la config
        target_module = app_module or self.module

        for attempt in range(1, self.max_attempts + 1):
            port = ports_to_try[(attempt - 1) % len(ports_to_try)]
            self.logger.info(
                f"Tentative {attempt}/{self.max_attempts} - Lancement de '{target_module}' sur le port {port}"
            )

            if await self._is_port_occupied(port):
                self.logger.warning(
                    f"Port {port} occupé, nouvelle tentative dans 2s..."
                )
                await asyncio.sleep(2)
                continue

            result = await self._start_on_port(port, target_module)
            if result["success"]:
                self.current_port = port
                self.current_url = result["url"]
                self.pid = result["pid"]

                await self._save_backend_info(result)
                return result
            else:
                self.logger.warning(
                    f"Echec tentative {attempt} sur le port {port}. Erreur: {result.get('error', 'Inconnue')}"
                )
                await asyncio.sleep(1)  # Courte pause avant de réessayer

        return {
            "success": False,
            "error": f"Impossible de démarrer le backend après {self.max_attempts} tentatives sur les ports {ports_to_try}",
            "url": None,
            "port": None,
            "pid": None,
        }

    def _log_stream(self, stream: IO[str], log_level: int):
        """Lit un stream et logue chaque ligne."""
        try:
            for line in iter(stream.readline, ""):
                if line:
                    self.logger.log(log_level, f"[BACKEND] {line.strip()}")
            stream.close()
        except Exception as e:
            self.logger.error(f"Erreur dans le thread de logging: {e}")

    def _get_conda_env_python_executable(self, env_name: str) -> Optional[str]:
        """Trouve le chemin de l'exécutable Python pour un environnement Conda donné."""
        try:
            self.logger.info(f"Recherche de l'environnement Conda nommé: '{env_name}'")
            # Exécute `conda info` pour obtenir la liste des environnements
            result = subprocess.run(
                ["conda", "info", "--envs", "--json"],
                capture_output=True,
                text=True,
                check=True,
                shell=True,
            )
            envs_data = json.loads(result.stdout)

            # Cherche le chemin de l'environnement cible
            env_path_str = None
            for env in envs_data.get("envs", []):
                if Path(env).name == env_name:
                    env_path_str = env
                    self.logger.info(
                        f"Chemin trouvé pour l'environnement '{env_name}': {env_path_str}"
                    )
                    break

            if not env_path_str:
                self.logger.error(
                    f"Environnement Conda '{env_name}' non trouvé dans la liste des environnements."
                )
                return None

            # Construit le chemin de l'exécutable Python
            python_executable = Path(env_path_str) / "python.exe"
            if python_executable.exists():
                self.logger.info(
                    f"Exécutable Python validé pour l'environnement '{env_name}': {python_executable}"
                )
                return str(python_executable)
            else:
                self.logger.error(
                    f"python.exe non trouvé dans l'environnement '{env_name}' au chemin: {python_executable}"
                )
                return None

        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            json.JSONDecodeError,
        ) as e:
            self.logger.error(
                f"Erreur critique lors de la recherche de l'environnement Conda via 'conda info': {e}"
            )
            return None

    async def _start_on_port(self, port: int, app_module: str) -> Dict[str, Any]:
        """
        Démarre une application backend sur un port spécifique.
        Args:
            port: Le port sur lequel démarrer.
            app_module: Le module applicatif à lancer (ex: 'api.main:app').
        """
        try:
            # Correction: Initialiser la JVM pour garantir que JAVA_HOME est correctement configuré.
            # Cette fonction est idempotente et ne fera rien si la JVM est déjà démarrée.
            self.logger.info(
                "Assurer l'initialisation de la JVM avant de lancer le backend..."
            )
            if not initialize_jvm():
                error_msg = "Échec de l'initialisation de la JVM. Le backend ne peut pas démarrer."
                self.logger.critical(error_msg)
                return {"success": False, "error": error_msg}
            self.logger.info("Initialisation de la JVM vérifiée avec succès.")

            server_type = self.config.get("server_type", "uvicorn")

            # Stratégie robuste : trouver l'exécutable Python de l'environnement Conda cible.
            # Stratégie robuste : utilise le nom de l'environnement Conda depuis .env, avec un fallback.
            conda_env_name = os.getenv("CONDA_ENV_NAME", "projet-is")
            python_executable = self._get_conda_env_python_executable(conda_env_name)

            if not python_executable:
                error_msg = f"Impossible de trouver l'exécutable Python pour l'environnement Conda '{conda_env_name}'. Vérifiez que 'conda' est dans le PATH et que l'environnement existe."
                self.logger.error(error_msg)
                return {"success": False, "error": error_msg}

            if server_type == "uvicorn":
                log_config_path = project_root.joinpath(
                    "argumentation_analysis", "config", "uvicorn_logging.json"
                )
                cmd = [
                    python_executable,
                    "-m",
                    "uvicorn",
                    app_module,
                    "--port",
                    str(port),
                    "--host",
                    "127.0.0.1",
                    "--log-config",
                    str(log_config_path),
                ]
            else:
                cmd = [
                    python_executable,
                    "-m",
                    self.module,
                    "--port",
                    str(port),
                    "--host",
                    "127.0.0.1",
                ]

            self.logger.info(f"Exécution via run_in_activated_env: {' '.join(cmd)}")

            env = os.environ.copy()

            # La logique de recherche du JAVA_HOME est maintenant gérée par `initialize_jvm()`.
            # La variable d'environnement sera automatiquement héritée par le sous-processus.
            self.logger.info(
                f"JAVA_HOME a été configuré par `jvm_setup`: {env.get('JAVA_HOME')}"
            )

            env["KMP_DUPLICATE_LIB_OK"] = "TRUE"

            # La gestion du PYTHONPATH est normalement gérée par l'environnement activé,
            # mais on le garde pour plus de robustesse.
            env["PYTHONPATH"] = str(project_root)

            if "PYTEST_CURRENT_TEST" in env:
                self.logger.warning(
                    "Suppression de 'PYTEST_CURRENT_TEST' de l'environnement pour désactiver le mock LLM."
                )
                del env["PYTEST_CURRENT_TEST"]

            env["INTEGRATION_TEST_MODE"] = "true"

            # run_in_activated_env retourne un CompletedProcess. Pour un serveur de longue durée,
            # nous avons besoin de Popen. Nous devons donc adapter notre approche.
            # Pour l'instant, nous supposons que le script peut etre modifié pour renvoyer un Popen
            # ou nous devons envelopper l'appel dans un thread.
            # La solution la plus simple est de ne pas utiliser le 'run_sync' qui attend la fin.
            # Au lieu de 'run_in_activated_env', nous construisons la commande et utilisons Popen.

            python_executable = self._get_conda_env_python_executable(
                os.getenv("CONDA_ENV_NAME", "projet-is")
            )
            if not python_executable:
                raise FileNotFoundError(
                    "L'exécutable python de l'environnement n'a pas pu être trouvé"
                )

            final_cmd = [python_executable] + cmd[
                1:
            ]  # On remplace 'python' par le chemin complet

            self.process = subprocess.Popen(
                final_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=project_root,
                env=env,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            # Démarrage des threads pour logger stdout et stderr du sous-processus
            self.log_threads = [
                threading.Thread(
                    target=self._log_stream, args=(self.process.stdout, logging.INFO)
                ),
                threading.Thread(
                    target=self._log_stream, args=(self.process.stderr, logging.ERROR)
                ),
            ]
            for t in self.log_threads:
                t.daemon = True
                t.start()

            backend_ready = await self._wait_for_backend(port)

            if backend_ready:
                url = f"http://127.0.0.1:{port}"
                return {
                    "success": True,
                    "url": url,
                    "port": port,
                    "pid": self.process.pid,
                    "error": None,
                }
            else:
                error_msg = f"Backend non accessible sur port {port} après {self.timeout_seconds}s"
                # Le processus est déjà terminé via _wait_for_backend
                return {
                    "success": False,
                    "error": error_msg,
                    "url": None,
                    "port": None,
                    "pid": None,
                }

        except Exception as e:
            self.logger.error(
                f"Erreur Démarrage Backend (port {port}): {e}", exc_info=True
            )
            return {
                "success": False,
                "error": str(e),
                "url": None,
                "port": None,
                "pid": None,
            }

    async def _wait_for_backend(
        self, port: int, app_module: Optional[str] = None
    ) -> bool:
        """Attend que le backend soit accessible via health check avec une patience accrue."""
        # Sélectionne l'endpoint de santé approprié
        if app_module and "api.main" in app_module:
            health_endpoint = "/health"
        else:
            health_endpoint = self.health_endpoint

        url = f"http://127.0.0.1:{port}{health_endpoint}"
        start_time = time.time()
        self.logger.info(
            f"Attente backend sur {url} (timeout: {self.timeout_seconds}s)"
        )

        # Boucle principale avec un timeout global long
        while time.time() - start_time < self.timeout_seconds:
            # Vérifie si le processus est toujours en cours d'exécution
            return_code = self.process.poll()
            if return_code is not None:
                self.logger.error(
                    f"Processus backend terminé prématurément (code: {return_code})."
                )
                # Vider et logger stderr pour le diagnostic
                stderr_output = ""
                try:
                    # Lecture non-bloquante de stderr
                    stderr_output = "".join(self.process.stderr.readlines())
                    if stderr_output:
                        self.logger.error("--- DEBUT SORTIE STDERR DU BACKEND ---")
                        for line in stderr_output.strip().split("\n"):
                            self.logger.error(f"[Backend STDERR] {line}")
                        self.logger.error("--- FIN SORTIE STDERR DU BACKEND ---")
                    else:
                        self.logger.error(
                            "Aucune sortie sur stderr n'a été capturée avant la fin du processus."
                        )
                except Exception as e:
                    self.logger.error(
                        f"Impossible de lire stderr du processus terminé : {e}"
                    )
                return False

            try:
                # Tente une connexion avec un timeout de connexion raisonnable (10s)
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            self.logger.info(
                                f"🎉 Backend accessible sur {url} après {time.time() - start_time:.1f}s."
                            )
                            return True
                        else:
                            self.logger.debug(
                                f"Health check a échoué avec status {response.status}"
                            )
            except aiohttp.ClientConnectorError as e:
                elapsed = time.time() - start_time
                self.logger.debug(
                    f"Tentative health check (connexion refusée) après {elapsed:.1f}s: {type(e).__name__}"
                )
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                self.logger.debug(
                    f"Tentative health check (timeout) après {elapsed:.1f}s."
                )
            except aiohttp.ClientError as e:
                elapsed = time.time() - start_time
                self.logger.warning(
                    f"Erreur client inattendue lors du health check après {elapsed:.1f}s: {type(e).__name__} - {e}"
                )

            # Pause substantielle entre les tentatives pour ne pas surcharger et laisser le temps au serveur de démarrer.
            await asyncio.sleep(2)

        # Si la boucle se termine, c'est un échec définitif par timeout global.
        self.logger.error(
            f"Timeout global atteint ({self.timeout_seconds}s) - Backend non accessible sur {url}"
        )
        if self.process.poll() is None:
            self.logger.error(
                "Le processus Backend est toujours en cours mais ne répond pas. Terminaison forcée..."
            )
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.logger.warning("La terminaison a échoué, forçage (kill)...")
                self.process.kill()
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
                    async with session.get(
                        f"http://127.0.0.1:{port}",
                        timeout=aiohttp.ClientTimeout(total=1),
                    ) as response:
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
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
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
            "status": "SUCCESS",
            "port": result["port"],
            "url": result["url"],
            "pid": result["pid"],
            "job_id": result["pid"],  # Compatibilité scripts PowerShell
            "health_endpoint": f"{result['url']}{self.health_endpoint}",
            "start_time": time.time(),
        }

        info_file = Path("backend_info.json")
        with open(info_file, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2)

        self.logger.info(f"Info backend sauvées: {info_file}")

    def get_status(self) -> Dict[str, Any]:
        """Retourne l'état actuel du backend"""
        return {
            "running": self.process is not None,
            "port": self.current_port,
            "url": self.current_url,
            "pid": self.pid,
            "process": self.process,
        }
