"""
Module de redirection pour maintenir la compatibilité avec le code existant.

Ce module importe et expose les éléments du module agents.core.extract
pour permettre aux importations de la forme 'from argumentation_analysis.agents.extract import X'
de fonctionner correctement.
"""

try:
    # Utiliser des imports relatifs pour éviter les problèmes d'initialisation circulaire
    from ..core.extract.extract_agent import *
    from ..core.extract.extract_definitions import *
    from ..core.extract.prompts import *

    # Exposer explicitement la classe ExtractAgent et la fonction setup_extract_agent
    # pour les importations de la forme:
    # from argumentation_analysis.agents.extract import extract_agent
    from ..core.extract.extract_agent import ExtractAgent

    # Créer un alias pour le module extract_agent
    import sys

    # Importer le module directement par son chemin relatif
    from ..core.extract import extract_agent as core_extract_agent_module

    sys.modules[
        "argumentation_analysis.agents.extract.extract_agent"
    ] = core_extract_agent_module
except ImportError as e:
    import logging

    logger = logging.getLogger(__name__)
    logger.error(f"ERREUR RÉELLE D'IMPORT (mocks éliminés Phase 2): {e}")
    logger.error("Corrigez le problème d'import au lieu d'utiliser des mocks")
    # AUCUN MOCK - on laisse l'erreur se propager pour forcer la correction
    raise ImportError(f"Import ExtractAgent échoué - corrigez le problème: {e}") from e
