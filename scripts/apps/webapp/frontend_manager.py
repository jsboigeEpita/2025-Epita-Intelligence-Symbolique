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
from typing import Dict, Optional, Any
from pathlib import Path
import aiohttp

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
        self.port = config.get('port', 3000)
        self.start_command = config.get('start_command', 'npm start')
        self.timeout_seconds = config.get('timeout_seconds', 90)
        
        # État runtime
        self.process: Optional[subprocess.Popen] = None
        self.current_url: Optional[str] = None
        self.pid: Optional[int] = None
        self.frontend_stdout_log_file: Optional[Any] = None
        self.frontend_stderr_log_file: Optional[Any] = None
        
    async def start(self) -> Dict[str, Any]:
        """
        Démarre le frontend React
        
        Returns:
            Dict contenant success, url, port, pid, error
        """
        if not self.enabled:
            return {
                'success': True,
                'url': None,
                'port': None,
                'pid': None,
                'error': 'Frontend désactivé'
            }
        
        try:
            # Vérification chemin frontend
            if not self.frontend_path.exists():
                return {
                    'success': False,
                    'error': f'Chemin frontend introuvable: {self.frontend_path}',
                    'url': None,
                    'port': None,
                    'pid': None
                }
            
            package_json = self.frontend_path / 'package.json'
            if not package_json.exists():
                return {
                    'success': False,
                    'error': f'package.json introuvable: {package_json}',
                    'url': None,
                    'port': None,
                    'pid': None
                }
            
            # Installation dépendances si nécessaire
            await self._ensure_dependencies()
            
            # Démarrage serveur React
            self.logger.info(f"Démarrage frontend: {self.start_command}")
            
            if sys.platform == "win32":
                cmd = ['cmd', '/c'] + self.start_command.split()
            else:
                cmd = ['sh', '-c', self.start_command]
            
            # Préparation des fichiers de log pour le frontend
            log_dir = Path("logs")
            log_dir.mkdir(parents=True, exist_ok=True) # parents=True pour créer logs/ si besoin
            
            # S'assurer de fermer les anciens fichiers de log s'ils existent
            if self.frontend_stdout_log_file:
                try:
                    self.frontend_stdout_log_file.close()
                except Exception:
                    pass # Ignorer les erreurs de fermeture
            if self.frontend_stderr_log_file:
                try:
                    self.frontend_stderr_log_file.close()
                except Exception:
                    pass

            self.frontend_stdout_log_file = open(log_dir / "frontend_stdout.log", "wb") # 'wb' pour write bytes (écrase)
            self.frontend_stderr_log_file = open(log_dir / "frontend_stderr.log", "wb") # 'wb' pour write bytes (écrase)

            self.logger.info(f"Redirection stdout du frontend vers: {log_dir / 'frontend_stdout.log'}")
            self.logger.info(f"Redirection stderr du frontend vers: {log_dir / 'frontend_stderr.log'}")

            self.process = subprocess.Popen(
                cmd,
                stdout=self.frontend_stdout_log_file,
                stderr=self.frontend_stderr_log_file,
                cwd=self.frontend_path,
                env=self._get_frontend_env()
            )
            
            # Attente démarrage
            frontend_ready = await self._wait_for_frontend()
            
            if frontend_ready:
                self.current_url = f"http://localhost:{self.port}"
                self.pid = self.process.pid
                
                return {
                    'success': True,
                    'url': self.current_url,
                    'port': self.port,
                    'pid': self.pid,
                    'error': None
                }
            else:
                # Échec - cleanup
                if self.process:
                    self.process.terminate()
                    self.process = None
                    
                return {
                    'success': False,
                    'error': f'Frontend non accessible après {self.timeout_seconds}s',
                    'url': None,
                    'port': None,
                    'pid': None
                }
                
        except Exception as e:
            self.logger.error(f"Erreur démarrage frontend: {e}")
            return {
                'success': False,
                'error': str(e),
                'url': None,
                'port': None,
                'pid': None
            }
    
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
    
    def _get_frontend_env(self) -> Dict[str, str]:
        """Prépare l'environnement pour le frontend"""
        env = os.environ.copy()
        
        # Variables spécifiques React
        env.update({
            'BROWSER': 'none',  # Empêche ouverture automatique navigateur
            'PORT': str(self.port),
            'GENERATE_SOURCEMAP': 'false',  # Performance
            'SKIP_PREFLIGHT_CHECK': 'true'  # Évite erreurs compatibilité
        })
        
        return env
    
    async def _wait_for_frontend(self) -> bool:
        """Attend que le frontend soit accessible, en gérant le failover de port de React."""
        start_time = time.time()
        url = None
        
        # Attendre un peu que le log soit écrit
        await asyncio.sleep(15)

        end_time = time.time() + self.timeout_seconds
        
        while time.time() < end_time:
            # 1. Essayer de détecter le port depuis les logs
            try:
                log_file = Path("logs/frontend_stdout.log")
                if log_file.exists():
                    # Fermer et rouvrir pour lire le contenu le plus récent
                    if self.frontend_stdout_log_file:
                        self.frontend_stdout_log_file.close()

                    with open(log_file, "r", encoding="utf-8") as f:
                        log_content = f.read()

                    # Ré-ouvrir en mode binaire pour l'écriture
                    self.frontend_stdout_log_file = open(log_file, "ab")
                    
                    match = re.search(r"Local:\s+(http://localhost:(\d+))", log_content)
                    if match:
                        detected_url = match.group(1)
                        detected_port = int(match.group(2))
                        if self.port != detected_port:
                            self.logger.info(f"Port frontend détecté: {detected_port} (failover de {self.port})")
                            self.port = detected_port
                        url = detected_url
                        break # Port trouvé, passer au health check
            except Exception as e:
                self.logger.warning(f"Impossible de lire le log du frontend pour détecter le port: {e}")

            await asyncio.sleep(5)

        if not url:
            url = f"http://localhost:{self.port}"
            self.logger.warning(f"Port non détecté dans les logs, tentative sur le port par défaut : {self.port}")

        # 2. Health check sur l'URL (détectée ou par défaut)
        while time.time() < end_time:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            self.logger.info(f"Frontend accessible sur {url}")
                            self.current_url = url # Mettre à jour l'URL finale
                            return True
            except Exception:
                pass  # Continue à attendre
            
            await asyncio.sleep(3)

        self.logger.error(f"Timeout - Frontend non accessible sur {url} après {self.timeout_seconds}s")
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
            'port': self.port,
            'url': self.current_url,
            'pid': self.pid,
            'path': str(self.frontend_path),
            'process': self.process
        }