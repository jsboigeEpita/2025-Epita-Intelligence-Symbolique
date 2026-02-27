"""
Knowledge base for argumentation dialogues.

Stores propositions and arguments, checks consistency,
and finds supporting/attacking arguments.

Adapted from 1_2_7_argumentation_dialogique/local_db_arg/src/core/knowledge_base.py.
"""

from typing import Dict, List

from .protocols import FormalArgument, Proposition


class KnowledgeBase:
    """Knowledge base with argumentation support."""

    def __init__(self):
        self.propositions: Dict[str, Proposition] = {}
        self.arguments: Dict[str, FormalArgument] = {}
        self.rules: List[Dict] = []
        self.preferences: Dict[str, float] = {}

    def add_proposition(self, prop: Proposition) -> None:
        """Add a proposition to the knowledge base."""
        self.propositions[prop.content] = prop

    def add_argument(self, arg: FormalArgument) -> None:
        """Add an argument and auto-register its premises and conclusion."""
        self.arguments[arg.id] = arg
        for premise in arg.premises:
            self.add_proposition(premise)
        self.add_proposition(arg.conclusion)

    def find_supporting_arguments(self, prop: Proposition) -> List[FormalArgument]:
        """Find arguments whose conclusion matches the proposition."""
        return [
            arg
            for arg in self.arguments.values()
            if arg.conclusion.content == prop.content
        ]

    def find_attacking_arguments(self, prop: Proposition) -> List[FormalArgument]:
        """Find arguments whose conclusion negates the proposition."""
        return [
            arg
            for arg in self.arguments.values()
            if arg.conclusion.content == f"\u00ac{prop.content}"
        ]

    def is_consistent(self) -> bool:
        """Check that no proposition and its negation coexist."""
        for prop_content in self.propositions:
            if f"\u00ac{prop_content}" in self.propositions:
                return False
        return True

    def entails(self, prop: Proposition) -> bool:
        """Check if the knowledge base contains this proposition."""
        return prop.content in self.propositions

    def get_all_propositions(self) -> List[Proposition]:
        return list(self.propositions.values())

    def get_all_arguments(self) -> List[FormalArgument]:
        return list(self.arguments.values())
