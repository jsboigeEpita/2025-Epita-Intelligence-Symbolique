import argumentation_analysis.core.environment

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour générer un rapport textuel sur la couverture des tests.

Ce script analyse le fichier coverage.xml et l'historique de couverture
pour générer un rapport textuel sur l'évolution de la couverture des tests.
"""

import os
import sys
import json
import datetime

# import xml.etree.ElementTree as ET # Déplacé vers coverage_utils
from pathlib import Path
from argumentation_analysis.utils.dev_tools.coverage_utils import parse_coverage_xml

# La fonction parse_coverage_xml a été déplacée vers project_core.dev_utils.coverage_utils
# et est importée ci-dessus.


def map_package_to_module(package_name):
    """
    Mappe un nom de package à un nom de module.

    Args:
        package_name (str): Nom du package

    Returns:
        str: Nom du module correspondant
    """
    mapping = {
        "core.communication": "Communication",
        "core": "Gestion d'État",
        "agents.core.extract": "Agents d'Extraction",
        "agents.core.informal": "Agents d'Analyse Informelle",
        "agents.tools.analysis": "Outils d'Analyse",
        ".": "Global",
    }

    for key, value in mapping.items():
        if key in package_name:
            return value

    return "Autre"  # La fonction est maintenant importée


def generate_text_report(history_file, output_file):
    """
    Génère un rapport textuel sur l'évolution de la couverture des tests.

    Args:
        history_file (str): Chemin vers le fichier d'historique
        output_file (str): Chemin vers le fichier de sortie
    """
    if not os.path.exists(history_file):
        print(f"Le fichier d'historique {history_file} n'existe pas.")
        return

    try:
        with open(history_file, "r") as f:
            history = json.load(f)
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier d'historique: {e}")
        return

    if len(history) < 2:
        print(
            "L'historique doit contenir au moins deux entrées pour calculer l'amélioration."
        )
        return

    # Prendre la première et la dernière entrée
    first_entry = history[0]
    last_entry = history[-1]

    # Calculer l'amélioration pour la couverture globale
    initial_global = first_entry.get("global", 0)
    current_global = last_entry.get("global", 0)
    global_improvement = current_global - initial_global

    # Calculer l'amélioration pour chaque module
    module_improvements = {}
    first_packages = first_entry.get("packages", {})
    last_packages = last_entry.get("packages", {})

    all_packages = set(first_packages.keys()) | set(last_packages.keys())
    for package in all_packages:
        initial = first_packages.get(package, 0)
        current = last_packages.get(package, 0)
        module = map_package_to_module(package)

        if module not in module_improvements:
            module_improvements[module] = []

        module_improvements[module].append(current - initial)

    # Calculer la moyenne d'amélioration pour chaque module
    avg_improvements = {
        module: sum(improvements) / len(improvements)
        for module, improvements in module_improvements.items()
    }

    # Générer le rapport
    report = []
    report.append("# Rapport d'Évolution de la Couverture des Tests")
    report.append("")
    report.append(f"Date du rapport: {datetime.datetime.now().strftime('%Y-%m-%d')}")
    report.append("")
    report.append("## 1. Couverture Globale")
    report.append("")
    report.append(f"- Couverture initiale: {initial_global:.2f}%")
    report.append(f"- Couverture actuelle: {current_global:.2f}%")
    report.append(f"- Amélioration: {global_improvement:+.2f}%")
    report.append("")
    report.append("## 2. Couverture par Module")
    report.append("")
    report.append(
        "| Module | Couverture Initiale | Couverture Actuelle | Amélioration |"
    )
    report.append(
        "|--------|---------------------|---------------------|--------------|"
    )

    # Trier les modules par amélioration décroissante
    sorted_modules = sorted(
        avg_improvements.keys(), key=lambda x: avg_improvements[x], reverse=True
    )

    for module in sorted_modules:
        # Calculer la couverture moyenne pour ce module
        initial_coverages = []
        current_coverages = []

        for package in first_packages:
            if map_package_to_module(package) == module:
                initial_coverages.append(first_packages.get(package, 0))

        for package in last_packages:
            if map_package_to_module(package) == module:
                current_coverages.append(last_packages.get(package, 0))

        if initial_coverages and current_coverages:
            initial_avg = sum(initial_coverages) / len(initial_coverages)
            current_avg = sum(current_coverages) / len(current_coverages)
            improvement = avg_improvements[module]

            report.append(
                f"| {module} | {initial_avg:.2f}% | {current_avg:.2f}% | {improvement:+.2f}% |"
            )

    report.append("")
    report.append("## 3. Modules Nécessitant des Améliorations")
    report.append("")

    # Identifier les modules avec une couverture inférieure à 50%
    low_coverage_modules = []
    for package, coverage in last_packages.items():
        if coverage < 50:
            module = map_package_to_module(package)
            low_coverage_modules.append((module, package, coverage))

    # Trier par couverture croissante
    low_coverage_modules.sort(key=lambda x: x[2])

    if low_coverage_modules:
        report.append(
            "Les modules suivants ont une couverture inférieure à 50% et devraient être prioritaires pour l'amélioration des tests:"
        )
        report.append("")
        for module, package, coverage in low_coverage_modules:
            report.append(f"- {module} ({package}): {coverage:.2f}%")
    else:
        report.append("Tous les modules ont une couverture supérieure à 50%.")

    report.append("")
    report.append("## 4. Recommandations")
    report.append("")
    report.append("1. **Priorités à court terme**:")
    report.append(
        "   - Résoudre les problèmes de dépendances pour permettre l'exécution de tous les tests"
    )
    report.append("   - Ajouter des tests pour les modules avec 0% de couverture")
    report.append("   - Corriger les tests qui échouent actuellement")
    report.append("")
    report.append("2. **Objectifs à moyen terme**:")
    report.append(
        "   - Augmenter la couverture des modules d'extraction et d'analyse informelle à au moins 50%"
    )
    report.append(
        "   - Améliorer la couverture des modules de communication avec une couverture inférieure à 20%"
    )
    report.append("   - Développer des tests d'intégration plus robustes")
    report.append("")
    report.append("3. **Objectifs à long terme**:")
    report.append("   - Atteindre une couverture globale d'au moins 80%")
    report.append(
        "   - Mettre en place une intégration continue avec vérification automatique de la couverture"
    )
    report.append("   - Documenter les stratégies de test pour chaque module")

    # Écrire le rapport dans un fichier
    try:
        with open(output_file, "w") as f:
            f.write("\n".join(report))
        print(f"Rapport généré avec succès dans {output_file}")
    except Exception as e:
        print(f"Erreur lors de l'écriture du rapport: {e}")


def main():
    """Fonction principale."""
    # Définir les chemins
    history_file = "results/coverage_history.json"
    output_file = "results/rapport_evolution_couverture.md"

    # Générer le rapport
    # generate_text_report(history_file, output_file) # Appel modifié ci-dessous

    # Convertir les chemins en objets Path pour la nouvelle fonction
    history_file_path = Path(history_file)
    output_file_path = Path(output_file)

    # Appeler la fonction importée
    generate_coverage_evolution_text_report(history_file_path, output_file_path)


if __name__ == "__main__":
    main()
