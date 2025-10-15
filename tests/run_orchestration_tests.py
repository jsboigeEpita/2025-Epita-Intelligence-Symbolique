#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de Lancement des Tests d'Orchestration
============================================

Script pour exécuter facilement tous les tests du système d'orchestration unifié.
Permet de lancer les tests par catégorie ou tous ensemble avec rapports détaillés.

Usage:
    python tests/run_orchestration_tests.py [options]

Options:
    --unit              : Tests unitaires seulement
    --integration       : Tests d'intégration seulement
    --coverage          : Avec couverture de code
    --verbose           : Mode verbose
    --fast              : Tests rapides seulement (skip slow)
    --html-report       : Génère un rapport HTML

Auteur: Intelligence Symbolique EPITA
Date: 10/06/2025
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_command(command, description):
    """Exécute une commande et affiche le résultat."""
    print(f"\n{'='*60}")
    print(f"EXECUTION: {description}")
    print(f"{'='*60}")
    print(f"Commande: {' '.join(command)}")
    print("-" * 60)

    try:
        result = subprocess.run(
            command, capture_output=True, text=True, cwd=project_root
        )

        if result.stdout:
            print("STDOUT:")
            print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        if result.returncode == 0:
            print("Succes!")
        else:
            print(f"Echec (code: {result.returncode})")

        return result.returncode == 0

    except Exception as e:
        print(f"Erreur lors de l'execution: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Lancement des tests d'orchestration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--unit", action="store_true", help="Tests unitaires seulement")
    parser.add_argument(
        "--integration", action="store_true", help="Tests d'intégration seulement"
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Avec couverture de code"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbose")
    parser.add_argument(
        "--fast", action="store_true", help="Tests rapides seulement (skip slow)"
    )
    parser.add_argument(
        "--html-report", action="store_true", help="Génère un rapport HTML"
    )
    parser.add_argument(
        "--parallel", "-n", type=int, default=1, help="Nombre de processus parallèles"
    )

    args = parser.parse_args()

    print("LANCEMENT DES TESTS D'ORCHESTRATION")
    print(f"Repertoire de travail: {project_root}")

    # Vérification de l'environnement
    print("\nVerification de l'environnement...")
    try:
        import pytest

        print(f"pytest version: {pytest.__version__}")
    except ImportError:
        print("pytest non installe. Installation...")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "pytest",
                "pytest-cov",
                "pytest-html",
            ]
        )

    # Construction de la commande pytest
    base_cmd = [sys.executable, "-m", "pytest"]

    # Sélection des tests
    test_paths = []
    if args.unit:
        test_paths.append("tests/unit/orchestration/")
        print("Mode: Tests unitaires uniquement")
    else:
        test_paths.extend(["tests/unit/orchestration/"])
        print("Mode: Tous les tests d'orchestration")

    # Options pytest
    pytest_args = []

    if args.verbose:
        pytest_args.append("-v")

    if args.fast:
        pytest_args.extend(["-m", "not slow"])

    if args.parallel > 1:
        pytest_args.extend(["-n", str(args.parallel)])

    if args.coverage:
        pytest_args.extend(
            [
                "--cov=argumentation_analysis.pipelines.orchestration",
                "--cov=argumentation_analysis.orchestrators",
                "--cov-report=term-missing",
            ]
        )
        if args.html_report:
            pytest_args.append("--cov-report=html:tests/reports/coverage_html")

    if args.html_report:
        pytest_args.extend(
            [
                "--html=tests/reports/orchestration_test_report.html",
                "--self-contained-html",
            ]
        )
        # Créer le répertoire de rapports
        reports_dir = project_root / "tests" / "reports"
        reports_dir.mkdir(exist_ok=True)

    # Ajout des options de formatage
    pytest_args.extend(["--tb=short", "--strict-markers", "--strict-config"])

    # Construction de la commande finale
    final_cmd = base_cmd + pytest_args + test_paths

    # Exécution des tests
    success = run_command(final_cmd, "Exécution des tests d'orchestration")

    # Résumé
    print(f"\n{'='*60}")
    print("RESUME DE L'EXECUTION")
    print(f"{'='*60}")

    if success:
        print("TOUS LES TESTS ONT REUSSI!")
        if args.html_report:
            print(f"Rapport HTML genere: tests/reports/orchestration_test_report.html")
        if args.coverage:
            print("Rapport de couverture genere")
    else:
        print("CERTAINS TESTS ONT ECHOUE")
        print("Verifiez les erreurs ci-dessus pour plus de details")

    print(f"\nFin d'execution (code de retour: {0 if success else 1})")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
