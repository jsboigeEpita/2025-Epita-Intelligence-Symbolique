"""Core package for the project.

This package contains the functional core of the application,
including utilities, pipelines, and other essential modules.
It serves as the primary entry point for accessing the project's
core functionalities.
"""

# Imports des composants core (sans dépendance circulaire)
from .shared_state import RhetoricalAnalysisState
from .llm_service import create_llm_service
from .bootstrap import *

# Exports principaux
__all__ = [
    'RhetoricalAnalysisState',
    'create_llm_service'
]

# Import conditionnel pour éviter la dépendance circulaire
def get_argumentation_analyzer():
    """Importe et retourne ArgumentationAnalyzer de manière lazy."""
    from .argumentation_analyzer import ArgumentationAnalyzer
    return ArgumentationAnalyzer

def get_analyzer():
    """Importe et retourne Analyzer de manière lazy."""
    from .argumentation_analyzer import Analyzer
    return Analyzer