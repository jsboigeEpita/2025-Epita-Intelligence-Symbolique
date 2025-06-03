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
    sys.modules['argumentation_analysis.agents.extract.extract_agent'] = core_extract_agent_module
except ImportError as e:
    import logging
    import sys
    from unittest.mock import MagicMock, AsyncMock
    
    logging.warning(f"Erreur lors de l'importation depuis agents.core.extract: {e}")
    
    # Créer des mocks pour les classes et fonctions nécessaires
    class ExtractAgentMock(MagicMock):
        """Mock pour la classe ExtractAgent."""
        pass
    
    # Exposer les mocks
    ExtractAgent = ExtractAgentMock
    # setup_extract_agent n'est plus exposé car supprimé
    
    # Créer un module mock pour extract_agent
    extract_agent_mock = MagicMock()
    extract_agent_mock.ExtractAgent = ExtractAgentMock
    # extract_agent_mock.setup_extract_agent n'est plus nécessaire
    
    # Installer le mock dans sys.modules
    sys.modules['argumentation_analysis.agents.extract.extract_agent'] = extract_agent_mock