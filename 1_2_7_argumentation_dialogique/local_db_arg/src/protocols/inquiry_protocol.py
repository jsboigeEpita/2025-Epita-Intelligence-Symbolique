from .base_protocol import DialogueProtocol
from ..core.models import DialogueType, SpeechAct


class InquiryProtocol(DialogueProtocol):
    """Protocole pour dialogues d'enquête collaborative"""

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
            # Terminaison naturelle avec compréhension mutuelle
            lambda h: len(h) >= 3
            and all(m.act in [SpeechAct.UNDERSTAND, SpeechAct.CONCEDE] for m in h[-3:]),
            # Limite de longueur
            lambda h: len(h) > 25,
            # Convergence vers la compréhension
            lambda h: len(h) >= 4 and h[-1].act == h[-2].act == SpeechAct.UNDERSTAND,
            # Détection de boucle (même pattern répété 3 fois)
            lambda h: len(h) >= 6 and self._detect_pattern_loop(h),
        ]

    def _detect_pattern_loop(self, history):
        """Détecte si les 6 derniers mouvements forment une boucle"""
        if len(history) < 6:
            return False

        recent = history[-6:]
        pattern1 = [(recent[0].act, recent[1].act)]
        pattern2 = [(recent[2].act, recent[3].act)]
        pattern3 = [(recent[4].act, recent[5].act)]

        return pattern1 == pattern2 == pattern3
