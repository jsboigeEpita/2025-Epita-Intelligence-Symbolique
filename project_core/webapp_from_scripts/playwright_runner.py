import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from project_core.core_from_scripts.environment_manager import EnvironmentManager


class PlaywrightRunner:
    """
    Gestionnaire d'exécution des tests Playwright
    """

    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.env_manager = EnvironmentManager(logger)

        self.enabled = config.get('enabled', True)
        self.browser = config.get('browser', 'chromium')
        self.headless = config.get('headless', True)
        self.timeout_ms = config.get('timeout_ms', 10000)
        self.test_paths = config.get('test_paths', ['tests_playwright/tests/'])
        self.screenshots_dir = Path(config.get('screenshots_dir', 'logs/screenshots'))
        self.traces_dir = Path(config.get('traces_dir', 'logs/traces'))

        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.traces_dir.mkdir(parents=True, exist_ok=True)

        self.last_results: Optional[Dict[str, Any]] = None

    async def run_tests(self, test_paths: List[str] = None,
                        runtime_config: Dict[str, Any] = None) -> bool:
        if not self.enabled:
            self.logger.info("Tests Playwright désactivés")
            return True

        effective_config = self._merge_runtime_config(runtime_config or {})
        test_paths = test_paths or self.test_paths

        self.logger.info(f"Démarrage tests Playwright: {test_paths}")
        self.logger.info(f"Configuration: {effective_config}")

        try:
            await self._prepare_test_environment(effective_config)
            playwright_command_str = self._build_playwright_command_string(
                test_paths, effective_config)
            result = await self._execute_tests(playwright_command_str, effective_config)
            success = await self._analyze_results(result)
            return success
        except Exception as e:
            self.logger.error(f"Erreur exécution tests: {e}", exc_info=True)
            return False

    def _merge_runtime_config(self, runtime_config: Dict[str, Any]) -> Dict[str, Any]:
        """Fusionne configuration par défaut avec runtime"""
        effective_config = {
            'backend_url': 'http://localhost:5003',
            'frontend_url': 'http://localhost:3000',
            'headless': self.headless,
            'browser': self.browser,
            'timeout_ms': self.timeout_ms,
        }
        effective_config.update(runtime_config)
        return effective_config

    async def _prepare_test_environment(self, config: Dict[str, Any]):
        """Prépare l'environnement pour les tests"""
        env_vars = {
            'BACKEND_URL': config['backend_url'],
            'FRONTEND_URL': config['frontend_url'],
            'PLAYWRIGHT_BASE_URL': config.get('frontend_url') or config['backend_url'],
            'HEADLESS': str(config['headless']).lower(),
            'BROWSER': config['browser'],
            'SCREENSHOTS_DIR': str(self.screenshots_dir),
            'TRACES_DIR': str(self.traces_dir)
        }
        for key, value in env_vars.items():
            os.environ[key] = value
        self.logger.info(f"Variables test configurées: {env_vars}")

    def _build_playwright_command_string(self, test_paths: List[str],
                                         config: Dict[str, Any]) -> str:
        """Construit la chaîne de commande 'pytest ...' pour les tests Playwright Python."""
        parts = ['pytest']  # Changement pour utiliser pytest
        parts.extend(test_paths)
        
        if not config.get('headless', True):
            parts.append('--headed')  # Option standard pour pytest-playwright
        
        # Le nom du navigateur (config['browser']) est généralement géré par pytest-playwright
        # via des fixtures ou des variables d'environnement (déjà définies dans _prepare_test_environment).
        # Ajouter --browser ici pourrait être redondant ou entrer en conflit.
        # Exemple: pytest-playwright utilise --browser chromium --browser firefox etc.
        # parts.append(f"--browser {config['browser']}") # Ne pas ajouter pour l'instant

        # La gestion du timeout global pour pytest est différente.
        # pytest-playwright a son propre mécanisme de timeout.
        # L'option --timeout de npx playwright test n'a pas d'équivalent direct simple pour pytest.
        # Le timeout_ms de la config est déjà utilisé pour les variables d'environnement.
        # Ne pas ajouter de --timeout global à la commande pytest pour l'instant.

        self.logger.info(f"Construction de la commande Pytest. Config headless: {config.get('headless', True)}, Browser: {config.get('browser')}")
        return ' '.join(parts)

    async def _execute_tests(self, playwright_command_str: str,
                           config: Dict[str, Any]) -> subprocess.CompletedProcess:
        # La commande n'a plus besoin du 'cd', on passe le répertoire de travail directement.
        self.logger.info(f"Commande à exécuter via EnvironmentManager: {playwright_command_str}")
        
        # Le répertoire de travail doit être celui où se trouve package.json,
        # ou la racine du projet si les chemins de test sont relatifs à la racine.
        # Les chemins de test comme 'tests/functional/...' sont relatifs à la racine du projet.
        test_dir = '.' # Changé de 'tests_playwright' à '.'

        try:
            # Utilisation de asyncio.to_thread pour ne pas bloquer la boucle
            result = await asyncio.to_thread(
                self.env_manager.run_in_conda_env,
                playwright_command_str,
                cwd=test_dir,
                capture_output=True
            )
            self.logger.info(f"Tests terminés - Code retour: {result.returncode}")
            return result
        except Exception as e:
            self.logger.error(f"Erreur majeure lors de l'appel à EnvironmentManager: {e}", exc_info=True)
            return subprocess.CompletedProcess(args=playwright_command_str, returncode=1, stdout="", stderr=str(e))

    async def _analyze_results(self, result: subprocess.CompletedProcess) -> bool:
        success = result.returncode == 0
        if result.stdout:
            self.logger.info("STDOUT:\n" + result.stdout)
        if result.stderr:
            self.logger.error("STDERR:\n" + result.stderr)

        self.logger.info(f"Analyse des résultats terminée. Succès: {success}")
        return success