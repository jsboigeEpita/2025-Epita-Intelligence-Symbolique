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
import threading
from typing import Dict, List, Optional, Any, IO
from pathlib import Path
import aiohttp

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
        self.timeout_seconds = config.get('timeout_seconds', 180) # Augmentation du timeout
        self.health_endpoint = config.get('health_endpoint', '/api/health')
        self.env_activation = config.get('env_activation',
                                       'powershell -File scripts/env/activate_project_env.ps1')
        
        # État runtime
        self.process: Optional[subprocess.Popen] = None
        self.current_port: Optional[int] = None
        self.current_url: Optional[str] = None
        self.pid: Optional[int] = None
        self.log_threads: List[threading.Thread] = []
        
    async def start_with_failover(self) -> Dict[str, Any]:
        """
        Démarre le backend avec failover automatique sur plusieurs ports
        
        Returns:
            Dict contenant success, url, port, pid, error
        """
        ports_to_try = [self.start_port] + self.fallback_ports
        
        for attempt in range(1, self.max_attempts + 1):
            port = ports_to_try[(attempt - 1) % len(ports_to_try)]
            self.logger.info(f"Tentative {attempt}/{self.max_attempts} - Port {port}")

            if await self._is_port_occupied(port):
                self.logger.warning(f"Port {port} occupé, nouvelle tentative dans 2s...")
                await asyncio.sleep(2)
                continue

            result = await self._start_on_port(port)
            if result['success']:
                self.current_port = port
                self.current_url = result['url']
                self.pid = result['pid']
                
                await self._save_backend_info(result)
                return result
            else:
                 self.logger.warning(f"Echec tentative {attempt} sur le port {port}. Erreur: {result.get('error', 'Inconnue')}")
                 await asyncio.sleep(1) # Courte pause avant de réessayer

        return {
            'success': False,
            'error': f"Impossible de démarrer le backend après {self.max_attempts} tentatives sur les ports {ports_to_try}",
            'url': None,
            'port': None,
            'pid': None
        }
    
    def _log_stream(self, stream: IO[str], log_level: int):
        """Lit un stream et logue chaque ligne."""
        try:
            for line in iter(stream.readline, ''):
                if line:
                    self.logger.log(log_level, f"[BACKEND] {line.strip()}")
            stream.close()
        except Exception as e:
            self.logger.error(f"Erreur dans le thread de logging: {e}")

    async def _start_on_port(self, port: int) -> Dict[str, Any]:
        """Démarre le backend sur un port spécifique"""
        try:
            server_type = self.config.get('server_type', 'uvicorn')
            if server_type == 'uvicorn':
                asgi_module = 'argumentation_analysis.services.web_api.asgi:app'
                cmd = ['uvicorn', asgi_module, '--port', str(port), '--host', '0.0.0.0']
            else:
                cmd = ['python', '-m', self.module, '--port', str(port)]
            
            self.logger.info(f"Démarrage backend: {' '.join(cmd)}")
            
            env = os.environ.copy()
            env['PYTHONPATH'] = str(Path.cwd())
            env['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
            self.logger.info("Variable d'environnement KMP_DUPLICATE_LIB_OK=TRUE définie pour contourner le conflit OpenMP.")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path.cwd(),
                env=env,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # Démarrer les threads de logging
            self.log_threads = []
            if self.process.stdout:
                stdout_thread = threading.Thread(target=self._log_stream, args=(self.process.stdout, logging.INFO))
                stdout_thread.daemon = True
                stdout_thread.start()
                self.log_threads.append(stdout_thread)

            if self.process.stderr:
                stderr_thread = threading.Thread(target=self._log_stream, args=(self.process.stderr, logging.ERROR))
                stderr_thread.daemon = True
                stderr_thread.start()
                self.log_threads.append(stderr_thread)

            backend_ready = await self._wait_for_backend(port)
            
            if backend_ready:
                url = f"http://localhost:{port}"
                return {'success': True, 'url': url, 'port': port, 'pid': self.process.pid, 'error': None}
            else:
                error_msg = f'Backend non accessible sur port {port} après {self.timeout_seconds}s'
                # Le processus est déjà terminé via _wait_for_backend
                return {'success': False, 'error': error_msg, 'url': None, 'port': None, 'pid': None}
                
        except Exception as e:
            self.logger.error(f"Erreur Démarrage Backend (port {port}): {e}", exc_info=True)
            return {'success': False, 'error': str(e), 'url': None, 'port': None, 'pid': None}
    
    async def _wait_for_backend(self, port: int) -> bool:
        """Attend que le backend soit accessible via health check avec une patience accrue."""
        url = f"http://localhost:{port}{self.health_endpoint}"
        start_time = time.time()
        self.logger.info(f"Attente backend sur {url} (timeout: {self.timeout_seconds}s)")

        # Boucle principale avec un timeout global long
        while time.time() - start_time < self.timeout_seconds:
            # Vérifie si le processus est toujours en cours d'exécution
            if self.process.poll() is not None:
                self.logger.error(f"Processus backend terminé prématurément (code: {self.process.returncode}). Voir logs pour détails.")
                return False

            try:
                # Tente une connexion avec un timeout de connexion raisonnable (10s)
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            self.logger.info(f"🎉 Backend accessible sur {url} après {time.time() - start_time:.1f}s.")
                            return True
                        else:
                            self.logger.debug(f"Health check a échoué avec status {response.status}")
            except aiohttp.ClientConnectorError as e:
                elapsed = time.time() - start_time
                self.logger.debug(f"Tentative health check (connexion refusée) après {elapsed:.1f}s: {type(e).__name__}")
            except asyncio.TimeoutError:
                 elapsed = time.time() - start_time
                 self.logger.debug(f"Tentative health check (timeout) après {elapsed:.1f}s.")
            except aiohttp.ClientError as e:
                elapsed = time.time() - start_time
                self.logger.warning(f"Erreur client inattendue lors du health check après {elapsed:.1f}s: {type(e).__name__} - {e}")

            # Pause substantielle entre les tentatives pour ne pas surcharger et laisser le temps au serveur de démarrer.
            await asyncio.sleep(5)

        # Si la boucle se termine, c'est un échec définitif par timeout global.
        self.logger.error(f"Timeout global atteint ({self.timeout_seconds}s) - Backend non accessible sur {url}")
        if self.process.poll() is None:
            self.logger.error("Le processus Backend est toujours en cours mais ne répond pas. Terminaison forcée...")
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