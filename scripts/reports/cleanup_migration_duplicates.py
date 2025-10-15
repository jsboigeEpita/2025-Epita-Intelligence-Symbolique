#!/usr/bin/env python3
"""
Script de Nettoyage Sécurisé - Doublons de Migration
===================================================

Script généré automatiquement le 2025-06-10T09:22:51.875502
Supprime 28 fichiers identifiés comme doublons obsolètes.

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

    files_to_delete = [
        "analyze_phase2_by_groups.py",
        "auto_logical_analysis_task1_fixed.py",
        "auto_logical_analysis_task1_VRAI.py",
        "batch_test_analysis.py",
        "diagnostic_tests_phases.py",
        "diagnostic_tests_unitaires.py",
        "final_system_integration_test.py",
        "fix_asyncio_decorators.py",
        "fix_critical_imports.py",
        "fix_return_assert.py",
        "fix_unicode_conda.py",
        "get_env_name.py",
        "localize_source_contents.py",
        "measure_final_success_rate.py",
        "migrate_to_service_manager.py",
        "minimal_test_diagnostic.py",
        "phase4_final_validation.py",
        "populate_extract_segments.py",
        "rapport_investigation_tests_unitaires.py",
        "test_jpype_killer.py",
        "test_orchestration_scenario.py",
        "test_practical_capabilities.py",
        "test_unicode_encoding.py",
        "validate_new_components_tests.py",
        "validate_unified_system.py",
        "validation_point4_rhetorical_analysis.py",
        "validation_point5_final_comprehensive.py",
        "validation_point5_realistic_final.py",
    ]

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

    print(f"\n📊 Nettoyage terminé:")
    print(f"  - {len(deleted_files)} fichiers supprimés")
    print(f"  - {len(errors)} erreurs")
    print(f"  - Sauvegarde: {backup_dir}")


if __name__ == "__main__":
    main()
