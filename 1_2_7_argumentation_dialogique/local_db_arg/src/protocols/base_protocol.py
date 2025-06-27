from abc import ABC, abstractmethod
from typing import Dict, List, Callable
from ..core.models import DialogueType, SpeechAct, DialogueMove


class DialogueProtocol(ABC):
    """Protocole abstrait pour les dialogues"""
    
    def __init__(self, dialogue_type: DialogueType):
        self.type = dialogue_type
        self.allowed_transitions: Dict[SpeechAct, List[SpeechAct]] = {}
        self.termination_conditions: List[Callable] = []
        self._setup_protocol()
    
    @abstractmethod
    def _setup_protocol(self) -> None:
        """Configure les règles spécifiques du protocole"""
        pass
    
    def is_valid_move(self, current_act: SpeechAct, next_act: SpeechAct) -> bool:
        """Vérifie si une transition est valide"""
        return next_act in self.allowed_transitions.get(current_act, [])
    
    def is_terminal_state(self, dialogue_history: List[DialogueMove]) -> bool:
        """Vérifie les conditions de terminaison"""
        return any(condition(dialogue_history) for condition in self.termination_conditions)
    
    def get_allowed_responses(self, last_act: SpeechAct) -> List[SpeechAct]:
        """Retourne les actes de parole autorisés en réponse"""
        return self.allowed_transitions.get(last_act, [])
