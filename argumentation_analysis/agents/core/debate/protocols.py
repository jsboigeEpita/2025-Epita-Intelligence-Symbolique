"""
Walton-Krabbe dialogue vocabulary — dialogue types, speech acts, propositions,
formal arguments and moves.

The three protocol classes (DialogueProtocol / InquiryProtocol /
PersuasionProtocol) were withdrawn (#2137): dead twins — the living workflow
path for formal dialogue is the JVM ``logic/dialogue_handler.py``.

Adapted from 1_2_7_argumentation_dialogique/local_db_arg/src/.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Union


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


# DialogueProtocol / InquiryProtocol / PersuasionProtocol were withdrawn
# (#2137): dead twins of the living JVM dialogue_handler — zero production
# callers; exercised only by tests and the CoursIA teaching notebooks.
