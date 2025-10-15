"""
Module d'agent de génération de contre-arguments.

Ce module fournit les composants pour analyser des arguments et
générer des contre-arguments pertinents.
"""

from .definitions import (
    Argument,
    CounterArgument,
    CounterArgumentType,
    ArgumentStrength,
    RhetoricalStrategy,
    Vulnerability,
    EvaluationResult,
    ValidationResult,
)
from .counter_agent import CounterArgumentAgent
from .parser import ArgumentParser, VulnerabilityAnalyzer
from .strategies import RhetoricalStrategies

__all__ = [
    "Argument",
    "CounterArgument",
    "CounterArgumentType",
    "ArgumentStrength",
    "RhetoricalStrategy",
    "Vulnerability",
    "EvaluationResult",
    "ValidationResult",
    "CounterArgumentAgent",
    "ArgumentParser",
    "VulnerabilityAnalyzer",
    "RhetoricalStrategies",
]
