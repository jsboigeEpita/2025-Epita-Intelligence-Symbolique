#!/usr/bin/env python3
"""
Script de Nettoyage Sécurisé - Doublons de Migration
===================================================

Script généré automatiquement le 2025-06-10T09:51:32.956384
Supprime 0 fichiers identifiés comme doublons obsolètes.

ATTENTION: Ce script crée une sauvegarde avant suppression !
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path


def create_backup():
    """Crée une sauvegarde complète avant suppression."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"backup_before_cleanup_{timestamp}")
    backup_dir.mkdir(exist_ok=True)

    print(f"📦 Création de la sauvegarde dans {backup_dir}")

    # Sauvegarde du répertoire scripts complet
    scripts_backup = backup_dir / "scripts"
    shutil.copytree("scripts", scripts_backup)

    # Sauvegarde du rapport d'analyse
    shutil.copy("reports/migration_duplicates_analysis.md", backup_dir)

    print(f"✅ Sauvegarde créée: {backup_dir}")
    return backup_dir


def main():
    """Exécute le nettoyage sécurisé."""

    files_to_delete = []

    print(f"🗑️ Nettoyage de {len(files_to_delete)} doublons identifiés")

    # 1. Créer la sauvegarde
    backup_dir = create_backup()

    # 2. Confirmation utilisateur
    print("\n📋 Fichiers à supprimer:")
    for filename in sorted(files_to_delete):
        print(f"  - {filename}")

    confirm = input("\n❓ Confirmer la suppression ? (yes/NO): ")
    if confirm.lower() != "yes":
        print("❌ Nettoyage annulé")
        return

    # 3. Suppression avec log
    deleted_files = []
    errors = []

    for filename in files_to_delete:
        filepath = Path("scripts") / filename
        try:
            if filepath.exists():
                filepath.unlink()
                deleted_files.append(filename)
                print(f"✅ Supprimé: {filename}")
            else:
                print(f"⚠️ Déjà absent: {filename}")
        except Exception as e:
            errors.append(f"{filename}: {e}")
            print(f"❌ Erreur: {filename} - {e}")

    # 4. Rapport final
    report = {
        "timestamp": datetime.now().isoformat(),
        "backup_location": str(backup_dir),
        "files_deleted": deleted_files,
        "errors": errors,
        "total_deleted": len(deleted_files),
    }

    # Sauvegarde du rapport
    with open(backup_dir / "cleanup_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\n📊 Nettoyage terminé:")
    print(f"  - {len(deleted_files)} fichiers supprimés")
    print(f"  - {len(errors)} erreurs")
    print(f"  - Sauvegarde: {backup_dir}")


if __name__ == "__main__":
    main()
