from typing import Dict, Optional, List  # Ajout de List ici
from .models import Proposition, Argument
from .knowledge_base import KnowledgeBase


class ArgumentationEngine:
    """Moteur d'argumentation pour générer et évaluer les arguments"""

    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base
        self.schemes = self._load_argumentation_schemes()

    def _load_argumentation_schemes(self) -> Dict[str, Dict]:
        """Charge les schémas d'argumentation standards"""
        return {
            "modus_ponens": {
                "premises": ["P", "P → Q"],
                "conclusion": "Q",
                "strength": 1.0,
            },
            "expert_opinion": {
                "premises": [
                    "Expert E says P",
                    "E is expert in domain D",
                    "P is in domain D",
                ],
                "conclusion": "P",
                "strength": 0.8,
            },
            "analogy": {
                "premises": [
                    "Case A has property X",
                    "Case B is similar to A",
                    "X is relevant",
                ],
                "conclusion": "Case B has property X",
                "strength": 0.6,
            },
            "cause_effect": {
                "premises": ["A causes B", "A occurred"],
                "conclusion": "B will occur",
                "strength": 0.7,
            },
            "consensus": {
                "premises": [
                    "Majority of experts agree on P",
                    "Experts are qualified",
                    "No systematic bias",
                ],
                "conclusion": "P is likely true",
                "strength": 0.85,
            },
            "empirical_evidence": {
                "premises": [
                    "Data shows P",
                    "Data is reliable",
                    "Sample is representative",
                ],
                "conclusion": "P is supported by evidence",
                "strength": 0.9,
            },
            "economic_argument": {
                "premises": ["Action A costs X", "Action A benefits Y", "Y > X"],
                "conclusion": "Action A is economically justified",
                "strength": 0.75,
            },
            "precautionary_principle": {
                "premises": [
                    "Risk R is possible",
                    "R has severe consequences",
                    "Prevention is possible",
                ],
                "conclusion": "Prevention should be taken",
                "strength": 0.7,
            },
            "moral_argument": {
                "premises": [
                    "Action A affects group G",
                    "G has rights",
                    "A violates rights",
                ],
                "conclusion": "Action A is morally wrong",
                "strength": 0.8,
            },
            "historical_precedent": {
                "premises": [
                    "Situation S occurred before",
                    "S led to outcome O",
                    "Current situation similar to S",
                ],
                "conclusion": "Outcome O is likely",
                "strength": 0.65,
            },
        }

    def generate_argument(
        self, target: Proposition, scheme: str = "modus_ponens"
    ) -> Optional[Argument]:
        """Génère un argument pour/contre une proposition"""
        if scheme not in self.schemes:
            return None

        scheme_def = self.schemes[scheme]
        supporting_props = self.kb.find_supporting_arguments(target)

        if supporting_props:
            premises = [arg.conclusion for arg in supporting_props[:2]]
            return Argument(
                id="",
                premises=premises,
                conclusion=target,
                strength=scheme_def["strength"],
                scheme=scheme,
            )

        # Génère un argument simple basé sur les propositions de la base
        related_props = [
            p
            for p in self.kb.get_all_propositions()
            if target.content.lower() in p.content.lower()
            or p.content.lower() in target.content.lower()
        ]

        if related_props:
            return Argument(
                id="",
                premises=related_props[:2],
                conclusion=target,
                strength=scheme_def["strength"],
                scheme=scheme,
            )

        return None

    def evaluate_argument(self, arg: Argument) -> float:
        """Évalue la force d'un argument"""
        base_strength = arg.strength

        # Facteurs d'évaluation
        premise_support = (
            sum(1 for p in arg.premises if self.kb.entails(p)) / len(arg.premises)
            if arg.premises
            else 0
        )
        consistency_factor = 1.0 if self.kb.is_consistent() else 0.5

        return base_strength * premise_support * consistency_factor

    def find_counter_arguments(self, target: Proposition) -> List[Argument]:
        """Trouve des contre-arguments à une proposition"""
        counter_args = []

        # Cherche des arguments directs contre la proposition
        attacking_args = self.kb.find_attacking_arguments(target)
        counter_args.extend(attacking_args)

        # Génère des contre-arguments basés sur des propositions contradictoires
        for prop in self.kb.get_all_propositions():
            if self._are_contradictory(target, prop):
                counter_arg = self.generate_argument(prop)
                if counter_arg:
                    counter_args.append(counter_arg)

        return counter_args

    def _are_contradictory(self, prop1: Proposition, prop2: Proposition) -> bool:
        """Vérifie si deux propositions sont contradictoires"""
        # Implémentation simplifiée
        return (
            prop1.content == f"¬{prop2.content}"
            or prop2.content == f"¬{prop1.content}"
            or (
                "not" in prop1.content.lower()
                and prop2.content.lower() in prop1.content.lower()
            )
            or (
                "not" in prop2.content.lower()
                and prop1.content.lower() in prop2.content.lower()
            )
        )
