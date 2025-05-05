#!/usr/bin/env python3
"""
Script de réorganisation du projet d'analyse argumentative.

Ce script crée une structure de répertoires plus propre et y déplace les fichiers
appropriés depuis la racine du projet.
"""

import os
import shutil
from pathlib import Path

# Définition des répertoires à créer
DIRECTORIES = {
    "scripts/cleanup": "Scripts de nettoyage du projet",
    "scripts/validation": "Scripts de validation des fichiers Markdown",
    "scripts/execution": "Scripts d'exécution des fonctionnalités principales",
    "docs": "Documentation supplémentaire",
    "examples": "Exemples de textes et données"
}

# Définition des fichiers à déplacer
FILES_TO_MOVE = {
    # Scripts de nettoyage
    "cleanup_obsolete_files.py": "scripts/cleanup/",
    "cleanup_project.py": "scripts/cleanup/",
    "cleanup_repository.py": "scripts/cleanup/",
    
    # Scripts de validation
    "validate_section_anchors.ps1": "scripts/validation/",
    "validate_toc_anchors.ps1": "scripts/validation/",
    "compare_markdown.ps1": "scripts/validation/",
    
    # Scripts d'exécution
    "run_extract_repair.py": "scripts/execution/",
    "run_verify_extracts.py": "scripts/execution/",
    
    # Documentation
    "README_cleanup_obsolete_files.md": "docs/",
    "README_ENVIRONNEMENT.md": "docs/",
    "rapport_final.md": "docs/",
    
    # Exemples
    "exemple_sophisme.txt": "examples/",
    "nouvelle_section_sujets_projets.md": "docs/"
}

# Fichiers à conserver à la racine
ROOT_FILES = [
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    ".gitignore",
    "reorganize_project.py"  # Ce script lui-même
]

def create_directories():
    """Crée les répertoires nécessaires."""
    print("Création des répertoires...")
    
    for directory, description in DIRECTORIES.items():
        os.makedirs(directory, exist_ok=True)
        
        # Créer un fichier README.md dans chaque répertoire
        readme_path = os.path.join(directory, "README.md")
        if not os.path.exists(readme_path):
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(f"# {directory}\n\n{description}\n")
        
        print(f"  ✓ {directory}")

def move_files():
    """Déplace les fichiers vers leurs nouveaux emplacements."""
    print("\nDéplacement des fichiers...")
    
    for file, destination in FILES_TO_MOVE.items():
        if os.path.exists(file):
            # Créer le répertoire de destination s'il n'existe pas
            os.makedirs(destination, exist_ok=True)
            
            # Chemin complet de destination
            dest_path = os.path.join(destination, os.path.basename(file))
            
            # Déplacer le fichier
            shutil.move(file, dest_path)
            print(f"  ✓ {file} → {dest_path}")
        else:
            print(f"  ✗ {file} non trouvé")

def update_imports():
    """Met à jour les imports dans les scripts déplacés."""
    print("\nMise à jour des imports dans les scripts...")
    
    # Cette fonction nécessiterait une analyse plus approfondie du code
    # pour mettre à jour correctement les imports relatifs
    print("  ⚠ Cette fonctionnalité n'est pas implémentée dans cette version")
    print("  ⚠ Vous devrez peut-être ajuster manuellement les imports dans les scripts déplacés")

def create_main_readme():
    """Crée un nouveau README.md à la racine qui référence la nouvelle structure."""
    print("\nMise à jour du README.md principal...")
    
    # Cette fonction nécessiterait une analyse du README.md existant
    # et l'ajout d'informations sur la nouvelle structure
    print("  ⚠ Cette fonctionnalité n'est pas implémentée dans cette version")
    print("  ⚠ Vous devrez mettre à jour manuellement le README.md pour refléter la nouvelle structure")

def main():
    """Fonction principale."""
    print("=== Réorganisation du projet d'analyse argumentative ===\n")
    
    # Créer les répertoires
    create_directories()
    
    # Déplacer les fichiers
    move_files()
    
    # Mettre à jour les imports
    update_imports()
    
    # Créer un nouveau README.md
    create_main_readme()
    
    print("\n=== Réorganisation terminée ===")
    print("\nActions à effectuer manuellement :")
    print("1. Vérifier que les scripts fonctionnent correctement dans leur nouvel emplacement")
    print("2. Ajuster les imports relatifs si nécessaire")
    print("3. Mettre à jour le README.md principal pour refléter la nouvelle structure")
    print("4. Committer les changements avec Git")

if __name__ == "__main__":
    main()