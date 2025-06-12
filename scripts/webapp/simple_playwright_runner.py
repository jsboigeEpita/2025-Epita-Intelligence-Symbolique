#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Playwright Runner
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any

def setup_logging():
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] [%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    return logging.getLogger(__name__)

def build_playwright_command(test_paths: List[str], config: Dict[str, Any], logger: logging.Logger) -> List[str]:
    """Construit la commande npx playwright test."""
    playwright_cmd = ['npx', 'playwright', 'test']
    playwright_cmd.extend(test_paths)
    playwright_cmd.append(f"--browser={config['browser']}")
    if not config['headless']:
        playwright_cmd.append('--headed')
    playwright_cmd.append(f"--timeout={config['timeout_ms']}")

    logger.info(f"Playwright command args: {' '.join(playwright_cmd)}")

    if sys.platform == "win32":
        project_root = Path(__file__).resolve().parents[2]
        activate_script = project_root / 'scripts' / 'env' / 'activate_project_env.ps1'
        
        command_to_run = ' '.join(playwright_cmd)
        
        # Le script d'activation doit être appelé avec son chemin absolu pour la robustesse.
        # La commande est ensuite exécutée depuis le répertoire tests_playwright
        ps_command = [
            'powershell.exe',
            '-ExecutionPolicy', 'Bypass',
            '-File', str(activate_script),
            '-CommandToRun', f"cd tests_playwright; {command_to_run}"
        ]
        return ps_command
    else:
        # Simplifié pour Linux/macOS
        command_to_run = ' '.join(playwright_cmd)
        return ['conda', 'run', '-n', 'projet-is', 'bash', '-c', f'cd tests_playwright && {command_to_run}']

def run_tests(logger: logging.Logger):
    """Prépare et exécute les tests."""
    logger.info("Starting simple playwright runner")
    
    # Configuration
    test_paths = ['tests/investigation-textes-varies.spec.js']
    config = {
        'browser': 'chromium',
        'headless': False,
        'timeout_ms': '30000', # 30s
    }

    # Création de la commande
    cmd = build_playwright_command(test_paths, config, logger)
    logger.info(f"Final command to execute: {' '.join(cmd)}")
    
    # Répertoire de travail
    project_root = Path(__file__).resolve().parents[2]

    # Exécution
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=project_root, # On exécute depuis la racine du projet
            check=True
        )
        logger.info("Playwright execution successful.")
        logger.info("STDOUT:\n" + result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error("Playwright execution failed.")
        logger.error(f"Return code: {e.returncode}")
        logger.error("STDOUT:\n" + e.stdout)
        logger.error("STDERR:\n" + e.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    logger = setup_logging()
    
    # Avant de lancer les tests, assurons-nous que les services tournent.
    # Pour ce test simple, on va assumer que l'utilisateur les a lancés manuellement.
    logger.info("Please ensure a web server is running and accessible before tests.")
    logger.info("This script will only run the Playwright tests.")
    
    run_tests(logger)