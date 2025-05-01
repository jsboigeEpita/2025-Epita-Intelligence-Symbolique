#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour exécuter les tests unitaires et d'intégration avec couverture de code.

Ce script utilise pytest et pytest-cov pour exécuter tous les tests et générer un rapport
de couverture détaillé aux formats HTML et XML. Il définit également un objectif de
couverture minimal et analyse la couverture par module.
"""

import sys
import os
import webbrowser
import subprocess
import json
from pathlib import Path
from collections import defaultdict

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Objectif de couverture minimal (en pourcentage)
COVERAGE_TARGET = 80

# Modules à analyser
MODULES_TO_ANALYZE = [
    "models",
    "services",
    "core",
    "scripts",
    "orchestration",
    "agents",
    "utils"
]

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


def create_coverage_config():
    """Crée un fichier de configuration pour la couverture de code."""
    coveragerc_path = current_dir / ".coveragerc"
    
    with open(coveragerc_path, "w") as f:
        f.write("""[run]
source = argumentiation_analysis
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

[html]
directory = tests/htmlcov
title = Rapport de couverture - Projet d'Analyse Argumentative

[xml]
output = tests/coverage.xml
""")
    
    return coveragerc_path


def analyze_coverage_by_module(coverage_data_path):
    """Analyse la couverture par module à partir du fichier coverage.json."""
    try:
        with open(coverage_data_path, 'r') as f:
            coverage_data = json.load(f)
        
        # Analyser la couverture par module
        module_coverage = defaultdict(lambda: {"covered_lines": 0, "total_lines": 0})
        
        for file_path, file_data in coverage_data.get("files", {}).items():
            # Extraire le nom du module à partir du chemin du fichier
            path_parts = Path(file_path).parts
            if "argumentiation_analysis" in path_parts:
                idx = path_parts.index("argumentiation_analysis")
                if idx + 1 < len(path_parts):
                    module_name = path_parts[idx + 1]
                    
                    # Compter les lignes couvertes et totales
                    covered_lines = sum(1 for line in file_data.get("executed_lines", []))
                    total_lines = len(file_data.get("executed_lines", [])) + len(file_data.get("missing_lines", []))
                    
                    module_coverage[module_name]["covered_lines"] += covered_lines
                    module_coverage[module_name]["total_lines"] += total_lines
        
        # Calculer le pourcentage de couverture par module
        module_percentages = {}
        for module, data in module_coverage.items():
            if data["total_lines"] > 0:
                percentage = (data["covered_lines"] / data["total_lines"]) * 100
                module_percentages[module] = percentage
        
        return module_percentages
    
    except Exception as e:
        print(f"Erreur lors de l'analyse de la couverture par module: {e}")
        return {}


def run_tests_with_coverage():
    """Exécute tous les tests avec couverture de code en utilisant pytest."""
    # Créer le fichier de configuration de couverture
    coveragerc_path = create_coverage_config()
    print(f"Fichier de configuration de couverture créé: {coveragerc_path}")
    
    # Construire les arguments pytest
    pytest_args = [
        "-v",  # Mode verbeux
        "--cov=argumentiation_analysis",  # Mesurer la couverture pour tout le package
        "--cov-report=term",  # Rapport dans le terminal
        "--cov-report=html",  # Rapport HTML
        "--cov-report=xml",  # Rapport XML pour CI/CD
        "--cov-report=json",  # Rapport JSON pour l'analyse
        f"--cov-config={coveragerc_path}"  # Utiliser le fichier de configuration
    ]
    
    # Exécuter pytest avec les arguments
    print("\n=== Exécution des tests unitaires et d'intégration avec couverture ===\n")
    result = pytest.main(pytest_args)
    
    # Analyser les résultats de couverture
    print("\n=== Rapport de couverture par module ===\n")
    
    # Analyser la couverture par module
    coverage_json_path = current_dir / ".coverage.json"
    if coverage_json_path.exists():
        module_percentages = analyze_coverage_by_module(coverage_json_path)
        
        # Afficher la couverture par module
        if module_percentages:
            print(f"{'Module':<15} | {'Couverture':<10} | {'Statut':<10}")
            print("-" * 40)
            
            total_coverage = 0
            module_count = 0
            
            for module in MODULES_TO_ANALYZE:
                if module in module_percentages:
                    percentage = module_percentages[module]
                    total_coverage += percentage
                    module_count += 1
                    
                    status = "✅" if percentage >= COVERAGE_TARGET else "⚠️"
                    print(f"{module:<15} | {percentage:>8.2f}% | {status}")
            
            # Calculer la couverture moyenne
            if module_count > 0:
                average_coverage = total_coverage / module_count
                print("-" * 40)
                status = "✅" if average_coverage >= COVERAGE_TARGET else "⚠️"
                print(f"{'MOYENNE':<15} | {average_coverage:>8.2f}% | {status}")
                
                # Vérifier si l'objectif de couverture est atteint
                if average_coverage < COVERAGE_TARGET:
                    print(f"\n⚠️ ATTENTION: La couverture de code moyenne ({average_coverage:.2f}%) est inférieure à l'objectif ({COVERAGE_TARGET}%).")
                    print("Veuillez ajouter plus de tests pour améliorer la couverture.")
                else:
                    print(f"\n✅ SUCCÈS: La couverture de code moyenne ({average_coverage:.2f}%) atteint l'objectif ({COVERAGE_TARGET}%).")
    
    # Afficher les chemins des rapports générés
    htmlcov_dir = current_dir / "htmlcov"
    if htmlcov_dir.exists():
        print(f"\nRapport HTML généré dans {htmlcov_dir}")
        
        # Ouvrir le rapport HTML dans le navigateur
        index_html = htmlcov_dir / "index.html"
        if index_html.exists():
            try:
                print("Ouverture du rapport HTML dans le navigateur...")
                webbrowser.open(f"file://{index_html}")
            except Exception as e:
                print(f"Impossible d'ouvrir le navigateur: {e}")
                print(f"Veuillez ouvrir manuellement le fichier: {index_html}")
    
    coverage_xml = current_dir / "coverage.xml"
    if coverage_xml.exists():
        print(f"Rapport XML généré dans {coverage_xml}")
    
    # Retourner le code de sortie approprié
    return result


if __name__ == "__main__":
    print("=== Tests avec Couverture - Projet d'Analyse Argumentative ===\n")
    
    # Vérifier si pytest-cov est installé
    if not has_coverage:
        print("Installation de pytest-cov...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest-cov"])
            print("pytest-cov installé avec succès.")
            has_coverage = True
        except subprocess.CalledProcessError:
            print("Erreur lors de l'installation de pytest-cov.")
    
    # Exécuter les tests avec couverture
    if has_coverage:
        print("Exécution des tests avec couverture de code...")
        exit_code = run_tests_with_coverage()
    else:
        print("Impossible d'exécuter les tests avec couverture. Veuillez installer pytest-cov.")
        exit_code = 1
    
    # Sortir avec le code approprié
    sys.exit(exit_code)