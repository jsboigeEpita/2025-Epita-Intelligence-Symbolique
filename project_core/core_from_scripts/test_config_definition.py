"""
Orchestrateur d'exécution des tests
===================================

Ce module centralise l'orchestration des tests :
- Exécution de pytest avec configurations variées
- Gestion des tests unitaires, d'intégration et de validation
- Support des modes rapide, authentique, et spécialisés
- Génération de rapports de test formatés

Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import os
import sys
import argparse
import subprocess
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from .common_utils import Logger, LogLevel, save_json_report, format_timestamp
from .environment_manager import EnvironmentManager


class TestMode(Enum):
    """Modes de test disponibles"""

    UNIT = "unit"
    INTEGRATION = "integration"
    VALIDATION = "validation"
    ALL = "all"
    FAST = "fast"
    AUTHENTIC = "authentic"
    COMPONENT = "component"


class TestLevel(Enum):
    """Niveaux de test"""

    BASIC = "basic"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"
    SMOKE = "smoke"


@dataclass
class TestConfig:
    """Configuration d'exécution des tests"""

    mode: TestMode
    level: TestLevel
    component: Optional[str] = None
    verbose: bool = False
    fast: bool = False
    authentic: bool = False
    capture_output: bool = True
    timeout: int = 300
    pytest_args: List[str] = None
    env_vars: Dict[str, str] = None

    def __post_init__(self):
        if self.pytest_args is None:
            self.pytest_args = []
        if self.env_vars is None:
            self.env_vars = {}


class TestRunner:
    """Orchestrateur principal des tests"""

    def __init__(self, logger: Logger = None):
        """
        Initialise le runner de tests

        Args:
            logger: Instance de logger à utiliser
        """
        self.logger = logger or Logger()
        self.env_manager = EnvironmentManager(self.logger)
        self.project_root = self.env_manager.project_root

        # Chemins de test standards
        self.test_paths = {
            "unit": "tests/unit",
            "integration": "tests/integration",
            "validation": "tests/validation_sherlock_watson",
            "all": "tests",
        }

        # Composants testables
        self.available_components = [
            "TweetyErrorAnalyzer",
            "UnifiedConfig",
            "FirstOrderLogicAgent",
            "AuthenticitySystem",
            "UnifiedOrchestrations",
        ]

        # Configuration par défaut
        self.default_pytest_args = [
            "-v",  # Verbeux
            "--color=yes",  # Couleurs
            "--tb=short",  # Traceback court
            "--durations=10",  # Top 10 des tests les plus lents
        ]

    def _build_pytest_command(
        self, config: TestConfig, test_paths: List[str]
    ) -> List[str]:
        """Construit la commande pytest avec les arguments appropriés"""
        cmd = ["python", "-m", "pytest"]

        # Arguments par défaut
        cmd.extend(self.default_pytest_args)

        # Mode verbeux
        if config.verbose:
            cmd.append("-vv")

        # Mode rapide
        if config.fast:
            cmd.extend(["--durations=5", "-x"])  # Stop au premier échec

        # Capture de sortie
        if not config.capture_output:
            cmd.append("-s")

        # Arguments personnalisés
        if config.pytest_args:
            cmd.extend(config.pytest_args)

        # Chemins de test
        cmd.extend(test_paths)

        return cmd

    def _get_test_paths_for_mode(self, config: TestConfig) -> List[str]:
        """Retourne les chemins de test selon le mode"""
        if config.component:
            # Test d'un composant spécifique
            component_paths = []
            for base_path in ["tests/unit", "tests/integration"]:
                component_path = os.path.join(
                    base_path, f"*{config.component.lower()}*"
                )
                if os.path.exists(base_path):
                    component_paths.append(component_path)
            return component_paths or [self.test_paths["unit"]]

        elif config.mode == TestMode.FAST:
            # Tests rapides uniquement
            return [os.path.join(self.test_paths["unit"], "test_*.py")]

        elif config.mode == TestMode.VALIDATION:
            # Tests de validation Sherlock/Watson
            return [self.test_paths["validation"]]

        elif config.mode == TestMode.ALL:
            # Tous les tests
            return [self.test_paths["all"]]

        else:
            # Mode standard selon le type
            mode_key = config.mode.value
            return [self.test_paths.get(mode_key, self.test_paths["unit"])]

    def _setup_test_environment(self, config: TestConfig):
        """Configure l'environnement pour les tests"""
        env_vars = {
            "PYTHONIOENCODING": "utf-8",
            "USE_REAL_JPYPE": "true" if config.authentic else "false",
            "TEST_MODE": config.mode.value.upper(),
            "TEST_LEVEL": config.level.value.upper(),
        }

        # Variables supplémentaires
        if config.env_vars:
            env_vars.update(config.env_vars)

        # Appliquer les variables
        self.env_manager.setup_environment_variables(env_vars)

        self.logger.debug(f"Environnement de test configuré: {list(env_vars.keys())}")

    def run_pytest(self, config: TestConfig) -> Dict[str, Any]:
        """
        Exécute pytest avec la configuration donnée

        Args:
            config: Configuration de test

        Returns:
            Résultats de l'exécution
        """
        self.logger.info(f"Exécution des tests en mode {config.mode.value}")

        # Configuration de l'environnement
        self._setup_test_environment(config)

        # Résolution des chemins de test
        test_paths = self._get_test_paths_for_mode(config)
        self.logger.debug(f"Chemins de test: {test_paths}")

        # Construction de la commande
        pytest_cmd = self._build_pytest_command(config, test_paths)
        self.logger.debug(f"Commande pytest: {' '.join(pytest_cmd)}")

        # Execution via l'environnement conda
        try:
            start_time = (
                self.logger.log.__self__.get_time()
                if hasattr(self.logger.log.__self__, "get_time")
                else None
            )

            result = self.env_manager.run_in_conda_env(
                pytest_cmd, capture_output=config.capture_output
            )

            # Analyse des résultats
            test_results = {
                "exit_code": result.returncode,
                "command": pytest_cmd,
                "config": {
                    "mode": config.mode.value,
                    "level": config.level.value,
                    "component": config.component,
                    "authentic": config.authentic,
                    "fast": config.fast,
                },
                "test_paths": test_paths,
                "success": result.returncode == 0,
            }

            if config.capture_output and hasattr(result, "stdout"):
                test_results["output"] = result.stdout
                test_results["stderr"] = result.stderr

                # Parser la sortie pytest pour extraire les statistiques
                test_results.update(self._parse_pytest_output(result.stdout))

            # Logging des résultats
            if test_results["success"]:
                self.logger.success("Tests exécutés avec succès")
            else:
                self.logger.error(f"Tests échoués (code: {result.returncode})")

            return test_results

        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution des tests: {e}")
            return {
                "exit_code": 1,
                "success": False,
                "error": str(e),
                "config": config.__dict__,
            }

    def _parse_pytest_output(self, output: str) -> Dict[str, Any]:
        """Parse la sortie pytest pour extraire les statistiques"""
        stats = {
            "tests_run": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "duration": 0.0,
        }

        if not output:
            return stats

        lines = output.split("\n")

        # Rechercher la ligne de résumé final
        for line in lines:
            line = line.strip()

            # Format: "X passed, Y failed, Z skipped in Xs"
            if "passed" in line and "in" in line:
                import re

                # Extraire les nombres
                passed_match = re.search(r"(\d+) passed", line)
                failed_match = re.search(r"(\d+) failed", line)
                skipped_match = re.search(r"(\d+) skipped", line)
                error_match = re.search(r"(\d+) error", line)
                duration_match = re.search(r"in ([\d.]+)s", line)

                if passed_match:
                    stats["passed"] = int(passed_match.group(1))
                if failed_match:
                    stats["failed"] = int(failed_match.group(1))
                if skipped_match:
                    stats["skipped"] = int(skipped_match.group(1))
                if error_match:
                    stats["errors"] = int(error_match.group(1))
                if duration_match:
                    stats["duration"] = float(duration_match.group(1))

                stats["tests_run"] = (
                    stats["passed"] + stats["failed"] + stats["skipped"]
                )
                break

        return stats

    def run_validation_suite(
        self,
        mode: str = "complete",
        generate_report: bool = False,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """
        Exécute la suite de validation Sherlock/Watson

        Args:
            mode: Mode de validation (complete, quick, edge_cases, mock_detection)
            generate_report: Générer un rapport HTML
            verbose: Mode verbeux

        Returns:
            Résultats de la validation
        """
        self.logger.info(f"Lancement validation Sherlock/Watson mode: {mode}")

        # Script de validation spécialisé
        script_path = os.path.join(
            self.project_root, "test_sherlock_watson_synthetic_validation.py"
        )

        if not os.path.exists(script_path):
            self.logger.error(f"Script de validation non trouvé: {script_path}")
            return {"success": False, "error": "Script non trouvé"}

        # Arguments selon le mode
        args = ["python", script_path]

        if mode == "quick":
            args.append("--quick-mode")
        elif mode == "edge_cases":
            args.append("--edge-cases-only")
        elif mode == "mock_detection":
            args.append("--mock-detection-focus")

        if verbose:
            args.append("--verbose")

        # Exécution
        try:
            result = self.env_manager.run_in_conda_env(args, capture_output=True)

            validation_results = {
                "exit_code": result.returncode,
                "success": result.returncode == 0,
                "mode": mode,
                "generate_report": generate_report,
            }

            if hasattr(result, "stdout"):
                validation_results["output"] = result.stdout
                validation_results["stderr"] = result.stderr

            # Recherche du rapport JSON généré
            if generate_report and result.returncode == 0:
                report_pattern = f"rapport_validation_sherlock_watson_synthetic_*.json"
                report_files = list(Path(self.project_root).glob(report_pattern))

                if report_files:
                    latest_report = max(report_files, key=lambda p: p.stat().st_mtime)
                    validation_results["report_file"] = str(latest_report)
                    self.logger.success(f"Rapport disponible: {latest_report}")

            if validation_results["success"]:
                self.logger.success("Validation Sherlock/Watson terminée avec succès")
            else:
                self.logger.error("Validation Sherlock/Watson échouée")

            return validation_results

        except Exception as e:
            self.logger.error(f"Erreur validation Sherlock/Watson: {e}")
            return {"success": False, "error": str(e)}

    def run_component_tests(
        self,
        component: str = None,
        authentic: bool = False,
        fast: bool = False,
        level: str = "all",
    ) -> Dict[str, Any]:
        """
        Exécute les tests de nouveaux composants

        Args:
            component: Composant spécifique à tester
            authentic: Mode authentique avec vrais services
            fast: Mode rapide
            level: Niveau de tests (unit, integration, all)

        Returns:
            Résultats des tests
        """
        self.logger.info("Exécution des tests de nouveaux composants")

        # Configuration de test
        config = TestConfig(
            mode=TestMode.COMPONENT if component else TestMode.ALL,
            level=TestLevel(level)
            if level in [l.value for l in TestLevel]
            else TestLevel.STANDARD,
            component=component,
            authentic=authentic,
            fast=fast,
            verbose=self.logger.verbose if hasattr(self.logger, "verbose") else False,
        )

        # Vérifications préalables pour mode authentique
        if authentic:
            issues = self._check_authentic_prerequisites()
            if issues:
                self.logger.warning("Prérequis authentiques manquants:")
                for issue in issues:
                    self.logger.warning(f"  - {issue}")
                return {"success": False, "issues": issues}

        # Exécution des tests
        return self.run_pytest(config)

    def _check_authentic_prerequisites(self) -> List[str]:
        """Vérifie les prérequis pour le mode authentique"""
        issues = []

        # Variables d'environnement requises
        required_env_vars = ["OPENAI_API_KEY"]
        for var in required_env_vars:
            if not os.getenv(var):
                issues.append(f"Variable d'environnement manquante: {var}")

        # Fichiers requis
        required_files = ["libs/tweety.jar", "config/taxonomies"]
        for file_path in required_files:
            full_path = os.path.join(self.project_root, file_path)
            if not os.path.exists(full_path):
                issues.append(f"Fichier manquant: {file_path}")

        # Dépendances Python critiques
        critical_deps = ["pytest", "numpy", "pandas", "openai"]
        missing_deps = []
        for dep in critical_deps:
            try:
                __import__(dep)
            except ImportError:
                missing_deps.append(dep)

        if missing_deps:
            issues.append(f"Dépendances manquantes: {', '.join(missing_deps)}")

        return issues


def run_pytest(
    test_path: str = "tests",
    verbose: bool = False,
    fast: bool = False,
    env_name: str = "projet-is",
) -> int:
    """Fonction utilitaire pour exécuter pytest"""
    logger = Logger(verbose=verbose)
    runner = TestRunner(logger)

    config = TestConfig(
        mode=TestMode.FAST if fast else TestMode.ALL,
        level=TestLevel.STANDARD,
        verbose=verbose,
        fast=fast,
    )

    results = runner.run_pytest(config)
    return results.get("exit_code", 1)


def run_python_script(
    script_path: str,
    args: List[str] = None,
    env_name: str = "projet-is",
    logger: Logger = None,
) -> int:
    """Fonction utilitaire pour exécuter un script Python"""
    if logger is None:
        logger = Logger()

    env_manager = EnvironmentManager(logger)

    command = ["python", script_path]
    if args:
        command.extend(args)

    try:
        result = env_manager.run_in_conda_env(command, env_name=env_name)
        return result.returncode
    except Exception as e:
        logger.error(f"Erreur exécution script: {e}")
        return 1


def main():
    """Point d'entrée principal pour utilisation en ligne de commande"""
    parser = argparse.ArgumentParser(description="Orchestrateur d'exécution des tests")

    parser.add_argument(
        "--mode",
        "-m",
        choices=[mode.value for mode in TestMode],
        default=TestMode.ALL.value,
        help="Mode de test à exécuter",
    )

    parser.add_argument(
        "--component", "-c", type=str, help="Composant spécifique à tester"
    )

    parser.add_argument(
        "--authentic", action="store_true", help="Mode authentique avec vrais services"
    )

    parser.add_argument("--fast", action="store_true", help="Mode rapide")

    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbeux")

    parser.add_argument(
        "--output", "-o", type=str, help="Fichier de sortie pour rapport JSON"
    )

    args = parser.parse_args()

    # Configuration du logger
    logger = Logger(verbose=args.verbose)
    runner = TestRunner(logger)

    # Configuration de test
    config = TestConfig(
        mode=TestMode(args.mode),
        level=TestLevel.STANDARD,
        component=args.component,
        authentic=args.authentic,
        fast=args.fast,
        verbose=args.verbose,
    )

    # Exécution des tests
    if args.mode == "validation":
        results = runner.run_validation_suite(
            mode="complete", generate_report=bool(args.output), verbose=args.verbose
        )
    else:
        results = runner.run_pytest(config)

    # Sauvegarde du rapport si demandé
    if args.output and results.get("success"):
        save_json_report(results, args.output, logger)

    # Code de sortie
    exit_code = results.get("exit_code", 1)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
