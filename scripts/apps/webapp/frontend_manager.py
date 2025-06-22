#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Frontend Manager - Gestionnaire du frontend React (optionnel)
=============================================================

Gère le démarrage et l'arrêt du frontend React quand nécessaire.

Auteur: Projet Intelligence Symbolique EPITA
Date: 07/06/2025
"""

import os
import sys
import time
import asyncio
import logging
import subprocess
import re
from typing import Dict, Optional, Any, Tuple
from pathlib import Path
import aiohttp
import psutil


class FrontendManager:
    """
    Gestionnaire du frontend React
    
    Fonctionnalités :
    - Démarrage serveur de développement React
    - Installation dépendances automatique
    - Health check de l'interface
    - Arrêt propre
    """
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        
        # Configuration
        self.enabled = config.get('enabled', False)
        self.frontend_path = Path(config.get('path', 'services/web_api/interface-web-argumentative'))
        self.start_port = config.get('start_port', 3000)
        self.fallback_ports = config.get('fallback_ports', [3001, 3002])
        self.start_command = config.get('start_command', 'npm start')
        self.timeout_seconds = config.get('timeout_seconds', 90)
        self.max_attempts = config.get('max_attempts', 5)
        
        # État runtime
        self.process: Optional[subprocess.Popen] = None
        self.current_port: Optional[int] = None
        self.current_url: Optional[str] = None
        self.pid: Optional[int] = None
        self.frontend_stdout_log_file: Optional[Any] = None
        self.frontend_stderr_log_file: Optional[Any] = None

    async def start_with_failover(self) -> Dict[str, Any]:
        """
        Démarre le frontend avec failover automatique sur plusieurs ports.
        """
        if not self.enabled:
            return {'success': True, 'error': 'Frontend désactivé'}

        ports_to_try = [self.start_port] + self.fallback_ports

        for attempt in range(1, self.max_attempts + 1):
            port = ports_to_try[(attempt - 1) % len(ports_to_try)]
            self.logger.info(f"Tentative Démarrage Frontend {attempt}/{self.max_attempts} - Port {port}")

            if await self._is_port_occupied(port):
                self.logger.warning(f"Port {port} occupé, prochaine tentative...")
                await asyncio.sleep(1)
                continue

            result = await self._start_on_port(port)
            if result['success']:
                self.current_port = result['port']
                self.current_url = result['url']
                self.pid = result['pid']
                return result

        return {
            'success': False,
            'error': f"Impossible de démarrer le frontend après {self.max_attempts} tentatives."
        }

    async def _start_on_port(self, port: int) -> Dict[str, Any]:
        """
        Démarre le frontend sur un port spécifique.
        """
        try:
            if not self.frontend_path.exists() or not (self.frontend_path / 'package.json').exists():
                return {'success': False, 'error': f'Chemin frontend ou package.json invalide: {self.frontend_path}'}

            await self._ensure_dependencies()

            self.logger.info(f"Lancement frontend sur port {port} avec: {self.start_command}")
            
            cmd = self.start_command.split()
            if sys.platform == "win32":
                cmd = ['cmd', '/c'] + cmd

            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            stdout_log = log_dir / "frontend_stdout.log"
            stderr_log = log_dir / "frontend_stderr.log"

            # Utilisation de with pour s'assurer que les fichiers sont fermés
            with open(stdout_log, "wb") as stdout_f, open(stderr_log, "wb") as stderr_f:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=stdout_f,
                    stderr=stderr_f,
                    cwd=self.frontend_path,
                    env=self._get_frontend_env(port)
                )

            frontend_ready, final_port, final_url = await self._wait_for_frontend(port)

            if frontend_ready:
                self.current_port = final_port
                self.current_url = final_url
                self.pid = self.process.pid
                return {'success': True, 'url': self.current_url, 'port': self.current_port, 'pid': self.pid}
            else:
                if self.process:
                    self.process.terminate()
                    self.process = None
                return {'success': False, 'error': f'Frontend non accessible sur le port {port} après {self.timeout_seconds}s'}

        except Exception as e:
            self.logger.error(f"Erreur majeure au démarrage du frontend sur port {port}: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    async def _ensure_dependencies(self):
        """S'assure que les dépendances npm sont installées"""
        node_modules = self.frontend_path / 'node_modules'
        
        if not node_modules.exists():
            self.logger.info("Installation dépendances npm...")
            
            try:
                process = subprocess.Popen(
                    ['npm', 'install'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=self.frontend_path
                )
                
                stdout, stderr = process.communicate(timeout=120)  # 2 min max
                
                if process.returncode != 0:
                    self.logger.error(f"Échec npm install: {stderr.decode()}")
                else:
                    self.logger.info("Dépendances npm installées")
                    
            except subprocess.TimeoutExpired:
                process.kill()
                self.logger.error("Timeout installation npm")
            except Exception as e:
                self.logger.error(f"Erreur npm install: {e}")
    
    def _get_frontend_env(self, port: int) -> Dict[str, str]:
        """Prépare l'environnement pour le frontend avec un port dynamique."""
        env = os.environ.copy()
        env.update({
            'BROWSER': 'none',
            'PORT': str(port),
            'GENERATE_SOURCEMAP': 'false',
            'SKIP_PREFLIGHT_CHECK': 'true'
        })
        return env

    async def _wait_for_frontend(self, initial_port: int) -> Tuple[bool, Optional[int], Optional[str]]:
        """Attend que le frontend soit accessible."""
        start_time = time.time()
        end_time = start_time + self.timeout_seconds
        
        detected_port = initial_port
        
        while time.time() < end_time:
            # Vérifier si le processus est toujours actif
            if self.process.poll() is not None:
                self.logger.error(f"Processus frontend terminé prématurément (code: {self.process.returncode}).")
                return False, None, None

            # Tentative de détection du port depuis les logs (Create React App peut changer de port)
            log_file = Path("logs/frontend_stdout.log")
            if log_file.exists():
                try:
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        log_content = f.read()
                    match = re.search(r"Local:\s+(http://localhost:(\d+))", log_content)
                    if match:
                        new_port = int(match.group(2))
                        if new_port != detected_port:
                            self.logger.info(f"React a changé de port: {detected_port} -> {new_port}")
                            detected_port = new_port
                except Exception:
                    pass

            url_to_check = f"http://localhost:{detected_port}"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url_to_check, timeout=5) as response:
                        if response.status == 200:
                            self.logger.info(f"🎉 Frontend accessible sur {url_to_check} après {time.time() - start_time:.1f}s.")
                            return True, detected_port, url_to_check
            except aiohttp.ClientError:
                pass # On continue d'attendre

            await asyncio.sleep(2)

        self.logger.error(f"Timeout - Frontend non accessible sur {url_to_check} après {self.timeout_seconds}s")
        return False, None, None

    async def _is_port_occupied(self, port: int) -> bool:
        """Vérifie si un port est déjà occupé."""
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                    return True
        except (psutil.AccessDenied, AttributeError):
            # Fallback pour les systèmes où psutil a des limitations
            try:
                with aiohttp.ClientSession() as session:
                    async with session.get(f"http://127.0.0.1:{port}", timeout=1):
                        return True
            except:
                pass
        return False

    async def health_check(self) -> bool:
        """Vérifie l'état de santé du frontend"""
        if not self.current_url:
            return False
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.current_url, 
                                     timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        self.logger.info("Frontend health OK")
                        return True
        except Exception as e:
            self.logger.error(f"Frontend health check échec: {e}")
            
        return False
    
    async def stop(self):
        """Arrête le frontend proprement"""
        if self.process:
            try:
                self.logger.info(f"Arrêt frontend PID {self.process.pid}")
                
                # Terminaison progressive
                self.process.terminate()
                
                # Attente arrêt propre (10s max pour React)
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill si nécessaire
                    self.process.kill()
                    self.process.wait()
                    
                self.logger.info("Frontend arrêté")
                
            except Exception as e:
                self.logger.error(f"Erreur arrêt frontend: {e}")
            finally:
                if self.frontend_stdout_log_file:
                    try:
                        self.frontend_stdout_log_file.close()
                    except Exception as log_e:
                        self.logger.error(f"Erreur fermeture frontend_stdout_log_file: {log_e}")
                    self.frontend_stdout_log_file = None
                
                if self.frontend_stderr_log_file:
                    try:
                        self.frontend_stderr_log_file.close()
                    except Exception as log_e:
                        self.logger.error(f"Erreur fermeture frontend_stderr_log_file: {log_e}")
                    self.frontend_stderr_log_file = None

                self.process = None
                self.current_url = None
                self.pid = None
    
    def get_status(self) -> Dict[str, Any]:
        """Retourne l'état actuel du frontend"""
        return {
            'enabled': self.enabled,
            'running': self.process is not None,
            'port': self.current_port,
            'url': self.current_url,
            'pid': self.pid,
            'path': str(self.frontend_path),
            'process': self.process
        }