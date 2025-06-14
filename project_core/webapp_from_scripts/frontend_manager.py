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
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger, backend_url: Optional[str] = None):
        self.config = config
        self.logger = logger
        self.backend_url = backend_url
        
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
            
            # Ce bloc est maintenant géré ci-dessous avec une logique plus robuste.
            
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

            self.frontend_stderr_log_file = open(log_dir / "frontend_stderr.log", "wb")
            self.logger.info(f"Redirection stderr du frontend vers: {log_dir / 'frontend_stderr.log'}")

            # On capture stdout pour détecter le démarrage, et stderr est redirigé vers un fichier de log
            if sys.platform == "win32":
                cmd = ['npm.cmd'] + self.start_command.split()[1:]
                shell = False
            else:
                cmd = self.start_command
                shell = True

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,  # Capture de la sortie standard
                stderr=subprocess.STDOUT, # Fusionner stdout et stderr pour tout capturer
                cwd=self.frontend_path,
                env=frontend_env,
                shell=shell,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
                universal_newlines=True, # Décode la sortie en texte
                encoding='utf-8',
                errors='replace'
            )
            
            # Attente démarrage en lisant la sortie
            frontend_ready = await self._wait_for_frontend_output()
            
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
            self.logger.error(f"Erreur démarrage frontend: {e}", exc_info=True)
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

        if self.backend_url:
            env['REACT_APP_API_URL'] = self.backend_url
            self.logger.info(f"Injection de REACT_APP_API_URL={self.backend_url} dans l'environnement du frontend.")
        else:
            self.logger.warning("Aucune backend_url fournie au FrontendManager. Le frontend pourrait utiliser une URL par défaut incorrecte.")

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

    async def _wait_for_frontend_output(self) -> bool:
        """
        Attend que le frontend soit prêt en lisant sa sortie standard (stdout).
        C'est plus fiable que le polling réseau.
        """
        self.logger.info("Attente du message de succès dans la sortie du frontend...")
        
        if not self.process or not self.process.stdout:
            self.logger.error("Le processus frontend n'a pas de flux stdout à lire.")
            return False

        try:
            # On utilise asyncio.wait_for pour gérer le timeout global
            await asyncio.wait_for(self._read_stdout_and_check(), timeout=self.timeout_seconds)
            self.logger.info("Message 'Compiled successfully' détecté. Le frontend est prêt.")
            return True
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout - Le message de succès du frontend n'a pas été trouvé après {self.timeout_seconds}s.")
            return False
        except Exception as e:
            self.logger.error(f"Erreur inattendue en attendant la sortie du frontend: {e}", exc_info=True)
            return False

    async def _read_stdout_and_check(self):
        """Tâche asynchrone pour lire stdout ligne par ligne."""
        loop = asyncio.get_event_loop()
         # La chaîne à rechercher. Peut être adaptée si les logs de react-scripts changent.
        success_strings = ["Compiled successfully!", "webpack compiled successfully", "webpack compiled with"]
        
        while True:
            if not self.process or not self.process.stdout:
                break
            
            # Utilise run_in_executor pour ne pas bloquer la boucle asyncio avec readline()
            line = await loop.run_in_executor(None, self.process.stdout.readline)
            
            if not line:
                # Le processus s'est peut-être terminé prématurément
                await asyncio.sleep(0.1) # Petite attente pour éviter une boucle trop rapide
                if self.process.poll() is not None:
                    self.logger.error("Le processus frontend s'est terminé prématurément.")
                    break
                continue

            self.logger.debug(f"[Frontend stdout] {line.strip()}")
            
            # Vérifie si l'une des chaînes de succès est présente
            if any(s in line for s in success_strings):
                return # La condition est remplie, on sort

    
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