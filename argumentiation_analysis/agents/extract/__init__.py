"""
Module d'agent d'extraction pour l'analyse argumentative.

Ce module fournit un agent capable d'extraire et de proposer des extraits pertinents
dans un texte source en se basant sur la dénomination de l'extrait et le contexte.
"""

from .extract_agent import ExtractAgent, setup_extract_agent
from .extract_definitions import ExtractAgentPlugin, ExtractResult

__all__ = [
    'ExtractAgent',
    'setup_extract_agent',
    'ExtractAgentPlugin',
    'ExtractResult'
]