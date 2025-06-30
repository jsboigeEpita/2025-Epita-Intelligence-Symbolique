"""
Package counter_agent pour la génération de contre-arguments.

Ce package fournit un agent capable d'analyser des arguments,
d'identifier leurs vulnérabilités, et de générer des contre-arguments
pertinents en utilisant différentes stratégies rhétoriques.
"""

from counter_agent.agent import (
    CounterArgumentAgent,
    Argument,
    CounterArgument,
    CounterArgumentType,
    ArgumentStrength,
    RhetoricalStrategy,
    Vulnerability,
    EvaluationResult,
    ValidationResult
)

__version__ = "0.1.0"

__all__ = [
    'CounterArgumentAgent',
    'Argument',
    'CounterArgument',
    'CounterArgumentType',
    'ArgumentStrength',
    'RhetoricalStrategy',
    'Vulnerability',
    'EvaluationResult',
    'ValidationResult'
] 