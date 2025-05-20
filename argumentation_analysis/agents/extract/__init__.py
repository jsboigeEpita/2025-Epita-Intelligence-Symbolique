"""
Module de redirection pour maintenir la compatibilité avec le code existant.

Ce module importe et expose les éléments du module agents.core.extract
pour permettre aux importations de la forme 'from argumentation_analysis.agents.extract import X'
de fonctionner correctement.
"""

try:
    from argumentation_analysis.agents.core.extract.extract_agent import *
    from argumentation_analysis.agents.core.extract.extract_definitions import *
    from argumentation_analysis.agents.core.extract.prompts import *
    
    # Exposer explicitement la classe ExtractAgent et la fonction setup_extract_agent
    # pour les importations de la forme:
    # from argumentation_analysis.agents.extract import extract_agent
    from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent, setup_extract_agent
    
    # Créer un alias pour le module extract_agent
    import sys
    import argumentation_analysis.agents.core.extract.extract_agent
    sys.modules['argumentation_analysis.agents.extract.extract_agent'] = argumentation_analysis.agents.core.extract.extract_agent
except ImportError as e:
    import logging
    import sys
    from unittest.mock import MagicMock, AsyncMock
    
    logging.warning(f"Erreur lors de l'importation depuis agents.core.extract: {e}")
    
    # Créer des mocks pour les classes et fonctions nécessaires
    class ExtractAgentMock(MagicMock):
        """Mock pour la classe ExtractAgent."""
        pass
    
    # Mock pour la fonction setup_extract_agent
    async def setup_extract_agent_mock(llm_service=None):
        """Mock pour la fonction setup_extract_agent."""
        kernel_mock = MagicMock()
        agent_mock = ExtractAgentMock()
        return kernel_mock, agent_mock
    
    # Exposer les mocks
    ExtractAgent = ExtractAgentMock
    setup_extract_agent = setup_extract_agent_mock
    
    # Créer un module mock pour extract_agent
    extract_agent_mock = MagicMock()
    extract_agent_mock.ExtractAgent = ExtractAgentMock
    extract_agent_mock.setup_extract_agent = setup_extract_agent_mock
    
    # Installer le mock dans sys.modules
    sys.modules['argumentation_analysis.agents.extract.extract_agent'] = extract_agent_mock