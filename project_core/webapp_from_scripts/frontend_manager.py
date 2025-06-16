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
import socket
import http.server
import socketserver
import threading

class FrontendManager:
    """
    Gestionnaire du frontend React
    
    Fonctionnalités :
    - Démarrage serveur de développement React
    - Installation dépendances automatique
    - Health check de l'interface
    - Arrêt propre
    """
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger, backend_url: Optional[str] = None, env: Optional[Dict[str, str]] = None):
        self.config = config
        self.logger = logger
        self.backend_url = backend_url
        self.env = env
        
        # Configuration
        self.enabled = config.get('enabled', False)
        self.frontend_path = Path(config.get('path', 'services/web_api/interface-web-argumentative'))
        self.port = config.get('port', 3000)
        self.start_command = config.get('start_command', 'npm start')
        self.timeout_seconds = config.get('timeout_seconds', 180)
        
        # État runtime
        self.static_server = None
        self.static_server_thread = None
        self.build_dir = None
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
            
            # Préparation de l'environnement. On utilise celui fourni par l'orchestrateur s'il existe.
            if self.env:
                frontend_env = self.env
                self.logger.info("Utilisation de l'environnement personnalisé fourni par l'orchestrateur.")
                # Mettre à jour le port du manager si défini dans l'env, pour la cohérence (ex: health_check)
                if 'PORT' in frontend_env:
                    try:
                        self.port = int(frontend_env['PORT'])
                        self.logger.info(f"Port du FrontendManager synchronisé à {self.port} depuis l'environnement.")
                    except (ValueError, TypeError):
                        self.logger.warning(f"La variable d'environnement PORT ('{frontend_env.get('PORT')}') n'est pas un entier valide.")
            else:
                self.logger.info("Aucun environnement personnalisé, construction d'un environnement par défaut.")
                frontend_env = self._get_frontend_env()

            # Installation dépendances si nécessaire
            await self._ensure_dependencies(frontend_env)
            
            # Build de l'application React
            self.logger.info("Construction de l'application React avec 'npm run build'")
            await self._build_react_app(frontend_env)
            
            # Démarrage du serveur de fichiers statiques
            self.logger.info(f"Démarrage du serveur de fichiers statiques sur le port {self.port}")
            self._start_static_server()
            
            # Attente démarrage via health check
            frontend_ready = await self._wait_for_health_check()
            
            if frontend_ready:
                self.current_url = f"http://localhost:{self.port}"
                # Pour le serveur statique, on n'a pas de process.pid traditionnel
                self.pid = getattr(self.static_server_thread, 'ident', None) if self.static_server_thread else None
                
                return {
                    'success': True,
                    'url': self.current_url,
                    'port': self.port,
                    'pid': self.pid,
                    'error': None
                }
            else:
                # Échec - cleanup
                self._stop_static_server()
                    
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
        
        # Toujours exécuter `npm install` pour garantir la fraîcheur des dépendances dans un contexte de test.
        # Cela évite les erreurs dues à un `node_modules` incomplet ou obsolète.
        self.logger.info("Lancement de 'npm install' pour garantir la fraîcheur des dépendances...")
        
        try:
            # Utilisation de l'environnement préparé pour trouver npm
            cmd = ['npm', 'install']
            # Sur Windows, npm.cmd est un script batch, il est donc plus fiable de l'exécuter avec `shell=True`.
            # La commande est jointe en une chaîne pour que le shell puisse l'interpréter correctement.
            is_windows = sys.platform == "win32"
            command_to_run = ' '.join(cmd) if is_windows else cmd

            process = subprocess.Popen(
                command_to_run,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.frontend_path,
                env=env,
                shell=is_windows,
                text=True, # Utiliser le mode texte pour un décodage automatique
                encoding='utf-8',
                errors='replace'
            )
            
            # Utilisation de communicate() pour lire stdout/stderr et attendre la fin.
            # Un timeout long est nécessaire car npm install peut être lent.
            stdout, stderr = process.communicate(timeout=300)  # 5 minutes de timeout
            
            if process.returncode != 0:
                self.logger.error(f"Échec de 'npm install'. Code de retour: {process.returncode}")
                self.logger.error(f"--- STDOUT ---\n{stdout}")
                self.logger.error(f"--- STDERR ---\n{stderr}")
                # Lever une exception pour que l'échec soit clair.
                raise RuntimeError(f"npm install a échoué avec le code {process.returncode}")
            else:
                self.logger.info("'npm install' terminé avec succès.")
                if stdout:
                     self.logger.debug(f"--- STDOUT de npm install ---\n{stdout}")
                
        except subprocess.TimeoutExpired:
            process.kill()
            self.logger.error("Timeout de 5 minutes dépassé pour 'npm install'. Le processus a été tué.")
            raise
        except Exception as e:
            self.logger.error(f"Erreur inattendue pendant 'npm install': {e}", exc_info=True)
            raise
    
    def _get_frontend_env(self) -> Dict[str, str]:
        """Prépare l'environnement pour le frontend"""
        env = os.environ.copy()
        
        # Variables spécifiques React
        env.update({
            'BROWSER': 'none',  # Empêche ouverture automatique navigateur
            'PORT': str(self.port),
            'GENERATE_SOURCEMAP': 'false',  # Performance
            'SKIP_PREFLIGHT_CHECK': 'true',  # Évite erreurs compatibilité
            'CI': 'false' # Force le mode non-interactif, mais en ignorant les warnings comme des erreurs
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

    async def _wait_for_health_check(self) -> bool:
        """Attend que le frontend soit prêt en effectuant des health checks réseau."""
        self.logger.info(f"Attente du frontend sur http://127.0.0.1:{self.port} (timeout: {self.timeout_seconds}s)")
        
        start_time = time.monotonic()
        
        # Pause initiale pour laisser le temps au serveur de dev de se lancer.
        # Create-react-app peut être lent à démarrer.
        initial_pause_s = 120
        self.logger.info(f"Pause initiale de {initial_pause_s}s avant health checks...")
        await asyncio.sleep(initial_pause_s)

        while time.monotonic() - start_time < self.timeout_seconds:
            if await self.health_check():
                self.logger.info("Frontend accessible.")
                return True
            
            # Vérifier si le processus n'a pas crashé
            if self.process and self.process.poll() is not None:
                self.logger.error(f"Le processus frontend s'est terminé prématurément avec le code {self.process.returncode}. Voir logs/frontend_stderr.log")
                return False

            await asyncio.sleep(2) # Attendre 2s entre les checks

        self.logger.error("Timeout - Le frontend n'est pas devenu accessible dans le temps imparti.")
        return False

    def _is_port_in_use(self, port: int) -> bool:
        """Vérifie si un port est en écoute (TCP)."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
            except socket.error as e:
                if e.errno == 98 or e.errno == 10048:  # 98: EADDRINUSE, 10048: WSAEADDRINUSE
                    self.logger.info(f"Le port {port} est bien en cours d'utilisation.")
                    return True
                else:
                    self.logger.warning(f"Erreur inattendue en vérifiant le port {port}: {e}")
                    return False
            return False
            
    async def health_check(self) -> bool:
        """Vérifie l'état de santé du frontend en testant si le port est ouvert."""
        # Note: self.current_url est défini *après* le health_check.
        # On se base uniquement sur le port ici.
        self.logger.debug(f"Vérification de l'état du port {self.port}...")
        
        # Le health check HTTP est trop instable. On se contente de vérifier que le port est ouvert.
        # C'est moins précis mais beaucoup plus robuste dans cet environnement.
        if self._is_port_in_use(self.port):
            self.logger.info(f"Health check bas niveau réussi: le port {self.port} est actif.")
            return True
        else:
            self.logger.debug(f"Health check bas niveau échoué: le port {self.port} n'est pas actif.")
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