#!/usr/bin/env python3
"""
Script d'organisation des fichiers éparpillés à la racine du projet
Sherlock-Watson-Moriarty Oracle Enhanced System
"""

import project_core.core_from_scripts.auto_env
import os
import shutil
from pathlib import Path
from datetime import datetime

def organize_root_files():
    """Organise les fichiers éparpillés à la racine selon leur type"""
    
    root_dir = Path(".")
    
    # Créer les répertoires de destination s'ils n'existent pas
    destinations = {
        "temp_files": "scripts/temp",
        "test_files": "tests/validation_sherlock_watson", 
        "log_files": "logs/traces",
        "json_results": "results/validation",
        "md_reports": "docs/rapports",
        "config_files": "config/pytest"
    }
    
    for dest_dir in destinations.values():
        os.makedirs(dest_dir, exist_ok=True)
    
    # Mapping des fichiers à déplacer
    file_mappings = {
        # Fichiers de test temporaires
        "test_*.py": "tests/validation_sherlock_watson",
        "fix_*.py": "scripts/temp",
        "temp_*.py": "scripts/temp", 
        "scratch_*.py": "scripts/temp",
        "minimal_*.py": "scripts/temp",
        "api_test_*.py": "scripts/temp",
        "check_*.py": "scripts/temp",
        "resultat_*.py": "scripts/temp",
        "validation_*.py": "scripts/temp",
        "verify_*.ps1": "scripts/temp",
        "pytest_*.py": "scripts/temp",
        
        # Logs et traces
        "*.log": "logs/traces",
        
        # Résultats JSON
        "phase_*.json": "results/validation",
        "rapport_*.json": "results/validation", 
        "*_results*.json": "results/validation",
        
        # Rapports markdown
        "*_summary.md": "docs/rapports",
        "rapport_*.md": "docs/rapports",
        "correction_*.md": "docs/rapports",
        "trace_*.md": "docs/rapports",
        
        # Configuration pytest
        "pytest*.ini": "config/pytest",
        
        # Scripts d'analyse
        "analyse_*.py": "scripts/analysis",
        "generer_*.py": "scripts/analysis",
        "create_*.py": "scripts/analysis",
        "setup_*.py": "scripts/env",
        "setup_*.sh": "scripts/env"
    }
    
    moved_files = []
    
    print("🔄 Organisation des fichiers à la racine...")
    
    for pattern, dest_folder in file_mappings.items():
        if "*" in pattern:
            # Utiliser glob pour les patterns
            import glob
            files = glob.glob(pattern)
        else:
            files = [pattern] if Path(pattern).exists() else []
            
        for file_path in files:
            if Path(file_path).is_file():
                # Créer le dossier de destination
                os.makedirs(dest_folder, exist_ok=True)
                
                # Déplacer le fichier
                dest_path = Path(dest_folder) / Path(file_path).name
                try:
                    shutil.move(file_path, dest_path)
                    moved_files.append(f"{file_path} → {dest_path}")
                    print(f"✅ Déplacé: {file_path} → {dest_path}")
                except Exception as e:
                    print(f"❌ Erreur déplacement {file_path}: {e}")
    
    # Créer un rapport de l'organisation
    report_path = f"docs/rapports/organisation_root_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# Rapport d'Organisation des Fichiers Racine\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Fichiers déplacés:** {len(moved_files)}\n\n")
        f.write("## Fichiers Déplacés\n\n")
        for file_move in moved_files:
            f.write(f"- {file_move}\n")
    
    print(f"\n✅ Organisation terminée. {len(moved_files)} fichiers déplacés.")
    print(f"📄 Rapport généré: {report_path}")
    
    return moved_files

if __name__ == "__main__":
    organize_root_files()