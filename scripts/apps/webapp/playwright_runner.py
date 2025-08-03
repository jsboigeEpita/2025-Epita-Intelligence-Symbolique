#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright Runner - Gestionnaire d'exécution des tests Playwright
=================================================================

Intègre et exécute les tests fonctionnels Playwright existants.

Auteur: Projet Intelligence Symbolique EPITA
Date: 07/06/2025
"""

import os
import sys
import asyncio
import logging
import subprocess
import argparse
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

# Ajout pour accéder à l'EnvironmentManager et aux utilitaires du projet
try:
    # Ce chemin est relatif à la structure attendue du projet
    from project_core.core_from_scripts.environment_manager import EnvironmentManager
    from project_core.core_from_scripts.common_utils import get_project_root
except ImportError:
    # Fallback robuste si le script est exécuté depuis un contexte inattendu
    # On remonte à la racine du projet et on l'ajoute au path
    current_dir = Path(__file__).resolve().parent
    project_root_path = None
    # Remonter jusqu'à trouver un marqueur de racine (ex: .git, pyproject.toml)
    for parent in current_dir.parents:
        if (parent / '.git').exists() or (parent / 'pyproject.toml').exists():
            project_root_path = parent
            break
    if project_root_path and str(project_root_path) not in sys.path:
        sys.path.insert(0, str(project_root_path))
    
    from project_core.core_from_scripts.environment_manager import EnvironmentManager
    from project_core.core_from_scripts.common_utils import get_project_root


class PlaywrightRunner:
    """
    Gestionnaire d'exécution des tests Playwright
    
    Fonctionnalités :
    - Exécution tests fonctionnels existants
    - Configuration runtime dynamique
    - Gestion modes headless/headed
    - Capture screenshots et traces
    - Rapports de résultats
    """
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        
        # Configuration Playwright
        self.enabled = config.get('enabled', True)
        self.browser = config.get('browser', 'chromium')
        self.headless = config.get('headless', True)
        self.timeout_ms = config.get('timeout_ms', 60000)
        self.slow_timeout_ms = config.get('slow_timeout_ms', 120000)
        self.test_paths = config.get('test_paths', ["tests/integration/webapp/"])
        self.screenshots_dir = Path(config.get('screenshots_dir', 'logs/screenshots'))
        self.traces_dir = Path(config.get('traces_dir', 'logs/traces'))
        
        # Création répertoires
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        
        # Variables runtime
        self.last_results: Optional[Dict[str, Any]] = None
        
    async def run_tests(self, test_paths: List[str] = None, 
                       runtime_config: Dict[str, Any] = None) -> bool:
        """
        Exécute les tests Playwright avec configuration runtime
        
        Args:
            test_paths: Chemins spécifiques des tests (optionnel)
            runtime_config: Configuration dynamique
            
        Returns:
            bool: True si tous les tests passent
        """
        if not self.enabled:
            self.logger.info("Tests Playwright désactivés")
            return True
        
        # Configuration effective
        effective_config = self._merge_runtime_config(runtime_config or {})
        test_paths = test_paths or self.test_paths
        
        self.logger.info(f"Démarrage tests Playwright: {test_paths}")
        self.logger.info(f"Configuration: {effective_config}")
        
        try:
            # Préparation environnement test
            await self._prepare_test_environment(effective_config)
            
            # Construction commande Playwright
            cmd = self._build_playwright_command(test_paths, effective_config)
            
            # Exécution tests
            result = await self._execute_tests(cmd, effective_config)
            
            # Analyse résultats
            success = await self._analyze_results(result)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erreur exécution tests: {e}")
            return False
    
    def _merge_runtime_config(self, runtime_config: Dict[str, Any]) -> Dict[str, Any]:
        """Fusionne configuration par défaut avec runtime"""
        effective_config = {
            'backend_url': 'http://localhost:8095',
            'frontend_url': 'http://localhost:8085',
            'headless': True, # Valeur par défaut standard
            'browser': self.browser,
            'timeout_ms': self.config.get('timeout_ms', 30000),
            'slow_timeout_ms': self.config.get('slow_timeout_ms', 60000),
            'screenshots': True,
            'traces': True,
            'pwdebug': '0'  # S'assurer que le mode debug est désactivé par défaut
        }
        
        # Appliquer la configuration runtime en premier
        effective_config.update(runtime_config)
        
        # Forcer le mode headed pour le débogage, cette valeur écrase toute autre config
        
        return effective_config
    
    async def _prepare_test_environment(self, config: Dict[str, Any]):
        """Prépare l'environnement pour les tests"""
        # Variables d'environnement pour les tests
        env_vars = {
            'BACKEND_URL': config['backend_url'],
            'FRONTEND_URL': config.get('frontend_url') or "",
            'HEADLESS': str(config['headless']).lower(),
            'BROWSER': config['browser'],
            'SCREENSHOTS_DIR': str(self.screenshots_dir),
            'TRACES_DIR': str(self.traces_dir),
            'KMP_DUPLICATE_LIB_OK': 'TRUE', # Contournement pour le conflit OpenMP
            'PWDEBUG': config.get('pwdebug', '0'), # Rendre le mode debug configurable
        }
        
        for key, value in env_vars.items():
            os.environ[key] = value
            
        self.logger.info(f"Variables test configurées: {env_vars}")
        
        # Nettoyage répertoires précédents
        await self._cleanup_previous_artifacts()
    
    async def _cleanup_previous_artifacts(self):
        """Nettoie les artifacts de tests précédents"""
        for artifact_dir in [self.screenshots_dir, self.traces_dir]:
            if artifact_dir.exists():
                for file in artifact_dir.glob('*'):
                    try:
                        if file.is_file():
                            file.unlink()
                    except Exception:
                        pass  # Ignore erreurs de suppression
    
    def _build_playwright_command(self, test_paths: List[str],
                                 config: Dict[str, Any]) -> List[str]:
        """Construit la commande pour exécuter les tests via Pytest."""

        self.logger.info(f"Préparation de la commande Pytest pour l'environnement Conda 'projet-is-roo-new'.")

        cmd = [
            'python', '-m', 'pytest',
            '-v',
            '-p', 'no:asyncio', # Désactive le plugin asyncio pour éviter les conflits avec Playwright
            '-p', 'pytest_playwright', # Force le chargement du plugin Playwright
            '--capture=no',
            '--slowmo=100',  # Ralentir un peu plus pour l'observation
            '--log-cli-level=DEBUG', # Augmenter la verbosité
            '--log-file=logs/pytest.log',
            # Le timeout est maintenant géré par l'orchestrateur principal
            # '--timeout', '300'
        ]
        
        # Correction: Convertir les chemins de test en chemins absolus pour éviter les erreurs "file not found"
        # lorsque la commande est exécutée depuis un autre répertoire de travail par le wrapper PowerShell.
        project_root = Path(get_project_root())
        # Convertit les chemins en format POSIX (avec /) pour une meilleure compatibilité entre les shells
        absolute_test_paths = [(project_root / path).as_posix() for path in test_paths]
        self.logger.info(f" chemins de test absolus (format POSIX) : {absolute_test_paths}")


        # Ajout du répertoire de test pour que pytest le découvre
        # Forçage pour le débogage du test qui timeout
        cmd.extend(absolute_test_paths)

        # Le mode Headless est géré par l'argument --headed.
        # On l'ajoute si la configuration le demande explicitement.
        if not config.get('headless', True):
            cmd.append('--headed')
        self.logger.info(f"Le mode Headless est configuré sur: {config.get('headless', True)}")

        # --tracing on est l'équivalent de --trace=on pour pytest-playwright
        if config.get('traces', True):
            cmd.append('--tracing=on')
            
        # Spécifier le navigateur à utiliser
        cmd.append(f'--browser={config["browser"]}')

        # Passer les URLs dynamiques à Pytest.
        # Ceci surcharge les valeurs par défaut définies dans tests/conftest.py
        if 'backend_url' in config:
            cmd.append(f"--backend-url={config['backend_url']}")
        if config.get('frontend_url'):
            cmd.append(f"--frontend-url={config['frontend_url']}")
        
        return cmd
    
    async def _read_stream(self, stream: asyncio.StreamReader, log_method):
        """Lit un flux ligne par ligne et l'enregistre."""
        while not stream.at_eof():
            line = await stream.readline()
            if line:
                log_method(line.decode(encoding='utf-8', errors='replace').rstrip())

    def _get_conda_env_python_executable(self, env_name: str) -> Optional[str]:
        """Trouve le chemin de l'exécutable Python pour un environnement Conda donné."""
        try:
            self.logger.info(f"Recherche de l'environnement Conda nommé: '{env_name}'")
            # Exécute `conda info` pour obtenir la liste des environnements. Utilisation de `shell=True` pour Windows.
            result = subprocess.run(['conda', 'info', '--envs', '--json'], capture_output=True, text=True, check=True, shell=True)
            envs_data = json.loads(result.stdout)
            
            # Cherche le chemin de l'environnement cible
            env_path_str = None
            for env in envs_data.get('envs', []):
                if Path(env).name == env_name:
                    env_path_str = env
                    self.logger.info(f"Chemin trouvé pour l'environnement '{env_name}': {env_path_str}")
                    break
            
            if not env_path_str:
                self.logger.error(f"Environnement Conda '{env_name}' non trouvé dans la liste des environnements.")
                return None

            # Construit le chemin de l'exécutable Python
            python_executable = Path(env_path_str) / 'python.exe'
            if python_executable.exists():
                self.logger.info(f"Exécutable Python validé pour l'environnement '{env_name}': {python_executable}")
                return str(python_executable)
            else:
                self.logger.error(f"python.exe non trouvé dans l'environnement '{env_name}' au chemin: {python_executable}")
                return None

        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Erreur critique lors de la recherche de l'environnement Conda via 'conda info': {e}")
            return None

    async def _execute_tests(self, cmd: List[str],
                             config: Dict[str, Any]) -> subprocess.CompletedProcess:
        """Exécute les tests via le wrapper PowerShell pour garantir l'activation de l'environnement Conda."""
        
        project_root = Path(get_project_root())
        wrapper_script = project_root / 'activate_project_env.ps1'

        if not wrapper_script.exists():
            error_msg = f"Script wrapper introuvable: {wrapper_script}"
            self.logger.error(error_msg)
            return subprocess.CompletedProcess(cmd, returncode=-1, stderr=error_msg)

        # La commande originale est jointe en une chaîne, avec des guillemets pour chaque argument
        # afin de gérer les chemins avec des espaces.
        command_to_run = " ".join(f'"{c}"' for c in cmd)

        final_cmd = [
            'powershell.exe',
            '-ExecutionPolicy', 'Bypass',
            '-File', str(wrapper_script),
            '-CommandToRun', command_to_run
        ]
        
        # Préparation de l'environnement pour le sous-processus
        script_env = os.environ.copy()
        
        command_str_for_log = " ".join(final_cmd)
        self.logger.info(f"Exécution de la commande de test via wrapper: {command_str_for_log}")

        timeout = config.get('test_timeout', 900)
        self.logger.info(f"Timeout configuré: {timeout}s")
        
        stdout_lines = []
        stderr_lines = []

        try:
            process = await asyncio.create_subprocess_exec(
                *final_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=script_env
            )

            async def log_stream(stream, log_func, line_buffer):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded_line = line.decode('utf-8', errors='replace').rstrip()
                    log_func(decoded_line)
                    line_buffer.append(decoded_line)

            stdout_task = asyncio.create_task(log_stream(process.stdout, self.logger.info, stdout_lines))
            stderr_task = asyncio.create_task(log_stream(process.stderr, self.logger.warning, stderr_lines))

            await asyncio.wait_for(asyncio.gather(stdout_task, stderr_task, process.wait()), timeout=timeout)
            
            returncode = process.returncode
            self.logger.info(f"Tests pytest terminés avec le code de retour : {returncode}")

        except asyncio.TimeoutError:
            self.logger.error(f"Timeout ({timeout}s) atteint pendant l'exécution des tests.")
            if 'process' in locals() and process.returncode is None:
                process.kill()
                await process.wait()
            return subprocess.CompletedProcess(command_str_for_log, returncode=-1, stdout="\n".join(stdout_lines), stderr="\n".join(stderr_lines))
        except Exception as e:
            self.logger.critical(f"Erreur critique lors de l'exécution du sous-processus de test : {e}", exc_info=True)
            return subprocess.CompletedProcess(command_str_for_log, returncode=-2, stdout="\n".join(stdout_lines), stderr=str(e))

        return subprocess.CompletedProcess(
            command_str_for_log,
            process.returncode,
            stdout="\n".join(stdout_lines),
            stderr="\n".join(stderr_lines)
        )
    
    async def _analyze_results(self, result: subprocess.CompletedProcess) -> bool:
        """Analyse les résultats de test et génère un rapport."""
        success = result.returncode == 0
        
        stdout_content = result.stdout or ""
        stderr_content = result.stderr or ""
        
        # Sauvegarde des logs bruts dans les fichiers
        stdout_file = self.traces_dir / 'playwright_stdout.log'
        stderr_file = self.traces_dir / 'playwright_stderr.log'
        with open(stdout_file, 'w', encoding='utf-8') as f:
            f.write(stdout_content)
        with open(stderr_file, 'w', encoding='utf-8') as f:
            f.write(stderr_content)

        self.last_results = {
            'success': success,
            'return_code': result.returncode,
            'stdout_lines': len(stdout_content.splitlines()),
            'stderr_lines': len(stderr_content.splitlines()),
            'artifacts': self._collect_artifacts()
        }
        
        if success:
            self.logger.info("Tests Playwright réussis.")
            # Optionnel: extraire des infos de la sortie si besoin
        else:
            # NOTE DE FUSION: On garde la sortie détaillée du stderr du stash.
            self.logger.error(f"Échec des tests (code de retour: {result.returncode}).")
            
            if stderr_content:
                self.logger.error("--- Erreurs (stderr) ---")
                # Pas besoin de logger chaque ligne car elles ont déjà été loggées en temps réel
                self.logger.error("Voir les logs [PYTEST_STDERR] ci-dessus pour les détails complets.")
                self.logger.error("--- Fin des erreurs ---")
            else:
                self.logger.error("Aucune sortie d'erreur (stderr) n'a été capturée, mais le code de retour indique un échec.")
        
        await self._save_test_report()
        
        return success
    
    def _extract_pytest_stats(self, stdout_lines: List[str]) -> Dict[str, Any]:
        """(Obsolète) Extrait les statistiques de pytest. Conservé pour antiquité."""
        # Cette fonction est maintenant largement obsolète car nous n'analysons plus
        # la sortie de pytest. On se base sur le code de retour de Playwright.
        stats = { 'detail': 'Parsing de sortie non effectué. Se baser sur success et return_code.' }
        return stats
    
    def _collect_artifacts(self) -> Dict[str, List[str]]:
        """Collecte les artifacts générés par les tests"""
        artifacts = {
            'screenshots': [],
            'traces': [],
            'videos': []
        }
        
        # Screenshots
        if self.screenshots_dir.exists():
            artifacts['screenshots'] = [
                str(f) for f in self.screenshots_dir.glob('*.png')
            ]
        
        # Traces et vidéos
        if self.traces_dir.exists():
            artifacts['traces'] = [
                str(f) for f in self.traces_dir.glob('*.zip')
            ]
            artifacts['videos'] = [
                str(f) for f in self.traces_dir.glob('*.webm')
            ]
        
        return artifacts
    
    async def _save_test_report(self):
        """Sauvegarde rapport détaillé en JSON"""
        if not self.last_results:
            return
            
        report_file = self.traces_dir / 'test_report.json'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.last_results, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Rapport test sauvé: {report_file}")
    
    def get_last_results(self) -> Optional[Dict[str, Any]]:
        """Retourne les derniers résultats de test"""
        return self.last_results
    
    def get_status(self) -> Dict[str, Any]:
        """Retourne l'état du runner"""
        return {
            'enabled': self.enabled,
            'browser': self.browser,
            'headless': self.headless,
            'test_paths': self.test_paths,
            'screenshots_dir': str(self.screenshots_dir),
            'traces_dir': str(self.traces_dir),
            'last_results': self.last_results
        }
if __name__ == '__main__':
    """
    Point d'entrée pour l'exécution directe du script.
    Permet de lancer les tests Playwright de manière autonome.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
    logger = logging.getLogger("PlaywrightRunnerCLI")

    parser = argparse.ArgumentParser(description="Exécute les tests Playwright.")
    parser.add_argument(
        '--test-file',
        type=str,
        help="Chemin spécifique vers un fichier de test à exécuter."
    )
    args = parser.parse_args()
    
    # Configuration par défaut pour le lancement direct
    default_config = {
        'enabled': True,
        'browser': 'chromium',
        'headless': True,
        'backend_url': os.getenv('BACKEND_URL', 'http://127.0.0.1:8095'),
        'frontend_url': os.getenv('FRONTEND_URL', 'http://127.0.0.1:8085'),
    }

    # Définir les chemins de test par défaut si aucun n'est spécifié
    test_paths_to_run = ['tests/e2e/python/']
    if args.test_file:
        test_paths_to_run = [args.test_file]

    runner = PlaywrightRunner(config=default_config, logger=logger)
    
    # Exécution des tests
    async def main():
        success = await runner.run_tests(test_paths=test_paths_to_run)
        
        # Affichage des résultats
        results = runner.get_last_results()
        if results:
            logger.info(f"Résultats finaux: {json.dumps(results, indent=2)}")
        
        # Propagation du code de sortie pour l'intégration CI/CD
        if not success:
            sys.exit(1)

    asyncio.run(main())