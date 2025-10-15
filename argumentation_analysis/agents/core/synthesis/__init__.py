"""
Module de synthèse unifiée pour l'agent de synthèse.

Ce module implémente l'Agent de Synthèse Unifié selon l'architecture progressive
définie dans docs/synthesis_agent_architecture.md. Il unifie les analyses formelles
et informelles en une synthèse cohérente.

Phase 1: SynthesisAgent Core - Coordination basique des agents existants
"""

from .synthesis_agent import SynthesisAgent
from .data_models import LogicAnalysisResult, InformalAnalysisResult, UnifiedReport

__all__ = [
    "SynthesisAgent",
    "LogicAnalysisResult",
    "InformalAnalysisResult",
    "UnifiedReport",
]
