"""
Counter-argument generation package.

Provides argument parsing, vulnerability analysis, rhetorical strategy selection,
counter-argument generation (LLM or template), and quality evaluation.

Integrated from student project 2.3.3-generation-contre-argument.
"""

from .counter_agent import CounterArgumentAgent, CounterArgumentPlugin
from .definitions import (
    Argument,
    ArgumentStrength,
    CounterArgument,
    CounterArgumentType,
    EvaluationResult,
    RhetoricalStrategy,
    ValidationResult,
    Vulnerability,
)
from .evaluator import CounterArgumentEvaluator
from .parser import ArgumentParser, VulnerabilityAnalyzer
from .strategies import RhetoricalStrategies

__all__ = [
    "CounterArgumentAgent",
    "CounterArgumentPlugin",
    "ArgumentParser",
    "VulnerabilityAnalyzer",
    "RhetoricalStrategies",
    "CounterArgumentEvaluator",
    "Argument",
    "ArgumentStrength",
    "CounterArgument",
    "CounterArgumentType",
    "EvaluationResult",
    "RhetoricalStrategy",
    "ValidationResult",
    "Vulnerability",
]


def register_with_capability_registry(registry):
    """Register counter-argument capabilities with the Lego registry.

    #1842: this is the module's ONE capability table — the surface
    ``registry_setup.setup_registry`` imports and calls. The routing entry
    is the phase ask (``counter_argument_generation``); parsing,
    vulnerability analysis, strategies and evaluation run inside the agent.
    """
    registry.register_agent(
        name="counter_argument_agent",
        agent_class=CounterArgumentAgent,
        capabilities=["counter_argument_generation"],
        metadata={
            "description": (
                "Generates counter-arguments using 5 rhetorical strategies, "
                "with argument parsing, vulnerability analysis, and quality evaluation."
            ),
        },
    )
