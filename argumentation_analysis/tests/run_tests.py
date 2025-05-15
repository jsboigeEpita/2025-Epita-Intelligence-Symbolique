#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour exécuter tous les tests unitaires et d'intégration du projet.

Ce script utilise pytest pour découvrir et exécuter tous les tests dans le répertoire tests.
Il génère également un rapport de couverture de code si le module pytest-cov est installé.
"""

import sys
import os
import subprocess
from pathlib import Path

# Ajouter les répertoires nécessaires au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
project_dir = parent_dir.parent

# Ajouter le répertoire parent au chemin de recherche des modules
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Ajouter le répertoire du projet au chemin de recherche des modules
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

# Configurer le chemin pour les imports relatifs
os.environ["PYTHONPATH"] = str(parent_dir)

# Essayer d'importer pytest et pytest-cov
try:
    import pytest
    has_pytest = True
except ImportError:
    has_pytest = False
    print("Module 'pytest' non trouvé. Veuillez l'installer avec: pip install pytest")
    sys.exit(1)

try:
    import pytest_cov
    has_coverage = True
except ImportError:
    has_coverage = False
    print("Module 'pytest-cov' non trouvé. Le rapport de couverture ne sera pas généré.")
    print("Pour installer pytest-cov: pip install pytest-cov")


def run_tests():
    """Exécute tous les tests unitaires et d'intégration avec pytest."""
    print("=== Tests Unitaires et d'Intégration - Projet d'Analyse Argumentative ===\n")
    
    # Construire les arguments pytest
    pytest_args = ["-v"]  # Mode verbeux
    
    # Ajouter la couverture si disponible
    # Temporairement désactivé pour le test
    has_coverage = False
    if has_coverage:
        pytest_args.extend([
            "--cov=" + str(parent_dir),
            "--cov-report=term",
            "--cov-report=html:./tests/htmlcov",
            "--cov-report=xml:./tests/coverage.xml",
            "--cov-config=./tests/.coveragerc"
        ])
    
    # Exécuter pytest avec les arguments
    result = pytest.main(pytest_args)
    
    # Afficher un message de résultat
    if result == 0:
        print("\n✅ Tous les tests ont réussi!")
    else:
        print("\n❌ Certains tests ont échoué.")
    
    # Afficher le chemin du rapport de couverture si généré
    if has_coverage:
        htmlcov_dir = current_dir / "htmlcov"
        if htmlcov_dir.exists():
            print(f"\nRapport HTML de couverture généré dans {htmlcov_dir}")
        
        coverage_xml = current_dir / "coverage.xml"
        if coverage_xml.exists():
            print(f"Rapport XML de couverture généré dans {coverage_xml}")
    
    return result


if __name__ == "__main__":
    # Créer le fichier .coveragerc s'il n'existe pas
    coveragerc_path = current_dir / ".coveragerc"
    if not coveragerc_path.exists():
        with open(coveragerc_path, "w") as f:
            f.write("""[run]
source = argumentation_analysis
omit =
    */__pycache__/*
    */tests/*
    */venv/*
    */env/*
    */.venv/*
    */site-packages/*
    */dist-packages/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if __name__ == .__main__.:
    pass
    raise ImportError
""")
        print(f"Fichier de configuration de couverture créé: {coveragerc_path}")
    
    # Exécuter les tests
    sys.exit(run_tests())