# -*- coding: utf-8 -*-
"""
Utilitaires pour la génération de rapports spécifiques aux outils de développement,
comme les rapports de couverture, de tests, etc.
"""

import logging
import json
import os  # Ajouté pour os.path.exists
from pathlib import Path  # Ajouté pour le typage de Path
from typing import Dict, List, Any, Optional  # Ajouté pour le typage

# Importation de la fonction de mapping depuis son nouvel emplacement
from .project_structure_utils import map_package_to_module

logger = logging.getLogger(__name__)


def generate_coverage_evolution_text_report(
    history_file_path: Path, output_file_path: Path
) -> bool:
    """
    Génère un rapport textuel sur l'évolution de la couverture des tests
    à partir d'un fichier d'historique JSON.

    Args:
        history_file_path (Path): Chemin vers le fichier d'historique JSON.
        output_file_path (Path): Chemin vers le fichier de sortie pour le rapport textuel.

    Returns:
        bool: True si le rapport a été généré et sauvegardé avec succès, False sinon.
    """
    logger.info(
        f"Génération du rapport d'évolution de la couverture depuis {history_file_path} vers {output_file_path}"
    )

    if not history_file_path.exists():
        logger.error(f"Le fichier d'historique {history_file_path} n'existe pas.")
        return False

    try:
        with open(history_file_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(
            f"Erreur de décodage JSON lors de la lecture du fichier d'historique {history_file_path}: {e}",
            exc_info=True,
        )
        return False
    except Exception as e:
        logger.error(
            f"Erreur inattendue lors de la lecture du fichier d'historique {history_file_path}: {e}",
            exc_info=True,
        )
        return False

    if not isinstance(history, list) or len(history) < 2:
        logger.warning(
            "L'historique doit être une liste et contenir au moins deux entrées pour calculer l'amélioration. Rapport non généré."
        )
        return False

    # Prendre la première et la dernière entrée pour une comparaison simple
    first_entry = history[0]
    last_entry = history[-1]

    report_lines: List[str] = ["# Rapport d'Évolution de la Couverture des Tests"]
    report_lines.append(
        f"Comparaison entre le {first_entry.get('timestamp', 'N/A')} et le {last_entry.get('timestamp', 'N/A')}\n"
    )

    # Couverture globale
    initial_global = first_entry.get(
        "global_line_rate", first_entry.get("global", 0.0)
    )  # Compatibilité avec ancien format
    current_global = last_entry.get("global_line_rate", last_entry.get("global", 0.0))
    global_improvement = current_global - initial_global
    report_lines.append(f"## Couverture Globale (Lignes)")
    report_lines.append(f"- Couverture initiale : {initial_global:.2f}%")
    report_lines.append(f"- Couverture actuelle  : {current_global:.2f}%")
    report_lines.append(f"- Amélioration        : {global_improvement:+.2f}%")
    report_lines.append("")

    # Amélioration par module (basé sur les packages)
    report_lines.append("## Amélioration de la Couverture par Module (Lignes)")
    module_improvements: Dict[str, List[float]] = {}
    first_packages = first_entry.get("packages", {})
    last_packages = last_entry.get("packages", {})

    all_package_names = set(first_packages.keys()) | set(last_packages.keys())

    for package_name in sorted(list(all_package_names)):
        initial_pkg_data = first_packages.get(package_name, {})
        current_pkg_data = last_packages.get(package_name, {})

        # S'assurer que les données sont des dictionnaires si le format a changé
        initial_rate = (
            initial_pkg_data
            if isinstance(initial_pkg_data, (int, float))
            else initial_pkg_data.get("line_rate", 0.0)
        )
        current_rate = (
            current_pkg_data
            if isinstance(current_pkg_data, (int, float))
            else current_pkg_data.get("line_rate", 0.0)
        )

        module_name = map_package_to_module(package_name)

        module_improvements.setdefault(module_name, []).append(
            current_rate - initial_rate
        )

    if module_improvements:
        for module_name, improvements in sorted(module_improvements.items()):
            avg_improvement = (
                sum(improvements) / len(improvements) if improvements else 0.0
            )
            # Afficher aussi la couverture actuelle du module si disponible
            # Pour cela, il faudrait agréger la couverture actuelle par module mappé
            current_module_rates = [
                (
                    last_packages.get(pkg_name, {})
                    if isinstance(last_packages.get(pkg_name, {}), dict)
                    else {"line_rate": last_packages.get(pkg_name, 0.0)}
                ).get("line_rate", 0.0)
                for pkg_name in all_package_names
                if map_package_to_module(pkg_name) == module_name
            ]
            avg_current_module_rate = (
                sum(current_module_rates) / len(current_module_rates)
                if current_module_rates
                else 0.0
            )
            report_lines.append(
                f"- {module_name}: Amélioration moyenne de {avg_improvement:+.2f}% (Couverture actuelle moy: {avg_current_module_rate:.2f}%)"
            )
    else:
        report_lines.append(
            "Aucune donnée de package disponible pour l'analyse par module."
        )
    report_lines.append("")

    # Sauvegarder le rapport
    try:
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        logger.info(
            f"Rapport d'évolution de la couverture sauvegardé avec succès : {output_file_path}"
        )
        return True
    except Exception as e:
        logger.error(
            f"Erreur lors de la sauvegarde du rapport d'évolution de la couverture vers {output_file_path}: {e}",
            exc_info=True,
        )
        return False
