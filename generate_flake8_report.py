#!/usr/bin/env python3
"""Script pour générer un rapport flake8 complet du projet."""

import subprocess
import sys
from pathlib import Path


def main():
    """Génère le rapport flake8 et analyse les résultats."""
    print("🔍 Génération du rapport flake8...")

    # Exécuter flake8
    result = subprocess.run(
        [sys.executable, "-m", "flake8", "."],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    # Sauvegarder le rapport
    report_path = Path("flake8_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(result.stdout)
        if result.stderr:
            f.write("\n=== STDERR ===\n")
            f.write(result.stderr)

    # Analyser les résultats
    lines = result.stdout.strip().split("\n")
    errors = [line for line in lines if line.strip()]

    print(f"\n✅ Rapport généré : {report_path}")
    print(f"📊 Nombre total d'erreurs : {len(errors)}")

    # Analyser par type d'erreur
    error_types = {}
    for error in errors:
        if ":" in error:
            parts = error.split(":")
            if len(parts) >= 4:
                error_code = (
                    parts[3].strip().split()[0] if parts[3].strip() else "UNKNOWN"
                )
                error_types[error_code] = error_types.get(error_code, 0) + 1

    print("\n📈 Distribution par type d'erreur :")
    for error_code, count in sorted(
        error_types.items(), key=lambda x: x[1], reverse=True
    )[:10]:
        print(f"  {error_code}: {count}")

    print(f"\n💾 Rapport complet sauvegardé dans {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
