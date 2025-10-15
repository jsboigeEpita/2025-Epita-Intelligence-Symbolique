from typing import Dict, List
from .models import Proposition, Argument


class KnowledgeBase:
    """Base de connaissances avec support d'argumentation"""

    def __init__(self):
        self.propositions: Dict[str, Proposition] = {}
        self.arguments: Dict[str, Argument] = {}
        self.rules: List[Dict] = []
        self.preferences: Dict[str, float] = {}

    def add_proposition(self, prop: Proposition) -> None:
        """Ajoute une proposition à la base"""
        self.propositions[prop.content] = prop

    def add_argument(self, arg: Argument) -> None:
        """Ajoute un argument à la base"""
        self.arguments[arg.id] = arg
        # Ajoute automatiquement les prémisses et conclusion
        for premise in arg.premises:
            self.add_proposition(premise)
        self.add_proposition(arg.conclusion)

    def find_supporting_arguments(self, prop: Proposition) -> List[Argument]:
        """Trouve les arguments supportant une proposition"""
        return [
            arg
            for arg in self.arguments.values()
            if arg.conclusion.content == prop.content
        ]

    def find_attacking_arguments(self, prop: Proposition) -> List[Argument]:
        """Trouve les arguments attaquant une proposition"""
        return [
            arg
            for arg in self.arguments.values()
            if arg.conclusion.content == f"¬{prop.content}"
        ]

    def is_consistent(self) -> bool:
        """Vérifie la cohérence de la base"""
        for prop_content in self.propositions:
            neg_content = f"¬{prop_content}"
            if neg_content in self.propositions:
                return False
        return True

    def entails(self, prop: Proposition) -> bool:
        """Vérifie si la base implique une proposition"""
        return prop.content in self.propositions

    def get_all_propositions(self) -> List[Proposition]:
        """Retourne toutes les propositions"""
        return list(self.propositions.values())

    def get_all_arguments(self) -> List[Argument]:
        """Retourne tous les arguments"""
        return list(self.arguments.values())
