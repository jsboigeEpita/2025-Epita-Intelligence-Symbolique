"""
Turn protocol for multi-turn conversational pipelines.

Defines the data structures and abstract base class for composable
turn strategies. Any execution mechanism (WorkflowExecutor, AgentGroupChat,
sequential, hierarchical) can be plugged in as a TurnStrategy.

Usage:
    from argumentation_analysis.orchestration.turn_protocol import (
        TurnResult, ConversationConfig, TurnStrategy,
    )
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from argumentation_analysis.orchestration.workflow_dsl import PhaseResult, PhaseStatus

logger = logging.getLogger("TurnProtocol")


@dataclass
class TurnResult:
    """Result of a single conversational turn."""

    turn_number: int
    phase_results: Dict[str, PhaseResult]
    confidence: float
    needs_refinement: bool
    questions_for_user: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    summary: Optional[str] = None

    def is_converged(self) -> bool:
        """True when all non-optional phases completed and confidence is high."""
        all_completed = all(
            r.status in (PhaseStatus.COMPLETED, PhaseStatus.SKIPPED)
            for r in self.phase_results.values()
        )
        return all_completed and not self.needs_refinement

    def get_output(self, phase_name: str) -> Any:
        """Get the output of a specific phase, or None if absent."""
        result = self.phase_results.get(phase_name)
        if result is not None:
            return result.output
        return None


@dataclass
class ConversationConfig:
    """Configuration for multi-turn execution."""

    max_rounds: int = 3
    convergence_fn: Optional[Callable[["TurnResult", "TurnResult"], bool]] = None
    confidence_threshold: float = 0.8
    timeout_per_round_seconds: Optional[float] = None


class TurnStrategy(ABC):
    """
    Abstract base for per-turn execution strategy.

    Implementations wrap a specific execution mechanism (workflow DAG,
    AgentGroupChat, sequential agents, etc.) and produce a TurnResult.
    """

    @abstractmethod
    async def execute_turn(
        self,
        input_data: Any,
        context: Dict[str, Any],
        state: Optional[Any] = None,
    ) -> TurnResult:
        """
        Execute one conversational turn.

        Args:
            input_data: Input text or data for this turn.
            context: Shared context dict (carries turn_number, previous outputs, etc.).
            state: Optional UnifiedAnalysisState for state tracking.

        Returns:
            TurnResult capturing phase outcomes, confidence, and refinement needs.
        """
        ...
