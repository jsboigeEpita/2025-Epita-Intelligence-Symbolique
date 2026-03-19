"""Tests for Description Logic (DL) handler.

Validates:
- Class loading from TweetyProject
- Concept/role/individual builders
- Complement, union, intersection, existential/universal restrictions
- TBox/ABox knowledge base construction
- Consistency checking, instance queries, subsumption queries
- String-based parse_and_query
- Error handling (JVM not ready, class not found, JException)
"""

import pytest
from unittest.mock import patch, MagicMock

from argumentation_analysis.agents.core.logic.dl_handler import DLHandler
from argumentation_analysis.agents.core.logic.tweety_initializer import (
    TweetyInitializer,
)


@pytest.fixture
def mock_initializer():
    init = MagicMock(spec=TweetyInitializer)
    init.is_jvm_ready.return_value = True
    return init


@pytest.fixture
def mock_jpype():
    """Mock jpype to avoid JVM dependency."""
    with patch("argumentation_analysis.agents.core.logic.dl_handler.jpype") as m:
        # Track class constructors
        mock_classes = {}

        def jclass_side_effect(class_name):
            cls = MagicMock()
            cls.__name__ = class_name.split(".")[-1]
            mock_classes[class_name] = cls
            return cls

        m.JClass.side_effect = jclass_side_effect

        # Use a specific class so ValueError isn't caught by JException handler
        class MockJException(Exception):
            def getMessage(self):
                return str(self)

        m.JException = MockJException
        m.JString = str

        yield m, mock_classes


# ──── Init & Class Loading ────


class TestDLHandlerInit:
    def test_requires_jvm(self, mock_initializer, mock_jpype):
        mock_initializer.is_jvm_ready.return_value = False
        with pytest.raises(RuntimeError, match="JVM"):
            DLHandler(mock_initializer)

    def test_init_success(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        assert handler._initializer_instance == mock_initializer
        assert handler._reasoner is None  # Lazy-loaded

    def test_loads_all_classes(self, mock_initializer, mock_jpype):
        jpype_mock, classes = mock_jpype
        DLHandler(mock_initializer)
        # Verify all expected classes were loaded
        loaded = [call.args[0] for call in jpype_mock.JClass.call_args_list]
        assert any("AtomicConcept" in c for c in loaded)
        assert any("AtomicRole" in c for c in loaded)
        assert any("Individual" in c for c in loaded)
        assert any("Complement" in c for c in loaded)
        assert any("Union" in c for c in loaded)
        assert any("Intersection" in c for c in loaded)
        assert any("ExistentialRestriction" in c for c in loaded)
        assert any("UniversalRestriction" in c for c in loaded)
        assert any("EquivalenceAxiom" in c for c in loaded)
        assert any("ConceptAssertion" in c for c in loaded)
        assert any("RoleAssertion" in c for c in loaded)
        assert any("DlBeliefSet" in c for c in loaded)
        assert any("DlParser" in c for c in loaded)
        assert any("NaiveDlReasoner" in c for c in loaded)

    def test_class_loading_failure(self, mock_initializer):
        with patch("argumentation_analysis.agents.core.logic.dl_handler.jpype") as m:
            m.JClass.side_effect = Exception("Class not found")
            with pytest.raises(RuntimeError, match="DL classes not available"):
                DLHandler(mock_initializer)


# ──── Concept Builders ────


class TestConceptBuilders:
    def test_concept(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        result = handler.concept("Animal")
        handler._AtomicConcept.assert_called_with("Animal")

    def test_role(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        result = handler.role("hasParent")
        handler._AtomicRole.assert_called_with("hasParent")

    def test_individual(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        result = handler.individual("john")
        handler._Individual.assert_called_with("john")

    def test_complement(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        concept = MagicMock()
        result = handler.complement(concept)
        handler._Complement.assert_called_once_with(concept)

    def test_union_two(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        c1, c2 = MagicMock(), MagicMock()
        result = handler.union(c1, c2)
        handler._Union.assert_called_once_with(c1, c2)

    def test_union_three(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        c1, c2, c3 = MagicMock(), MagicMock(), MagicMock()
        result = handler.union(c1, c2, c3)
        assert handler._Union.call_count == 2

    def test_intersection_two(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        c1, c2 = MagicMock(), MagicMock()
        result = handler.intersection(c1, c2)
        handler._Intersection.assert_called_once_with(c1, c2)

    def test_intersection_three(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        c1, c2, c3 = MagicMock(), MagicMock(), MagicMock()
        result = handler.intersection(c1, c2, c3)
        assert handler._Intersection.call_count == 2

    def test_exists(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        role, concept = MagicMock(), MagicMock()
        result = handler.exists(role, concept)
        handler._ExistentialRestriction.assert_called_once_with(role, concept)

    def test_forall(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        role, concept = MagicMock(), MagicMock()
        result = handler.forall(role, concept)
        handler._UniversalRestriction.assert_called_once_with(role, concept)


# ──── KB Construction ────


class TestKBConstruction:
    def test_empty_kb(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        kb = handler.create_knowledge_base()
        handler._DlBeliefSet.assert_called_once()

    def test_tbox_equivalences(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        kb = handler.create_knowledge_base(
            tbox=[("Human", "Mortal"), ("Dog", "Animal")]
        )
        # 2 equivalence axioms added
        assert kb.add.call_count == 2
        assert handler._EquivalenceAxiom.call_count == 2

    def test_abox_concept_assertions(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        kb = handler.create_knowledge_base(
            abox_concepts=[("john", "Human"), ("rex", "Dog")]
        )
        assert kb.add.call_count == 2
        assert handler._ConceptAssertion.call_count == 2

    def test_abox_role_assertions(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        kb = handler.create_knowledge_base(abox_roles=[("john", "hasChild", "mary")])
        assert kb.add.call_count == 1
        assert handler._RoleAssertion.call_count == 1

    def test_full_kb(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        kb = handler.create_knowledge_base(
            tbox=[("Parent", "Human")],
            abox_concepts=[("john", "Parent")],
            abox_roles=[("john", "hasChild", "mary")],
        )
        assert kb.add.call_count == 3  # 1 tbox + 1 abox_concept + 1 abox_role


# ──── Reasoner ────


class TestReasonerLazyLoad:
    def test_lazy_load(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        assert handler._reasoner is None
        reasoner = handler._get_reasoner()
        assert handler._reasoner is not None
        handler._NaiveDlReasoner.assert_called_once()

    def test_caching(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        r1 = handler._get_reasoner()
        r2 = handler._get_reasoner()
        assert r1 is r2
        handler._NaiveDlReasoner.assert_called_once()


# ──── Reasoning ────


class TestConsistencyCheck:
    def test_consistent_kb(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        mock_reasoner = MagicMock()
        mock_reasoner.query.return_value = True
        handler._NaiveDlReasoner.return_value = mock_reasoner

        kb = MagicMock()
        result, msg = handler.is_consistent(kb)
        assert result is True
        assert "consistent" in msg.lower()

    def test_jexception_returns_false(self, mock_initializer, mock_jpype):
        jpype_mock, _ = mock_jpype
        handler = DLHandler(mock_initializer)
        mock_reasoner = MagicMock()
        mock_reasoner.query.side_effect = jpype_mock.JException("Inconsistency")
        handler._NaiveDlReasoner.return_value = mock_reasoner

        kb = MagicMock()
        result, msg = handler.is_consistent(kb)
        assert result is False

    def test_unexpected_error(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        mock_reasoner = MagicMock()
        mock_reasoner.query.side_effect = ValueError("unexpected")
        handler._NaiveDlReasoner.return_value = mock_reasoner

        kb = MagicMock()
        result, msg = handler.is_consistent(kb)
        assert result is False


class TestConceptQuery:
    def test_positive_query(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        mock_reasoner = MagicMock()
        mock_reasoner.query.return_value = True
        handler._NaiveDlReasoner.return_value = mock_reasoner

        kb = MagicMock()
        assert handler.query_concept(kb, "john", "Human") is True

    def test_negative_query(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        mock_reasoner = MagicMock()
        mock_reasoner.query.return_value = False
        handler._NaiveDlReasoner.return_value = mock_reasoner

        kb = MagicMock()
        assert handler.query_concept(kb, "john", "Dog") is False

    def test_query_error_propagates(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        mock_reasoner = MagicMock()
        mock_reasoner.query.side_effect = RuntimeError("query failed")
        handler._NaiveDlReasoner.return_value = mock_reasoner

        kb = MagicMock()
        with pytest.raises(RuntimeError):
            handler.query_concept(kb, "john", "Human")


class TestSubsumptionQuery:
    def test_subsumption_holds(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        mock_reasoner = MagicMock()
        mock_reasoner.query.return_value = (
            False  # C ⊓ ¬D not entailed → subsumption holds
        )
        handler._NaiveDlReasoner.return_value = mock_reasoner

        kb = MagicMock()
        assert handler.query_subsumption(kb, "Dog", "Animal") is True

    def test_subsumption_fails(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        mock_reasoner = MagicMock()
        mock_reasoner.query.return_value = True  # C ⊓ ¬D entailed → no subsumption
        handler._NaiveDlReasoner.return_value = mock_reasoner

        kb = MagicMock()
        assert handler.query_subsumption(kb, "Animal", "Dog") is False

    def test_subsumption_error_propagates(self, mock_initializer, mock_jpype):
        handler = DLHandler(mock_initializer)
        mock_reasoner = MagicMock()
        mock_reasoner.query.side_effect = RuntimeError("fail")
        handler._NaiveDlReasoner.return_value = mock_reasoner

        kb = MagicMock()
        with pytest.raises(RuntimeError):
            handler.query_subsumption(kb, "A", "B")


class TestParseAndQuery:
    def test_entailed(self, mock_initializer, mock_jpype):
        jpype_mock, _ = mock_jpype
        handler = DLHandler(mock_initializer)

        mock_parser = MagicMock()
        handler._DlParser.return_value = mock_parser

        mock_reasoner = MagicMock()
        mock_reasoner.query.return_value = True
        handler._NaiveDlReasoner.return_value = mock_reasoner

        result, msg = handler.parse_and_query("kb_string", "query_string")
        assert result is True
        assert "ENTAILED" in msg

    def test_not_entailed(self, mock_initializer, mock_jpype):
        jpype_mock, _ = mock_jpype
        handler = DLHandler(mock_initializer)

        mock_parser = MagicMock()
        handler._DlParser.return_value = mock_parser

        mock_reasoner = MagicMock()
        mock_reasoner.query.return_value = False
        handler._NaiveDlReasoner.return_value = mock_reasoner

        result, msg = handler.parse_and_query("kb", "q")
        assert result is False
        assert "NOT entailed" in msg

    def test_jexception(self, mock_initializer, mock_jpype):
        jpype_mock, _ = mock_jpype
        handler = DLHandler(mock_initializer)

        mock_parser = MagicMock()
        mock_parser.parseBeliefBase.side_effect = jpype_mock.JException("parse error")
        handler._DlParser.return_value = mock_parser

        result, msg = handler.parse_and_query("bad", "q")
        assert result is False
        assert "FUNC_ERROR" in msg

    def test_unexpected_error(self, mock_initializer, mock_jpype):
        jpype_mock, _ = mock_jpype
        handler = DLHandler(mock_initializer)

        mock_parser = MagicMock()
        mock_parser.parseBeliefBase.side_effect = ValueError("unexpected")
        handler._DlParser.return_value = mock_parser

        result, msg = handler.parse_and_query("bad", "q")
        assert result is False
        assert "FUNC_ERROR" in msg
