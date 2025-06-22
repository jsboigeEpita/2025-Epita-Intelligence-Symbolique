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
        self.timeout_ms = config.get('timeout_ms', 10000)
        self.slow_timeout_ms = config.get('slow_timeout_ms', 20000)
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
            'backend_url': 'http://localhost:5003',
            'frontend_url': 'http://localhost:3000',
            'headless': self.headless,
            'browser': self.browser,
            'timeout_ms': self.config.get('timeout_ms', 30000),
            'slow_timeout_ms': self.config.get('slow_timeout_ms', 60000),
            'screenshots': True,
            'traces': True
        }
        
        # Override avec runtime
        effective_config.update(runtime_config)
        
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
            'DEBUG': 'pw:api' # Ajout du logging de debug pour Playwright
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
        """Construit la commande en appelant directement le script Playwright."""

        # Construction d'un chemin absolu vers l'exécutable Playwright
        # pour garantir qu'il soit trouvé par asyncio.create_subprocess_exec.
        base_path = Path.cwd()
        playwright_executable_path = base_path / 'node_modules' / '.bin' / 'playwright'

        if sys.platform == "win32":
            # Sous Windows, l'exécutable est un script .cmd
            playwright_executable_path = playwright_executable_path.with_suffix('.cmd')

        if not playwright_executable_path.exists():
            self.logger.error(f"L'exécutable Playwright n'a pas été trouvé à: {playwright_executable_path}")
            # On pourrait vouloir lever une exception ici pour arrêter le processus
            # au lieu de continuer avec une commande qui échouera.
            raise FileNotFoundError(f"Playwright executable not found at {playwright_executable_path}")

        cmd = [str(playwright_executable_path), 'test']
        
        # Ajout des chemins de tests
        cmd.extend(test_paths)
        
        # Options Playwright
        # On ne spécifie plus --browser car le fichier de config Playwright
        # contient déjà des projets qui le définissent.
        # cmd.append(f'--browser={config["browser"]}')
        
        if not config['headless']:
            cmd.append('--headed')
        
        # La configuration pour les screenshots, traces et vidéos
        # est généralement gérée dans le fichier playwright.config.js
        # pour plus de robustesse. On s'assure que les répertoires
        # sont définis via les variables d'environnement.
        # On peut forcer certaines options ici si nécessaire.
        
        # Exemple pour forcer le traçage :
        # NOTE DE FUSION: On garde la logique du stash qui utilise pytest, car c'est
        # l'implémentation actuelle. La migration vers l'exécutable playwright natif
        # (de "Updated upstream") est un changement trop important pour cette correction.
        
        pytest_args = []
        if config.get('headless', True):
            pytest_args.append('--headless')
            
        pytest_args.extend([
            f'--browser={config["browser"]}',
            '--screenshot=on',
        ])

        if config.get('traces', True):
            pytest_args.append('--trace')
        
        # Chemins de tests
        pytest_args.extend(test_paths)
        
        # La commande est construite pour être utilisée avec l'activation d'environnement
        # MODIFICATION : On appelle directement 'pytest' pour que 'conda run' puisse le trouver
        # au lieu d'utiliser 'python -m pytest', ce qui change le contexte d'exécution.
        cmd = ['pytest']
        cmd.extend(pytest_args)
        
        return cmd
    
    async def _read_stream(self, stream: asyncio.StreamReader, log_method):
        """Lit un flux ligne par ligne et l'enregistre."""
        while not stream.at_eof():
            line = await stream.readline()
            if line:
                log_method(line.decode(encoding='utf-8', errors='replace').rstrip())

    async def _execute_tests(self, cmd: List[str],
                             config: Dict[str, Any]) -> subprocess.CompletedProcess:
        """Exécute les tests en utilisant EnvironmentManager.run_in_conda_env pour une activation robuste."""
        
        self.logger.info("Utilisation de EnvironmentManager pour l'exécution des tests.")
        
        # Le EnvironmentManager.run_in_conda_env est synchrone.
        # Nous devons l'appeler dans un thread séparé pour ne pas bloquer la boucle asyncio.
        
        def blocking_test_execution():
            """Wrapper synchrone pour l'exécution des tests."""
            try:
                manager = EnvironmentManager(self.logger)
                # La commande `cmd` est déjà correctement formatée (ex: ['python', '-m', 'pytest', ...])
                # run_in_conda_env s'occupera de l'exécuter via `conda run` ou via chemin direct.
                self.logger.info(f"Commande à exécuter dans l'environnement conda: {' '.join(cmd)}")
                
                # On utilise capture_output=True pour récupérer stdout/stderr
                result = manager.run_in_conda_env(
                    cmd,
                    capture_output=True,
                    # Le manager utilisera l'env par défaut (`projet-is`)
                )
                
                # Logger la sortie directement depuis le résultat
                if result.stdout:
                    for line in result.stdout.splitlines():
                        self.logger.info(f"[PYTEST_STDOUT] {line}")
                if result.stderr:
                    for line in result.stderr.splitlines():
                        self.logger.warning(f"[PYTEST_STDERR] {line}")
                        
                return result
            except Exception as e:
                self.logger.critical(f"Erreur fatale dans le thread d'exécution des tests: {e}", exc_info=True)
                return subprocess.CompletedProcess(
                    ' '.join(cmd),
                    returncode=1,
                    stdout="",
                    stderr=str(e)
                )

        timeout = config.get('test_timeout', 600)
        self.logger.info(f"Timeout configuré: {timeout}s")
        
        try:
            # Exécuter la fonction bloquante dans un thread et attendre le résultat
            completed_process = await asyncio.wait_for(
                asyncio.to_thread(blocking_test_execution),
                timeout=timeout
            )
            self.logger.info(f"Exécution des tests via EnvironmentManager terminée avec le code: {completed_process.returncode}")
            return completed_process
            
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout ({timeout}s) atteint lors de l'exécution des tests.")
            return subprocess.CompletedProcess( ' '.join(cmd), returncode=-1, stdout="", stderr="Timeout expired")
        except Exception as e:
            self.logger.critical(f"Erreur critique non gérée lors de l'attente du thread de test: {e}", exc_info=True)
            return subprocess.CompletedProcess(' '.join(cmd), returncode=-2, stdout="", stderr=f"Unhandled exception: {e}")
    
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

    # Configuration par défaut pour le lancement direct
    default_config = {
        'enabled': True,
        'browser': 'chromium',
        'headless': True,
        'test_paths': ['integration/webapp/'],
        'backend_url': os.getenv('BACKEND_URL', 'http://127.0.0.1:5003'),
        'frontend_url': os.getenv('FRONTEND_URL', 'http://127.0.0.1:3000'),
    }

    runner = PlaywrightRunner(config=default_config, logger=logger)
    
    # Exécution des tests
    async def main():
        success = await runner.run_tests()
        
        # Affichage des résultats
        results = runner.get_last_results()
        if results:
            logger.info(f"Résultats finaux: {json.dumps(results['stats'], indent=2)}")
        
        # Propagation du code de sortie pour l'intégration CI/CD
        if not success:
            sys.exit(1)

    asyncio.run(main())