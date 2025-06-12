#!/usr/bin/env python3
"""
Script pour préparer un commit avec les modifications effectuées.

Ce script vérifie l'état actuel du dépôt Git, ajoute les nouveaux fichiers et répertoires,
et prépare un message de commit descriptif.
"""

import project_core.core_from_scripts.auto_env
import os
import subprocess
import sys

def run_command(command):
    """Exécute une commande shell et retourne le résultat."""
    try:
        result = subprocess.run(command, shell=True, check=True,
                               capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Erreur: {e.stderr}"

def check_git_status():
    """Vérifie l'état actuel du dépôt Git."""
    print("Vérification de l'état du dépôt Git...")
    success, output = run_command("git status")
    if success:
        print(output)
        return True
    else:
        print(output)
        return False

def add_new_files():
    """Ajoute les nouveaux fichiers et répertoires au suivi Git."""
    print("\nAjout des nouveaux fichiers et répertoires...")
    
    # Liste des répertoires à ajouter
    directories = [
        "scripts/cleanup",
        "scripts/execution",
        "scripts/validation",
        "docs",
        "examples"
    ]
    
    # Liste des fichiers à ajouter
    files = [
        "reorganize_project.py",
        "prepare_commit.py",
        "README_updated.md"
    ]
    
    # Ajouter les répertoires
    for directory in directories:
        success, output = run_command(f"git add {directory}")
        if success:
            print(f"✓ Répertoire ajouté: {directory}")
        else:
            print(f"✗ Erreur lors de l'ajout du répertoire {directory}: {output}")
    
    # Ajouter les fichiers
    for file in files:
        success, output = run_command(f"git add {file}")
        if success:
            print(f"✓ Fichier ajouté: {file}")
        else:
            print(f"✗ Erreur lors de l'ajout du fichier {file}: {output}")
    
    return True

def prepare_commit_message():
    """Prépare un message de commit descriptif."""
    commit_message = """Réorganisation du projet et nettoyage des fichiers à la racine

Cette réorganisation vise à améliorer la structure du projet en:
1. Créant un répertoire 'scripts/' pour tous les scripts utilitaires
   - scripts/cleanup/ : Scripts de nettoyage du projet
   - scripts/execution/ : Scripts d'exécution des fonctionnalités principales
   - scripts/validation/ : Scripts de validation des fichiers Markdown
2. Créant un répertoire 'docs/' pour la documentation supplémentaire
3. Créant un répertoire 'examples/' pour les exemples de textes et données
4. Ajoutant des README.md détaillés dans chaque répertoire
5. Mettant à jour le README.md principal pour refléter la nouvelle structure

Cette organisation permet de:
- Réduire l'encombrement à la racine du projet
- Améliorer la lisibilité et la maintenabilité du code
- Faciliter la navigation dans le projet
- Clarifier la documentation
"""
    
    print("\nMessage de commit préparé:")
    print("-" * 50)
    print(commit_message)
    print("-" * 50)
    
    # Écrire le message dans un fichier temporaire
    with open("commit_message.txt", "w", encoding="utf-8") as f:
        f.write(commit_message)
    
    print("\nLe message de commit a été enregistré dans 'commit_message.txt'")
    print("Pour committer les changements, exécutez:")
    print("git commit -F commit_message.txt")
    
    return True

def main():
    """Fonction principale."""
    print("=== Préparation du commit ===\n")
    
    # Vérifier l'état du dépôt Git
    if not check_git_status():
        print("Erreur lors de la vérification de l'état du dépôt Git.")
        return 1
    
    # Ajouter les nouveaux fichiers
    if not add_new_files():
        print("Erreur lors de l'ajout des nouveaux fichiers.")
        return 1
    
    # Préparer le message de commit
    if not prepare_commit_message():
        print("Erreur lors de la préparation du message de commit.")
        return 1
    
    print("\n=== Préparation du commit terminée ===")
    print("\nPour finaliser le commit, exécutez:")
    print("git commit -F commit_message.txt")
    print("\nPour annuler les modifications, exécutez:")
    print("git reset")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())