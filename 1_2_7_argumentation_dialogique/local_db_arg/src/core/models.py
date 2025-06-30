from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Union
from datetime import datetime
import uuid


class DialogueType(Enum):
    """Types de dialogues selon Walton-Krabbe"""
    INFORMATION_SEEKING = "information_seeking"
    INQUIRY = "inquiry" 
    PERSUASION = "persuasion"
    NEGOTIATION = "negotiation"
    DELIBERATION = "deliberation"
    ERISTIC = "eristic"


class SpeechAct(Enum):
    """Actes de parole formalisés"""
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
    """Représentation d'une proposition logique"""
    content: str
    truth_value: Optional[bool] = None
    confidence: float = 1.0
    source: Optional[str] = None
    
    def __hash__(self):
        return hash(self.content)
    
    def __str__(self):
        return self.content


@dataclass
class Argument:
    """Structure d'un argument"""
    id: str
    premises: List[Proposition]
    conclusion: Proposition
    strength: float = 1.0
    scheme: Optional[str] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
    
    def __str__(self):
        premises_str = ", ".join(str(p) for p in self.premises)
        return f"[{premises_str}] → {self.conclusion}"


@dataclass
class DialogueMove:
    """Mouvement dans le dialogue"""
    id: str
    speaker: str
    act: SpeechAct
    content: Union[Proposition, Argument, str]
    timestamp: datetime
    target: Optional[str] = None  # ID du mouvement ciblé
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now()
    
    def __str__(self):
        return f"{self.speaker}: {self.act.value} - {self.content}"
