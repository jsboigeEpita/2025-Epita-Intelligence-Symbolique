"""
Module d'intégration avec les LLMs pour la génération de contre-arguments.

Ce module contient les composants pour interagir avec les grands modèles
de langage (LLMs) afin de générer et d'analyser des contre-arguments.
"""

from .prompts import (
    ARGUMENT_ANALYSIS_PROMPT,
    VULNERABILITY_IDENTIFICATION_PROMPT,
    COUNTER_ARGUMENT_GENERATION_PROMPT,
    COUNTER_ARGUMENT_EVALUATION_PROMPT,
    format_prompt,
)
from .llm_generator import LLMGenerator

__all__ = [
    "ARGUMENT_ANALYSIS_PROMPT",
    "VULNERABILITY_IDENTIFICATION_PROMPT",
    "COUNTER_ARGUMENT_GENERATION_PROMPT",
    "COUNTER_ARGUMENT_EVALUATION_PROMPT",
    "format_prompt",
    "LLMGenerator",
]
