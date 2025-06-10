"""Core package for the project.

This package contains the functional core of the application,
including utilities, pipelines, and other essential modules.
It serves as the primary entry point for accessing the project's
core functionalities.
"""

# Import principal pour l'analyse d'argumentation
from .argumentation_analyzer import ArgumentationAnalyzer, Analyzer

# Imports des autres composants core
from .shared_state import RhetoricalAnalysisState
from .llm_service import create_llm_service
from .bootstrap import *

# Exports principaux
__all__ = [
    'ArgumentationAnalyzer',
    'Analyzer',
    'RhetoricalAnalysisState',
    'create_llm_service'
]