from .base_protocol import DialogueProtocol
from ..core.models import DialogueType, SpeechAct


class PersuasionProtocol(DialogueProtocol):
    """Protocole pour dialogues de persuasion"""

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
            SpeechAct.QUESTION: [SpeechAct.CLAIM, SpeechAct.ARGUE, SpeechAct.SUPPORT],
            SpeechAct.REFUTE: [SpeechAct.ARGUE, SpeechAct.CONCEDE, SpeechAct.CHALLENGE],
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
            lambda h: len(h) > 30,  # Limite de longueur
            lambda h: len(h) > 2 and h[-1].act == h[-2].act == SpeechAct.RETRACT,
        ]
