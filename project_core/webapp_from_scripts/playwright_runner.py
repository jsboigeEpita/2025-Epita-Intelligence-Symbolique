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
        self.process_timeout_s = config.get('process_timeout_s', 600)  # Timeout global du processus en secondes
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
            'API_BASE_URL': config['backend_url'], # Correction du nom de la variable
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
        # Construction d'un chemin absolu vers npx.cmd pour éviter les problèmes de PATH et de shell=True.
        # C'est la méthode la plus robuste pour Windows.
        node_home = os.getenv('NODE_HOME')
        if not node_home:
            raise EnvironmentError("La variable d'environnement NODE_HOME n'est pas définie. Impossible de trouver npx.")
        
        npx_executable = Path(node_home) / 'npx.cmd'
        if not npx_executable.is_file():
            raise FileNotFoundError(f"L'exécutable npx.cmd n'a pas été trouvé à l'emplacement attendu: {npx_executable}")

        self.logger.info(f"Utilisation de l'exécutable npx trouvé à: {npx_executable}")

        parts = [str(npx_executable), 'playwright', 'test']
        parts.extend(test_paths)
        
        if not config.get('headless', True):
            parts.append('--headed')
            
        # Lorsque le fichier de configuration utilise des "projets",
        # il faut utiliser --project au lieu de --browser.
        parts.append(f"--project={config['browser']}")
        
        # Utiliser un reporter qui ne bloque pas la fin du processus
        parts.append('--reporter=list')

        self.logger.info(f"Construction de la commande 'npx playwright': {parts}")
        return parts

    async def _execute_tests(self, playwright_command_parts: List[str],
                           config: Dict[str, Any]) -> subprocess.CompletedProcess:
        """Exécute les tests en utilisant asyncio.create_subprocess_exec pour un contrôle total."""
        
        self.logger.info(f"Commande à exécuter (via asyncio): {' '.join(playwright_command_parts)}")
        
        proc = None
        playwright_stdout_log = Path("logs") / "playwright_stdout.log"
        playwright_stderr_log = Path("logs") / "playwright_stderr.log"
        self.logger.info(f"Redirection stdout de Playwright vers: {playwright_stdout_log}")
        self.logger.info(f"Redirection stderr de Playwright vers: {playwright_stderr_log}")

        try:
            with open(playwright_stdout_log, 'wb') as stdout_file, \
                 open(playwright_stderr_log, 'wb') as stderr_file:
                
                proc = await asyncio.create_subprocess_exec(
                    *playwright_command_parts,
                    stdout=stdout_file,
                    stderr=stderr_file
                )

                # Attendre la fin du processus
                return_code = await proc.wait()

                self.logger.info(f"Tests terminés - Code retour: {return_code}")
            
            # Lire le contenu des logs pour le retour
            stdout = playwright_stdout_log.read_text(encoding='utf-8', errors='ignore')
            stderr = playwright_stderr_log.read_text(encoding='utf-8', errors='ignore')

            # Retourner un objet compatible avec l'analyseur de résultats
            return subprocess.CompletedProcess(
                args=playwright_command_parts,
                returncode=return_code,
                stdout=stdout,
                stderr=stderr
            )

        except asyncio.CancelledError:
            self.logger.warning("L'exécution des tests a été annulée (probablement par timeout).")
            if proc:
                self.logger.info(f"Tentative de terminaison forcée du processus Playwright (PID: {proc.pid})...")
                try:
                    proc.terminate()
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                    self.logger.info("Processus Playwright terminé.")
                except Exception:
                    self.logger.error(f"Échec de la terminaison, tentative de kill du processus Playwright (PID: {proc.pid})...")
                    proc.kill()
                    await proc.wait()
                    self.logger.warning("Processus Playwright tué.")
            # Il est essentiel de relancer CancelledError pour que le timeout de l'orchestrateur fonctionne.
            raise

        except Exception as e:
            self.logger.error(f"Erreur majeure lors de l'exécution de la commande Playwright avec asyncio: {e}", exc_info=True)
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