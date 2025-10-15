#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de test pour l'intégration de l'utilitaire de lazy loading avec l'agent d'analyse informelle.
Ce script vérifie que l'agent peut correctement charger et utiliser la taxonomie des sophismes.
"""

import os
import sys
import json
import logging
from unittest.mock import MagicMock
from pathlib import Path
import pytest  # Ajout pour le marqueur
from unittest.mock import MagicMock
import semantic_kernel as sk

# Ajouter le répertoire racine au path pour pouvoir importer les modules
root_dir = str(Path(__file__).parent.parent.parent)
sys.path.append(root_dir)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("TestInformalIntegration")

# Ajouter le chemin pour l'importation
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.mark.use_real_numpy
def test_informal_integration():
    """
    Teste l'intégration de l'utilitaire de lazy loading avec l'agent d'analyse informelle.
    """
    logger.info("Test de l'intégration avec l'agent d'analyse informelle...")

    try:
        # Importer la classe InformalAnalysisPlugin
        from argumentation_analysis.agents.core.informal.informal_definitions import (
            InformalAnalysisPlugin,
        )

        # Créer une instance de la classe
        logger.info("Création d'une instance de InformalAnalysisPlugin...")
        mock_kernel = MagicMock(spec=sk.Kernel)
        plugin = InformalAnalysisPlugin(kernel=mock_kernel)

        # Explorer la hiérarchie des sophismes à partir de la racine (PK=0)
        logger.info(
            "Exploration de la hiérarchie des sophismes depuis la racine (PK=0)..."
        )
        hierarchy_json = plugin.explore_fallacy_hierarchy("0")

        # Convertir la réponse JSON en dictionnaire Python
        hierarchy = json.loads(hierarchy_json)

        # Vérifier que la réponse ne contient pas d'erreur
        assert (
            "error" not in hierarchy or not hierarchy["error"]
        ), f"Erreur lors de l'exploration de la hiérarchie: {hierarchy.get('error')}"

        # Vérifier que la réponse contient les informations attendues
        assert "current_node" in hierarchy, "La réponse ne contient pas de nœud courant"

        assert "children" in hierarchy, "La réponse ne contient pas d'enfants"

        # Afficher des informations sur la hiérarchie
        current_node = hierarchy["current_node"]
        children = hierarchy["children"]

        logger.info(
            f"Nœud courant: PK={current_node.get('pk')}, Nom={current_node.get('nom_vulgarisé') or current_node.get('text_fr')}"
        )
        logger.info(f"Nombre d'enfants: {len(children)}")

        # Afficher les premiers enfants
        for i, child in enumerate(children[:5]):
            logger.info(
                f"  Enfant {i+1}: PK={child.get('pk')}, Nom={child.get('nom_vulgarisé') or child.get('text_fr')}"
            )

        # Si toutes les assertions passent, le test est réussi.

    except Exception as e:
        logger.error(f"Erreur lors du test d'intégration: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    result = test_informal_integration()
    print(f"\nRésultat du test d'intégration: {'SUCCÈS' if result else 'ÉCHEC'}")
