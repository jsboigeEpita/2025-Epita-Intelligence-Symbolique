"""
Module de redirection pour maintenir la compatibilité avec le code existant.

Ce module importe et expose les éléments du module agents.core.extract
pour permettre aux importations de la forme 'from argumentiation_analysis.agents.extract import X'
de fonctionner correctement.
"""

try:
    from argumentiation_analysis.agents.core.extract.extract_agent import *
    from argumentiation_analysis.agents.core.extract.extract_definitions import *
    from argumentiation_analysis.agents.core.extract.prompts import *
    
    # Exposer explicitement le module extract_agent pour les importations de la forme:
    # from argumentiation_analysis.agents.extract import extract_agent
    import argumentiation_analysis.agents.core.extract.extract_agent as extract_agent
except ImportError as e:
    import logging
    logging.warning(f"Erreur lors de l'importation depuis agents.core.extract: {e}")