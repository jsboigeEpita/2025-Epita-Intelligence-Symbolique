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
    from project_core.managers.environment_manager import EnvironmentManager
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
    
    from project_core.managers.environment_manager import EnvironmentManager
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
        self.test_paths = config.get('test_paths', ["tests/e2e/python/"])
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
        Exécute les tests Playwright de manière groupée.
        
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
        
        # Si un chemin de dossier est fourni, trouver tous les fichiers de test
        base_test_paths = test_paths or self.test_paths
        all_test_files = []
        for path_str in base_test_paths:
            path = Path(path_str)
            if path.is_dir():
                all_test_files.extend([str(p) for p in path.rglob('test_*.py')])
            elif path.is_file():
                all_test_files.append(str(path))

        self.logger.info(f"Lancement des tests sur {len(all_test_files)} fichier(s).")
        self.logger.info(f"Fichiers cibles: {all_test_files}")
        self.logger.info(f"Configuration: {effective_config}")

        try:
            # Préparation de l'environnement
            await self._prepare_test_environment(effective_config)

            # Construction de la commande pour tous les fichiers
            cmd = self._build_playwright_command(all_test_files, effective_config)

            # Exécution de tous les tests en une seule fois
            result = await self._execute_tests(cmd, effective_config)

            # Analyse des résultats
            success = await self._analyze_results(result)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erreur exécution tests: {e}", exc_info=True)
            return False
    
    def _merge_runtime_config(self, runtime_config: Dict[str, Any]) -> Dict[str, Any]:
        """Fusionne configuration par défaut avec runtime"""
        self.logger.info("--- Début fusion configuration runtime ---")
        self.logger.info(f"Configuration runtime reçue: {runtime_config}")
        
        effective_config = {
            'backend_url': 'http://localhost:5003',
            'frontend_url': 'http://localhost:3000',
            'headless': True, # Valeur par défaut standard
            'browser': self.browser,
            'timeout_ms': self.config.get('timeout_ms', 30000),
            'slow_timeout_ms': self.config.get('slow_timeout_ms', 60000),
            'screenshots': True,
            'traces': True
        }
        self.logger.info(f"Configuration effective initiale: {effective_config}")
        
        # Appliquer la configuration runtime en premier
        effective_config.update(runtime_config)
        self.logger.info(f"Configuration effective après fusion: {effective_config}")
        
        # Vérification finale de la valeur headless
        final_headless_value = effective_config.get('headless')
        self.logger.info(f"VALEUR FINALE POUR HEADLESS: {final_headless_value} (Type: {type(final_headless_value)})")
        self.logger.info("--- Fin fusion configuration runtime ---")
        
        return effective_config
    
    async def _prepare_test_environment(self, config: Dict[str, Any]):
        """Prépare l'environnement pour les tests"""
        # Variables d'environnement pour les tests
        env_vars = {
            'BACKEND_URL': config['backend_url'],
            'FRONTEND_URL': config['frontend_url'],
            'HEADLESS': str(config['headless']).lower(),
            'BROWSER': config['browser'],
            'SCREENSHOTS_DIR': str(self.screenshots_dir),
            'TRACES_DIR': str(self.traces_dir),
            'KMP_DUPLICATE_LIB_OK': 'TRUE', # Contournement pour le conflit OpenMP
            'PWDEBUG': '0' # DÉSACTIVÉ : Forçait le mode headed et l'inspecteur.
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
        self.logger.info("Préparation de la commande Pytest.")
        
        # La commande commence maintenant directement avec 'pytest'.
        # Elle sera préfixée par le chemin complet de l'exécutable plus tard.
        cmd = [
            'pytest',
            '-p', 'playwright', # Forcer le chargement du plugin playwright
            '-v',
            '-s', # Alias pour --capture=no, pour voir les prints en direct
            '-x',  # Arrêter après la première défaillance
            '--slowmo=100',  # Ralentir un peu plus pour l'observation
            '--log-cli-level=DEBUG', # Augmenter la verbosité
            '--log-file=logs/pytest.log',
        ]

        cmd.extend(test_paths)

        # Le mode Headless est géré par l'argument --headed.
        # On l'ajoute si la configuration le demande explicitement.
        # Le mode headless est maintenant entièrement géré via la variable d'environnement
        # HEADLESS et le fichier playwright.config.js. L'argument en ligne de commande
        # est non seulement inutile, mais il cause une erreur "unrecognized arguments".
        self.logger.info("Le mode Headless est contrôlé par la variable d'environnement HEADLESS.")

        if config.get('traces', True):
            cmd.append('--tracing=on')
            
        cmd.append(f'--browser={config["browser"]}')

        if 'backend_url' in config:
            cmd.append(f"--backend-url={config['backend_url']}")
        if 'frontend_url' in config:
            cmd.append(f"--frontend-url={config['frontend_url']}")
        
        return cmd
    
    async def _read_stream(self, stream: asyncio.StreamReader, log_method):
        """Lit un flux ligne par ligne et l'enregistre."""
        while not stream.at_eof():
            line = await stream.readline()
            if line:
                log_method(line.decode(encoding='utf-8', errors='replace').rstrip())

    def _get_conda_env_executable(self, env_name: str, executable_name: str) -> Optional[str]:
        """Trouve le chemin d'un exécutable pour un environnement Conda donné."""
        try:
            self.logger.info(f"Recherche de l'exécutable '{executable_name}' dans l'environnement Conda '{env_name}'")
            
            result = subprocess.run(['conda', 'info', '--envs', '--json'], capture_output=True, text=True, check=True, shell=True)
            envs_data = json.loads(result.stdout)
            
            env_path_str = None
            for env in envs_data.get('envs', []):
                if Path(env).name == env_name:
                    env_path_str = env
                    self.logger.info(f"Chemin trouvé pour l'environnement '{env_name}': {env_path_str}")
                    break
            
            if not env_path_str:
                self.logger.error(f"Environnement Conda '{env_name}' non trouvé.")
                return None

            # Sur Windows, les scripts sont dans le sous-dossier "Scripts"
            executable_path = Path(env_path_str) / 'Scripts' / f'{executable_name}.exe'
            if not executable_path.exists():
                 # Fallback pour les systèmes non-Windows
                executable_path = Path(env_path_str) / 'bin' / executable_name
            
            if executable_path.exists():
                self.logger.info(f"Exécutable '{executable_name}' validé: {executable_path}")
                return str(executable_path)
            else:
                self.logger.error(f"'{executable_name}' non trouvé dans '{env_path_str}' (vérifié dans Scripts/ et bin/).")
                return None

        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Erreur critique lors de la recherche de l'exécutable Conda '{executable_name}': {e}")
            return None

    async def _execute_tests(self, cmd: List[str],
                             config: Dict[str, Any]) -> subprocess.CompletedProcess:
        """Exécute les tests directement avec l'exécutable pytest de l'environnement Conda cible."""
        
        env_name = "projet-is-roo-new"
        pytest_executable = self._get_conda_env_executable(env_name, "pytest")

        if not pytest_executable:
            error_msg = f"Impossible de trouver l'exécutable 'pytest' pour l'environnement Conda '{env_name}'."
            self.logger.error(error_msg)
            return subprocess.CompletedProcess(cmd, returncode=-1, stderr=error_msg)

        # Remplacer 'pytest' par le chemin complet de l'exécutable
        if cmd and cmd[0] == 'pytest':
            cmd[0] = pytest_executable
        else:
            self.logger.warning(f"La commande de test ne commence pas par 'pytest'. Tentative d'insertion de l'exécutable au début.")
            cmd.insert(0, pytest_executable)

        # Préparation de l'environnement pour le sous-processus
        script_env = os.environ.copy()
        
        command_str_for_log = " ".join(cmd)
        self.logger.info(f"Exécution de la commande de test directe: {command_str_for_log}")

        timeout = config.get('test_timeout', 900)
        self.logger.info(f"Timeout configuré: {timeout}s")
        
        stdout_lines = []
        stderr_lines = []

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
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
        'backend_url': os.getenv('BACKEND_URL', 'http://127.0.0.1:5003'),
        'frontend_url': os.getenv('FRONTEND_URL', 'http://127.0.0.1:3000'),
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