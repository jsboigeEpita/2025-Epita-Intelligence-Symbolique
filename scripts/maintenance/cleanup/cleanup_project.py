#!/usr/bin/env python3
"""
Script de nettoyage complet du projet d'analyse argumentative.

Ce script effectue les opérations suivantes :
1. Supprime les fichiers temporaires (*.pyc, __pycache__, etc.)
2. Supprime les fichiers de logs obsolètes
3. Crée le répertoire `data` s'il n'existe pas
4. Met à jour le fichier `.gitignore` du dépôt pour ignorer les fichiers sensibles et temporaires
5. Supprime les fichiers de rapports obsolètes
6. Vérifie que les fichiers sensibles ne sont pas suivis par Git

La racine du projet est le plus proche ancêtre portant un `.git` (#3726) : la version
précédente la calculait par profondeur (`.parent.parent.parent`) et valait `scripts/`,
si bien que le `.gitignore` complété était `scripts/.gitignore` — un fichier que git ne
suit pas — et non celui du dépôt.

`--dry-run` affiche ce qui serait supprimé ou ajouté sans rien écrire ni supprimer.
`--gitignore PATH` vise un autre `.gitignore` (relatif à la racine du dépôt, ou absolu).
"""

import argparse
import os
import sys
import shutil
import subprocess
import re
from pathlib import Path
from datetime import datetime, timedelta


class ProjectRootNotFound(RuntimeError):
    """Aucun ancêtre de ce fichier ne porte de `.git` : le dépôt est introuvable."""


def find_project_root(start: Path | None = None) -> Path:
    """Racine du dépôt : le plus proche ancêtre portant une entrée `.git`.

    `.exists()` et non `.is_dir()` : dans un worktree, `.git` est un fichier.
    Refuser bruyamment vaut mieux que retomber sur un répertoire faux — c'est
    précisément le défaut que #3726 répare.
    """
    origin = (start or Path(__file__)).resolve()
    for candidate in (origin, *origin.parents):
        if (candidate / ".git").exists():
            return candidate
    raise ProjectRootNotFound(f"aucun .git au-dessus de {origin}")


try:
    PROJECT_ROOT = find_project_root()
except ProjectRootNotFound as exc:  # script autonome : on sort proprement, code 2
    print(f"Erreur: racine du dépôt introuvable ({exc}).")
    raise SystemExit(2)

# Configuration
ARGUMENTIATION_ANALYSIS_DIR = PROJECT_ROOT / "argumentation_analysis"
DATA_DIR = ARGUMENTIATION_ANALYSIS_DIR / "data"
LOG_RETENTION_DAYS = 30  # Nombre de jours à conserver les logs


def _skip_in_dry_run(action: str, path: Path, dry_run: bool) -> bool:
    """En dry-run, annonce la mutation et dit à l'appelant de la sauter."""
    if dry_run:
        print(f"[dry-run] {action}: {path}")
        return True
    return False


def run_git_command(command):
    """Exécute une commande git et retourne le résultat."""
    try:
        result = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Erreur: {e.stderr}"


def remove_files_from_git_tracking(pattern, is_dir=False, dry_run=False):
    """Supprime les fichiers correspondant au pattern du suivi Git sans les supprimer du système."""
    # Commande de base
    base_cmd = "git rm --cached"
    if is_dir:
        base_cmd += " -r"

    if dry_run:
        print(f"[dry-run] {base_cmd} {pattern}")
        return True

    # Exécute la commande (ignorera les erreurs si aucun fichier ne correspond)
    command = f"{base_cmd} {pattern}"
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Fichiers correspondant à '{pattern}' supprimés du suivi Git.")
            return True
        else:
            # Si la commande échoue parce qu'aucun fichier ne correspond, ce n'est pas une erreur
            if "did not match any files" in result.stderr:
                print(
                    f"Aucun fichier correspondant à '{pattern}' n'a été trouvé dans le suivi Git."
                )
                return True
            else:
                print(
                    f"Échec de la suppression des fichiers '{pattern}' du suivi Git: {result.stderr}"
                )
                return False
    except Exception as e:
        print(f"Erreur lors de l'exécution de la commande: {e}")
        return False


def delete_temp_files(dry_run=False):
    """Supprime les fichiers temporaires Python."""
    print("\n=== Suppression des fichiers temporaires Python ===")

    # Supprimer les dossiers __pycache__
    pycache_dirs = list(PROJECT_ROOT.glob("**/__pycache__"))
    for pycache_dir in pycache_dirs:
        if _skip_in_dry_run("supprimerait le dossier", pycache_dir, dry_run):
            continue
        try:
            shutil.rmtree(pycache_dir)
            print(f"Supprimé: {pycache_dir}")
        except Exception as e:
            print(f"Erreur lors de la suppression de {pycache_dir}: {e}")

    # Supprimer les fichiers .pyc, .pyo, .pyd
    for ext in ["*.pyc", "*.pyo", "*.pyd"]:
        for pyc_file in PROJECT_ROOT.glob(f"**/{ext}"):
            if _skip_in_dry_run("supprimerait le fichier", pyc_file, dry_run):
                continue
            try:
                pyc_file.unlink()
                print(f"Supprimé: {pyc_file}")
            except Exception as e:
                print(f"Erreur lors de la suppression de {pyc_file}: {e}")

    # Supprimer les fichiers temporaires de Jupyter Notebook
    for ipynb_checkpoint in PROJECT_ROOT.glob("**/.ipynb_checkpoints"):
        if _skip_in_dry_run("supprimerait", ipynb_checkpoint, dry_run):
            continue
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
            if _skip_in_dry_run("supprimerait le fichier", temp_file, dry_run):
                continue
            try:
                temp_file.unlink()
                print(f"Supprimé: {temp_file}")
            except Exception as e:
                print(f"Erreur lors de la suppression de {temp_file}: {e}")

    print("Suppression des fichiers temporaires terminée.")


def clean_old_logs(dry_run=False):
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
                if _skip_in_dry_run("supprimerait le log obsolète", log_file, dry_run):
                    deleted_count += 1
                    continue
                log_file.unlink()
                print(f"Supprimé log obsolète: {log_file}")
                deleted_count += 1
        except Exception as e:
            print(f"Erreur lors de la suppression de {log_file}: {e}")

    # Nettoyer les dossiers de logs vides
    for log_dir in log_dirs:
        try:
            if not any(log_dir.iterdir()):
                if _skip_in_dry_run("supprimerait le dossier vide", log_dir, dry_run):
                    continue
                log_dir.rmdir()
                print(f"Supprimé dossier de logs vide: {log_dir}")
        except Exception as e:
            print(f"Erreur lors de la suppression du dossier {log_dir}: {e}")

    if deleted_count == 0:
        print(
            f"Aucun fichier de log obsolète (plus vieux que {LOG_RETENTION_DAYS} jours) trouvé."
        )
    else:
        print(f"{deleted_count} fichiers de logs obsolètes supprimés.")


def ensure_data_directory(dry_run=False):
    """Crée le répertoire data s'il n'existe pas."""
    print("\n=== Vérification du répertoire data ===")

    try:
        if _skip_in_dry_run("créerait le répertoire", DATA_DIR, dry_run):
            pass
        else:
            DATA_DIR.mkdir(exist_ok=True)
        print(f"Répertoire data vérifié: {DATA_DIR}")

        # Créer un fichier .gitkeep pour conserver le dossier vide dans Git
        gitkeep_file = DATA_DIR / ".gitkeep"
        if not gitkeep_file.exists():
            if _skip_in_dry_run("créerait le fichier", gitkeep_file, dry_run):
                return True
            gitkeep_file.touch()
            print(f"Fichier .gitkeep créé dans {DATA_DIR}")

        return True
    except Exception as e:
        print(f"Erreur lors de la création du répertoire data: {e}")
        return False


def update_gitignore(gitignore_path=None, dry_run=False):
    """Met à jour le fichier .gitignore pour ignorer les fichiers sensibles et temporaires."""
    print("\n=== Mise à jour du fichier .gitignore ===")

    if gitignore_path is None:
        target = PROJECT_ROOT / ".gitignore"
    else:
        target = Path(gitignore_path)
        if not target.is_absolute():
            target = PROJECT_ROOT / target

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
        "Thumbs.db",
    ]

    # Lire le contenu actuel du .gitignore
    if target.exists():
        with open(target, "r", encoding="utf-8") as f:
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
            if pattern and not re.search(
                rf"^{re.escape(pattern)}$", current_content, re.MULTILINE
            ):
                new_entries.append(entry)

    # Si des nouvelles entrées doivent être ajoutées
    if new_entries:
        if _skip_in_dry_run(
            f"ajouterait {len(new_entries)} entrées à", target, dry_run
        ):
            for entry in new_entries:
                print(f"[dry-run]   {entry}")
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "a", encoding="utf-8", newline="\n") as f:
            f.write("\n# Ajouté par le script de nettoyage\n")
            for entry in new_entries:
                f.write(f"{entry}\n")
        print(
            f"Fichier .gitignore mis à jour avec {len(new_entries)} nouvelles entrées."
        )
    else:
        print("Fichier .gitignore déjà à jour, aucune modification nécessaire.")


def delete_obsolete_reports(dry_run=False):
    """Supprime les fichiers de rapports obsolètes."""
    print("\n=== Suppression des fichiers de rapports obsolètes ===")

    # Liste des fichiers de rapports à supprimer
    obsolete_reports = [
        PROJECT_ROOT / "rapport_verification_structure.html",
        PROJECT_ROOT / "rapport_verification_finale.md",
    ]

    # Supprimer les fichiers
    deleted_count = 0
    for report_file in obsolete_reports:
        if report_file.exists():
            if _skip_in_dry_run(
                "supprimerait le rapport obsolète", report_file, dry_run
            ):
                deleted_count += 1
                continue
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


def check_sensitive_files(dry_run=False):
    """Vérifie que les fichiers sensibles ne sont pas suivis par Git."""
    print("\n=== Vérification des fichiers sensibles ===")

    # Liste des patterns de fichiers sensibles
    sensitive_patterns = [".env", "data/extract_sources.json"]

    # Vérifier chaque pattern
    for pattern in sensitive_patterns:
        pattern_path = ARGUMENTIATION_ANALYSIS_DIR / pattern
        if pattern_path.exists():
            rel_path = os.path.relpath(pattern_path, PROJECT_ROOT)
            check_command = f'git status --porcelain "{rel_path}"'
            check_success, check_output = run_git_command(check_command)

            if check_success:
                if check_output.strip() and not check_output.strip().startswith("??"):
                    print(
                        f"ATTENTION: Le fichier sensible {rel_path} est suivi par Git!"
                    )
                    print(f"Suppression du fichier {rel_path} du suivi Git...")
                    remove_files_from_git_tracking(rel_path, dry_run=dry_run)
                else:
                    print(
                        f"Le fichier sensible {rel_path} est correctement ignoré par Git."
                    )
            else:
                print(
                    f"Impossible de vérifier si le fichier {rel_path} est ignoré par Git."
                )


def main(argv=None):
    """Fonction principale."""
    parser = argparse.ArgumentParser(
        description="Nettoie le dépôt : fichiers temporaires, logs, .gitignore, rapports."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche ce qui serait fait, sans rien écrire ni supprimer.",
    )
    parser.add_argument(
        "--gitignore",
        type=Path,
        default=None,
        help="Cible du .gitignore à compléter (relatif à la racine du dépôt, ou absolu).",
    )
    args = parser.parse_args(argv)

    print("=== Début du nettoyage du projet ===")
    print(f"Racine du dépôt: {PROJECT_ROOT}")
    if args.dry_run:
        print("[dry-run] aucun fichier ne sera écrit ni supprimé.")

    # 1. Supprimer les fichiers temporaires
    delete_temp_files(dry_run=args.dry_run)

    # 2. Nettoyer les logs obsolètes
    clean_old_logs(dry_run=args.dry_run)

    # 3. Assurer l'existence du répertoire data
    ensure_data_directory(dry_run=args.dry_run)

    # 4. Mettre à jour le .gitignore
    update_gitignore(gitignore_path=args.gitignore, dry_run=args.dry_run)

    # 5. Supprimer les rapports obsolètes
    delete_obsolete_reports(dry_run=args.dry_run)

    # 6. Vérifier les fichiers sensibles
    check_sensitive_files(dry_run=args.dry_run)

    print("\n=== Nettoyage du projet terminé ===")
    if args.dry_run:
        print("[dry-run] rien n'a été modifié.")
        return 0
    print("\nPour finaliser le nettoyage, n'oubliez pas de commiter les changements:")
    print("git add .")
    print('git commit -m "Nettoyage des fichiers sensibles et temporaires du projet"')
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Erreur non gérée: {e}")
        sys.exit(1)
