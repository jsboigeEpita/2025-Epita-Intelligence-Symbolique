"""
Debate data structures — enums, dataclasses, and personality profiles.

Extracted from the enhanced_argumentation_main.py monolith.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ArgumentType(Enum):
    """Types of debate arguments."""

    OPENING_STATEMENT = "opening_statement"
    CLAIM = "claim"
    EVIDENCE = "evidence"
    REBUTTAL = "rebuttal"
    COUNTER_REBUTTAL = "counter_rebuttal"
    CLOSING_STATEMENT = "closing_statement"


class DebatePhase(Enum):
    """Phases of a structured debate."""

    OPENING = "opening"
    MAIN_ARGUMENTS = "main_arguments"
    REBUTTALS = "rebuttals"
    CLOSING = "closing"
    CONCLUDED = "concluded"


@dataclass
class ArgumentMetrics:
    """Multi-dimensional argument quality metrics (all 0.0-1.0).

    ``relevance_score`` and ``novelty_score`` compare an argument with the
    others: the analyzer leaves them at ``None`` when there is nothing to
    compare with (#2344).
    """

    logical_coherence: float = 0.0
    evidence_quality: float = 0.0
    relevance_score: Optional[float] = 0.0
    emotional_appeal: float = 0.0
    readability_score: Optional[float] = None
    fact_check_score: Optional[float] = None
    novelty_score: Optional[float] = 0.0
    persuasiveness: float = 0.0


@dataclass
class EnhancedArgument:
    """Argument with comprehensive metadata and scoring."""

    agent_name: str
    position: str  # "for" or "against"
    content: str
    argument_type: ArgumentType
    timestamp: str
    phase: DebatePhase
    references: List[str] = field(default_factory=list)
    citations: List[Dict[str, str]] = field(default_factory=list)
    metrics: ArgumentMetrics = field(default_factory=ArgumentMetrics)
    logical_structure: Dict[str, Any] = field(default_factory=dict)
    word_count: int = 0
    response_to: Optional[str] = None

    def __post_init__(self):
        self.word_count = len(self.content.split())
        self.id = f"{self.agent_name}_{self.timestamp}_{hash(self.content) % 10000}"


@dataclass
class DebateState:
    """Full state of a debate in progress or concluded."""

    topic: str
    agents: List[str]
    arguments: List[EnhancedArgument]
    current_turn: int
    max_turns: int
    phase: DebatePhase
    winner: Optional[str] = None
    audience_votes: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    performance_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    argument_network: Dict[str, List[str]] = field(default_factory=dict)
    debate_summary: str = ""
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())


# 8 personality archetypes for debate agents.
# strengths/weaknesses lists withdrawn (#2137): get_agent_capabilities
# lists only the names — no reader of the fields existed.
AGENT_PERSONALITIES = {
    "The Scholar": {
        "description": "Academic and evidence-based. Relies on research, studies, and peer-reviewed sources.",
    },
    "The Pragmatist": {
        "description": "Focuses on practical implications and real-world consequences.",
    },
    "The Devil's Advocate": {
        "description": "Challenges assumptions and conventional wisdom. Points out contradictions.",
    },
    "The Idealist": {
        "description": "Argues from moral principles and ethical foundations.",
    },
    "The Skeptic": {
        "description": "Questions everything and demands rigorous proof.",
    },
    "The Populist": {
        "description": "Represents common sense. Speaks in accessible language.",
    },
    "The Economist": {
        "description": "Analyzes through cost-benefit analysis and market principles.",
    },
    "The Philosopher": {
        "description": "Deep abstract reasoning with thought experiments.",
    },
}
