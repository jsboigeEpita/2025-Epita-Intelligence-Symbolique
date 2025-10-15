# -*- coding: utf-8 -*-
"""
Utilitaires pour la manipulation et l'analyse des données de couverture de test.
"""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional, List  # Ajout de List
import datetime  # Garder l'import original
import json  # Ajout de json

logger = logging.getLogger(__name__)


def parse_coverage_xml(xml_path: Path) -> Optional[Dict[str, Any]]:
    """
    Parse un fichier coverage.xml et extrait les informations de couverture.

    Args:
        xml_path (Path): Chemin vers le fichier coverage.xml.

    Returns:
        Optional[Dict[str, Any]]: Dictionnaire contenant les informations de couverture
                                  (global, lines_valid, lines_covered, packages, timestamp),
                                  ou None en cas d'erreur.
    """
    logger.info(f"Analyse du fichier de couverture XML : {xml_path}")
    if not isinstance(xml_path, Path):
        try:
            xml_path = Path(xml_path)
        except TypeError:
            logger.error(
                f"Le chemin fourni n'est pas valide ou convertible en Path: {xml_path}"
            )
            return None

    if not xml_path.exists() or not xml_path.is_file():
        logger.error(
            f"Le fichier de couverture XML n'existe pas ou n'est pas un fichier : {xml_path}"
        )
        return None

    try:
        tree = ET.parse(str(xml_path))  # ET.parse attend une chaîne ou un objet fichier
        root = tree.getroot()

        # Extraire la couverture globale
        line_rate_str = root.get(
            "line-rate", "0"
        )  # Utiliser .get() pour éviter AttributeError si l'attribut manque
        branch_rate_str = root.get("branch-rate", "0")  # Ajout pour plus de complétude

        line_rate = float(line_rate_str) * 100
        branch_rate = float(branch_rate_str) * 100

        lines_valid = int(root.get("lines-valid", "0"))
        lines_covered = int(root.get("lines-covered", "0"))
        branches_valid = int(root.get("branches-valid", "0"))
        branches_covered = int(root.get("branches-covered", "0"))

        # Extraire la couverture par package
        packages_coverage: Dict[str, Dict[str, float]] = {}  # Type plus précis
        packages_node = root.find("packages")
        if packages_node is not None:
            for package_node in packages_node.findall("package"):
                name = package_node.get("name", "")
                pkg_line_rate_str = package_node.get("line-rate", "0")
                pkg_branch_rate_str = package_node.get("branch-rate", "0")
                if name:  # S'assurer que le nom du package n'est pas vide
                    packages_coverage[name] = {
                        "line_rate": float(pkg_line_rate_str) * 100,
                        "branch_rate": float(pkg_branch_rate_str) * 100,
                    }
        else:
            logger.warning(
                "Aucun noeud 'packages' trouvé dans le fichier XML de couverture."
            )

        coverage_data = {
            "global_line_rate": line_rate,
            "global_branch_rate": branch_rate,
            "lines_valid": lines_valid,
            "lines_covered": lines_covered,
            "branches_valid": branches_valid,
            "branches_covered": branches_covered,
            "packages": packages_coverage,
            "timestamp": datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),  # Format de timestamp plus précis
        }
        logger.info(
            f"Analyse XML de couverture réussie pour {xml_path}. Taux de lignes global: {line_rate:.2f}%"
        )
        return coverage_data
    except ET.ParseError as e_parse:
        logger.error(
            f"Erreur d'analyse XML (ParseError) dans le fichier {xml_path}: {e_parse}",
            exc_info=True,
        )
        return None
    except Exception as e:
        logger.error(
            f"Erreur inattendue lors de l'analyse du fichier XML de couverture {xml_path}: {e}",
            exc_info=True,
        )
        return None


def create_initial_coverage_history(
    coverage_data: Dict[str, Any], history_file_path: Path
) -> bool:
    """
    Crée un fichier d'historique de couverture initial avec les données de couverture actuelles
    et une entrée fictive antérieure pour simuler une progression.

    Args:
        coverage_data (Dict[str, Any]): Dictionnaire des données de couverture actuelles
                                         (tel que retourné par parse_coverage_xml).
        history_file_path (Path): Chemin vers le fichier d'historique JSON à créer.

    Returns:
        bool: True si l'historique a été créé et sauvegardé avec succès, False sinon.
    """
    logger.info(
        f"Création de l'historique de couverture initial dans {history_file_path}"
    )

    if not coverage_data or not isinstance(coverage_data, dict):
        logger.error(
            "Données de couverture invalides ou manquantes pour créer l'historique initial."
        )
        return False

    # Créer une entrée fictive antérieure avec une couverture légèrement inférieure
    # Utiliser datetime.datetime pour la manipulation de dates
    previous_date_dt = datetime.datetime.now() - datetime.timedelta(days=30)
    previous_date_str = previous_date_dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )  # Format plus précis

    previous_coverage = (
        coverage_data.copy()
    )  # Copie profonde pour éviter de modifier l'original si mutable
    previous_coverage["timestamp"] = previous_date_str

    # Réduire légèrement la couverture globale (line_rate)
    current_global_line_rate = previous_coverage.get("global_line_rate", 0.0)
    previous_coverage["global_line_rate"] = max(0.0, current_global_line_rate - 5.0)

    current_lines_covered = previous_coverage.get("lines_covered", 0)
    previous_coverage["lines_covered"] = int(
        current_lines_covered * 0.9
    )  # Réduction de 10%

    # Réduire la couverture de chaque package (line_rate)
    previous_packages_data = previous_coverage.get("packages", {})
    updated_previous_packages: Dict[str, Dict[str, float]] = {}
    if isinstance(previous_packages_data, dict):
        for package_name, package_metrics in previous_packages_data.items():
            if isinstance(package_metrics, dict):
                current_pkg_line_rate = package_metrics.get("line_rate", 0.0)
                updated_previous_packages[package_name] = {
                    "line_rate": max(0.0, current_pkg_line_rate - 5.0),
                    "branch_rate": package_metrics.get(
                        "branch_rate", 0.0
                    ),  # Conserver branch_rate
                }
            elif isinstance(package_metrics, (int, float)):  # Ancien format possible
                updated_previous_packages[package_name] = {
                    "line_rate": max(0.0, float(package_metrics) - 5.0)
                }
    previous_coverage["packages"] = updated_previous_packages

    # Créer l'historique avec les deux entrées
    history_entries = [previous_coverage, coverage_data]

    # Sauvegarder l'historique
    try:
        history_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(history_file_path, "w", encoding="utf-8") as f:
            json.dump(history_entries, f, indent=2)
        logger.info(
            f"Historique de couverture initialisé et sauvegardé dans {history_file_path}"
        )
        return True
    except Exception as e:
        logger.error(
            f"Erreur lors de la sauvegarde du fichier d'historique initial {history_file_path}: {e}",
            exc_info=True,
        )
        return False


def save_coverage_history(
    coverage_data: Dict[str, Any], history_file_path: Path
) -> bool:
    """
    Sauvegarde (ou ajoute à) les données de couverture dans un fichier d'historique JSON.

    Args:
        coverage_data (Dict[str, Any]): Nouvelles données de couverture à ajouter.
        history_file_path (Path): Chemin vers le fichier d'historique JSON.

    Returns:
        bool: True si la sauvegarde a réussi, False sinon.
    """
    logger.info(
        f"Sauvegarde des données de couverture dans l'historique : {history_file_path}"
    )
    history_entries: List[Dict[str, Any]] = []  # Nécessite List from typing

    if not isinstance(coverage_data, dict) or not coverage_data:
        logger.error("Aucune donnée de couverture fournie pour la sauvegarde.")
        return False

    # Charger l'historique existant s'il existe
    if history_file_path.exists():
        try:
            with open(history_file_path, "r", encoding="utf-8") as f:
                history_entries = json.load(f)  # Nécessite json import
            if not isinstance(history_entries, list):
                logger.warning(
                    f"Le fichier d'historique {history_file_path} ne contenait pas une liste. Il sera écrasé."
                )
                history_entries = []
        except json.JSONDecodeError as e_json:
            logger.warning(
                f"Erreur de décodage JSON en lisant l'historique {history_file_path}: {e_json}. Le fichier sera écrasé."
            )
            history_entries = []
        except Exception as e_read:
            logger.error(
                f"Erreur inattendue en lisant l'historique {history_file_path}: {e_read}. Tentative d'écrasement.",
                exc_info=True,
            )
            history_entries = []

    # Ajouter les nouvelles données
    if "timestamp" not in coverage_data:  # S'assurer que le timestamp est présent
        coverage_data["timestamp"] = datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        logger.debug(
            f"Timestamp ajouté aux données de couverture: {coverage_data['timestamp']}"
        )

    history_entries.append(coverage_data)

    # Sauvegarder l'historique mis à jour
    try:
        history_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(history_file_path, "w", encoding="utf-8") as f:
            json.dump(history_entries, f, indent=2)
        logger.info(
            f"Historique de couverture sauvegardé avec succès dans {history_file_path} ({len(history_entries)} entrées)."
        )
        return True
    except Exception as e_write:
        logger.error(
            f"Erreur lors de la sauvegarde du fichier d'historique {history_file_path}: {e_write}",
            exc_info=True,
        )
        return False


# D'autres fonctions liées à la couverture (historique, etc.) iront ici.
