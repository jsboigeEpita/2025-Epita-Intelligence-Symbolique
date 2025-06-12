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
            
            # Construction commande playwright
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
            # PLAYWRIGHT_BASE_URL est utilisée par playwright.config.js pour les tests .spec.js
            # On utilise backend_url par défaut, car c'est souvent la cible principale des tests d'interface.
            # Si le frontend est sur un port différent et est la cible, ajuster ici ou via runtime_config.
            'PLAYWRIGHT_BASE_URL': config.get('frontend_url') or config['backend_url'],
            'HEADLESS': str(config['headless']).lower(),
            'BROWSER': config['browser'],
            'SCREENSHOTS_DIR': str(self.screenshots_dir),
            'TRACES_DIR': str(self.traces_dir)
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
        """Construit la commande npx playwright test avec les bonnes options."""
        
        # Commande de base
        playwright_cmd = ['npx', 'playwright', 'test']
        
        # Ajout des chemins de tests
        playwright_cmd.extend(test_paths)

        # Ajout des options Playwright
        playwright_cmd.append(f"--browser={config['browser']}")
        if not config['headless']:
            playwright_cmd.append('--headed')
        
        playwright_cmd.append(f"--timeout={config['timeout_ms']}")
        
        # La configuration pour les screenshots et les traces est dans playwright.config.js
        # et est activée par défaut.
        
        # Commande complète avec activation de l'environnement
        if sys.platform == "win32":
            # Le CWD pour l'exécution sera `tests_playwright` donc les paths sont relatifs
            # La commande `npx` utilisera le node portable si `NODE_HOME` est dans le PATH
            # ce qui est fait par `activate_project_env.ps1`
            command_to_run = ' '.join(playwright_cmd)
            # Le script activate_project_env.ps1 doit être appelé depuis la racine du projet.
            # Le CWD de _execute_tests est 'tests_playwright', donc on utilise un chemin relatif.
            activate_script_path = (Path.cwd() / 'scripts/env/activate_project_env.ps1').resolve()
            cmd = [
                'powershell', '-File', str(activate_script_path),
                '-CommandToRun', command_to_run
            ]
        else:
            # Pour Linux/macOS
            command_to_run = ' '.join(playwright_cmd)
            cmd = ['conda', 'run', '-n', 'projet-is', 'bash', '-c', f'cd tests_playwright && {command_to_run}']

        return cmd
    
    async def _execute_tests(self, cmd: List[str],
                           config: Dict[str, Any]) -> subprocess.CompletedProcess:
        """Exécute les tests et capture la sortie"""
        self.logger.info(f"Commande test: {' '.join(cmd)}")
        
        # Le répertoire de travail pour playwright est "tests_playwright"
        cwd = Path.cwd() / 'tests_playwright'
        
        # Fichiers de log
        stdout_file = self.traces_dir / 'playwright_stdout.log'
        stderr_file = self.traces_dir / 'playwright_stderr.log'
        
        try:
            # Exécution avec capture depuis le bon répertoire
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=config.get('test_timeout', 300),  # 5 min par défaut
                cwd=cwd
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
        stats = self._extract_playwright_stats(stdout_lines)
        
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
    
    def _extract_playwright_stats(self, stdout_lines: List[str]) -> Dict[str, Any]:
        """Extrait les statistiques de la sortie de Playwright."""
        stats = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'timedOut': 0,
            'interrupted': 0,
            'duration': 0.0
        }
        import re

        # Regex pour trouver la ligne de résumé
        # Ex: "1 test passed (15.2s)" ou "2 tests failed (1 worker)"
        summary_re = re.compile(r"(\d+)\s+test[s]?\s+(passed|failed|skipped|timed out|interrupted)")
        duration_re = re.compile(r"\(([\d\.]+)s\)")

        for line in reversed(stdout_lines):
            duration_match = duration_re.search(line)
            if duration_match:
                try:
                    stats['duration'] = float(duration_match.group(1))
                except ValueError:
                    pass

            matches = summary_re.findall(line)
            if matches:
                for count, status in matches:
                    status_key = status.replace(' ', '')
                    if status_key == "timedout": status_key = "timedOut"
                    if status_key in stats:
                        stats[status_key] = int(count)
                
                stats['total'] = sum(v for k, v in stats.items() if k not in ['duration'])
                # Une fois qu'on a trouvé le résumé, on peut arrêter
                return stats
        
        # Fallback si le parsing ne trouve rien
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