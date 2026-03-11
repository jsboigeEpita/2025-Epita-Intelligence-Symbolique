# tests/unit/argumentation_analysis/agents/core/debate/test_knowledge_base.py
"""Tests for KnowledgeBase — proposition/argument storage and retrieval."""

import pytest
from argumentation_analysis.agents.core.debate.knowledge_base import KnowledgeBase
from argumentation_analysis.agents.core.debate.protocols import (
    FormalArgument,
    Proposition,
)


@pytest.fixture
def kb():
    return KnowledgeBase()


@pytest.fixture
def props():
    return {
        "rain": Proposition(content="It is raining"),
        "wet": Proposition(content="The ground is wet"),
        "cold": Proposition(content="It is cold"),
        "not_rain": Proposition(content="\u00acIt is raining"),
    }


class TestKnowledgeBaseInit:
    def test_empty(self, kb):
        assert len(kb.propositions) == 0
        assert len(kb.arguments) == 0
        assert kb.rules == []
        assert kb.preferences == {}


class TestAddProposition:
    def test_add_single(self, kb, props):
        kb.add_proposition(props["rain"])
        assert "It is raining" in kb.propositions

    def test_add_multiple(self, kb, props):
        kb.add_proposition(props["rain"])
        kb.add_proposition(props["cold"])
        assert len(kb.propositions) == 2

    def test_overwrite_same_content(self, kb):
        p1 = Proposition(content="A", truth_value=True)
        p2 = Proposition(content="A", truth_value=False)
        kb.add_proposition(p1)
        kb.add_proposition(p2)
        assert len(kb.propositions) == 1
        assert kb.propositions["A"].truth_value is False


class TestAddArgument:
    def test_add_argument(self, kb, props):
        arg = FormalArgument(
            premises=[props["rain"]],
            conclusion=props["wet"],
        )
        kb.add_argument(arg)
        assert arg.id in kb.arguments

    def test_auto_registers_premises(self, kb, props):
        arg = FormalArgument(premises=[props["rain"]], conclusion=props["wet"])
        kb.add_argument(arg)
        assert "It is raining" in kb.propositions
        assert "The ground is wet" in kb.propositions

    def test_auto_registers_conclusion(self, kb, props):
        arg = FormalArgument(premises=[], conclusion=props["cold"])
        kb.add_argument(arg)
        assert "It is cold" in kb.propositions


class TestFindArguments:
    def test_find_supporting(self, kb, props):
        arg = FormalArgument(premises=[props["rain"]], conclusion=props["wet"])
        kb.add_argument(arg)
        found = kb.find_supporting_arguments(props["wet"])
        assert len(found) == 1
        assert found[0] is arg

    def test_no_supporting(self, kb, props):
        arg = FormalArgument(premises=[props["rain"]], conclusion=props["wet"])
        kb.add_argument(arg)
        found = kb.find_supporting_arguments(props["cold"])
        assert len(found) == 0

    def test_find_attacking(self, kb, props):
        arg = FormalArgument(premises=[props["cold"]], conclusion=props["not_rain"])
        kb.add_argument(arg)
        found = kb.find_attacking_arguments(props["rain"])
        assert len(found) == 1

    def test_no_attacking(self, kb, props):
        arg = FormalArgument(premises=[props["rain"]], conclusion=props["wet"])
        kb.add_argument(arg)
        found = kb.find_attacking_arguments(props["rain"])
        assert len(found) == 0

    def test_multiple_supporting(self, kb, props):
        arg1 = FormalArgument(premises=[props["rain"]], conclusion=props["wet"])
        arg2 = FormalArgument(premises=[props["cold"]], conclusion=props["wet"])
        kb.add_argument(arg1)
        kb.add_argument(arg2)
        found = kb.find_supporting_arguments(props["wet"])
        assert len(found) == 2


class TestConsistency:
    def test_consistent_empty(self, kb):
        assert kb.is_consistent()

    def test_consistent_no_contradictions(self, kb, props):
        kb.add_proposition(props["rain"])
        kb.add_proposition(props["cold"])
        assert kb.is_consistent()

    def test_inconsistent(self, kb, props):
        kb.add_proposition(props["rain"])
        kb.add_proposition(props["not_rain"])
        assert not kb.is_consistent()


class TestEntails:
    def test_entails_present(self, kb, props):
        kb.add_proposition(props["rain"])
        assert kb.entails(props["rain"])

    def test_not_entails_absent(self, kb, props):
        assert not kb.entails(props["rain"])


class TestGetAll:
    def test_get_all_propositions(self, kb, props):
        kb.add_proposition(props["rain"])
        kb.add_proposition(props["cold"])
        all_props = kb.get_all_propositions()
        assert len(all_props) == 2

    def test_get_all_arguments(self, kb, props):
        arg1 = FormalArgument(premises=[props["rain"]], conclusion=props["wet"])
        arg2 = FormalArgument(premises=[props["cold"]], conclusion=props["wet"])
        kb.add_argument(arg1)
        kb.add_argument(arg2)
        all_args = kb.get_all_arguments()
        assert len(all_args) == 2

    def test_empty_gets(self, kb):
        assert kb.get_all_propositions() == []
        assert kb.get_all_arguments() == []
