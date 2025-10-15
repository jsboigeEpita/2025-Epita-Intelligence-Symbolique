# -*- coding: utf-8 -*-
"""
Utilitaires pour la génération de visualisations spécifiques aux outils de développement,
comme les graphiques de couverture de test.
"""

import logging
import json
import os
from pathlib import Path  # Ajout pour le typage
from typing import Dict, List, Any  # Ajout pour le typage

import matplotlib.pyplot as plt
import numpy as np

# import pandas as pd # Pas utilisé directement dans les fonctions déplacées ici

# Importation de la fonction de mapping depuis son nouvel emplacement
from .project_structure_utils import map_package_to_module

logger = logging.getLogger(__name__)

# Définir les couleurs pour les différents modules (peut être partagé ou configurable)
# Ce dictionnaire COLORS est utilisé par les fonctions ci-dessous.
# Il pourrait être passé en argument ou importé d'un module de configuration.
DEFAULT_MODULE_COLORS: Dict[str, str] = {
    "Communication": "#1f77b4",
    "Gestion d'État": "#ff7f0e",
    "Agents d'Extraction": "#2ca02c",
    "Agents d'Analyse Informelle": "#d62728",
    "Outils d'Analyse": "#9467bd",
    "Global": "#8c564b",
    "Project Core Utilities": "#e377c2",  # rose
    "Project Core Dev Utilities": "#7f7f7f",  # gris moyen
    "Argumentation Analysis Utilities": "#bcbd22",  # olive
    "Argumentation Analysis Analytics": "#17becf",  # cyan
    "Autre": "#aec7e8",  # bleu clair pour fallback
}


def generate_coverage_trend_chart(
    history_file_path: Path, output_dir_path: Path, module_colors: Dict[str, str] = None
) -> bool:
    """
    Génère un graphique montrant l'évolution de la couverture des tests au fil du temps.
    """
    logger.info(
        f"Génération du graphique d'évolution de la couverture depuis {history_file_path} vers {output_dir_path}"
    )
    if module_colors is None:
        module_colors = DEFAULT_MODULE_COLORS

    if not history_file_path.exists():
        logger.error(f"Le fichier d'historique {history_file_path} n'existe pas.")
        return False

    try:
        with open(history_file_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception as e:
        logger.error(
            f"Erreur lors de la lecture du fichier d'historique {history_file_path}: {e}",
            exc_info=True,
        )
        return False

    if not history or not isinstance(history, list):
        logger.warning(
            f"L'historique dans {history_file_path} est vide ou n'est pas une liste. Graphique non généré."
        )
        return False

    # Préparer les données pour le graphique
    dates = [
        entry.get("timestamp", "").split(" ")[0] for entry in history
    ]  # Prendre seulement la date YYYY-MM-DD

    # S'assurer que toutes les entrées ont les clés attendues pour la couverture globale
    global_coverage_raw = [
        entry.get("global_line_rate", entry.get("global")) for entry in history
    ]
    if any(gc is None for gc in global_coverage_raw):
        logger.warning(
            f"Données de couverture globale manquantes dans certaines entrées de {history_file_path}. Graphique partiel ou incorrect possible."
        )
        # Filtrer les None pour éviter les erreurs de plot, mais cela peut fausser le graphique
        valid_entries_for_global = [
            (d, gc) for d, gc in zip(dates, global_coverage_raw) if gc is not None
        ]
        if not valid_entries_for_global:
            logger.error(
                "Aucune donnée de couverture globale valide trouvée. Graphique non généré."
            )
            return False
        dates_global, global_coverage = zip(*valid_entries_for_global)
    else:
        dates_global, global_coverage = dates, [float(gc) for gc in global_coverage_raw]

    # Créer un DataFrame pour les modules
    module_data: Dict[str, List[float]] = {}
    all_modules_found = set()

    for entry in history:
        packages = entry.get("packages", {})
        if isinstance(packages, dict):
            for package_name, package_info in packages.items():
                module_name = map_package_to_module(package_name)
                all_modules_found.add(module_name)
                # Extraire line_rate, compatible avec ancien et nouveau format de coverage_data
                line_rate = 0.0
                if isinstance(
                    package_info, dict
                ):  # Nouveau format avec dict de métriques
                    line_rate = package_info.get("line_rate", 0.0)
                elif isinstance(
                    package_info, (int, float)
                ):  # Ancien format avec float direct
                    line_rate = float(package_info)

                module_data.setdefault(module_name, [0.0] * len(history))[
                    dates.index(entry.get("timestamp", "").split(" ")[0])
                ] = line_rate

    # S'assurer que tous les modules ont une liste de la bonne longueur
    for module_name_iter in all_modules_found:
        if module_name_iter not in module_data:  # Devrait déjà y être via setdefault
            module_data[module_name_iter] = [0.0] * len(history)
        elif len(module_data[module_name_iter]) != len(history):
            # Tenter de corriger si une entrée manquait pour un module à un certain timestamp
            # Ceci est une heuristique, une structure de données plus robuste serait mieux.
            temp_list = [0.0] * len(history)
            for i, date_str in enumerate(dates):
                # Trouver l'entrée correspondante dans l'historique
                matching_entry = next(
                    (
                        e
                        for e in history
                        if e.get("timestamp", "").split(" ")[0] == date_str
                    ),
                    None,
                )
                if matching_entry:
                    pkg_info_for_module = next(
                        (
                            pi
                            for pn, pi in matching_entry.get("packages", {}).items()
                            if map_package_to_module(pn) == module_name_iter
                        ),
                        None,
                    )
                    if pkg_info_for_module:
                        if isinstance(pkg_info_for_module, dict):
                            temp_list[i] = pkg_info_for_module.get("line_rate", 0.0)
                        elif isinstance(pkg_info_for_module, (int, float)):
                            temp_list[i] = float(pkg_info_for_module)
            module_data[module_name_iter] = temp_list

    plt.figure(figsize=(14, 8))
    plt.plot(
        dates_global,
        global_coverage,
        marker="o",
        linewidth=3,
        color=module_colors.get("Global", "#8c564b"),
        label="Couverture Globale (Lignes)",
    )

    for module_name_plot, coverages_plot in sorted(module_data.items()):
        if len(coverages_plot) == len(
            dates
        ):  # S'assurer que les données correspondent aux dates
            plt.plot(
                dates,
                coverages_plot,
                marker="s",
                linewidth=2,
                color=module_colors.get(module_name_plot, "#333333"),
                label=module_name_plot,
            )

    plt.axhline(y=80, color="r", linestyle="--", label="Objectif (80%)")
    plt.title(
        "Évolution de la Couverture des Tests (Lignes) au Fil du Temps", fontsize=16
    )
    plt.xlabel("Date", fontsize=12)
    plt.ylabel("Couverture (%)", fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout(rect=[0, 0, 0.85, 1])  # Ajuster pour la légende externe

    output_dir_path.mkdir(parents=True, exist_ok=True)
    output_file = output_dir_path / "coverage_trend.png"
    try:
        plt.savefig(output_file, dpi=300)
        logger.info(
            f"Graphique d'évolution de la couverture sauvegardé dans {output_file}"
        )
    except Exception as e_save:
        logger.error(
            f"Erreur lors de la sauvegarde du graphique {output_file}: {e_save}",
            exc_info=True,
        )
        plt.close()  # S'assurer de fermer la figure en cas d'erreur de sauvegarde
        return False
    finally:
        plt.close()  # Toujours fermer la figure
    return True


def generate_module_comparison_chart(
    history_file_path: Path, output_dir_path: Path, module_colors: Dict[str, str] = None
) -> bool:
    """
    Génère un graphique comparant la couverture des différents modules pour la dernière entrée de l'historique.
    """
    logger.info(
        f"Génération du graphique de comparaison des modules depuis {history_file_path} vers {output_dir_path}"
    )
    if module_colors is None:
        module_colors = DEFAULT_MODULE_COLORS

    if not history_file_path.exists():
        logger.error(f"Le fichier d'historique {history_file_path} n'existe pas.")
        return False

    try:
        with open(history_file_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception as e:
        logger.error(
            f"Erreur lors de la lecture du fichier d'historique {history_file_path}: {e}",
            exc_info=True,
        )
        return False

    if not history or not isinstance(history, list):
        logger.warning(
            f"L'historique dans {history_file_path} est vide ou n'est pas une liste. Graphique non généré."
        )
        return False

    latest_entry = history[-1]
    packages = latest_entry.get("packages", {})
    if not isinstance(packages, dict):
        logger.warning(
            f"Données de 'packages' invalides dans la dernière entrée de {history_file_path}. Graphique non généré."
        )
        return False

    module_avg_coverage: Dict[str, float] = {}
    module_package_counts: Dict[str, int] = {}

    for package_name, package_info in packages.items():
        module_name = map_package_to_module(package_name)
        line_rate = 0.0
        if isinstance(package_info, dict):
            line_rate = package_info.get("line_rate", 0.0)
        elif isinstance(package_info, (int, float)):
            line_rate = float(package_info)

        module_avg_coverage[module_name] = (
            module_avg_coverage.get(module_name, 0.0) + line_rate
        )
        module_package_counts[module_name] = (
            module_package_counts.get(module_name, 0) + 1
        )

    for module_name_calc in module_avg_coverage:
        if module_package_counts[module_name_calc] > 0:
            module_avg_coverage[module_name_calc] /= module_package_counts[
                module_name_calc
            ]

    if not module_avg_coverage:
        logger.info("Aucune donnée de couverture par module à visualiser.")
        return False

    sorted_modules = sorted(module_avg_coverage.items(), key=lambda item: item[1])
    modules_sorted_names = [item[0] for item in sorted_modules]
    coverages_sorted_values = [item[1] for item in sorted_modules]

    colors = [module_colors.get(module, "#333333") for module in modules_sorted_names]

    plt.figure(
        figsize=(10, max(6, len(modules_sorted_names) * 0.5))
    )  # Ajuster la hauteur dynamiquement
    bars = plt.barh(modules_sorted_names, coverages_sorted_values, color=colors)

    for bar_item in bars:
        width = bar_item.get_width()
        plt.text(
            width + 1,
            bar_item.get_y() + bar_item.get_height() / 2,
            f"{width:.1f}%",
            ha="left",
            va="center",
            fontsize=9,
        )

    plt.axvline(x=80, color="r", linestyle="--", label="Objectif (80%)")
    plt.title(
        "Comparaison de la Couverture des Tests (Lignes) par Module (Dernière Mesure)",
        fontsize=14,
    )
    plt.xlabel("Couverture (%)", fontsize=12)
    plt.ylabel("Module", fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.6, axis="x")
    plt.legend()
    plt.tight_layout()

    output_dir_path.mkdir(parents=True, exist_ok=True)
    output_file = output_dir_path / "module_comparison.png"
    try:
        plt.savefig(output_file, dpi=300)
        logger.info(
            f"Graphique de comparaison des modules sauvegardé dans {output_file}"
        )
    except Exception as e_save:
        logger.error(
            f"Erreur lors de la sauvegarde du graphique {output_file}: {e_save}",
            exc_info=True,
        )
        plt.close()
        return False
    finally:
        plt.close()
    return True


def generate_coverage_improvement_chart(
    history_file_path: Path, output_dir_path: Path, module_colors: Dict[str, str] = None
) -> bool:
    """
    Génère un graphique montrant l'amélioration de la couverture des tests par module
    entre la première et la dernière entrée de l'historique.
    """
    logger.info(
        f"Génération du graphique d'amélioration de la couverture depuis {history_file_path} vers {output_dir_path}"
    )
    if module_colors is None:
        module_colors = DEFAULT_MODULE_COLORS

    if not history_file_path.exists():
        logger.error(f"Le fichier d'historique {history_file_path} n'existe pas.")
        return False

    try:
        with open(history_file_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception as e:
        logger.error(
            f"Erreur lors de la lecture du fichier d'historique {history_file_path}: {e}",
            exc_info=True,
        )
        return False

    if not isinstance(history, list) or len(history) < 2:
        logger.warning(
            f"L'historique dans {history_file_path} doit être une liste avec au moins deux entrées. Graphique non généré."
        )
        return False

    first_entry = history[0]
    last_entry = history[-1]

    first_packages = first_entry.get("packages", {})
    last_packages = last_entry.get("packages", {})

    if not isinstance(first_packages, dict) or not isinstance(last_packages, dict):
        logger.warning(
            "Données de 'packages' invalides dans les entrées d'historique. Graphique non généré."
        )
        return False

    all_package_names = set(first_packages.keys()) | set(last_packages.keys())
    module_improvements_agg: Dict[str, List[float]] = {}

    for package_name in all_package_names:
        module_name = map_package_to_module(package_name)

        initial_rate = 0.0
        first_pkg_info = first_packages.get(package_name)
        if isinstance(first_pkg_info, dict):
            initial_rate = first_pkg_info.get("line_rate", 0.0)
        elif isinstance(first_pkg_info, (int, float)):
            initial_rate = float(first_pkg_info)

        current_rate = 0.0
        last_pkg_info = last_packages.get(package_name)
        if isinstance(last_pkg_info, dict):
            current_rate = last_pkg_info.get("line_rate", 0.0)
        elif isinstance(last_pkg_info, (int, float)):
            current_rate = float(last_pkg_info)

        module_improvements_agg.setdefault(module_name, []).append(
            current_rate - initial_rate
        )

    avg_improvements: Dict[str, float] = {}
    for module_name_calc, improvements_list in module_improvements_agg.items():
        if improvements_list:
            avg_improvements[module_name_calc] = sum(improvements_list) / len(
                improvements_list
            )

    if not avg_improvements:
        logger.info(
            "Aucune donnée d'amélioration de couverture par module à visualiser."
        )
        return False

    sorted_modules = sorted(avg_improvements.items(), key=lambda item: item[1])
    modules_sorted_names = [item[0] for item in sorted_modules]
    improvements_sorted_values = [item[1] for item in sorted_modules]

    colors = [module_colors.get(module, "#333333") for module in modules_sorted_names]

    plt.figure(figsize=(10, max(6, len(modules_sorted_names) * 0.5)))
    bars = plt.barh(modules_sorted_names, improvements_sorted_values, color=colors)

    for bar_item in bars:
        width = bar_item.get_width()
        plt.text(
            width + (0.5 if width >= 0 else -0.5),
            bar_item.get_y() + bar_item.get_height() / 2,
            f"{width:+.1f}%",
            ha="left" if width >= 0 else "right",
            va="center",
            fontsize=9,
        )

    plt.title(
        "Amélioration de la Couverture des Tests (Lignes) par Module (Comparaison Premier/Dernier)",
        fontsize=14,
    )
    plt.xlabel("Amélioration (%)", fontsize=12)
    plt.ylabel("Module", fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.6, axis="x")
    plt.axvline(x=0, color="k", linestyle="-", linewidth=0.8)
    plt.tight_layout()

    output_dir_path.mkdir(parents=True, exist_ok=True)
    output_file = output_dir_path / "coverage_improvement.png"
    try:
        plt.savefig(output_file, dpi=300)
        logger.info(
            f"Graphique d'amélioration de la couverture sauvegardé dans {output_file}"
        )
    except Exception as e_save:
        logger.error(
            f"Erreur lors de la sauvegarde du graphique {output_file}: {e_save}",
            exc_info=True,
        )
        plt.close()
        return False
    finally:
        plt.close()
    return True
