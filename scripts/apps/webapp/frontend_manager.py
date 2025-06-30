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
    - Création de build pour la production
    """

    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        
        # NOTE DE FUSION: On combine la recherche de chemin du stash et la gestion de port de l'upstream.
        self.enabled = config.get('enabled', True)
        self.frontend_path = self._find_frontend_path(config.get('path'))
        self.start_port = config.get('start_port', 3000)
        self.fallback_ports = config.get('fallback_ports', list(range(3001, 3011)))
        self.start_command = config.get('start_command', 'npm start')
        self.build_command = config.get('build_command', 'npm run build')
        self.timeout_seconds = config.get('timeout_seconds', 90)
        self.max_attempts = config.get('max_attempts', 5)
        
        # État runtime
        self.process: Optional[subprocess.Popen] = None
        self.current_port: Optional[int] = None
        self.current_url: Optional[str] = None
        self.pid: Optional[int] = None

    # NOTE DE FUSION: On garde la logique de recherche de `_find_frontend_path`
    # tout en intégrant la logique de démarrage robuste de l'upstream.
    def _find_frontend_path(self, configured_path: Optional[str]) -> Optional[Path]:
        """Trouve le chemin du projet frontend de manière robuste."""
        if configured_path and Path(configured_path).exists():
            self.logger.info(f"Utilisation du chemin frontend configuré : {configured_path}")
            return Path(configured_path)

        project_root = Path(__file__).resolve().parents[3]
        candidate_paths = [
            project_root / "interface_web",
            project_root / "frontend",
            project_root / "services/web_api/interface-web-argumentative"
        ]
        for path in candidate_paths:
            if (path / "package.json").exists():
                self.logger.info(f"Chemin frontend auto-détecté : {path}")
                return path
        
        self.logger.error("Impossible de trouver le répertoire du projet frontend : vérifiez la config ou la structure des dossiers.")
        return None

    async def start_with_failover(self) -> Dict[str, Any]:
        """
        Démarre le serveur de développement frontend en utilisant 'npm start'.
        Cette méthode est plus robuste et standard pour un environnement de développement.
        """
        if not self.enabled:
            return {'success': True, 'error': 'Frontend désactivé'}

        if not self.frontend_path:
            return {'success': False, 'error': 'Chemin du frontend non trouvé.'}

        # S'assurer que les dépendances sont installées avant de démarrer
        if not await self._ensure_dependencies():
            return {'success': False, 'error': "L'installation des dépendances (npm install) a échoué."}

        ports_to_try = [self.start_port] + self.fallback_ports
        
        for port in ports_to_try:
            self.logger.info(f"Tentative de démarrage du serveur de développement sur le port {port}")
            if await self._is_port_occupied(port):
                continue

            result = await self._start_dev_server(port)
            if result['success']:
                self.logger.info(f"[Frontend] [OK] Serveur de développement démarré sur {result['url']}")
                return result
            else:
                self.logger.warning(f"Échec de la tentative sur le port {port}. Raison: {result.get('error', 'Inconnue')}")

        error_msg = f"Impossible de démarrer le serveur de développement sur les ports configurés: {ports_to_try}"
        self.logger.error(error_msg)
        return {'success': False, 'error': error_msg}

    async def _start_dev_server(self, port: int) -> Dict[str, Any]:
        """Démarre le serveur de développement React et capture ses logs en temps réel."""
        host = "localhost"
        env = os.environ.copy()
        env['PORT'] = str(port)
        # Ajout pour empêcher l'ouverture automatique du navigateur, ce qui peut causer des crashs.
        env['BROWSER'] = 'none'
        
        cmd = ['cmd', '/c'] + self.start_command.split() if sys.platform == "win32" else self.start_command.split()
        
        log_listener_tasks = []
        try:
            self.logger.info(f"Exécution de la commande: {' '.join(cmd)} avec PORT={port}")
            self.logger.info("--- DEBUG: Redirection de la sortie standard du frontend vers la console principale ---")
            
            # DEBUG: On redirige la sortie directement vers la console pour un débogage brut
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=None, # Hérite de la sortie standard du parent
                stderr=None, # Hérite de la sortie d'erreur du parent
                cwd=self.frontend_path,
                env=env
            )
            self.pid = self.process.pid
            self.logger.info(f"Processus frontend démarré avec PID: {self.pid}")

            # Les tâches de lecture de stream ne sont plus nécessaires avec la redirection directe
            # log_listener_tasks.append(
            #     asyncio.create_task(self._log_stream(self.process.stdout, logging.INFO))
            # )
            # log_listener_tasks.append(
            #     asyncio.create_task(self._log_stream(self.process.stderr, logging.ERROR))
            # )

            server_ready, url = await self._wait_for_dev_server(port, host)
            
            if server_ready:
                self.current_port = port
                self.current_url = url
                self.logger.info(f"Serveur de développement prêt. URL: {self.current_url}")
                return {'success': True, 'url': self.current_url, 'port': self.current_port, 'pid': self.pid}
            else:
                raise Exception(f"Le serveur de développement n'a pas pu démarrer sur le port {port}.")

        except Exception as e:
            self.logger.error(f"Erreur critique lors du démarrage du serveur de développement: {e}", exc_info=True)
            await self.stop()
            return {'success': False, 'error': str(e)}
        finally:
            # S'assurer que les tâches de lecture des logs sont terminées
            for task in log_listener_tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*log_listener_tasks, return_exceptions=True)

    # async def _log_stream(self, stream, log_level):
    #     """Lit et logue le contenu d'un stream (stdout/stderr) en temps réel."""
    #     while not stream.at_eof():
    #         try:
    #             line = await stream.readline()
    #             if line:
    #                 self.logger.log(log_level, f"[FRONTEND_LOG] {line.decode('utf-8', errors='ignore').strip()}")
    #         except Exception as e:
    #             self.logger.error(f"[FRONTEND_LOG] Erreur de lecture du stream: {e}")
    #             break

    async def _ensure_dependencies(self) -> bool:
        """S'assure que les dépendances npm sont installées. Retourne True si succès."""
        node_modules = self.frontend_path / 'node_modules'
        
        if node_modules.exists():
            self.logger.info("Le dossier 'node_modules' existe déjà. Installation des dépendances sautée.")
            return True

        self.logger.info(f"Le dossier 'node_modules' est manquant. Lancement de 'npm install' dans {self.frontend_path}...")
        
        try:
            cmd = ['cmd', '/c', 'npm', 'install'] if sys.platform == "win32" else ['npm', 'install']
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.frontend_path,
                text=True,
                encoding='utf-8'
            )
            
            stdout, stderr = process.communicate(timeout=180)  # 3 min max
            
            if process.returncode != 0:
                self.logger.error(f"--- ERREUR NPM INSTALL ---")
                self.logger.error(f"Code de retour: {process.returncode}")
                self.logger.error(f"STDOUT:\n{stdout}")
                self.logger.error(f"STDERR:\n{stderr}")
                return False
            else:
                self.logger.info("Dépendances npm installées avec succès.")
                return True
                
        except subprocess.TimeoutExpired:
            process.kill()
            self.logger.error("Timeout (3 minutes) dépassé lors de l'installation des dépendances npm.")
            return False
        except Exception as e:
            self.logger.error(f"Erreur imprévue lors de 'npm install': {e}", exc_info=True)
            return False

    async def _wait_for_dev_server(self, port: int, host: str, timeout: int = 120) -> Tuple[bool, Optional[str]]:
        """Attend que le serveur de développement React soit accessible."""
        start_time = time.time()
        url_to_check = f"http://{host}:{port}/"
        
        self.logger.info(f"Attente du serveur de développement sur {url_to_check} (timeout: {timeout}s)")
        
        # Regex pour détecter le succès dans les logs de React
        success_pattern = re.compile(r'compiled successfully', re.IGNORECASE)

        log_path = Path("logs/frontend_dev_server_stdout.log")

        while time.time() - start_time < timeout:
            # 1. Vérifier si le processus est toujours en cours - TEMPORAIREMENT DÉSACTIVÉ POUR DIAGNOSTIC
            #    Le processus npm semble se terminer même si le serveur webpack continue.
            # if self.process and self.process.returncode is not None:
            #     self.logger.error(f"Serveur de développement terminé prématurément (code: {self.process.returncode}). Les logs ci-dessus devraient indiquer la cause.")
            #     return False, None

            # 2. Sonde HTTP
            #    C'est la méthode la plus fiable pour savoir si le serveur est prêt.
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url_to_check, timeout=3) as response:
                        if response.status == 200:
                            self.logger.info(f"🎉 Serveur de développement accessible via HTTP sur {url_to_check} en {time.time() - start_time:.1f}s.")
                            return True, url_to_check
            except Exception as e:
                # C'est normal si le serveur n'est pas encore prêt.
                # Capturer toutes les exceptions (ClientError, ConnectionRefusedError, etc.)
                # self.logger.debug(f"Sonde HTTP ({url_to_check}) a échoué : {type(e).__name__}. Nouvelle tentative...")
                pass
            
            await asyncio.sleep(2)

        self.logger.error(f"Timeout - Serveur de développement non accessible sur {url_to_check} après {timeout}s")
        return False, None

    async def _is_port_occupied(self, port: int) -> bool:
        """
        Vérifie si un port est déjà occupé et logue le nom du processus coupable.
        """
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                    try:
                        proc = psutil.Process(conn.pid)
                        self.logger.warning(
                            f"Le port {port} est déjà occupé par le processus : "
                            f"'{proc.name()}' (PID: {proc.pid})."
                        )
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        self.logger.warning(
                            f"Le port {port} est déjà occupé par un processus (PID: {conn.pid}), "
                            "mais les détails sont inaccessibles."
                        )
                    return True
        except (psutil.AccessDenied, AttributeError) as e:
            self.logger.warning(f"Impossible de vérifier les ports avec psutil ({e}). Utilisation du fallback.")
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
        """Arrête le processus du serveur de développement frontend."""
        if not self.process:
            return
        
        self.logger.info(f"Tentative d'arrêt du processus frontend (PID: {self.pid})")
        
        # Le processus est un asyncio.subprocess.Process
        if self.process.returncode is None: # Si le processus est toujours en cours
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=10.0)
                self.logger.info(f"Processus frontend (PID: {self.pid}) terminé avec succès.")
            except asyncio.TimeoutError:
                self.logger.warning(f"Le processus frontend (PID: {self.pid}) n'a pas répondu à terminate. Tentative de kill.")
                self.process.kill()
                await self.process.wait()
                self.logger.info(f"Processus frontend (PID: {self.pid}) tué.")
            except Exception as e:
                self.logger.error(f"Erreur lors de l'arrêt du processus frontend : {e}")

        self.process = None
        self.pid = None
        self.current_url = None
        self.current_port = None

    async def build(self) -> bool:
        """Construit l'application React pour la production."""
        if not self.frontend_path:
            self.logger.error("Chemin du frontend non configuré, impossible de construire.")
            return False

        self.logger.info(f"--- Démarrage du Build Frontend ('{self.build_command}') ---")
        
        # S'assurer que les dépendances sont là avant de construire
        if not await self._ensure_dependencies():
            return False

        try:
            cmd = ['cmd', '/c'] + self.build_command.split() if sys.platform == "win32" else self.build_command.split()
            
            # Utilisation de subprocess.Popen pour la cohérence avec le reste du module
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.frontend_path,
                text=True,
                encoding='utf-8'
            )
            
            # Attendre la fin du processus de build
            stdout, stderr = process.communicate(timeout=300) # 5 minutes max pour le build

            if process.returncode != 0:
                self.logger.error(f"--- ERREUR NPM BUILD ---")
                self.logger.error(f"Code de retour: {process.returncode}")
                self.logger.error(f"STDOUT:\n{stdout}")
                self.logger.error(f"STDERR:\n{stderr}")
                return False
            else:
                self.logger.info("--- Build terminé avec succès ---")
                build_dir = self.frontend_path / 'build'
                if build_dir.exists():
                    self.logger.info(f"Artefacts de build trouvés dans: {build_dir}")
                    return True
                else:
                    self.logger.error(f"Build réussi mais dossier '{build_dir}' introuvable.")
                    return False

        except Exception as e:
            self.logger.error(f"Erreur imprévue lors de 'npm run build': {e}", exc_info=True)
            return False
    
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
if __name__ == '__main__':
    """
    Point d'entrée pour l'exécution directe.
    Exemple:
    python scripts/apps/webapp/frontend_manager.py build
    python scripts/apps/webapp/frontend_manager.py start
    """
    import argparse
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
    logger = logging.getLogger("FrontendManagerCLI")

    parser = argparse.ArgumentParser(description="Gestionnaire de build et de serveur de développement Frontend.")
    parser.add_argument('action', choices=['build', 'start'], help="L'action à effectuer: 'build' pour créer les fichiers statiques, 'start' pour lancer le serveur de dev.")
    args = parser.parse_args()

    manager = FrontendManager(config={}, logger=logger)

    async def main():
        if not manager.enabled or not manager.frontend_path:
            logger.error("Frontend Manager n'est pas activé ou le chemin est introuvable. Arrêt.")
            sys.exit(1)

        if args.action == 'build':
            logger.info("--- Démarrage du Build Frontend ---")
            success = await manager.build()
            if success:
                logger.info("--- Build terminé avec succès ---")
                sys.exit(0)
            else:
                logger.error("--- Le Build a échoué ---")
                sys.exit(1)
        
        elif args.action == 'start':
            logger.info("--- Démarrage du Frontend via Build & Serve ---")
            result = await manager.start_with_failover()
            if result.get('success'):
                logger.info(f"Serveur statique démarré avec succès sur {result.get('url')}")
                logger.info("Le serveur tourne en arrière-plan. Terminez le script avec CTRL+C.")
                # Garde le script en vie pour que le serveur continue de tourner
                try:
                    while True:
                        await asyncio.sleep(60)
                except KeyboardInterrupt:
                    logger.info("Arrêt manuel du serveur...")
                    await manager.stop()
                    logger.info("Serveur arrêté.")
            else:
                logger.error(f"--- Échec du démarrage du serveur: {result.get('error')} ---")
                sys.exit(1)

    asyncio.run(main())