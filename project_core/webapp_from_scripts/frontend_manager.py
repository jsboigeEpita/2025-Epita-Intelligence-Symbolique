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
            
            # Préparation de l'environnement qui sera utilisé pour toutes les commandes npm
            frontend_env = self._get_frontend_env()

            # Installation dépendances si nécessaire
            await self._ensure_dependencies(frontend_env)
            
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

            # Sur Windows, il est plus robuste d'utiliser shell=True avec la commande sous forme de chaîne
            # pour que le PATH de l'environnement soit correctement interprété.
            start_cmd_str = ' '.join(self.start_command.split())
            self.process = subprocess.Popen(
                start_cmd_str,
                stdout=self.frontend_stdout_log_file,
                stderr=self.frontend_stderr_log_file,
                cwd=self.frontend_path,
                env=frontend_env,
                shell=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
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
    
    async def _ensure_dependencies(self, env: Dict[str, str]):
        """S'assure que les dépendances npm sont installées"""
        node_modules = self.frontend_path / 'node_modules'
        
        if not node_modules.exists():
            self.logger.info("Le répertoire 'node_modules' est manquant. Lancement de 'npm install'...")
            
            try:
                # Utilisation de l'environnement préparé pour trouver npm
                cmd = ['npm', 'install']
                if sys.platform == "win32":
                    # Sur windows, Popen a besoin de shell=True pour trouver npm.cmd via le PATH modifié
                    process = subprocess.Popen(
                        ' '.join(cmd),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=self.frontend_path,
                        env=env,
                        shell=True
                    )
                else:
                    # Sur les autres systèmes, la liste de commandes avec env fonctionne bien.
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=self.frontend_path,
                        env=env
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
            'SKIP_PREFLIGHT_CHECK': 'true',  # Évite erreurs compatibilité
            'CI': 'true' # Force le mode non-interactif
        })
        
        # Ajout du chemin npm/node à l'environnement
        npm_path = self._find_npm_executable()
        if npm_path:
            self.logger.info(f"Utilisation de npm trouvé dans: {npm_path}")
            # Ajout au PATH pour que Popen le trouve
            env['PATH'] = f"{npm_path}{os.pathsep}{env.get('PATH', '')}"
        else:
            self.logger.warning("npm non trouvé via les méthodes de recherche. Utilisation du PATH système.")
            
        return env

    def _find_npm_executable(self) -> Optional[str]:
        """
        Trouve l'exécutable npm en cherchant dans des emplacements connus.
        - Variable d'environnement NPM_HOME ou NODE_HOME
        - Chemins standards (non implémenté pour l'instant pour rester portable)
        """
        # 1. Vérifier les variables d'environnement
        for var in ['NPM_HOME', 'NODE_HOME']:
            home_path = os.environ.get(var)
            if home_path and Path(home_path).exists():
                npm_dir = Path(home_path)
                # Sur Windows, npm.cmd est souvent directement dans le répertoire
                # Sur Linux/macOS, dans le sous-répertoire 'bin'
                if sys.platform == "win32":
                    executable = npm_dir / 'npm.cmd'
                    if executable.is_file():
                        return str(npm_dir)
                else:
                    executable = npm_dir / 'bin' / 'npm'
                    if executable.is_file():
                        return str(npm_dir / 'bin')

        # 2. (Optionnel) chercher dans des chemins hardcodés si nécessaire
        # ...

        self.logger.debug("NPM_HOME ou NODE_HOME non trouvées ou invalides.")
        return None

    async def _wait_for_frontend(self) -> bool:
        """Attend que le frontend soit accessible"""
        url = f"http://localhost:{self.port}"
        start_time = time.time()
        
        # Attente initiale pour démarrage React
        await asyncio.sleep(30)
        
        while time.time() - start_time < self.timeout_seconds:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            self.logger.info(f"Frontend accessible sur {url}")
                            return True
            except Exception:
                # Continue à attendre
                pass
                
            await asyncio.sleep(3)
        
        self.logger.error(f"Timeout - Frontend non accessible sur {url}")
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