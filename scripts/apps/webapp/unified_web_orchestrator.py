#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orchestrateur Unifié d'Application Web Python
==============================================

Remplace tous les scripts PowerShell redondants d'intégration web :
- integration_test_with_trace.ps1
- integration_test_with_trace_robust.ps1  
- integration_test_with_trace_fixed.ps1
- integration_test_trace_working.ps1
- integration_test_trace_simple_success.ps1
- sprint3_final_validation.py
- test_backend_fixed.ps1

Auteur: Projet Intelligence Symbolique EPITA
Date: 07/06/2025
"""

import os
import sys
import time
import json
import yaml
import asyncio
import logging
import argparse
import subprocess
import threading
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

# Correction du chemin pour les imports internes
# Le script est dans D:/.../scripts/apps/webapp/ ; la racine du projet est 3 niveaux au-dessus.
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Imports internes
from scripts.apps.webapp.backend_manager import BackendManager
from scripts.apps.webapp.frontend_manager import FrontendManager
from scripts.apps.webapp.playwright_runner import PlaywrightRunner
from scripts.apps.webapp.process_cleaner import ProcessCleaner

# Import du gestionnaire centralisé des ports
try:
    from project_core.config.port_manager import PortManager, get_port_manager, set_environment_variables
    CENTRAL_PORT_MANAGER_AVAILABLE = True
except ImportError as e:
    CENTRAL_PORT_MANAGER_AVAILABLE = False
    print(f"[WARNING] Gestionnaire centralisé des ports non disponible ({e}), utilisation des ports par défaut")

class WebAppStatus(Enum):
    """États de l'application web"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    STOPPING = "stopping"

@dataclass
class TraceEntry:
    """Entrée de trace d'action"""
    timestamp: str
    action: str
    details: str = ""
    result: str = ""
    screenshot: str = ""
    status: str = "success"

@dataclass
class WebAppInfo:
    """Informations sur l'état de l'application web"""
    backend_url: Optional[str] = None
    backend_port: Optional[int] = None
    backend_pid: Optional[int] = None
    frontend_url: Optional[str] = None
    frontend_port: Optional[int] = None
    frontend_pid: Optional[int] = None
    status: WebAppStatus = WebAppStatus.STOPPED
    start_time: Optional[datetime] = None

class UnifiedWebOrchestrator:
    """
    Orchestrateur unifié pour applications web Python
    
    Fonctionnalités principales :
    - Démarrage/arrêt backend Flask avec failover de ports
    - Démarrage/arrêt frontend React (optionnel)
    - Exécution tests Playwright intégrés
    - Tracing complet des opérations
    - Cleanup automatique des processus
    - Configuration centralisée
    """
    
    def __init__(self, config_path: str = "config/webapp_config.yml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.logger = self._setup_logging()
        
        # Gestionnaires spécialisés
        self.process_cleaner = ProcessCleaner(self.logger)
        self.backend_manager = BackendManager(self.config.get('backend', {}), self.logger)
        self.frontend_manager = FrontendManager(self.config.get('frontend', {}), self.logger, self.process_cleaner)
        self.playwright_runner = PlaywrightRunner(self.config.get('playwright', {}), self.logger)
        
        # État de l'application
        self.app_info = WebAppInfo()
        self.trace_log: List[TraceEntry] = []
        self.start_time = datetime.now()
        
        # Configuration runtime
        self.headless = True
        self.timeout_minutes = 10
        self.enable_trace = True
        
    def _load_config(self) -> Dict[str, Any]:
        """Charge la configuration depuis le fichier YAML"""
        if not self.config_path.exists():
            self._create_default_config()
            
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Erreur chargement config {self.config_path}: {e}")
            return self._get_default_config()
    
    def _create_default_config(self):
        """Crée une configuration par défaut"""
        default_config = self._get_default_config()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Configuration par défaut de l'application web avec gestion centralisée des ports"""
        
        # Configuration avec gestionnaire centralisé si disponible
        if CENTRAL_PORT_MANAGER_AVAILABLE:
            try:
                port_manager = get_port_manager()
                backend_port = port_manager.get_port('backend')
                frontend_port = port_manager.get_port('frontend')
                fallback_ports = port_manager.config['ports']['backend'].get('fallback', list(range(backend_port + 1, backend_port + 21)))
                
                # Configuration des variables d'environnement
                set_environment_variables()
                print(f"[PORTS] Configuration centralisée chargée - Backend: {backend_port}, Frontend: {frontend_port}")
                
            except Exception as e:
                print(f"[PORTS] Erreur gestionnaire centralisé: {e}, utilisation des valeurs par défaut")
                backend_port = 5010
                frontend_port = 3000
                fallback_ports = list(range(backend_port + 1, backend_port + 21))
        else:
            backend_port = 5010
            frontend_port = 3000
            fallback_ports = list(range(backend_port + 1, backend_port + 21))
        
        return {
            'webapp': {
                'name': 'Argumentation Analysis Web App',
                'version': '1.0.0',
                'environment': 'development'
            },
            'backend': {
                'enabled': True,
                'module': 'argumentation_analysis.services.web_api.app',
                'start_port': backend_port,
                'fallback_ports': fallback_ports,
                'max_attempts': 3,
                'timeout_seconds': 30,
                'health_endpoint': '/api/health',
                'env_activation': f'powershell -File "{project_root.joinpath("scripts", "env", "activate_project_env.ps1")}"'
            },
            'frontend': {
                'enabled': False,  # Optionnel selon besoins
                'path': 'services/web_api/interface-web-argumentative',
                'start_port': frontend_port,
                'fallback_ports': list(range(frontend_port + 1, frontend_port + 11)),
                'start_command': 'npm start',
                'timeout_seconds': 180
            },
            'playwright': {
                'enabled': True,
                'browser': 'chromium',
                'headless': True,
                'timeout_ms': 10000,
                'slow_timeout_ms': 20000,
                'test_paths': ['tests/e2e/python'],
                'screenshots_dir': 'logs/screenshots',
                'traces_dir': 'logs/traces'
            },
            'logging': {
                'level': 'INFO',
                'file': 'logs/webapp_orchestrator.log',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'cleanup': {
                'auto_cleanup': True,
                'kill_processes': ['python*', 'node*'],
                'process_filters': ['app.py', 'web_api', 'serve']
            }
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Configure le système de logging"""
        logging_config = self.config.get('logging', {})
        log_file = Path(logging_config.get('file', 'logs/webapp_orchestrator.log'))
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, logging_config.get('level', 'INFO')),
            format=logging_config.get('format', '%(asctime)s - %(levelname)s - %(message)s'),
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout.reconfigure(encoding='utf-8'))
            ]
        )
        
        return logging.getLogger(__name__)
    
    def add_trace(self, action: str, details: str = "", result: str = "", 
                  screenshot: str = "", status: str = "success"):
        """Ajoute une entrée de trace"""
        if not self.enable_trace:
            return
            
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        entry = TraceEntry(timestamp, action, details, result, screenshot, status)
        self.trace_log.append(entry)
        
        # Log avec couleurs
        color = "\033[96m" if status == "success" else "\033[91m"  # Cyan ou Rouge
        reset = "\033[0m"
        
        self.logger.info(f"{color}[{timestamp}] {action}{reset}")
        if details:
            self.logger.info(f"   Détails: {details}")
        if result:
            self.logger.info(f"   Résultat: {result}")
    
    async def start_webapp(self, headless: bool = True, frontend_enabled: bool = None) -> bool:
        """
        Démarre l'application web complète
        
        Args:
            headless: Mode headless pour Playwright
            frontend_enabled: Force activation/désactivation frontend
            
        Returns:
            bool: True si démarrage réussi
        """
        self.headless = headless
        self.app_info.start_time = datetime.now()
        
        self.add_trace("[START] DEMARRAGE APPLICATION WEB",
                      f"Mode: {'Headless' if headless else 'Visible'}", 
                      "Initialisation orchestrateur")
        
        try:
            # 1. Nettoyage préalable
            await self._cleanup_previous_instances()
            
            # 2. Démarrage backend (obligatoire)
            if not await self._start_backend():
                return False
            
            # 3. Démarrage frontend (optionnel)
            frontend_enabled = frontend_enabled if frontend_enabled is not None else self.config['frontend']['enabled']
            if frontend_enabled:
                await self._start_frontend(frontend_enabled)
            
            # 4. Validation des services
            if not await self._validate_services():
                return False
            
            self.app_info.status = WebAppStatus.RUNNING
            self.add_trace("[OK] APPLICATION WEB OPERATIONNELLE",
                          f"Backend: {self.app_info.backend_url}", 
                          "Tous les services démarrés")
            
            return True
            
        except Exception as e:
            self.add_trace("[ERROR] ERREUR DEMARRAGE", str(e), "Echec critique", status="error")
            self.app_info.status = WebAppStatus.ERROR
            return False
    
    async def run_tests(self, test_paths: List[str] = None, **kwargs) -> bool:
        """
        Exécute les tests Playwright
        
        Args:
            test_paths: Chemins des tests à exécuter
            **kwargs: Options supplémentaires pour Playwright
            
        Returns:
            bool: True si tests réussis
        """
        if self.app_info.status != WebAppStatus.RUNNING:
            self.add_trace("[WARNING] APPLICATION NON DEMARREE", "", "Demarrage requis avant tests", status="error")
            if not await self.start_webapp(self.headless):
                self.add_trace("[ERROR] ECHEC DEMARRAGE PRE-TEST", "", "Impossible de lancer l'application pour les tests", status="error")
                return False
        
        self.add_trace("[TEST] EXECUTION TESTS PLAYWRIGHT",
                      f"Tests: {test_paths or 'tous'}")
        
        # Configuration runtime pour Playwright
        test_config = {
            'backend_url': self.app_info.backend_url,
            'frontend_url': self.app_info.frontend_url,
            'headless': self.headless,
            **kwargs
        }
        
        test_success = await self.playwright_runner.run_tests(test_paths, test_config)

        return test_success
    
    async def stop_webapp(self):
        """Arrête l'application web et nettoie les ressources"""
        self.add_trace("[STOP] ARRET APPLICATION WEB", "Nettoyage en cours")
        self.app_info.status = WebAppStatus.STOPPING
        
        try:
            # Arrêt frontend
            if self.app_info.frontend_pid:
                await self.frontend_manager.stop()
                
            # Arrêt backend  
            if self.app_info.backend_pid:
                await self.backend_manager.stop()
                
            # Cleanup processus
            await self.process_cleaner.cleanup_webapp_processes()

            # Déverrouillage du port
            if CENTRAL_PORT_MANAGER_AVAILABLE:
                self._unlock_port()
            
            self.app_info = WebAppInfo()  # Reset
            self.add_trace("[OK] ARRET TERMINE", "", "Toutes les ressources liberees")
            
        except Exception as e:
            self.add_trace("[WARNING] ERREUR ARRET", str(e), "Nettoyage partiel", status="error")
    
    async def full_integration_test(self, headless: bool = True,
                                   frontend_enabled: bool = True, # Forcer le frontend pour les tests E2E
                                   test_paths: List[str] = None) -> bool:
        """
        Test d'intégration complet : démarrage + tests + arrêt
        
        Remplace toutes les fonctions des scripts PowerShell
        
        Returns:
            bool: True si intégration complète réussie
        """
        success = False
        
        try:
            self.add_trace("[TEST] INTEGRATION COMPLETE",
                          "Démarrage orchestration complète")
            
            # 1. Démarrage application
            if not await self.start_webapp(headless, frontend_enabled):
                self.add_trace("[ERROR] ECHEC DEMARRAGE PRE-TEST", "L'application web n'a pas pu démarrer.", "", status="error")
                return False

            # S'assurer que le frontend a démarré si les tests sont exécutés
            if not self.app_info.frontend_url:
                self.add_trace("[ERROR] FRONTEND INDISPONIBLE",
                               "Le frontend n'a pas démarré, impossible de lancer les tests E2E.",
                               "", status="error")
                return False
            
            # 2. Attente stabilisation
            await asyncio.sleep(2)
            
            # 3. Exécution tests
            self.logger.info(f"Lancement de la suite de tests complète: {test_paths or 'par défaut'}")
            success = await self.run_tests(test_paths)
            
            if success:
                self.add_trace("[SUCCESS] INTEGRATION REUSSIE",
                               "Tous les tests ont passé",
                               "Application web validée")
            else:
                self.add_trace("[ERROR] ECHEC INTEGRATION",
                              "Certains tests ont échoué", 
                              "Voir logs détaillés", status="error")
            
        finally:
            # 4. Nettoyage systématique
            await self.stop_webapp()
            
            # 5. Sauvegarde trace
            await self._save_trace_report()
        
        return success
    
    # ========================================================================
    # MÉTHODES PRIVÉES
    # ========================================================================
    
    async def _cleanup_previous_instances(self):
        """Nettoie les instances précédentes, en ciblant d'abord les ports."""
        self.add_trace("[CLEAN] NETTOYAGE PREALABLE", "Forçage de la libération des ports et arrêt des instances existantes")

        # Nettoyage ciblé des ports backend (toujours nécessaire)
        backend_ports_to_clean = [self.config['backend']['start_port']] + self.config['backend'].get('fallback_ports', [])
        self.logger.info(f"Nettoyage des ports du BACKEND: {backend_ports_to_clean}")
        self.process_cleaner.cleanup_by_port(backend_ports_to_clean)

        # Nettoyage ciblé des ports frontend (si configurés)
        frontend_config = self.config.get('frontend', {})
        if frontend_config and frontend_config.get('port'):
            frontend_ports_to_clean = [frontend_config['port']] + frontend_config.get('fallback_ports', [])
            self.logger.info(f"Nettoyage des ports du FRONTEND: {frontend_ports_to_clean}")
            self.process_cleaner.cleanup_by_port(frontend_ports_to_clean)
        else:
            self.logger.info("Aucun port frontend à nettoyer (non configuré ou clé 'port' manquante).")
        
        # On attend un court instant pour laisser le temps aux processus de se terminer
        await asyncio.sleep(1)

        # On exécute ensuite le nettoyage général pour les processus qui n'utiliseraient pas de port
        self.logger.info("Nettoyage général des processus restants...")
        await self.process_cleaner.cleanup_webapp_processes()
    
    async def _start_backend(self) -> bool:
        """Démarre le backend avec failover de ports"""
        self.add_trace("[BACKEND] DEMARRAGE BACKEND", "Lancement avec failover de ports")
        
        result = await self.backend_manager.start_with_failover()
        if result['success']:
            self.app_info.backend_url = result['url']
            self.app_info.backend_port = result['port']
            self.app_info.backend_pid = result['pid']
            
            # Verrouillage du port pour les autres processus
            if CENTRAL_PORT_MANAGER_AVAILABLE:
                self._lock_port('backend', self.app_info.backend_port)

            self.add_trace("[OK] BACKEND OPERATIONNEL",
                           f"Port: {result['port']} (verrouillé) | PID: {result['pid']}",
                           f"URL: {result['url']}")
            return True
        else:
            self.add_trace("[ERROR] ECHEC BACKEND", result['error'], "", status="error")
            return False
    
    async def _start_frontend(self, force_start: bool = False) -> bool:
        """Démarre le frontend React"""
        # La condition de démarrage prend en compte la configuration ET le flag de forçage
        should_start = self.config['frontend'].get('enabled', False) or force_start
        if not should_start:
            self.add_trace("[FRONTEND] DEMARRAGE IGNORE", "Frontend désactivé dans la configuration et non forcé.", status="success")
            return True
            
        self.add_trace("[FRONTEND] DEMARRAGE FRONTEND", "Lancement interface React")
        
        result = await self.frontend_manager.start_with_failover()
        if result['success']:
            self.app_info.frontend_url = result['url']
            self.app_info.frontend_port = result['port']
            self.app_info.frontend_pid = result['pid']
            
            self.add_trace("[OK] FRONTEND OPERATIONNEL",
                          f"Port: {result['port']}", 
                          f"URL: {result['url']}")
            return True
        else:
            self.add_trace("[WARNING] FRONTEND ECHEC", result['error'], "Continue sans frontend", status="error")
            return True  # Non bloquant
    
    async def _validate_services(self) -> bool:
        """Valide que les services répondent correctement"""
        self.add_trace("[CHECK] VALIDATION SERVICES", "Verification endpoints")
        
        # Test backend obligatoire
        if not await self.backend_manager.health_check():
            self.add_trace("[ERROR] BACKEND INACCESSIBLE", "", "Echec validation", status="error")
            return False
            
        # Test frontend optionnel
        if self.app_info.frontend_url:
            frontend_ok = await self.frontend_manager.health_check()
            if not frontend_ok:
                self.add_trace("[WARNING] FRONTEND INACCESSIBLE", "", "Continue avec backend seul")
        
        self.add_trace("[OK] SERVICES VALIDES", "Tous les endpoints repondent")
        return True

    def _lock_port(self, service: str, port: int):
        """Utilise PortManager pour verrouiller le port dans .port_lock."""
        self.add_trace(f"[LOCK] VERROUILLAGE PORT", f"Service: {service}, Port: {port}")
        try:
            # On utilise une instance fraîche pour éviter les conflits d'état
            pm = PortManager()
            lock_data = {'service': service, 'port': port}
            with open(pm.lock_file_path, 'w', encoding='utf-8') as f:
                json.dump(lock_data, f)
            # DEBUG: Vérifier le contenu du fichier de verrouillage juste après l'écriture
            with open(pm.lock_file_path, 'r', encoding='utf-8') as f_read:
                self.logger.info(f"DEBUG: Contenu de .port_lock écrit : {f_read.read()}")
            self.logger.info(f"Port {port} pour le service {service} verrouillé dans {pm.lock_file_path}")
        except Exception as e:
            self.add_trace("[ERROR] ECHEC VERROUILLAGE", str(e), status="error")

    def _unlock_port(self):
        """Utilise PortManager pour déverrouiller le port."""
        self.add_trace("[UNLOCK] DEVERROUILLAGE PORT", "Suppression du fichier .port_lock")
        try:
            pm = PortManager()
            pm.unlock_port()
            self.logger.info("Fichier de verrouillage des ports supprimé.")
        except Exception as e:
            self.add_trace("[ERROR] ECHEC DEVERROUILLAGE", str(e), status="error")
    
    async def _save_trace_report(self):
        """Sauvegarde le rapport de trace"""
        if not self.enable_trace or not self.trace_log:
            return
            
        trace_file = Path("logs/webapp_integration_trace.md")
        trace_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Génération du rapport Markdown
        content = self._generate_trace_markdown()
        
        with open(trace_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        self.add_trace("[SAVE] TRACE SAUVEGARDEE", f"Fichier: {trace_file}")
    
    def _generate_trace_markdown(self) -> str:
        """Génère le rapport de trace en Markdown"""
        duration = (datetime.now() - self.start_time).total_seconds()
        success_count = sum(1 for entry in self.trace_log if entry.status == "success")
        error_count = len(self.trace_log) - success_count
        
        content = f"""# 🎯 TRACE D'EXÉCUTION - ORCHESTRATEUR WEB UNIFIÉ

**Date d'exécution:** {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}  
**Mode:** {'Interface Cachée (Headless)' if self.headless else 'Interface Visible'}  
**Backend:** {self.app_info.backend_url or 'Non démarré'}  
**Frontend:** {self.app_info.frontend_url or 'Non démarré'}  
**Durée totale:** {duration:.2f} secondes

---

## 📋 ACTIONS DÉTAILLÉES

"""
        
        for entry in self.trace_log:
            status_emoji = "✅" if entry.status == "success" else "❌"
            content += f"""
### {status_emoji} {entry.timestamp} - {entry.action}
"""
            if entry.details:
                content += f"**Détails:** {entry.details}\n"
            if entry.result:
                content += f"**Résultat:** {entry.result}\n"
            if entry.screenshot:
                content += f"**Screenshot:** {entry.screenshot}\n"
        
        content += f"""

---

## 📊 RÉSUMÉ D'EXÉCUTION
- **Nombre d'actions:** {len(self.trace_log)}
- **Succès:** {success_count}
- **Erreurs:** {error_count}
- **Statut final:** {'✅ SUCCÈS' if error_count == 0 else '❌ ÉCHEC'}

## 🔧 CONFIGURATION TECHNIQUE
- **Backend Port:** {self.app_info.backend_port}
- **Frontend Port:** {self.app_info.frontend_port}
- **Mode Headless:** {self.headless}
- **Config:** {self.config_path}
"""
        
        return content

def main():
    """Point d'entrée principal en ligne de commande"""
    parser = argparse.ArgumentParser(description="Orchestrateur Unifié d'Application Web")
    parser.add_argument('--config', default='config/webapp_config.yml', 
                       help='Chemin du fichier de configuration')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Mode headless pour les tests')
    parser.add_argument('--visible', action='store_true',
                       help='Mode visible (override headless)')
    parser.add_argument('--frontend', action='store_true',
                       help='Force activation frontend')
    parser.add_argument('--tests', nargs='*',
                       help='Chemins spécifiques des tests à exécuter')
    parser.add_argument('--timeout', type=int, default=10,
                       help='Timeout en minutes')
    
    # Commandes
    parser.add_argument('--start', action='store_true',
                       help='Démarre seulement l\'application')
    parser.add_argument('--stop', action='store_true', 
                       help='Arrête l\'application')
    parser.add_argument('--test', action='store_true',
                       help='Exécute seulement les tests')
    parser.add_argument('--integration', action='store_true', default=True,
                       help='Test d\'intégration complet (défaut)')
    
    parser.add_argument('--no-playwright', action='store_true',
                       help='Désactive l\'exécution des tests Playwright')
    
    args = parser.parse_args()
    
    # Override headless si --visible
    headless = args.headless and not args.visible
    
    # Création orchestrateur
    orchestrator = UnifiedWebOrchestrator(args.config)
    orchestrator.headless = headless
    orchestrator.timeout_minutes = args.timeout
    
    async def run_command():
        try:
            if args.stop:
                await orchestrator.stop_webapp()
                return True
            elif args.start:
                # Démarrage simple, mais on maintient le processus en vie
                if await orchestrator.start_webapp(headless, args.frontend):
                    print(f"Backend démarré en arrière-plan. PID de l'orchestrateur : {os.getpid()}. PID du backend : {orchestrator.app_info.backend_pid}")
                    # La boucle de maintien est supprimée pour un comportement non bloquant.
                    # Le processus se terminera, mais le serveur backend (uvicorn) continuera de tourner.
                    return True # Renvoyer True pour indiquer le succès
                else:
                    return False

            elif args.test:
                # Test d'intégration qui encapsule le démarrage, l'exécution et l'arrêt
                success = False
                try:
                    # DEBUG: Forcer l'exécution d'un seul test pour isoler le problème de blocage.
                    isolated_test_path = ['tests/e2e/python/test_validation_form.py']
                    orchestrator.logger.warning(f"DEBUGGING: Exécution d'un test isolé: {isolated_test_path}")
                    
                    # On utilise le test isolé si aucun autre n'est spécifié via la ligne de commande
                    tests_to_run = args.tests or isolated_test_path
                    success = await orchestrator.run_tests(tests_to_run)
                finally:
                    # Arrêt systématique de l'application
                    await orchestrator.stop_webapp()
                return success
            else:  # Integration par défaut
                # Pour un test d'intégration complet, le frontend est TOUJOURS requis.
                # Le flag --frontend sert à l'activer pour d'autres commandes comme --start.
                return await orchestrator.full_integration_test(
                    headless=headless,
                    frontend_enabled=True,
                    test_paths=args.tests
                )
        except KeyboardInterrupt:
            print("\n🛑 Interruption utilisateur")
            await orchestrator.stop_webapp()
            return False
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return False
    
    # Exécution asynchrone
    success = asyncio.run(run_command())
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()