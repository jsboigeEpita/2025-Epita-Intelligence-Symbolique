#!/usr/bin/env python3
"""
TestRunner - Module unifié pour l'exécution des tests avec gestion des services
Remplace les 4 implémentations PowerShell différentes identifiées dans la cartographie :
- start_web_application_simple.ps1
- backend_failover_non_interactive.ps1  
- integration_tests_with_failover.ps1
- run_integration_tests.ps1

Auteur: Projet Intelligence Symbolique EPITA
Date: 07/06/2025
"""

import os
import sys
import time
import logging
import subprocess
import threading
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

# Import du ServiceManager local
from .service_manager import ServiceManager, ServiceConfig, create_default_configs

try:
    import pytest
except ImportError:
    print("PyTest non installé. Installation requise: pip install pytest")


class TestType(Enum):
    """Types de tests supportés"""
    UNIT = "unit"
    INTEGRATION = "integration" 
    FUNCTIONAL = "functional"
    PLAYWRIGHT = "playwright"
    E2E = "e2e"


@dataclass
class TestConfig:
    """Configuration d'exécution de tests"""
    test_type: TestType
    test_paths: List[str]
    requires_backend: bool = False
    requires_frontend: bool = False
    conda_env: Optional[str] = None
    timeout: int = 300
    parallel: bool = False
    browser: str = "chromium"  # Pour tests Playwright
    headless: bool = True


class EnvironmentManager:
    """Gestionnaire d'environnement conda/venv - remplace activate_project_env.ps1"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.original_env = dict(os.environ)
        
    def activate_conda_env(self, env_name: str) -> bool:
        """Active un environnement conda"""
        try:
            # Recherche de conda
            conda_base = self._find_conda_installation()
            if not conda_base:
                self.logger.error("Installation conda non trouvée")
                return False
            
            # Activation de l'environnement
            if sys.platform == "win32":
                activate_script = conda_base / "Scripts" / "activate.bat"
                env_path = conda_base / "envs" / env_name
            else:
                activate_script = conda_base / "bin" / "activate"
                env_path = conda_base / "envs" / env_name
            
            if not env_path.exists():
                self.logger.error(f"Environnement conda '{env_name}' non trouvé dans {env_path}")
                return False
            
            # Mise à jour PATH et variables d'environnement
            if sys.platform == "win32":
                python_path = env_path / "python.exe"
                scripts_path = env_path / "Scripts"
            else:
                python_path = env_path / "bin" / "python"
                scripts_path = env_path / "bin"
            
            os.environ["PATH"] = f"{scripts_path}{os.pathsep}{os.environ['PATH']}"
            os.environ["CONDA_DEFAULT_ENV"] = env_name
            os.environ["CONDA_PREFIX"] = str(env_path)
            
            self.logger.info(f"Environnement conda '{env_name}' activé")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur activation conda '{env_name}': {e}")
            return False
    
    def _find_conda_installation(self) -> Optional[Path]:
        """Trouve l'installation conda"""
        possible_paths = [
            Path.home() / "miniconda3",
            Path.home() / "anaconda3", 
            Path("/opt/conda"),
            Path("/usr/local/conda"),
        ]
        
        # Essayer variable d'environnement CONDA_PREFIX
        if "CONDA_PREFIX" in os.environ:
            conda_prefix = Path(os.environ["CONDA_PREFIX"])
            if conda_prefix.exists():
                possible_paths.insert(0, conda_prefix.parent)
        
        for path in possible_paths:
            if path.exists() and (path / "bin" / "conda").exists():
                return path
        
        return None
    
    def restore_environment(self):
        """Restaure l'environnement original"""
        os.environ.clear()
        os.environ.update(self.original_env)
        self.logger.info("Environnement restauré")


class TestRunner:
    """Runner unifié pour tous types de tests avec gestion des services"""
    
    def __init__(self, log_level: int = logging.INFO):
        self.logger = self._setup_logging(log_level)
        self.service_manager = ServiceManager(log_level)
        self.env_manager = EnvironmentManager(self.logger)
        self.test_configs: Dict[str, TestConfig] = {}
        
        # Enregistrement des configurations de services par défaut
        for config in create_default_configs():
            self.service_manager.register_service(config)
        
        self._register_default_test_configs()
    
    def _setup_logging(self, level: int) -> logging.Logger:
        """Configuration du logging"""
        logger = logging.getLogger('TestRunner')
        logger.setLevel(level)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _register_default_test_configs(self):
        """Enregistre les configurations de test par défaut"""
        configs = [
            TestConfig(
                test_type=TestType.UNIT,
                test_paths=["tests/unit"],
                requires_backend=False,
                requires_frontend=False,
                timeout=120,
                parallel=True
            ),
            TestConfig(
                test_type=TestType.INTEGRATION,
                test_paths=["tests/integration"],
                requires_backend=True,
                requires_frontend=False,
                timeout=300
            ),
            TestConfig(
                test_type=TestType.FUNCTIONAL,
                test_paths=["tests/functional"],
                requires_backend=True,
                requires_frontend=False,
                timeout=300
            ),
            TestConfig(
                test_type=TestType.PLAYWRIGHT,
                test_paths=["tests/playwright"],
                requires_backend=True,
                requires_frontend=True,
                timeout=600,
                browser="chromium",
                headless=True
            ),
            TestConfig(
                test_type=TestType.E2E,
                test_paths=["tests/e2e"],
                requires_backend=True,
                requires_frontend=True,
                timeout=900,
                browser="chromium",
                headless=False
            )
        ]
        
        for config in configs:
            self.test_configs[config.test_type.value] = config
    
    def register_test_config(self, name: str, config: TestConfig):
        """Enregistre une configuration de test personnalisée"""
        self.test_configs[name] = config
        self.logger.info(f"Configuration de test enregistrée: {name}")
    
    def start_required_services(self, config: TestConfig) -> Dict[str, Tuple[bool, Optional[int]]]:
        """Démarre les services requis pour les tests"""
        results = {}
        
        if config.requires_backend:
            self.logger.info("Démarrage du service backend...")
            success, port = self.service_manager.start_service_with_failover("backend-flask")
            results["backend"] = (success, port)
            
            if not success:
                self.logger.error("Échec démarrage backend - abandon")
                return results
        
        if config.requires_frontend:
            self.logger.info("Démarrage du service frontend...")
            success, port = self.service_manager.start_service_with_failover("frontend-react")
            results["frontend"] = (success, port)
            
            if not success:
                self.logger.error("Échec démarrage frontend - nettoyage backend")
                if config.requires_backend:
                    self.service_manager.stop_service("backend-flask")
                return results
        
        return results
    
    def run_pytest_command(self, config: TestConfig, extra_args: List[str] = None) -> int:
        """Exécute une commande pytest avec la configuration donnée"""
        cmd = ["python", "-m", "pytest"]
        
        # Ajout des chemins de test
        cmd.extend(config.test_paths)
        
        # Options pytest
        cmd.extend([
            "-v",  # Mode verbeux
            "--tb=short",  # Traceback court
            f"--timeout={config.timeout}",
        ])
        
        # Exécution parallèle si supportée
        if config.parallel:
            cmd.extend(["-n", "auto"])  # Nécessite pytest-xdist
        
        # Configuration spécifique Playwright
        if config.test_type in [TestType.PLAYWRIGHT, TestType.E2E]:
            cmd.extend([
                f"--browser={config.browser}",
                f"--headed={'false' if config.headless else 'true'}",
            ])
        
        # Arguments supplémentaires
        if extra_args:
            cmd.extend(extra_args)
        
        self.logger.info(f"Exécution: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=False,
                text=True,
                timeout=config.timeout
            )
            return result.returncode
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout après {config.timeout}s")
            return 124
        except Exception as e:
            self.logger.error(f"Erreur exécution pytest: {e}")
            return 1
    
    def run_tests(self, test_type: str, extra_args: List[str] = None, conda_env: str = None) -> int:
        """
        Point d'entrée principal - remplace les scripts PowerShell
        Équivalent unifié de :
        - integration_tests_with_failover.ps1
        - backend_failover_non_interactive.ps1
        - run_integration_tests.ps1
        """
        if test_type not in self.test_configs:
            self.logger.error(f"Type de test non supporté: {test_type}")
            self.logger.info(f"Types disponibles: {list(self.test_configs.keys())}")
            return 1
        
        config = self.test_configs[test_type]
        
        # Activation environnement conda si spécifié
        if conda_env or config.conda_env:
            env_name = conda_env or config.conda_env
            if not self.env_manager.activate_conda_env(env_name):
                return 1
        
        services_started = {}
        exit_code = 1
        
        try:
            # Démarrage des services requis avec failover intelligent
            self.logger.info(f"Préparation tests {test_type}...")
            services_started = self.start_required_services(config)
            
            # Vérification que tous les services requis sont démarrés
            all_services_ok = True
            for service, (success, port) in services_started.items():
                if not success:
                    self.logger.error(f"Service {service} non démarré")
                    all_services_ok = False
                else:
                    self.logger.info(f"Service {service} démarré sur port {port}")
            
            if not all_services_ok:
                self.logger.error("Échec démarrage des services - abandon tests")
                return 1
            
            # Délai d'attente pour stabilisation des services
            if services_started:
                self.logger.info("Attente stabilisation des services...")
                time.sleep(5)
            
            # Exécution des tests
            self.logger.info(f"Lancement des tests {test_type}...")
            exit_code = self.run_pytest_command(config, extra_args)
            
            if exit_code == 0:
                self.logger.info(f"Tests {test_type} réussis ✓")
            else:
                self.logger.error(f"Tests {test_type} échoués (code: {exit_code})")
        
        finally:
            # Nettoyage systématique - pattern Cleanup-Services
            self.logger.info("Nettoyage des services...")
            self.service_manager.stop_all_services()
            
            # Restauration environnement
            if conda_env or config.conda_env:
                self.env_manager.restore_environment()
        
        return exit_code
    
    def run_integration_tests_with_failover(self, extra_args: List[str] = None) -> int:
        """Remplace integration_tests_with_failover.ps1"""
        return self.run_tests("integration", extra_args)
    
    def run_playwright_tests(self, headless: bool = True, browser: str = "chromium") -> int:
        """Exécution spécialisée tests Playwright avec configuration"""
        config = self.test_configs["playwright"]
        config.headless = headless
        config.browser = browser
        
        return self.run_tests("playwright")
    
    def start_web_application(self, wait: bool = True) -> Dict[str, Tuple[bool, Optional[int]]]:
        """
        Remplace start_web_application_simple.ps1
        Démarre backend + frontend avec failover
        """
        results = {}
        
        self.logger.info("Démarrage application web complète...")
        
        # Démarrage backend
        success, port = self.service_manager.start_service_with_failover("backend-flask")
        results["backend"] = (success, port)
        
        if success:
            # Démarrage frontend
            success, port = self.service_manager.start_service_with_failover("frontend-react")
            results["frontend"] = (success, port)
            
            if success:
                self.logger.info("Application web démarrée avec succès")
                if wait:
                    try:
                        self.logger.info("Appuyez sur Ctrl+C pour arrêter l'application")
                        while True:
                            time.sleep(1)
                    except KeyboardInterrupt:
                        self.logger.info("Arrêt demandé par l'utilisateur")
                        self.service_manager.stop_all_services()
            else:
                self.logger.error("Échec démarrage frontend")
                self.service_manager.stop_service("backend-flask")
        else:
            self.logger.error("Échec démarrage backend")
        
        return results
    
    def get_services_status(self) -> Dict:
        """Retourne le statut de tous les services"""
        return {
            "services": self.service_manager.list_all_services(),
            "test_configs": list(self.test_configs.keys())
        }


def main():
    """Point d'entrée CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(description="TestRunner unifié - remplace les scripts PowerShell")
    parser.add_argument("command", choices=[
        "unit", "integration", "functional", "playwright", "e2e",
        "start-app", "status"
    ], help="Commande à exécuter")
    
    parser.add_argument("--conda-env", help="Environnement conda à activer")
    parser.add_argument("--headless", action="store_true", help="Mode headless pour tests navigateur")
    parser.add_argument("--browser", default="chromium", help="Navigateur pour tests (chromium, firefox, webkit)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbeux")
    parser.add_argument("--wait", action="store_true", help="Attendre après démarrage app")
    parser.add_argument("extra_args", nargs="*", help="Arguments supplémentaires pour pytest")
    
    args = parser.parse_args()
    
    # Configuration logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    runner = TestRunner(log_level)
    
    if args.command == "start-app":
        results = runner.start_web_application(wait=args.wait)
        return 0 if all(success for success, _ in results.values()) else 1
    
    elif args.command == "status":
        status = runner.get_services_status()
        print("=== Status des Services ===")
        for service in status["services"]:
            print(f"- {service['name']}: {'Running' if service['running'] else 'Stopped'}")
        print(f"\nConfigurations de tests: {', '.join(status['test_configs'])}")
        return 0
    
    elif args.command == "playwright":
        return runner.run_playwright_tests(headless=args.headless, browser=args.browser)
    
    else:
        return runner.run_tests(args.command, args.extra_args, args.conda_env)


if __name__ == "__main__":
    sys.exit(main())