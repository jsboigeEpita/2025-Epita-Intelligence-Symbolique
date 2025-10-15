# -*- coding: utf-8 -*-
"""
Utilitaires liés à la structure du projet, au mappage de modules/packages, etc.
Principalement pour les outils de développement et de reporting.
"""

import logging
from typing import Dict, Optional  # Ajouté pour le typage

logger = logging.getLogger(__name__)

# Ce mapping pourrait être externalisé ou rendu plus configurable si nécessaire.
DEFAULT_PACKAGE_TO_MODULE_MAPPING: Dict[str, str] = {
    # 'project_core.utils': 'Project Core Utilities', # Supprimé
    # 'project_core.dev_utils': 'Project Core Dev Utilities', # Supprimé
    # 'project_core.service_setup': 'Project Core Service Setup', # Supprimé
    # 'project_core.pipelines': 'Project Core Pipelines', # Supprimé
    "argumentation_analysis.utils": "Argumentation Analysis Utilities",
    "argumentation_analysis.analytics": "Argumentation Analysis Analytics",
    "argumentation_analysis.mocks": "Argumentation Analysis Mocks",
    "argumentation_analysis.agents": "Argumentation Agents",
    "argumentation_analysis.services": "Argumentation Services",
    "argumentation_analysis.pipelines": "Argumentation Pipelines",
    "argumentation_analysis.nlp": "Argumentation NLP Components",
    "argumentation_analysis.ui": "Argumentation UI Components",
    "scripts.execution": "Scripts - Execution",
    "scripts.reporting": "Scripts - Reporting",
    "scripts.data_processing": "Scripts - Data Processing",
    "scripts.maintenance": "Scripts - Maintenance",
    "scripts.setup": "Scripts - Setup",
    "scripts.utils": "Scripts - Utilities (Legacy)",  # Marquer comme legacy si pertinent
    "tests.unit": "Tests - Unit",
    "tests.functional": "Tests - Functional",
    "tests.integration": "Tests - Integration",
    "tests.environment_checks": "Tests - Environment Checks",
    "core.communication": "Legacy Core Communication",  # Exemple de renommage pour clarté
    "core": "Legacy Core (General)",
    "agents.core.extract": "Legacy Agents Extraction",
    "agents.core.informal": "Legacy Agents Informal Analysis",
    "agents.tools.analysis": "Legacy Analysis Tools",
    ".": "Global/Non-Specific",  # Pour la racine ou les packages non clairement identifiés
    "": "Global/Non-Specific",  # Pour le cas où le nom du package est vide
}


def map_package_to_module(
    package_name: str, custom_mapping: Optional[Dict[str, str]] = None
) -> str:
    """
    Mappe un nom de package (tel que trouvé dans coverage.xml) à un nom de module
    plus lisible ou conceptuel pour les rapports.

    La fonction essaie de trouver la correspondance la plus spécifique en premier.
    Si aucune correspondance exacte n'est trouvée, elle tente des correspondances partielles.

    Args:
        package_name (str): Nom du package (par exemple, 'project_core.utils.file_utils').
        custom_mapping (Optional[Dict[str, str]]): Un dictionnaire de mappage personnalisé
                                                    qui peut surcharger ou étendre le mappage par défaut.
                                                    Les clés sont les noms de package, les valeurs les noms de module.

    Returns:
        str: Nom du module correspondant, ou 'Autre' si aucun mappage n'est trouvé.
    """
    if not package_name:  # Gérer le cas d'un nom de package vide
        return DEFAULT_PACKAGE_TO_MODULE_MAPPING.get("", "Autre")

    current_mapping = DEFAULT_PACKAGE_TO_MODULE_MAPPING.copy()
    if custom_mapping:
        current_mapping.update(custom_mapping)

    # Essayer une correspondance exacte d'abord
    if package_name in current_mapping:
        return current_mapping[package_name]

    # Essayer des correspondances partielles (du plus spécifique au plus général)
    # Trier les clés du mapping par longueur décroissante pour trouver la plus spécifique d'abord
    sorted_mapping_keys = sorted(current_mapping.keys(), key=len, reverse=True)

    for key in sorted_mapping_keys:
        if (
            key == "." and package_name == "."
        ):  # Cas spécial pour le package racine parfois noté '.'
            return current_mapping[key]
        if key != "." and package_name.startswith(
            key
        ):  # Vérifier si le nom du package commence par une clé de mapping
            return current_mapping[key]

    logger.debug(
        f"Aucun mappage de module trouvé pour le package '{package_name}'. Retour de 'Autre'."
    )
    return "Autre"
