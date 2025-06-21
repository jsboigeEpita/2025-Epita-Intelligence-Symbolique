#!/usr/bin/env python3
"""
Script de nettoyage complet du projet d'analyse argumentative.

Ce script effectue les opérations suivantes :
1. Supprime les fichiers temporaires (*.pyc, __pycache__, etc.)
2. Supprime les fichiers de logs obsolètes
3. Crée le répertoire `data` s'il n'existe pas
4. Met à jour le fichier `.gitignore` pour ignorer les fichiers sensibles et temporaires
5. Supprime les fichiers de rapports obsolètes
import argumentation_analysis.core.environment
6. Vérifie que les fichiers sensibles ne sont pas suivis par Git
"""

import os
import sys
import shutil
import subprocess
import re
import glob
from pathlib import Path
from datetime import datetime, timedelta

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent # Racine du projet
ARGUMENTIATION_ANALYSIS_DIR = PROJECT_ROOT / "argumentation_analysis" # Chemin corrigé
DATA_DIR = ARGUMENTIATION_ANALYSIS_DIR / "data"
LOG_RETENTION_DAYS = 30  # Nombre de jours à conserver les logs


def run_git_command(command):
    """Exécute une commande git et retourne le résultat."""
    try:
        result = subprocess.run(command, shell=True, check=True,
                               capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Erreur: {e.stderr}"


def remove_files_from_git_tracking(pattern, is_dir=False):
    """Supprime les fichiers correspondant au pattern du suivi Git sans les supprimer du système."""
    # Commande de base
    base_cmd = "git rm --cached"
    if is_dir:
        base_cmd += " -r"
    
    # Exécute la commande (ignorera les erreurs si aucun fichier ne correspond)
    command = f'{base_cmd} {pattern}'
    try:
        result = subprocess.run(command, shell=True,
                               capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Fichiers correspondant à '{pattern}' supprimés du suivi Git.")
            return True
        else:
            # Si la commande échoue parce qu'aucun fichier ne correspond, ce n'est pas une erreur
            if "did not match any files" in result.stderr:
                print(f"Aucun fichier correspondant à '{pattern}' n'a été trouvé dans le suivi Git.")
                return True
            else:
                print(f"Échec de la suppression des fichiers '{pattern}' du suivi Git: {result.stderr}")
                return False
    except Exception as e:
        print(f"Erreur lors de l'exécution de la commande: {e}")
        return False


def delete_temp_files():
    """Supprime les fichiers temporaires Python."""
    print("\n=== Suppression des fichiers temporaires Python ===")
    
    # Supprimer les dossiers __pycache__
    pycache_dirs = list(PROJECT_ROOT.glob("**/__pycache__"))
    for pycache_dir in pycache_dirs:
        try:
            shutil.rmtree(pycache_dir)
            print(f"Supprimé: {pycache_dir}")
        except Exception as e:
            print(f"Erreur lors de la suppression de {pycache_dir}: {e}")
    
    # Supprimer les fichiers .pyc, .pyo, .pyd
    for ext in ["*.pyc", "*.pyo", "*.pyd"]:
        for pyc_file in PROJECT_ROOT.glob(f"**/{ext}"):
            try:
                pyc_file.unlink()
                print(f"Supprimé: {pyc_file}")
            except Exception as e:
                print(f"Erreur lors de la suppression de {pyc_file}: {e}")
    
    # Supprimer les fichiers temporaires de Jupyter Notebook
    for ipynb_checkpoint in PROJECT_ROOT.glob("**/.ipynb_checkpoints"):
        try:
            if ipynb_checkpoint.is_dir():
                shutil.rmtree(ipynb_checkpoint)
            else:
                ipynb_checkpoint.unlink()
            print(f"Supprimé: {ipynb_checkpoint}")
        except Exception as e:
            print(f"Erreur lors de la suppression de {ipynb_checkpoint}: {e}")
    
    # Supprimer les fichiers temporaires d'éditeur
    for temp_pattern in ["*.swp", "*.swo", "*~", "#*#"]:
        for temp_file in PROJECT_ROOT.glob(f"**/{temp_pattern}"):
            try:
                temp_file.unlink()
                print(f"Supprimé: {temp_file}")
            except Exception as e:
                print(f"Erreur lors de la suppression de {temp_file}: {e}")
    
    print("Suppression des fichiers temporaires terminée.")


def clean_old_logs():
    """Supprime les fichiers de logs obsolètes."""
    print("\n=== Suppression des fichiers de logs obsolètes ===")
    
    # Date limite pour conserver les logs
    cutoff_date = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    
    # Rechercher tous les fichiers de logs
    log_files = list(PROJECT_ROOT.glob("**/*.log"))
    log_dirs = [d for d in PROJECT_ROOT.glob("**/logs") if d.is_dir()]
    
    # Supprimer les fichiers de logs obsolètes
    deleted_count = 0
    for log_file in log_files:
        try:
            # Obtenir la date de dernière modification
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff_date:
                log_file.unlink()
                print(f"Supprimé log obsolète: {log_file}")
                deleted_count += 1
        except Exception as e:
            print(f"Erreur lors de la suppression de {log_file}: {e}")
    
    # Nettoyer les dossiers de logs vides
    for log_dir in log_dirs:
        try:
            if not any(log_dir.iterdir()):
                log_dir.rmdir()
                print(f"Supprimé dossier de logs vide: {log_dir}")
        except Exception as e:
            print(f"Erreur lors de la suppression du dossier {log_dir}: {e}")
    
    if deleted_count == 0:
        print(f"Aucun fichier de log obsolète (plus vieux que {LOG_RETENTION_DAYS} jours) trouvé.")
    else:
        print(f"{deleted_count} fichiers de logs obsolètes supprimés.")


def ensure_data_directory():
    """Crée le répertoire data s'il n'existe pas."""
    print("\n=== Vérification du répertoire data ===")
    
    try:
        DATA_DIR.mkdir(exist_ok=True)
        print(f"Répertoire data vérifié: {DATA_DIR}")
        
        # Créer un fichier .gitkeep pour conserver le dossier vide dans Git
        gitkeep_file = DATA_DIR / ".gitkeep"
        if not gitkeep_file.exists():
            gitkeep_file.touch()
            print(f"Fichier .gitkeep créé dans {DATA_DIR}")
        
        return True
    except Exception as e:
        print(f"Erreur lors de la création du répertoire data: {e}")
        return False


def update_gitignore():
    """Met à jour le fichier .gitignore pour ignorer les fichiers sensibles et temporaires."""
    print("\n=== Mise à jour du fichier .gitignore ===")
    
    gitignore_path = PROJECT_ROOT / ".gitignore"
    
    # Entrées à ajouter si elles ne sont pas déjà présentes
    entries_to_add = [
        "# Fichiers temporaires Python",
        "__pycache__/",
        "*.py[cod]",
        "*$py.class",
        "*.so",
        ".Python",
        
        "# Environnements virtuels",
        "venv/",
        ".venv/",
        "env/",
        "ENV/",
        
        "# Fichiers de configuration sensibles",
        ".env",
        "*.env",
        "**/.env",
        
        "# Fichiers de logs",
        "*.log",
        "logs/",
        
        "# Cache et téléchargements",
        "text_cache/",
        "temp_downloads/",
        
        "# Données",
        "data/",
        "!data/.gitkeep",
        "!data/extract_sources.json.gz.enc",
        
        "# Configuration UI non chiffrée",
        "data/extract_sources.json",
        
        "# Rapports de tests et couverture",
        ".pytest_cache/",
        "htmlcov/",
        ".coverage*",
        
        "# Dossiers de backups",
        "**/backups/",
        "!**/backups/__init__.py",
        
        "# Fichiers JAR",
        "*.jar",
        
        "# Fichiers temporaires Jupyter Notebook",
        ".ipynb_checkpoints/",
        
        "# Fichiers de configuration IDE / Editeur",
        ".vscode/",
        ".idea/",
        "*.sublime-project",
        "*.sublime-workspace",
        "*.swp",
        "*.swo",
        "*~",
        "#*#",
        
        "# Fichiers spécifiques OS",
        ".DS_Store",
        "Thumbs.db"
    ]
    
    # Lire le contenu actuel du .gitignore
    if gitignore_path.exists():
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            current_content = f.read()
    else:
        current_content = ""
    
    # Préparer le nouveau contenu
    new_entries = []
    for entry in entries_to_add:
        # Vérifier si l'entrée ou une entrée similaire existe déjà
        if entry.startswith("#"):
            # Pour les commentaires, on les ajoute toujours
            if entry not in current_content:
                new_entries.append(entry)
        else:
            # Pour les patterns, on vérifie s'ils existent déjà
            pattern = entry.strip()
            if pattern and not re.search(rf"^{re.escape(pattern)}$", current_content, re.MULTILINE):
                new_entries.append(entry)
    
    # Si des nouvelles entrées doivent être ajoutées
    if new_entries:
        with open(gitignore_path, 'a', encoding='utf-8') as f:
            f.write("\n# Ajouté par le script de nettoyage\n")
            for entry in new_entries:
                f.write(f"{entry}\n")
        print(f"Fichier .gitignore mis à jour avec {len(new_entries)} nouvelles entrées.")
    else:
        print("Fichier .gitignore déjà à jour, aucune modification nécessaire.")


def delete_obsolete_reports():
    """Supprime les fichiers de rapports obsolètes."""
    print("\n=== Suppression des fichiers de rapports obsolètes ===")
    
    # Liste des fichiers de rapports à supprimer
    obsolete_reports = [
        PROJECT_ROOT / "rapport_verification_structure.html",
        PROJECT_ROOT / "rapport_verification_finale.md"
    ]
    
    # Supprimer les fichiers
    deleted_count = 0
    for report_file in obsolete_reports:
        if report_file.exists():
            try:
                report_file.unlink()
                print(f"Supprimé rapport obsolète: {report_file}")
                deleted_count += 1
            except Exception as e:
                print(f"Erreur lors de la suppression de {report_file}: {e}")
    
    if deleted_count == 0:
        print("Aucun fichier de rapport obsolète trouvé.")
    else:
        print(f"{deleted_count} fichiers de rapports obsolètes supprimés.")


def check_sensitive_files():
    """Vérifie que les fichiers sensibles ne sont pas suivis par Git."""
    print("\n=== Vérification des fichiers sensibles ===")
    
    # Liste des patterns de fichiers sensibles
    sensitive_patterns = [
        ".env",
        "data/extract_sources.json"
    ]
    
    # Vérifier chaque pattern
    for pattern in sensitive_patterns:
        pattern_path = ARGUMENTIATION_ANALYSIS_DIR / pattern
        if pattern_path.exists():
            rel_path = os.path.relpath(pattern_path, PROJECT_ROOT)
            check_command = f'git status --porcelain "{rel_path}"'
            check_success, check_output = run_git_command(check_command)
            
            if check_success:
                if check_output.strip() and not check_output.strip().startswith("??"):
                    print(f"ATTENTION: Le fichier sensible {rel_path} est suivi par Git!")
                    print(f"Suppression du fichier {rel_path} du suivi Git...")
                    remove_files_from_git_tracking(rel_path)
                else:
                    print(f"Le fichier sensible {rel_path} est correctement ignoré par Git.")
            else:
                print(f"Impossible de vérifier si le fichier {rel_path} est ignoré par Git.")


def main():
    """Fonction principale."""
    print("=== Début du nettoyage du projet ===")
    print(f"Répertoire de travail actuel: {PROJECT_ROOT}")
    
    # 1. Supprimer les fichiers temporaires
    delete_temp_files()
    
    # 2. Nettoyer les logs obsolètes
    clean_old_logs()
    
    # 3. Assurer l'existence du répertoire data
    ensure_data_directory()
    
    # 4. Mettre à jour le .gitignore
    update_gitignore()
    
    # 5. Supprimer les rapports obsolètes
    delete_obsolete_reports()
    
    # 6. Vérifier les fichiers sensibles
    check_sensitive_files()
    
    print("\n=== Nettoyage du projet terminé ===")
    print("\nPour finaliser le nettoyage, n'oubliez pas de commiter les changements:")
    print("git add .")
    print("git commit -m \"Nettoyage des fichiers sensibles et temporaires du projet\"")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Erreur non gérée: {e}")
        sys.exit(1)