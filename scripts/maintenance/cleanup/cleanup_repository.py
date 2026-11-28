#!/usr/bin/env python3
"""
Script de nettoyage du dépôt.

Ce script crée un fichier .env.example comme modèle et supprime les dossiers vides
qui ne devraient pas être versionnés, tout en préservant les fichiers de configuration
existants.

La racine du projet est le plus proche ancêtre portant un `.git` (#3726) : la version
précédente la calculait par profondeur (`.parent.parent.parent`) et valait `scripts/`,
si bien que le modèle était écrit dans `scripts/argumentation_analysis/.env.example` —
un chemin ignoré par git — au lieu de celui du dépôt.

`--dry-run` affiche ce qui serait fait, sans rien écrire, supprimer ni désindexer.
"""

import argumentation_analysis.core.environment
import argparse
import os
import shutil
import subprocess
from pathlib import Path
import sys


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
    """Supprime les fichiers correspondant au pattern du suivi Git sans les supprimer du système.
    Utilise une approche simple compatible avec cmd.exe."""
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


def main(argv=None):
    """Fonction principale."""
    parser = argparse.ArgumentParser(
        description="Crée les modèles de configuration et retire les dossiers vides du suivi."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche ce qui serait fait, sans rien écrire, supprimer ni désindexer.",
    )
    args = parser.parse_args(argv)
    dry_run = args.dry_run

    # Afficher le répertoire de travail actuel pour le débogage
    current_dir = os.getcwd()
    print(f"Répertoire de travail actuel: {current_dir}")
    print(f"Racine du dépôt: {PROJECT_ROOT}")
    if dry_run:
        print("[dry-run] aucun fichier ne sera écrit, supprimé ni désindexé.")

    print("\n=== Nettoyage des fichiers du suivi Git ===")

    # Suppression des fichiers __pycache__ du suivi Git
    print("\nSuppression des dossiers __pycache__ du suivi Git...")
    remove_files_from_git_tracking("*/__pycache__", is_dir=True, dry_run=dry_run)

    # Suppression des fichiers .pyc du suivi Git
    print("\nSuppression des fichiers .pyc du suivi Git...")
    remove_files_from_git_tracking("*.pyc", dry_run=dry_run)

    # Suppression des fichiers .jar du suivi Git
    print("\nSuppression des fichiers .jar du suivi Git...")
    remove_files_from_git_tracking("*.jar", dry_run=dry_run)

    print("\n=== Gestion des fichiers de configuration ===")

    # Création d'un fichier .env.example comme modèle
    arg_analysis_path = PROJECT_ROOT / "argumentation_analysis"
    env_path = arg_analysis_path / ".env"
    env_example_path = arg_analysis_path / ".env.example"

    print(f"Vérification du fichier .env à: {env_path}")

    if env_path.exists():
        print("Fichier .env trouvé.")
        if not env_example_path.exists():
            print("Création du fichier exemple .env.example...")
            if _skip_in_dry_run("créerait le modèle", env_example_path, dry_run):
                pass
            else:
                try:
                    with open(
                        env_example_path, "w", encoding="utf-8", newline="\n"
                    ) as f:
                        f.write(
                            """# Exemple de configuration pour le projet d'analyse argumentative
# Copiez ce fichier vers .env et modifiez les valeurs selon votre configuration

# Service LLM à utiliser (OpenAI, Azure, etc.)
GLOBAL_LLM_SERVICE="OpenAI"

# Clé API pour OpenAI
OPENAI_API_KEY="votre-clé-api-openai"

# Modèle de chat OpenAI à utiliser
OPENAI_CHAT_MODEL_ID="gpt-5.6-luna"

# Phrase secrète pour le chiffrement des configurations
TEXT_CONFIG_PASSPHRASE="votre-phrase-secrète"
"""
                        )
                    print("Fichier .env.example créé avec succès.")
                except Exception as e:
                    print(f"Erreur lors de la création du fichier .env.example: {e}")
    else:
        print(f"Fichier .env non trouvé à {env_path}")

    print(f"Chemin vers argumentation_analysis: {arg_analysis_path}")

    # Suppression du dossier config vide
    config_path = arg_analysis_path / "config"
    print(f"Vérification du dossier config à: {config_path}")

    if config_path.exists():
        try:
            if not any(config_path.iterdir()):
                if _skip_in_dry_run(
                    "supprimerait le dossier vide", config_path, dry_run
                ):
                    pass
                else:
                    print(f"Suppression du dossier vide {config_path}...")
                    config_path.rmdir()
                    print("Dossier config supprimé avec succès.")
            else:
                print("Le dossier config n'est pas vide, conservation.")
        except Exception as e:
            print(f"Erreur lors de la suppression du dossier config: {e}")
    else:
        print(f"Dossier config non trouvé à {config_path}")

    # Vérification du fichier .env
    print(f"Vérification du fichier .env à: {env_path}")

    if env_path.exists():
        print("Fichier .env trouvé.")

        # Vérification que .env est bien ignoré par Git en utilisant git status
        rel_path = os.path.relpath(env_path, PROJECT_ROOT)
        check_command = f'git status --porcelain "{rel_path}"'
        check_success, check_output = run_git_command(check_command)

        if check_success:
            if check_output.strip() and not check_output.strip().startswith("??"):
                print("ATTENTION: Le fichier .env est suivi par Git!")
                print(
                    "Vérifiez que la règle '.env' est bien présente dans votre fichier .gitignore."
                )
            else:
                print("Le fichier .env est correctement ignoré par Git.")
        else:
            print("Impossible de vérifier si le fichier .env est ignoré par Git.")
    else:
        print(f"Fichier .env non trouvé à {env_path}")

    print("\nNettoyage terminé.")
    if dry_run:
        print("[dry-run] rien n'a été modifié.")
        return 0
    print(
        "\nNOTE: Le fichier .env contenant des informations sensibles est toujours présent."
    )
    print(
        "Pour une sécurité optimale, assurez-vous qu'il est correctement ignoré par Git."
    )
    print(
        "Vérifiez avec 'git status' que le fichier .env n'apparaît pas dans les fichiers à commiter."
    )
    print("\nPour finaliser le nettoyage, n'oubliez pas de commiter les changements:")
    print('git commit -m "Nettoyage des fichiers sensibles et temporaires du dépôt"')
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Erreur non gérée: {e}")
        sys.exit(1)
