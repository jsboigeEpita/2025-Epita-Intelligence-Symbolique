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
    
    # Exposer explicitement le module extract_agent pour les importations de la forme:
    # from argumentation_analysis.agents.extract import extract_agent
    import argumentation_analysis.agents.core.extract.extract_agent as extract_agent
except ImportError as e:
    import logging
    logging.warning(f"Erreur lors de l'importation depuis agents.core.extract: {e}")