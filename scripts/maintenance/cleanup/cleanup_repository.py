#!/usr/bin/env python3
"""
Script de nettoyage du dépôt.

Ce script crée un fichier .env.example comme modèle et supprime les dossiers vides
qui ne devraient pas être versionnés, tout en préservant les fichiers de configuration
existants.
"""

import argumentation_analysis.core.environment
import os
import shutil
import subprocess
from pathlib import Path
import sys


def run_git_command(command):
    """Exécute une commande git et retourne le résultat."""
    try:
        result = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Erreur: {e.stderr}"


def remove_files_from_git_tracking(pattern, is_dir=False):
    """Supprime les fichiers correspondant au pattern du suivi Git sans les supprimer du système.
    Utilise une approche simple compatible avec cmd.exe."""
    # Commande de base
    base_cmd = "git rm --cached"
    if is_dir:
        base_cmd += " -r"

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


def main():
    # Afficher le répertoire de travail actuel pour le débogage
    current_dir = os.getcwd()
    print(f"Répertoire de travail actuel: {current_dir}")

    # Chemin de base du projet (racine du projet)
    base_path = Path(__file__).resolve().parent.parent.parent

    print("\n=== Nettoyage des fichiers du suivi Git ===")

    # Suppression des fichiers __pycache__ du suivi Git
    print("\nSuppression des dossiers __pycache__ du suivi Git...")
    remove_files_from_git_tracking("*/__pycache__", is_dir=True)

    # Suppression des fichiers .pyc du suivi Git
    print("\nSuppression des fichiers .pyc du suivi Git...")
    remove_files_from_git_tracking("*.pyc")

    # Suppression des fichiers .jar du suivi Git
    print("\nSuppression des fichiers .jar du suivi Git...")
    remove_files_from_git_tracking("*.jar")

    print("\n=== Gestion des fichiers de configuration ===")

    # Création d'un fichier .env.example comme modèle
    env_path = base_path / "argumentiation_analysis" / ".env"
    env_example_path = base_path / "argumentiation_analysis" / ".env.example"

    print(f"Vérification du fichier .env à: {env_path}")

    if env_path.exists():
        print(f"Fichier .env trouvé.")
        if not env_example_path.exists():
            print(f"Création du fichier exemple .env.example...")
            try:
                with open(env_example_path, "w") as f:
                    f.write(
                        """# Exemple de configuration pour le projet d'analyse argumentative
# Copiez ce fichier vers .env et modifiez les valeurs selon votre configuration

# Service LLM à utiliser (OpenAI, Azure, etc.)
GLOBAL_LLM_SERVICE="OpenAI"

# Clé API pour OpenAI
OPENAI_API_KEY="votre-clé-api-openai"

# Modèle de chat OpenAI à utiliser
OPENAI_CHAT_MODEL_ID="gpt-5-mini"

# Phrase secrète pour le chiffrement des configurations
TEXT_CONFIG_PASSPHRASE="votre-phrase-secrète"
"""
                    )
                print(f"Fichier .env.example créé avec succès.")
            except Exception as e:
                print(f"Erreur lors de la création du fichier .env.example: {e}")
    else:
        print(f"Fichier .env non trouvé à {env_path}")

    # Chemin absolu vers le dossier argumentiation_analysis
    # Comme nous sommes déjà dans le répertoire de travail actuel, nous devons remonter
    # si nous sommes dans un sous-répertoire de argumentiation_analysis
    if "argumentiation_analysis" in str(base_path):
        # Si nous sommes dans un sous-répertoire de argumentiation_analysis
        parts = base_path.parts
        idx = parts.index("argumentiation_analysis")
        arg_analysis_path = Path(*parts[: idx + 1])
    else:
        # Si nous sommes à la racine du projet
        arg_analysis_path = base_path / "argumentiation_analysis"

    print(f"Chemin vers argumentiation_analysis: {arg_analysis_path}")

    # Suppression du dossier config vide
    config_path = arg_analysis_path / "config"
    print(f"Vérification du dossier config à: {config_path}")

    if config_path.exists():
        try:
            if not any(config_path.iterdir()):
                print(f"Suppression du dossier vide {config_path}...")
                config_path.rmdir()
                print(f"Dossier config supprimé avec succès.")
            else:
                print(f"Le dossier config n'est pas vide, conservation.")
        except Exception as e:
            print(f"Erreur lors de la suppression du dossier config: {e}")
    else:
        print(f"Dossier config non trouvé à {config_path}")

    # Vérification du fichier .env
    env_path = arg_analysis_path / ".env"
    print(f"Vérification du fichier .env à: {env_path}")

    if env_path.exists():
        print(f"Fichier .env trouvé.")

        # Vérification que .env est bien ignoré par Git en utilisant git status
        rel_path = os.path.relpath(env_path, base_path)
        check_command = f'git status --porcelain "{rel_path}"'
        check_success, check_output = run_git_command(check_command)

        if check_success:
            if check_output.strip() and not check_output.strip().startswith("??"):
                print(f"ATTENTION: Le fichier .env est suivi par Git!")
                print(
                    f"Vérifiez que la règle '.env' est bien présente dans votre fichier .gitignore."
                )
            else:
                print(f"Le fichier .env est correctement ignoré par Git.")
        else:
            print(f"Impossible de vérifier si le fichier .env est ignoré par Git.")
    else:
        print(f"Fichier .env non trouvé à {env_path}")

    print("\nNettoyage terminé.")
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


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Erreur non gérée: {e}")
        sys.exit(1)
