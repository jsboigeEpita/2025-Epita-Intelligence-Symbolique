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

    # Exposer la classe ExtractAgent et le module `extract_agent` sous les trois
    # formes d'accès : attribut de package, `import ...extract.extract_agent`, et
    # `from ...extract import extract_agent`. Le commentaire d'origine annonçait
    # une fonction `setup_extract_agent` qui n'a jamais existé (#2122).
    from ..core.extract.extract_agent import ExtractAgent

    import sys

    from ..core.extract import extract_agent as extract_agent

    # `sys.modules` couvre les deux formes d'import ; l'attribut de package
    # couvre `pkg.extract_agent`, que la seule entrée `sys.modules` ne pose pas
    # (c'est le machinery d'import qui pose l'attribut, pas cette affectation).
    sys.modules["argumentation_analysis.agents.extract.extract_agent"] = extract_agent
except ImportError as e:
    import logging

    logger = logging.getLogger(__name__)
    logger.error(f"ERREUR RÉELLE D'IMPORT (mocks éliminés Phase 2): {e}")
    logger.error("Corrigez le problème d'import au lieu d'utiliser des mocks")
    # AUCUN MOCK - on laisse l'erreur se propager pour forcer la correction
    raise ImportError(f"Import ExtractAgent échoué - corrigez le problème: {e}") from e
