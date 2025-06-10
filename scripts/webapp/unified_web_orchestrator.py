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

# Auto-activation environnement au démarrage
try:
    _current_script_path = Path(__file__).resolve()
    _project_root = _current_script_path.parent.parent.parent
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))
    
    from scripts.core.environment_manager import auto_activate_env
    from scripts.core.auto_env import _load_dotenv_intelligent
    
    # Activation automatique de l'environnement projet-is
    print("🔧 Auto-activation environnement conda...")
    if auto_activate_env("projet-is", silent=False):
        print("✅ Environnement 'projet-is' auto-activé")
    else:
        print("⚠️ Impossible d'auto-activer l'environnement, continuons quand même...")
    
    # Chargement .env intelligent
    if _load_dotenv_intelligent(_project_root, silent=False):
        print("✅ Configuration .env chargée")
    
except Exception as e:
    print(f"⚠️ Erreur auto-activation: {e}")
    print("Continuons sans auto-activation...")

# Imports internes
from scripts.webapp.backend_manager import BackendManager
from scripts.webapp.frontend_manager import FrontendManager
from scripts.webapp.playwright_runner import PlaywrightRunner
from scripts.webapp.process_cleaner import ProcessCleaner

# Import du gestionnaire centralisé des ports
try:
    from project_core.config.port_manager import get_port_manager, set_environment_variables
    CENTRAL_PORT_MANAGER_AVAILABLE = True
except ImportError:
    CENTRAL_PORT_MANAGER_AVAILABLE = False
    print("[WARNING] Gestionnaire centralisé des ports non disponible, utilisation des ports par défaut")

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
        self.backend_manager = BackendManager(self.config.get('backend', {}), self.logger)
        self.frontend_manager = FrontendManager(self.config.get('frontend', {}), self.logger)
        self.playwright_runner = PlaywrightRunner(self.config.get('playwright', {}), self.logger)
        self.process_cleaner = ProcessCleaner(self.logger)
        
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
                fallback_ports = port_manager.config['ports']['backend'].get('fallback', [5004, 5005, 5006])
                
                # Configuration des variables d'environnement
                set_environment_variables()
                print(f"[PORTS] Configuration centralisée chargée - Backend: {backend_port}, Frontend: {frontend_port}")
                
            except Exception as e:
                print(f"[PORTS] Erreur gestionnaire centralisé: {e}, utilisation des valeurs par défaut")
                backend_port = 5003
                frontend_port = 3000
                fallback_ports = [5004, 5005, 5006]
        else:
            backend_port = 5003
            frontend_port = 3000
            fallback_ports = [5004, 5005, 5006]
        
        return {
            'webapp': {
                'name': 'Argumentation Analysis Web App',
                'version': '1.0.0',
                'environment': 'development'
            },
            'backend': {
                'enabled': True,
                'module': 'api.main_simple:app',
                'start_port': backend_port,
                'fallback_ports': fallback_ports,
                'max_attempts': 5,
                'timeout_seconds': 30,
                'health_endpoint': '/health',
                'env_activation': 'powershell -File scripts/env/activate_project_env.ps1'
            },
            'frontend': {
                'enabled': False,  # Optionnel selon besoins
                'path': 'services/web_api/interface-web-argumentative',
                'port': frontend_port,
                'start_command': 'npm start',
                'timeout_seconds': 90
            },
            'playwright': {
                'enabled': True,
                'browser': 'chromium',
                'headless': True,
                'timeout_ms': 10000,
                'slow_timeout_ms': 20000,
                'test_paths': ['tests/functional/'],
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
                logging.StreamHandler(sys.stdout)
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
                await self._start_frontend()
            
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
            return False
        
        self.add_trace("[TEST] EXECUTION TESTS PLAYWRIGHT",
                      f"Tests: {test_paths or 'tous'}")
        
        # Configuration runtime pour Playwright
        test_config = {
            'backend_url': self.app_info.backend_url,
            'frontend_url': self.app_info.frontend_url or self.app_info.backend_url,
            'headless': self.headless,
            **kwargs
        }
        
        return await self.playwright_runner.run_tests(test_paths, test_config)
    
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
            
            self.app_info = WebAppInfo()  # Reset
            self.add_trace("[OK] ARRET TERMINE", "", "Toutes les ressources liberees")
            
        except Exception as e:
            self.add_trace("[WARNING] ERREUR ARRET", str(e), "Nettoyage partiel", status="error")
    
    async def full_integration_test(self, headless: bool = True, 
                                   frontend_enabled: bool = None,
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
                return False
            
            # 2. Attente stabilisation
            await asyncio.sleep(2)
            
            # 3. Exécution tests
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
        """Nettoie les instances précédentes"""
        self.add_trace("[CLEAN] NETTOYAGE PREALABLE", "Arret instances existantes")
        await self.process_cleaner.cleanup_webapp_processes()
    
    async def _start_backend(self) -> bool:
        """Démarre le backend avec failover de ports"""
        self.add_trace("[BACKEND] DEMARRAGE BACKEND", "Lancement avec failover de ports")
        
        result = await self.backend_manager.start_with_failover()
        if result['success']:
            self.app_info.backend_url = result['url']
            self.app_info.backend_port = result['port']
            self.app_info.backend_pid = result['pid']
            
            self.add_trace("[OK] BACKEND OPERATIONNEL",
                          f"Port: {result['port']} | PID: {result['pid']}", 
                          f"URL: {result['url']}")
            return True
        else:
            self.add_trace("[ERROR] ECHEC BACKEND", result['error'], "", status="error")
            return False
    
    async def _start_frontend(self) -> bool:
        """Démarre le frontend React"""
        if not self.config['frontend']['enabled']:
            return True
            
        self.add_trace("[FRONTEND] DEMARRAGE FRONTEND", "Lancement interface React")
        
        result = await self.frontend_manager.start()
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
                return await orchestrator.start_webapp(headless, args.frontend)
            elif args.test:
                return await orchestrator.run_tests(args.tests)
            else:  # Integration par défaut
                return await orchestrator.full_integration_test(
                    headless, args.frontend, args.tests)
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