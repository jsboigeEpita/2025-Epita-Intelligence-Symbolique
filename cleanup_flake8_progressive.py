#!/usr/bin/env python3
"""
Script de nettoyage progressif des erreurs flake8.
Mission D-CI-06 Phase 5c - Nettoyage imports inutilisés (F401, F841).
"""

import subprocess
import sys
from pathlib import Path
import time

# Répertoires à nettoyer par ordre de priorité (moins risqué en premier)
DIRECTORIES_TO_CLEAN = [
    "demos/",
    "examples/",
    "scripts/",
    "project_core/",
    "argumentation_analysis/",
]


def run_command(cmd, cwd=None):
    """Exécute une commande et retourne le résultat."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd,
    )
    return result


def count_flake8_errors(directory="."):
    """Compte le nombre d'erreurs flake8 dans un répertoire."""
    result = run_command(f"python -m flake8 {directory}")
    lines = [l for l in result.stdout.split("\n") if l.strip()]
    return len(lines)


def clean_directory_with_autoflake(directory):
    """Nettoie un répertoire avec autoflake."""
    print(f"\n{'='*60}")
    print(f"📁 Nettoyage de : {directory}")
    print(f"{'='*60}")

    # Compter les erreurs avant
    print(f"\n🔍 Analyse flake8 AVANT nettoyage...")
    errors_before = count_flake8_errors(directory)
    print(f"   Erreurs détectées : {errors_before}")

    # Dry-run autoflake pour voir ce qui serait modifié
    print(f"\n🧪 Simulation autoflake (dry-run)...")
    dry_run_cmd = f"python -m autoflake --remove-all-unused-imports --remove-unused-variables --recursive --check {directory}"
    dry_run_result = run_command(dry_run_cmd)

    files_to_modify = [l for l in dry_run_result.stdout.split("\n") if "Unused" in l]
    print(f"   Fichiers à modifier : {len(files_to_modify)}")

    if len(files_to_modify) == 0:
        print(f"   ✅ Aucune modification nécessaire dans {directory}")
        return {
            "directory": directory,
            "errors_before": errors_before,
            "errors_after": errors_before,
            "files_modified": 0,
            "status": "skipped",
        }

    # Application réelle
    print(f"\n✨ Application du nettoyage autoflake...")
    clean_cmd = f"python -m autoflake --remove-all-unused-imports --remove-unused-variables --recursive --in-place {directory}"
    clean_result = run_command(clean_cmd)

    print(f"   ✅ Nettoyage terminé")

    # Compter les erreurs après
    print(f"\n🔍 Analyse flake8 APRÈS nettoyage...")
    errors_after = count_flake8_errors(directory)
    print(f"   Erreurs détectées : {errors_after}")

    reduction = errors_before - errors_after
    if reduction > 0:
        percentage = (reduction / errors_before) * 100 if errors_before > 0 else 0
        print(f"   📉 Réduction : -{reduction} erreurs (-{percentage:.1f}%)")
    else:
        print(
            f"   ⚠️  Pas de réduction d'erreurs (peut-être des erreurs non-F401/F841)"
        )

    return {
        "directory": directory,
        "errors_before": errors_before,
        "errors_after": errors_after,
        "files_modified": len(files_to_modify),
        "reduction": reduction,
        "status": "completed",
    }


def main():
    """Fonction principale."""
    print(
        """
╔═══════════════════════════════════════════════════════════╗
║  MISSION D-CI-06 PHASE 5c                                 ║
║  Nettoyage Progressif des Erreurs Flake8                  ║
║  Cible : F401 (imports inutilisés), F841 (vars inutilisées) ║
╚═══════════════════════════════════════════════════════════╝
"""
    )

    # Baseline globale
    print("\n📊 BASELINE INITIALE (tout le projet)")
    total_errors_initial = count_flake8_errors(".")
    print(f"   Total erreurs flake8 : {total_errors_initial}")

    results = []

    # Nettoyer chaque répertoire
    for directory in DIRECTORIES_TO_CLEAN:
        if not Path(directory).exists():
            print(f"\n⚠️  Répertoire {directory} n'existe pas, passage au suivant...")
            continue

        result = clean_directory_with_autoflake(directory)
        results.append(result)

        # Pause pour laisser le temps de vérifier
        time.sleep(1)

    # Rapport final
    print(f"\n{'='*60}")
    print("📊 RAPPORT FINAL DE NETTOYAGE")
    print(f"{'='*60}\n")

    total_reduction = 0
    total_files_modified = 0

    for result in results:
        if result["status"] == "completed":
            print(
                f"✅ {result['directory']:30s} | "
                f"Avant: {result['errors_before']:6d} | "
                f"Après: {result['errors_after']:6d} | "
                f"Réduction: -{result['reduction']:5d}"
            )
            total_reduction += result["reduction"]
            total_files_modified += result["files_modified"]
        else:
            print(f"⏭️  {result['directory']:30s} | Pas de modifications nécessaires")

    print(f"\n{'='*60}")
    print(f"📈 STATISTIQUES GLOBALES")
    print(f"{'='*60}")
    print(f"   Erreurs initiales     : {total_errors_initial:,}")

    total_errors_final = count_flake8_errors(".")
    print(f"   Erreurs finales       : {total_errors_final:,}")
    print(f"   Réduction totale      : -{total_errors_initial - total_errors_final:,}")

    if total_errors_initial > 0:
        percentage = (
            (total_errors_initial - total_errors_final) / total_errors_initial
        ) * 100
        print(f"   Pourcentage réduit    : {percentage:.2f}%")

    print(f"   Fichiers modifiés     : {total_files_modified}")

    print(f"\n💾 Prochaines étapes recommandées :")
    print(f"   1. Vérifier les modifications : git diff")
    print(f"   2. Exécuter black : python -m black --check .")
    print(
        f"   3. Commit intermédiaire : git add . && git commit -m 'refactor: remove unused imports (F401, F841) - D-CI-06 Phase 5c'"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
