"""
Data structures for counter-argument generation.

Defines argument parsing results, vulnerability analysis, counter-argument
types, rhetorical strategies, and evaluation criteria.

Adapted from 2.3.3-generation-contre-argument/counter_agent/agent/definitions.py.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List


class CounterArgumentType(Enum):
    """Types of counter-arguments."""

    DIRECT_REFUTATION = "direct_refutation"
    COUNTER_EXAMPLE = "counter_example"
    ALTERNATIVE_EXPLANATION = "alternative_explanation"
    PREMISE_CHALLENGE = "premise_challenge"
    REDUCTIO_AD_ABSURDUM = "reductio_ad_absurdum"


class ArgumentStrength(Enum):
    """Argument strength levels.

    ``DECISIVE`` comes from a model's judgment against ``DECISIVE_CRITERION``,
    which the LLM counter-argument prompt carries. The template path's
    ``_assess_strength`` reads word counts and evidence words, which cannot tell
    a decisive counter from a strong one, so it stops at ``STRONG``.
    """

    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    DECISIVE = "decisive"


DECISIVE_CRITERION = (
    'Use "decisive" only when the counter-argument shows the target cannot '
    "stand as stated: a counter-example to a universal claim, or a "
    "contradiction between its premises."
)


class RhetoricalStrategy(Enum):
    """Rhetorical strategies for counter-arguments."""

    SOCRATIC_QUESTIONING = "socratic_questioning"
    REDUCTIO_AD_ABSURDUM = "reductio_ad_absurdum"
    ANALOGICAL_COUNTER = "analogical_counter"
    AUTHORITY_APPEAL = "authority_appeal"
    STATISTICAL_EVIDENCE = "statistical_evidence"


@dataclass
class Argument:
    """Parsed argument structure."""

    content: str
    premises: List[str]
    conclusion: str
    argument_type: str
    confidence: float


@dataclass
class Vulnerability:
    """Vulnerability identified in an argument."""

    type: str
    target: str
    description: str
    score: float
    suggested_counter_type: CounterArgumentType


@dataclass
class CounterArgument:
    """Generated counter-argument."""

    original_argument: Argument
    counter_type: CounterArgumentType
    counter_content: str
    target_component: str
    strength: ArgumentStrength
    confidence: float
    supporting_evidence: List[str] = field(default_factory=list)
    rhetorical_strategy: str = ""


@dataclass
class EvaluationResult:
    """Quality evaluation of a counter-argument."""

    relevance: float
    logical_strength: float
    persuasiveness: float
    originality: float
    clarity: float
    overall_score: float
    recommendations: List[str] = field(default_factory=list)


# ValidationResult was withdrawn (#2137): declared and exported but never
# instantiated anywhere — the production validation verdict is a dict of the
# same shape built by invoke_callables._build_counter_argument_validation
# (the delivered #1180 contract), not this dataclass.
