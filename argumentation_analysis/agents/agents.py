import abc
from enum import Enum
import semantic_kernel as sk


class AgentType(Enum):
    """Enumeration of available agent archetypes."""

    INFORMAL_FALLACY = "InformalFallacy"
    SHERLOCK_JTMS = "SherlockJTMS"


class FallacyAgentBase(abc.ABC):
    """Abstract base class for fallacy detection agents."""

    def __init__(self, kernel: sk.Kernel):
        """Initializes the agent with a semantic kernel instance."""
        self._kernel = kernel

    @abc.abstractmethod
    async def analyze_text(self, text: str) -> dict:
        """
        Analyzes a given text for fallacies.

        :param text: The text to analyze.
        :return: A dictionary containing the analysis results.
        """
        pass
