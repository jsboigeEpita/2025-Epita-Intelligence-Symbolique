"""
Debate agents and protocols — multi-agent adversarial argumentation.

Provides two complementary debate systems:

1. **Enhanced Debate System** (from enhanced_argumentation_main.py):
   - 8 personality archetypes with adaptive strategies
   - Phase-based debate (opening, main, rebuttals, closing)
   - 8-metric argument scoring (logic, evidence, relevance, etc.)
   - Audience simulation and comprehensive winner determination

2. **Walton-Krabbe Dialogue Protocols** (from local_db_arg/):
   - Formal dialogue types (inquiry, persuasion, negotiation, etc.)
   - Speech act transitions with termination conditions
   - Knowledge base with consistency checking
   - 10 argumentation schemes

Integration from student project 1_2_7_argumentation_dialogique (GitHub #42).
"""

from .debate_definitions import (
    ArgumentType,
    DebatePhase,
    ArgumentMetrics,
    EnhancedArgument,
    DebateState,
    AGENT_PERSONALITIES,
)
from .debate_agent import (
    DebateAgent,
    DebatePlugin,
    EnhancedArgumentationAgent,
    EnhancedDebateModerator,
)
from .debate_scoring import ArgumentAnalyzer
from .protocols import (
    DialogueType,
    SpeechAct,
    Proposition,
    DialogueProtocol,
    InquiryProtocol,
    PersuasionProtocol,
)

__all__ = [
    "DebateAgent",
    "DebatePlugin",
    "EnhancedArgumentationAgent",
    "EnhancedDebateModerator",
    "ArgumentType",
    "DebatePhase",
    "ArgumentMetrics",
    "EnhancedArgument",
    "DebateState",
    "AGENT_PERSONALITIES",
    "ArgumentAnalyzer",
    "DialogueType",
    "SpeechAct",
    "Proposition",
    "DialogueProtocol",
    "InquiryProtocol",
    "PersuasionProtocol",
]

# #1842: no register_with_capability_registry here. The debate capability
# table lives on the production surface (registry_setup.setup_registry) —
# this module's former second table was only ever called by tests, and its
# register_agent("debate_agent") would COLLIDE with the wired one
# (ValueError: Component 'debate_agent' is already registered).
