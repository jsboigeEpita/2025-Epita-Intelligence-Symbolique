"""
Définitions pour l'agent de génération de contre-arguments.

Ce module contient les définitions des structures de données
utilisées par l'agent de génération de contre-arguments.
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Any


class CounterArgumentType(Enum):
    """Types de contre-arguments possibles."""

    DIRECT_REFUTATION = "direct_refutation"
    COUNTER_EXAMPLE = "counter_example"
    ALTERNATIVE_EXPLANATION = "alternative_explanation"
    PREMISE_CHALLENGE = "premise_challenge"
    REDUCTIO_AD_ABSURDUM = "reductio_ad_absurdum"


class ArgumentStrength(Enum):
    """Force d'un argument."""

    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    DECISIVE = "decisive"


class RhetoricalStrategy(Enum):
    """Stratégies rhétoriques pour les contre-arguments."""

    SOCRATIC_QUESTIONING = "socratic_questioning"
    REDUCTIO_AD_ABSURDUM = "reductio_ad_absurdum"
    ANALOGICAL_COUNTER = "analogical_counter"
    AUTHORITY_APPEAL = "authority_appeal"
    STATISTICAL_EVIDENCE = "statistical_evidence"


@dataclass
class Argument:
    """Structure représentant un argument."""

    content: str
    premises: List[str]
    conclusion: str
    argument_type: str
    confidence: float


@dataclass
class Vulnerability:
    """Structure représentant une vulnérabilité dans un argument."""

    type: str
    target: str
    description: str
    score: float
    suggested_counter_type: CounterArgumentType


@dataclass
class CounterArgument:
    """Structure représentant un contre-argument."""

    original_argument: Argument
    counter_type: CounterArgumentType
    counter_content: str
    target_component: str
    strength: ArgumentStrength
    confidence: float
    supporting_evidence: List[str]
    rhetorical_strategy: str


@dataclass
class EvaluationResult:
    """Résultat de l'évaluation d'un contre-argument."""

    relevance: float
    logical_strength: float
    persuasiveness: float
    originality: float
    clarity: float
    overall_score: float
    recommendations: List[str]


@dataclass
class ValidationResult:
    """Résultat de la validation logique d'un contre-argument."""

    is_valid_attack: bool
    original_survives: bool
    counter_succeeds: bool
    logical_consistency: bool
    formal_representation: Optional[str] = None
