# -*- coding: utf-8 -*-
"""
Script orchestrateur de démonstration pour le projet d'Intelligence Symbolique EPITA.

Ce script principal a pour but de lancer les différentes démonstrations du projet,
qui sont organisées en sous-scripts pour plus de clarté et de modularité.

Plan d'exécution :
1.  Vérification et installation des dépendances de base.
2.  Lancement du sous-script `demo_notable_features.py` pour les fonctionnalités de base.
3.  Lancement du sous-script `demo_advanced_features.py` pour les fonctionnalités complexes.
4.  Exécution de la suite de tests complète du projet via `pytest`.

Prérequis :
- Le script doit être exécuté depuis la racine du projet.

Exécution :
python examples/scripts_demonstration/demonstration_epita.py
"""
import logging
import sys
import os
import subprocess
import time
from pathlib import Path

def setup_environment():
    """Configure le logger et le chemin système pour l'exécution."""
    logger = logging.getLogger("demonstration_orchestrator")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # S'assurer que le répertoire de travail est la racine du projet
    os.chdir(project_root)
    
    logger.info(f"Environnement configuré. Racine du projet : {project_root}")
    return logger, project_root

def check_and_install_dependencies(logger: logging.Logger):
    """Vérifie et installe les dépendances Python de base si elles sont manquantes."""
    logger.info("\n--- Vérification des dépendances (seaborn, markdown) ---")
    dependencies = ["seaborn", "markdown"]
    for package_name in dependencies:
        try:
            __import__(package_name.replace("-", "_"))
            logger.info(f"Le package '{package_name}' est déjà installé.")
        except ImportError:
            logger.warning(f"Le package '{package_name}' n'est pas trouvé. Tentative d'installation...")
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", package_name], 
                    check=True, capture_output=True, text=True, timeout=300
                )
                logger.info(f"SUCCÈS: Le package '{package_name}' a été installé.")
            except Exception as e:
                logger.error(f"ERREUR: Échec de l'installation de '{package_name}': {e}")

def run_subprocess(script_name: str, logger: logging.Logger):
    """Exécute un sous-script Python et affiche sa sortie."""
    script_path = Path("examples/scripts_demonstration") / script_name
    logger.info(f"\n--- Lancement du sous-script : {script_name} ---")
    
    if not script_path.exists():
        logger.error(f"Le sous-script {script_path} n'a pas été trouvé.")
        return

    start_time = time.time()
    try:
        process = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            check=True, timeout=600  # 10 minutes
        )
        duration = time.time() - start_time
        logger.info(f"--- Sortie de {script_name} (durée: {duration:.2f}s) ---")
        for line in process.stdout.splitlines():
            logger.info(line)
        if process.stderr:
            logger.warning(f"--- Sortie d'erreur de {script_name} ---")
            for line in process.stderr.splitlines():
                logger.warning(line)
        logger.info(f"--- Fin du sous-script : {script_name} ---")

    except subprocess.CalledProcessError as e:
        duration = time.time() - start_time
        logger.error(f"Le sous-script {script_name} a échoué (code: {e.returncode}, durée: {duration:.2f}s).")
        logger.error(f"--- Sortie de {script_name} ---\n{e.stdout}")
        logger.error(f"--- Erreurs de {script_name} ---\n{e.stderr}")
    except subprocess.TimeoutExpired:
        logger.error(f"Le sous-script {script_name} a dépassé le timeout de 10 minutes.")
    except Exception as e:
        logger.error(f"Une erreur inattendue est survenue en lançant {script_name}: {e}", exc_info=True)

def run_project_tests(logger: logging.Logger):
    """Exécute la suite de tests du projet avec pytest."""
    logger.info("\n--- Lancement de la suite de tests du projet (pytest) ---")
    start_time = time.time()
    try:
        process = subprocess.run(
            [sys.executable, "-m", "pytest"],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=900  # 15 minutes
        )
        duration = time.time() - start_time
        logger.info(f"Tests exécutés en {duration:.2f} secondes.")
        
        logger.info("\n--- Sortie des tests ---")
        logger.info(process.stdout)
        if process.stderr:
            logger.error("\n--- Erreurs des tests ---")
            logger.error(process.stderr)
            
        if process.returncode == 0:
            logger.info("\nSUCCÈS : Tous les tests sont passés.")
        else:
            logger.warning(f"\nAVERTISSEMENT : Certains tests ont échoué (code: {process.returncode}).")

    except Exception as e:
        logger.error(f"Erreur lors de l'exécution des tests : {e}", exc_info=True)

if __name__ == "__main__":
    main_logger, project_root_path = setup_environment()
    main_logger.info("=== Début de l'orchestrateur de démonstration EPITA ===")
    
    # 1. Vérifier les dépendances
    check_and_install_dependencies(main_logger)
    
    # 2. Lancer les sous-scripts de démonstration
    run_subprocess("demo_notable_features.py", main_logger)
    run_subprocess("demo_advanced_features.py", main_logger)
    
    # 3. Lancer les tests du projet
    run_project_tests(main_logger)
    
    main_logger.info("\n=== Fin de l'orchestrateur de démonstration EPITA ===")