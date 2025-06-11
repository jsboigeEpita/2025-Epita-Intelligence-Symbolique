#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright JavaScript Runner - Runner asynchrone pour tests Playwright JavaScript
=================================================================================

Runner non-bloquant pour exécuter les tests Playwright JavaScript (.spec.js)
en mode headed/headless avec capture screenshots et traces.

Auteur: Intelligence Symbolique EPITA
Date: 11/06/2025
"""

import os
import sys
import asyncio
import logging
import subprocess
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import tempfile

class PlaywrightJSRunner:
    """
    Runner asynchrone pour tests Playwright JavaScript
    
    Fonctionnalités :
    - Exécution tests .spec.js via npx playwright test
    - Mode headed/headless configurable
    - Exécution non-bloquante avec timeout
    - Capture screenshots, vidéos et traces
    - Rapports de résultats détaillés
    """
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        
        # Configuration Playwright
        self.enabled = config.get('enabled', True)
        self.browser = config.get('browser', 'chromium')
        self.headless = config.get('headless', False)
        self.timeout_ms = config.get('timeout_ms', 30000)
        self.slow_timeout_ms = config.get('slow_timeout_ms', 60000)
        self.base_url = config.get('base_url', 'http://localhost:3000')
        self.screenshots_dir = Path(config.get('screenshots_dir', 'logs/screenshots'))
        self.traces_dir = Path(config.get('traces_dir', 'logs/traces'))
        self.test_timeout = config.get('test_timeout', 600)  # 10 minutes
        
        # Création répertoires
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        
        # Variables runtime
        self.last_results: Optional[Dict[str, Any]] = None
        
    async def run_tests(self, test_paths: List[str] = None, 
                       runtime_config: Dict[str, Any] = None) -> bool:
        """
        Exécute les tests Playwright JavaScript de façon asynchrone
        
        Args:
            test_paths: Chemins des tests .spec.js
            runtime_config: Configuration dynamique
            
        Returns:
            bool: True si tous les tests passent
        """
        if not self.enabled:
            self.logger.info("Tests Playwright JavaScript désactivés")
            return True
        
        # Configuration effective
        effective_config = self._merge_runtime_config(runtime_config or {})
        test_paths = test_paths or ['tests/jtms-interface.spec.js']
        
        self.logger.info(f"Démarrage tests Playwright JS: {test_paths}")
        self.logger.info(f"Configuration: {effective_config}")
        
        try:
            # Préparation environnement
            await self._prepare_test_environment(effective_config)
            
            # Construction commande npx playwright
            cmd = self._build_playwright_command(test_paths, effective_config)
            
            # Exécution tests non-bloquante
            result = await self._execute_tests_async(cmd, effective_config)
            
            # Analyse résultats
            success = await self._analyze_results(result)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erreur exécution tests Playwright JS: {e}", exc_info=True) # Ajout de exc_info
            return False
    
    def _merge_runtime_config(self, runtime_config: Dict[str, Any]) -> Dict[str, Any]:
        """Fusionne configuration par défaut avec runtime"""
        effective_config = {
            'base_url': self.base_url,
            'headless': self.headless,
            'browser': self.browser,
            'timeout_ms': self.timeout_ms,
            'slow_timeout_ms': self.slow_timeout_ms,
            'screenshots': True,
            'traces': True,
            'videos': True
        }
        
        # Override avec runtime
        effective_config.update(runtime_config)
        
        return effective_config
    
    async def _prepare_test_environment(self, config: Dict[str, Any]):
        """Prépare l'environnement pour les tests"""
        # Variables d'environnement pour Playwright
        env_vars = {
            'BASE_URL': config['base_url'],
            'HEADLESS': 'false' if not config['headless'] else 'true',
            'BROWSER': config['browser'],
            'TIMEOUT': str(config['timeout_ms']),
            'SLOW_TIMEOUT': str(config['slow_timeout_ms'])
        }
        
        self.logger.info(f"Variables test configurées: {env_vars}")
        
        # Application variables
        for key, value in env_vars.items():
            os.environ[key] = str(value)
    
    def _build_playwright_command(self, test_paths: List[str],
                                 config: Dict[str, Any]) -> List[str]:
        """Construit la commande npx playwright test"""
        
        # Commande de base compatible Windows
        if sys.platform == "win32":
            cmd = ['npx.cmd', 'playwright', 'test']
        else:
            cmd = ['npx', 'playwright', 'test']
        
        # Fichiers de test
        cmd.extend(test_paths)
        
        # Options Playwright
        if not config['headless']:
            cmd.append('--headed')
            
        # Navigateur spécifique
        cmd.extend(['--project', config['browser']])
        
        # Timeout
        cmd.extend(['--timeout', str(config['timeout_ms'])])
        
        # Captures
        if config.get('screenshots', True):
            # cmd.append('--screenshot=only-on-failure') # Correction ici
            pass
        if config.get('traces', True):
            cmd.append('--trace=on-first-retry')
            
        if config.get('videos', True):
            # cmd.append('--video=retain-on-failure')
            pass
        
        # Mode verbose
        cmd.append('--reporter=line')
        
        return cmd
    
    async def _execute_tests_async(self, cmd: List[str], 
                                  config: Dict[str, Any]) -> subprocess.CompletedProcess:
        """Exécute les tests de façon asynchrone avec timeout"""
        self.logger.info(f"Commande Playwright: {' '.join(cmd)}")
        
        # Répertoire de travail
        cwd = Path.cwd() / 'tests_playwright'
        
        # Fichiers de log
        stdout_file = self.traces_dir / 'playwright_stdout.log'
        stderr_file = self.traces_dir / 'playwright_stderr.log'
        
        try:
            # Utiliser asyncio.to_thread pour exécuter subprocess.run de manière non bloquante
            def run_sync_process():
                return subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=self.test_timeout, # subprocess.run a son propre timeout
                    cwd=cwd,
                    shell=False # Important pour la sécurité et la gestion des arguments
                )

            # Exécuter la fonction bloquante dans un thread séparé
            completed_process = await asyncio.to_thread(run_sync_process)
            
            # DEBUG: Afficher la sortie brute pour analyse
            self.logger.info("--- DEBUT SORTIE BRUTE PLAYWRIGHT ---")
            self.logger.info("--- STDOUT ---")
            self.logger.info(completed_process.stdout)
            self.logger.info("--- STDERR ---")
            self.logger.info(completed_process.stderr)
            self.logger.info("--- FIN SORTIE BRUTE PLAYWRIGHT ---")

            stdout_text = completed_process.stdout
            stderr_text = completed_process.stderr
            return_code = completed_process.returncode

            # Sauvegarde logs
            with open(stdout_file, 'w', encoding='utf-8') as f:
                f.write(stdout_text)
            with open(stderr_file, 'w', encoding='utf-8') as f:
                f.write(stderr_text)
            
            self.logger.info(f"Tests terminés - Code retour: {return_code}")
            
            # Pas besoin de simuler AsyncResult, subprocess.run retourne un CompletedProcess
            return completed_process
            
        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Timeout tests après {self.test_timeout}s: {e}")
            # Sauvegarder ce qui a été capturé avant le timeout
            if e.stdout:
                with open(stdout_file, 'w', encoding='utf-8') as f:
                    f.write(e.stdout)
            if e.stderr:
                with open(stderr_file, 'w', encoding='utf-8') as f:
                    f.write(e.stderr)
            # Créer un objet résultat pour l'analyse, marquant l'échec dû au timeout
            class TimeoutResult:
                def __init__(self):
                    self.returncode = -1 # Code spécifique pour timeout
                    self.stdout = e.stdout if e.stdout else ""
                    self.stderr = e.stderr if e.stderr else "TimeoutExpired"
            return TimeoutResult()
        except Exception as e:
            self.logger.error(f"Erreur exécution tests: {e}", exc_info=True)
            # Créer un objet résultat pour l'analyse en cas d'autre exception
            class ErrorResult:
                def __init__(self):
                    self.returncode = -2 # Code spécifique pour autre erreur
                    self.stdout = ""
                    self.stderr = str(e)
            return ErrorResult()
    
    async def _analyze_results(self, result) -> bool:
        """Analyse les résultats de test et génère rapport"""
        success = result.returncode == 0
        
        # Parsing sortie Playwright
        stdout_lines = result.stdout.split('\n') if result.stdout else []
        stderr_lines = result.stderr.split('\n') if result.stderr else []
        
        # Extraction statistiques basiques
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for line in stdout_lines:
            if 'passed' in line and 'failed' in line:
                # Format: "X passed, Y failed"
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'passed' and i > 0:
                            passed_tests = int(parts[i-1])
                        elif part == 'failed' and i > 0:
                            failed_tests = int(parts[i-1])
                    total_tests = passed_tests + failed_tests
                except:
                    pass
            elif 'passed' in line and 'failed' not in line:
                # Format: "X passed"
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'passed' and i > 0:
                            passed_tests = int(parts[i-1])
                            total_tests = passed_tests
                except:
                    pass
        
        # Stockage résultats
        self.last_results = {
            'success': success,
            'return_code': result.returncode,
            'stats': {
                'total': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'skipped': 0,
                'errors': 0,
                'duration': 0.0
            },
            'stdout_lines': len(stdout_lines),
            'stderr_lines': len(stderr_lines),
            'artifacts': {
                'screenshots': [],
                'traces': [],
                'videos': []
            }
        }
        
        # Recherche artefacts générés
        await self._collect_artifacts()
        
        # Sauvegarde rapport
        report_file = self.traces_dir / 'test_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.last_results, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Tests réussis: {self.last_results['stats']}")
        self.logger.info(f"Rapport test sauvé: {report_file}")
        
        return success
    
    async def _collect_artifacts(self):
        """Collecte les artefacts générés par Playwright"""
        try:
            # Screenshots
            screenshots_path = Path('tests_playwright/test-results')
            if screenshots_path.exists():
                screenshots = list(screenshots_path.rglob('*.png'))
                self.last_results['artifacts']['screenshots'] = [str(p) for p in screenshots]
            
            # Traces
            traces = list(screenshots_path.rglob('*.zip')) if screenshots_path.exists() else []
            self.last_results['artifacts']['traces'] = [str(p) for p in traces]
            
            # Vidéos
            videos = list(screenshots_path.rglob('*.webm')) if screenshots_path.exists() else []
            self.last_results['artifacts']['videos'] = [str(p) for p in videos]
            
        except Exception as e:
            self.logger.warning(f"Erreur collecte artefacts: {e}")

# Factory function pour compatibilité
def create_playwright_js_runner(config: Dict[str, Any], logger: logging.Logger) -> PlaywrightJSRunner:
    """Factory function pour créer le runner Playwright JS"""
    return PlaywrightJSRunner(config, logger)