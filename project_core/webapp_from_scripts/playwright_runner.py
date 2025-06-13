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
        self.timeout_ms = config.get('timeout_ms', 30000)
        self.test_paths = config.get('test_paths', ['tests_playwright/tests/'])
        self.screenshots_dir = Path(config.get('screenshots_dir', 'logs/screenshots'))
        self.traces_dir = Path(config.get('traces_dir', 'logs/traces'))

        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.traces_dir.mkdir(parents=True, exist_ok=True)

        self.last_results: Optional[Dict[str, Any]] = None

    async def run_tests(self, test_paths: List[str] = None,
                            runtime_config: Dict[str, Any] = None,
                            pytest_args: List[str] = None) -> bool:
        # Configuration de la variable d'environnement pour forcer la config de test
        os.environ['USE_MOCK_CONFIG'] = '1'
        self.logger.info("Variable d'environnement 'USE_MOCK_CONFIG' définie à '1'")
        if not self.enabled:
            self.logger.info("Tests Playwright désactivés")
            return True

        effective_config = self._merge_runtime_config(runtime_config or {})
        test_paths = test_paths or self.test_paths

        self.logger.info(f"Démarrage tests Playwright: {test_paths}")
        self.logger.info(f"Configuration: {effective_config}")

        try:
            await self._prepare_test_environment(effective_config)
            playwright_command_parts = self._build_playwright_command_string(
                test_paths, effective_config)
            result = await self._execute_tests(playwright_command_parts, effective_config)
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
                                         config: Dict[str, Any]) -> List[str]:
        """Construit la liste de commande 'npx playwright test ...'."""
        # Sur Windows, npx est souvent dans le PATH, mais on peut le rendre plus robuste
        # en utilisant le chemin direct si on le connaît. Pour l'instant, on se fie au PATH.
        npx_executable = 'npx'

        parts = [npx_executable, 'playwright', 'test']
        parts.extend(test_paths)
        
        if not config.get('headless', True):
            parts.append('--headed')
            
        # Lorsque le fichier de configuration utilise des "projets",
        # il faut utiliser --project au lieu de --browser.
        parts.append(f"--project={config['browser']}")
        parts.append(f"--timeout={config['timeout_ms']}")

        self.logger.info(f"Construction de la commande 'npx playwright': {parts}")
        return parts

    async def _execute_tests(self, playwright_command_parts: List[str],
                           config: Dict[str, Any]) -> subprocess.CompletedProcess:
        
        self.logger.info(f"Commande à exécuter: {' '.join(playwright_command_parts)}")
        
        # Le répertoire de travail doit être la racine du projet
        test_dir = '.'

        try:
            # Utilisation de asyncio.create_subprocess_shell pour une meilleure gestion async
            # On passe une chaîne de caractères à shell
            command_str = ' '.join(playwright_command_parts)
            process = await asyncio.create_subprocess_shell(
                command_str,
                cwd=test_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            result = subprocess.CompletedProcess(
                args=playwright_command_parts,
                returncode=process.returncode,
                stdout=stdout.decode('utf-8', errors='ignore'),
                stderr=stderr.decode('utf-8', errors='ignore')
            )
            
            self.logger.info(f"Tests terminés - Code retour: {result.returncode}")
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur majeure lors de l'exécution de la commande Playwright: {e}", exc_info=True)
            return subprocess.CompletedProcess(args=' '.join(playwright_command_parts), returncode=1, stdout="", stderr=str(e))

    async def _analyze_results(self, result: subprocess.CompletedProcess) -> bool:
        success = result.returncode == 0
        
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Sauvegarder la sortie complète dans des fichiers pour éviter la troncature des logs
        if result.stdout:
            stdout_log_path = log_dir / "pytest_stdout.log"
            with open(stdout_log_path, "w", encoding="utf-8") as f:
                f.write(result.stdout)
            self.logger.info(f"Sortie STDOUT des tests sauvegardée dans {stdout_log_path}")
        else:
            self.logger.info("Aucune sortie STDOUT des tests à sauvegarder.")
    
        if result.stderr:
            stderr_log_path = log_dir / "pytest_stderr.log"
            with open(stderr_log_path, "w", encoding="utf-8") as f:
                f.write(result.stderr)
            self.logger.error(f"Sortie STDERR des tests sauvegardée dans {stderr_log_path}")
        else:
            self.logger.info("Aucune sortie STDERR des tests à sauvegarder.")
    
        # Afficher un résumé si la sortie n'est pas trop longue
        if result.stdout and len(result.stdout) < 2000:
            self.logger.info("STDOUT (aperçu):\n" + result.stdout)
        if result.stderr and len(result.stderr) < 2000:
            self.logger.error("STDERR (aperçu):\n" + result.stderr)
    
        self.logger.info(f"Analyse des résultats terminée. Succès: {success}")
        return success