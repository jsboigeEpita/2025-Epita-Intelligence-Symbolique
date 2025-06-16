import asyncio
import glob
import json
import logging
import os
import shutil
import subprocess
import sys
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
        self.test_type = config.get('test_type', 'python')  # 'python' ou 'javascript'
        self.browser = config.get('browser', 'chromium')
        self.headless = config.get('headless', True)
        self.timeout_ms = config.get('timeout_ms', 30000)
        
        default_paths = {
            'python': ['tests/e2e/python/'],
            'javascript': ['tests/e2e/js/'],
            'demos': ['tests/e2e/demos/']
        }
        self.test_paths = config.get('test_paths', default_paths.get(self.test_type, []))
        
        self.process_timeout_s = config.get('process_timeout_s', 600)
        self.screenshots_dir = Path(config.get('screenshots_dir', 'logs/screenshots'))
        self.traces_dir = Path(config.get('traces_dir', 'logs/traces'))

        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.traces_dir.mkdir(parents=True, exist_ok=True)

        self.last_results: Optional[Dict[str, Any]] = None

    async def run_tests(self,
                            test_type: str = None,
                            test_paths: List[str] = None,
                            runtime_config: Dict[str, Any] = None,
                            pytest_args: List[str] = None,
                            playwright_config_path: str = None) -> bool:
        # Configuration de la variable d'environnement pour forcer la config de test
        os.environ['USE_MOCK_CONFIG'] = '1'
        self.logger.info("Variable d'environnement 'USE_MOCK_CONFIG' définie à '1'")
        if not self.enabled:
            self.logger.info("Tests Playwright désactivés")
            return True

        effective_config = self._merge_runtime_config(runtime_config or {})
        test_paths = test_paths or self.test_paths
        effective_test_type = test_type or self.test_type

        self.logger.info(f"Démarrage tests Playwright: {test_paths}")
        self.logger.info(f"Configuration: {effective_config}")

        try:
            await self._prepare_test_environment(effective_config)
            
            command_parts = self._build_command(
                effective_test_type,
                test_paths,
                effective_config,
                pytest_args or [],
                playwright_config_path
            )
            
            result = await self._execute_tests(command_parts, effective_config)
            success = await self._analyze_results(result)
            return success
        except Exception as e:
            self.logger.error(f"Erreur exécution tests: {e}", exc_info=True)
            return False

    def _merge_runtime_config(self, runtime_config: Dict[str, Any]) -> Dict[str, Any]:
        """Fusionne la configuration par défaut avec celle fournie à l'exécution."""
        # Priorité : runtime_config > self.config > valeurs par défaut
        effective_config = {
            'backend_url': 'http://localhost:5003', # Valeur par défaut
            'frontend_url': 'http://localhost:3000', # Valeur par défaut
            'headless': self.headless,
            'browser': self.browser,
            'timeout_ms': self.timeout_ms,
        }
        effective_config.update(self.config) # Appliquer la config de l'instance
        effective_config.update(runtime_config) # Écraser avec la config runtime
        return effective_config

    async def _prepare_test_environment(self, config: Dict[str, Any]):
        """Prépare l'environnement d'exécution pour les tests Playwright."""
        env_vars = {
            'BACKEND_URL': config['backend_url'],
            'FRONTEND_URL': config['frontend_url'],
            'PLAYWRIGHT_BASE_URL': config.get('frontend_url', config['backend_url']),
            # Les variables spécifiques à Playwright comme BROWSER, HEADLESS, etc.,
            # sont passées en ligne de commande plutôt que via les variables d'environnement
            # pour éviter les conflits avec le fichier de configuration Playwright.
        }
        for key, value in env_vars.items():
            if value:
                os.environ[key] = str(value)
        self.logger.info(f"Variables test configurées: {env_vars}")

    def _build_command(self,
                       test_type: str,
                       test_paths: List[str],
                       config: Dict[str, Any],
                       pytest_args: List[str],
                       playwright_config_path: Optional[str]) -> List[str]:
        """Construit dynamiquement la commande de test en fonction du type."""
        self.logger.info(f"Building command for test_type: {test_type}")
        if test_type == 'python':
            return self._build_python_command(test_paths, config, pytest_args)
        elif test_type == 'javascript':
            return self._build_js_command(test_paths, config, playwright_config_path)
        else:
            raise ValueError(f"Type de test inconnu : '{test_type}'")

    def _build_python_command(self, test_paths: List[str], config: Dict[str, Any], pytest_args: List[str]):
        """Construit la commande pour les tests basés sur Pytest."""
        parts = [sys.executable, '-m', 'pytest']
        
        # Passer les URLs en tant qu'options et non en tant que chemins de test
        if config.get('backend_url'):
            parts.append(f"--backend-url={config['backend_url']}")
        if config.get('frontend_url'):
            parts.append(f"--frontend-url={config['frontend_url']}")
            
        # Passer les options de navigateur
        if config.get('browser'):
            parts.append(f"--browser={config['browser']}")
        if not config.get('headless', True):
            parts.append("--headed")

        # Ajouter les chemins de test réels
        if test_paths:
            parts.extend(test_paths)
        
        # Ajouter les arguments pytest supplémentaires
        if pytest_args:
            parts.extend(pytest_args)
            
        self.logger.info(f"Commande Pytest construite: {parts}")
        return parts

    def _build_js_command(self, test_paths: List[str], config: Dict[str, Any], playwright_config_path: Optional[str]):
        """Construit la commande pour les tests JS natifs Playwright."""
        node_home = os.getenv('NODE_HOME')
        if not node_home:
            raise RuntimeError("NODE_HOME n'est pas défini. Impossible de trouver npx.")
        
        npx_executable = str(Path(node_home) / 'npx.cmd') if sys.platform == "win32" else str(Path(node_home) / 'bin' / 'npx')

        parts = [npx_executable, 'playwright', 'test']
        parts.extend(test_paths)
        
        if playwright_config_path:
            parts.append(f"--config={playwright_config_path}")

        if not config.get('headless', True):
            parts.append('--headed')
            
        if config.get('browser'):
            parts.append(f"--project={config['browser']}")
        
        if config.get('timeout_ms'):
            parts.append(f"--timeout={config['timeout_ms']}")

        self.logger.info(f"Commande JS Playwright construite: {parts}")
        return parts

    async def _execute_tests(self, playwright_command_parts: List[str],
                           config: Dict[str, Any]) -> subprocess.CompletedProcess:
        
        self.logger.info(f"Commande à exécuter: {' '.join(playwright_command_parts)}")
        
        # Le répertoire de travail doit être la racine du projet
        test_dir = '.'

        try:
            # Utilisation de asyncio.create_subprocess_shell pour une meilleure gestion async
            process = await asyncio.create_subprocess_shell(
                ' '.join(playwright_command_parts),
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


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Exécuteur de tests Playwright.")
    parser.add_argument(
        'test_paths',
        nargs='+',
        help="Chemins vers les fichiers ou répertoires de test Playwright."
    )
    parser.add_argument(
        '--config',
        dest='playwright_config_path',
        help="Chemin vers le fichier de configuration Playwright (ex: playwright.config.js)."
    )
    parser.add_argument(
        '--browser',
        default='chromium',
        help="Nom du navigateur à utiliser (ex: chromium, firefox, webkit)."
    )
    parser.add_argument(
        '--headed',
        action='store_true',
        help="Exécuter les tests en mode 'headed' (avec interface graphique)."
    )
    args = parser.parse_args()

    # Configuration du logger pour la sortie console
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    main_logger = logging.getLogger('PlaywrightRunnerCLI')
    main_logger.setLevel(logging.INFO)
    main_logger.addHandler(console_handler)

    # Configuration de base pour le runner
    runner_config = {
        'browser': args.browser,
        'headless': not args.headed,
    }

    runner = PlaywrightRunner(runner_config, main_logger)

    # Exécution asynchrone des tests
    main_logger.info("Initialisation de l'exécution des tests depuis le CLI.")
    
    success = asyncio.run(runner.run_tests(
        test_paths=args.test_paths,
        playwright_config_path=args.playwright_config_path
    ))

    main_logger.info(f"Exécution terminée. Succès: {success}")
    exit_code = 0 if success else 1
    exit(exit_code)