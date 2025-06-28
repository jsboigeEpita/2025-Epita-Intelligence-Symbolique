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
        self.test_paths = config.get('test_paths', ['tests/functional/'])
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
            
            # Construction commande pytest
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
            'timeout_ms': self.timeout_ms,
            'slow_timeout_ms': self.slow_timeout_ms,
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
            # Forcer KMP_DUPLICATE_LIB_OK pour éviter les crashs avec MKL
            'KMP_DUPLICATE_LIB_OK': 'TRUE',
            # Le mode DEBUG est maintenant activé via page.pause() dans le code de test
        }
        
        # Mettre à jour l'environnement actuel du processus
        os.environ.update(env_vars)
            
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
    
    def _build_playwright_command(self, test_paths: List[str], config: Dict[str, Any]) -> List[str]:
        """Construit la commande pytest directe pour Playwright."""
        self.logger.info("Préparation de la commande Pytest pour l'environnement Conda 'projet-is'.")

        python_executable = self._get_conda_env_python_executable()
        if not python_executable:
            raise RuntimeError("Impossible de trouver l'exécutable Python pour l'environnement Conda 'projet-is'.")

        # Base de la commande
        cmd = [
            str(python_executable),
            "-m", "pytest",
            "-v",  # Verbose
            "-p", "no:asyncio", # Empêche le plugin pytest-asyncio de causer des conflits
            "--capture=no", # Affiche les prints en temps réel
            "--slowmo=100", # Ralentit les opérations Playwright
            "--log-cli-level=DEBUG", # Niveau de log pour la console
            f"--log-file={self.traces_dir / 'pytest.log'}"
        ]
        
        # Chemins des tests
        cmd.extend(test_paths)

        # Options Playwright
        if not config.get('headless', True):
            cmd.append('--headed')
            self.logger.info(f"Le mode Headless est configuré sur: {config.get('headless')}")

        cmd.append(f'--tracing={"on" if config.get("traces") else "off"}')
        cmd.append(f'--browser={config.get("browser", "chromium")}')

        # URLs pour les fixtures
        cmd.append(f'--backend-url={config.get("backend_url")}')
        cmd.append(f'--frontend-url={config.get("frontend_url")}')
        
        return cmd

    def _get_conda_env_python_executable(self, env_name: str = "projet-is") -> Optional[Path]:
         """
         Trouve le chemin de l'exécutable Python pour un environnement Conda donné.
         """
         self.logger.info(f"Recherche de l'environnement Conda nommé: '{env_name}'")
         try:
             # Commande pour obtenir les informations sur les environnements conda en format JSON
             command = ["conda", "env", "list", "--json"]
             result = subprocess.run(command, capture_output=True, text=True, check=True)
            
             data = json.loads(result.stdout)
            
             # Recherche du chemin de l'environnement
             for env_path_str in data.get("envs", []):
                 env_path = Path(env_path_str)
                 if env_path.name == env_name:
                     self.logger.info(f"Chemin trouvé pour l'environnement '{env_name}': {env_path}")
                     python_executable = env_path / "python.exe" if sys.platform == "win32" else env_path / "bin" / "python"
                     if python_executable.exists():
                         self.logger.info(f"Exécutable Python validé pour l'environnement '{env_name}': {python_executable}")
                         return python_executable
                     else:
                         self.logger.warning(f"Chemin de l'environnement '{env_name}' trouvé, mais l'exécutable Python '{python_executable}' est introuvable.")
                         return None

             self.logger.error(f"L'environnement Conda '{env_name}' est introuvable dans la liste des environnements.")
             return None

         except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError) as e:
             self.logger.error(f"Erreur lors de la recherche de l'environnement Conda '{env_name}': {e}")
             return None
    
    async def _execute_tests(self, cmd: List[str],
                           config: Dict[str, Any]) -> subprocess.CompletedProcess:
        """Exécute les tests et capture la sortie"""
        self.logger.info(f"Commande test: {' '.join(cmd)}")
        
        # Fichiers de log
        stdout_file = self.traces_dir / 'pytest_stdout.log'
        stderr_file = self.traces_dir / 'pytest_stderr.log'
        
        try:
            # Exécution avec capture
            if sys.platform == "win32":
                # PowerShell nécessite gestion spéciale
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=config.get('test_timeout', 900),  # Augmenté pour le débogage interactif
                    cwd=Path.cwd()
                )
            else:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=config.get('test_timeout', 900),
                    cwd=Path.cwd()
                )
            
            # Sauvegarde logs
            with open(stdout_file, 'w', encoding='utf-8') as f:
                f.write(result.stdout)
            with open(stderr_file, 'w', encoding='utf-8') as f:
                f.write(result.stderr)
            
            self.logger.info(f"Tests terminés - Code retour: {result.returncode}")
            return result
            
        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Timeout tests après {e.timeout}s")
            raise
        except Exception as e:
            self.logger.error(f"Erreur exécution tests: {e}")
            raise
    
    async def _analyze_results(self, result: subprocess.CompletedProcess) -> bool:
        """Analyse les résultats de test et génère rapport"""
        success = result.returncode == 0
        
        # Parsing sortie pytest
        stdout_lines = result.stdout.split('\n') if result.stdout else []
        stderr_lines = result.stderr.split('\n') if result.stderr else []
        
        # Extraction statistiques
        stats = self._extract_pytest_stats(stdout_lines)
        
        # Sauvegarde résultats détaillés
        self.last_results = {
            'success': success,
            'return_code': result.returncode,
            'stats': stats,
            'stdout_lines': len(stdout_lines),
            'stderr_lines': len(stderr_lines),
            'artifacts': self._collect_artifacts()
        }
        
        # Log résumé
        if success:
            self.logger.info(f"Tests réussis: {stats}")
        else:
            self.logger.error(f"[ERROR] Tests échoués: {stats}")
            
            # Log premières erreurs
            error_lines = [line for line in stderr_lines if line.strip()][:10]
            for error_line in error_lines:
                self.logger.error(f"   {error_line}")
        
        # Génération rapport JSON
        await self._save_test_report()
        
        return success
    
    def _extract_pytest_stats(self, stdout_lines: List[str]) -> Dict[str, Any]:
        """Extrait les statistiques de pytest"""
        stats = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': 0,
            'duration': 0.0
        }
        
        for line in stdout_lines:
            # Ligne de résumé pytest
            if ' passed' in line or ' failed' in line:
                # Ex: "5 passed, 2 failed in 23.45s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'passed' and i > 0:
                        stats['passed'] = int(parts[i-1])
                    elif part == 'failed' and i > 0:
                        stats['failed'] = int(parts[i-1])
                    elif part == 'skipped' and i > 0:
                        stats['skipped'] = int(parts[i-1])
                    elif part == 'error' and i > 0:
                        stats['errors'] = int(parts[i-1])
                    elif 'in' in parts and i < len(parts) - 1:
                        try:
                            duration_str = parts[i+1].rstrip('s')
                            stats['duration'] = float(duration_str)
                        except (ValueError, IndexError):
                            pass
        
        stats['total'] = stats['passed'] + stats['failed'] + stats['skipped'] + stats['errors']
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