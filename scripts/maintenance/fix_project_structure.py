#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script principal pour résoudre les problèmes structurels du projet.

Ce script exécute toutes les étapes nécessaires pour résoudre les problèmes
structurels du projet, notamment :
1. Mise à jour des importations
2. Mise à jour des références aux chemins
3. Téléchargement des JARs de test
4. Vérification des importations
"""

import os
import sys
import subprocess
import logging
import argparse
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

def run_command(command, description):
    """
    Exécute une commande et affiche le résultat.
    
    Args:
        command (list): Commande à exécuter
        description (str): Description de la commande
    
    Returns:
        int: Code de retour de la commande
    """
    logging.info(f"\n=== {description} ===")
    logging.info(f"Commande: {' '.join(command)}")
    
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.stdout:
            for line in result.stdout.splitlines():
                logging.info(line)
        
        if result.stderr:
            for line in result.stderr.splitlines():
                logging.warning(line)
        
        if result.returncode == 0:
            logging.info(f"✅ {description} terminé avec succès.")
        else:
            logging.error(f"❌ {description} a échoué avec le code {result.returncode}.")
        
        return result.returncode
    
    except Exception as e:
        logging.error(f"❌ Erreur lors de l'exécution de la commande: {e}")
        return 1

def main():
    parser = argparse.ArgumentParser(description="Résout les problèmes structurels du projet")
    parser.add_argument('--dry-run', action='store_true', help="Ne pas effectuer les modifications")
    parser.add_argument('--skip-jars', action='store_true', help="Ne pas télécharger les JARs de test")
    parser.add_argument('--skip-imports', action='store_true', help="Ne pas mettre à jour les importations")
    parser.add_argument('--skip-paths', action='store_true', help="Ne pas mettre à jour les références aux chemins")
    parser.add_argument('--skip-tests', action='store_true', help="Ne pas exécuter les tests")
    args = parser.parse_args()
    
    # Déterminer le répertoire du script
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    
    # Créer les répertoires nécessaires
    logging.info("\n=== Création des répertoires nécessaires ===")
    directories = [
        project_dir / "argumentiation_analysis" / "libs",
        project_dir / "argumentiation_analysis" / "libs" / "native",
        project_dir / "argumentiation_analysis" / "tests" / "resources" / "libs",
        project_dir / "argumentiation_analysis" / "tests" / "resources" / "libs" / "native",
    ]
    
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            logging.info(f"Répertoire créé ou existant: {directory}")
        except Exception as e:
            logging.error(f"Erreur lors de la création du répertoire {directory}: {e}")
    
    # Créer les fichiers .gitkeep
    logging.info("\n=== Création des fichiers .gitkeep ===")
    gitkeep_files = [
        project_dir / "argumentiation_analysis" / "libs" / ".gitkeep",
        project_dir / "argumentiation_analysis" / "libs" / "native" / ".gitkeep",
        project_dir / "argumentiation_analysis" / "tests" / "resources" / "libs" / ".gitkeep",
        project_dir / "argumentiation_analysis" / "tests" / "resources" / "libs" / "native" / ".gitkeep",
    ]
    
    for gitkeep_file in gitkeep_files:
        try:
            gitkeep_file.touch()
            logging.info(f"Fichier créé ou existant: {gitkeep_file}")
        except Exception as e:
            logging.error(f"Erreur lors de la création du fichier {gitkeep_file}: {e}")
    
    # Installer le package en mode développement
    logging.info("\n=== Installation du package en mode développement ===")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], check=True)
        logging.info("✅ Package installé en mode développement.")
    except Exception as e:
        logging.error(f"❌ Erreur lors de l'installation du package: {e}")
    
    # Mettre à jour les importations
    if not args.skip_imports:
        update_imports_cmd = [sys.executable, str(script_dir / "update_imports.py")]
        if not args.dry_run:
            run_command(update_imports_cmd, "Mise à jour des importations")
        else:
            run_command(update_imports_cmd + ["--dry-run"], "Analyse des importations (dry-run)")
    
    # Mettre à jour les références aux chemins
    if not args.skip_paths:
        update_paths_cmd = [sys.executable, str(script_dir / "update_paths.py")]
        if not args.dry_run:
            run_command(update_paths_cmd, "Mise à jour des références aux chemins")
        else:
            run_command(update_paths_cmd + ["--dry-run"], "Analyse des références aux chemins (dry-run)")
    
    # Télécharger les JARs de test
    if not args.skip_jars:
        download_jars_cmd = [sys.executable, str(script_dir / "download_test_jars.py")]
        if args.dry_run:
            logging.info("\n=== Téléchargement des JARs de test (simulation) ===")
            logging.info("En mode dry-run, les JARs ne sont pas téléchargés.")
        else:
            run_command(download_jars_cmd, "Téléchargement des JARs de test")
    
    # Vérifier les importations
    if not args.skip_tests:
        test_imports_cmd = [sys.executable, str(script_dir / "utils/test_imports_utils.py")]
        run_command(test_imports_cmd, "Vérification des importations")
    
    logging.info("\n=== Résumé ===")
    if args.dry_run:
        logging.info("Mode dry-run: aucune modification n'a été effectuée.")
        logging.info("Exécutez à nouveau sans l'option --dry-run pour appliquer les modifications.")
    else:
        logging.info("Toutes les étapes ont été exécutées.")
        logging.info("Pour tester les modifications, exécutez les tests unitaires:")
        logging.info("  cd argumentiation_analysis/tests")
        logging.info("  python run_tests.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())