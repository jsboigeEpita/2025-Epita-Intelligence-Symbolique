"""
Walton-Krabbe dialogue protocols — formal argumentation dialogue framework.

Provides 6 dialogue types (inquiry, persuasion, negotiation, etc.),
9 speech act types with transition rules, and termination conditions.

Adapted from 1_2_7_argumentation_dialogique/local_db_arg/src/.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union


class DialogueType(Enum):
    """Dialogue types according to Walton-Krabbe taxonomy."""

    INFORMATION_SEEKING = "information_seeking"
    INQUIRY = "inquiry"
    PERSUASION = "persuasion"
    NEGOTIATION = "negotiation"
    DELIBERATION = "deliberation"
    ERISTIC = "eristic"


class SpeechAct(Enum):
    """Formalized speech acts for dialogue moves."""

    CLAIM = "claim"
    QUESTION = "question"
    CHALLENGE = "challenge"
    ARGUE = "argue"
    CONCEDE = "concede"
    RETRACT = "retract"
    SUPPORT = "support"
    REFUTE = "refute"
    UNDERSTAND = "understand"


@dataclass
class Proposition:
    """A logical proposition with optional truth value and confidence."""

    content: str
    truth_value: Optional[bool] = None
    confidence: float = 1.0
    source: Optional[str] = None

    def __hash__(self):
        return hash(self.content)

    def __eq__(self, other):
        if isinstance(other, Proposition):
            return self.content == other.content
        return NotImplemented

    def __str__(self):
        return self.content


@dataclass
class FormalArgument:
    """A structured argument with premises and conclusion.

    Named FormalArgument to avoid conflict with the debate system's
    EnhancedArgument.
    """

    premises: List[Proposition]
    conclusion: Proposition
    strength: float = 1.0
    scheme: Optional[str] = None
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())

    def __str__(self):
        premises_str = ", ".join(str(p) for p in self.premises)
        return f"[{premises_str}] -> {self.conclusion}"


@dataclass
class DialogueMove:
    """A move in a dialogue — speaker performs a speech act on content."""

    speaker: str
    act: SpeechAct
    content: Union[Proposition, FormalArgument, str]
    target: Optional[str] = None
    id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())

    def __str__(self):
        return f"{self.speaker}: {self.act.value} - {self.content}"


class DialogueProtocol(ABC):
    """Abstract dialogue protocol with transition rules and termination conditions."""

    def __init__(self, dialogue_type: DialogueType):
        self.type = dialogue_type
        self.allowed_transitions: Dict[SpeechAct, List[SpeechAct]] = {}
        self.termination_conditions: List[Callable] = []
        self._setup_protocol()

    @abstractmethod
    def _setup_protocol(self) -> None:
        """Configure protocol-specific rules."""
        pass

    def is_valid_move(self, current_act: SpeechAct, next_act: SpeechAct) -> bool:
        """Check if a transition from current_act to next_act is valid."""
        return next_act in self.allowed_transitions.get(current_act, [])

    def is_terminal_state(self, dialogue_history: List[DialogueMove]) -> bool:
        """Check if any termination condition is met."""
        return any(
            condition(dialogue_history) for condition in self.termination_conditions
        )

    def get_allowed_responses(self, last_act: SpeechAct) -> List[SpeechAct]:
        """Get speech acts allowed in response to last_act."""
        return self.allowed_transitions.get(last_act, [])


class InquiryProtocol(DialogueProtocol):
    """Protocol for collaborative inquiry dialogues."""

    def __init__(self):
        super().__init__(DialogueType.INQUIRY)

    def _setup_protocol(self):
        self.allowed_transitions = {
            SpeechAct.QUESTION: [
                SpeechAct.CLAIM,
                SpeechAct.ARGUE,
                SpeechAct.QUESTION,
                SpeechAct.SUPPORT,
            ],
            SpeechAct.CLAIM: [
                SpeechAct.SUPPORT,
                SpeechAct.CHALLENGE,
                SpeechAct.QUESTION,
                SpeechAct.UNDERSTAND,
            ],
            SpeechAct.SUPPORT: [
                SpeechAct.QUESTION,
                SpeechAct.UNDERSTAND,
                SpeechAct.CHALLENGE,
            ],
            SpeechAct.CHALLENGE: [
                SpeechAct.ARGUE,
                SpeechAct.SUPPORT,
                SpeechAct.QUESTION,
            ],
            SpeechAct.ARGUE: [
                SpeechAct.CHALLENGE,
                SpeechAct.UNDERSTAND,
                SpeechAct.QUESTION,
                SpeechAct.SUPPORT,
            ],
            SpeechAct.UNDERSTAND: [
                SpeechAct.QUESTION,
                SpeechAct.UNDERSTAND,
                SpeechAct.CLAIM,
            ],
            SpeechAct.REFUTE: [SpeechAct.ARGUE, SpeechAct.QUESTION],
            SpeechAct.CONCEDE: [SpeechAct.QUESTION, SpeechAct.UNDERSTAND],
        }
        self.termination_conditions = [
            lambda h: len(h) >= 3
            and all(m.act in [SpeechAct.UNDERSTAND, SpeechAct.CONCEDE] for m in h[-3:]),
            lambda h: len(h) > 25,
            lambda h: len(h) >= 4 and h[-1].act == h[-2].act == SpeechAct.UNDERSTAND,
            lambda h: len(h) >= 6 and self._detect_pattern_loop(h),
        ]

    def _detect_pattern_loop(self, history):
        if len(history) < 6:
            return False
        recent = history[-6:]
        p1 = [(recent[0].act, recent[1].act)]
        p2 = [(recent[2].act, recent[3].act)]
        p3 = [(recent[4].act, recent[5].act)]
        return p1 == p2 == p3


class PersuasionProtocol(DialogueProtocol):
    """Protocol for persuasion dialogues."""

    def __init__(self):
        super().__init__(DialogueType.PERSUASION)

    def _setup_protocol(self):
        self.allowed_transitions = {
            SpeechAct.CLAIM: [
                SpeechAct.CHALLENGE,
                SpeechAct.CONCEDE,
                SpeechAct.QUESTION,
                SpeechAct.SUPPORT,
            ],
            SpeechAct.CHALLENGE: [
                SpeechAct.ARGUE,
                SpeechAct.RETRACT,
                SpeechAct.SUPPORT,
            ],
            SpeechAct.ARGUE: [
                SpeechAct.CHALLENGE,
                SpeechAct.CONCEDE,
                SpeechAct.REFUTE,
                SpeechAct.SUPPORT,
            ],
            SpeechAct.QUESTION: [
                SpeechAct.CLAIM,
                SpeechAct.ARGUE,
                SpeechAct.SUPPORT,
            ],
            SpeechAct.REFUTE: [
                SpeechAct.ARGUE,
                SpeechAct.CONCEDE,
                SpeechAct.CHALLENGE,
            ],
            SpeechAct.SUPPORT: [
                SpeechAct.UNDERSTAND,
                SpeechAct.CHALLENGE,
                SpeechAct.QUESTION,
            ],
            SpeechAct.CONCEDE: [SpeechAct.CLAIM, SpeechAct.QUESTION],
            SpeechAct.RETRACT: [SpeechAct.CLAIM, SpeechAct.QUESTION],
            SpeechAct.UNDERSTAND: [SpeechAct.CLAIM, SpeechAct.QUESTION],
        }
        self.termination_conditions = [
            lambda h: len(h) > 0 and h[-1].act == SpeechAct.CONCEDE,
            lambda h: len(h) > 30,
            lambda h: len(h) > 2 and h[-1].act == h[-2].act == SpeechAct.RETRACT,
        ]
