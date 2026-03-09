"""Tests for Conditional Logic (CL) handler.

Validates:
- Class loading from TweetyProject
- Proposition/negation/conjunction/disjunction builders
- Conditional creation (with and without premise)
- Knowledge base construction from (conclusion, premise) pairs
- Simple formula parser (!, &, |)
- Query reasoning (accepted/rejected)
- String-based parse_and_query
- ZReasoner (System Z) lazy loading
- Error handling (JVM not ready, class not found, JException)
"""
import pytest
from unittest.mock import patch, MagicMock

from argumentation_analysis.agents.core.logic.cl_handler import CLHandler
from argumentation_analysis.agents.core.logic.tweety_initializer import TweetyInitializer


@pytest.fixture
def mock_initializer():
    init = MagicMock(spec=TweetyInitializer)
    init.is_jvm_ready.return_value = True
    return init


@pytest.fixture
def mock_jpype():
    """Mock jpype to avoid JVM dependency."""
    with patch("argumentation_analysis.agents.core.logic.cl_handler.jpype") as m:
        mock_classes = {}

        def jclass_side_effect(class_name):
            cls = MagicMock()
            cls.__name__ = class_name.split(".")[-1]
            mock_classes[class_name] = cls
            return cls

        m.JClass.side_effect = jclass_side_effect
        class MockJException(Exception):
            def getMessage(self):
                return str(self)
        m.JException = MockJException
        m.JString = str

        yield m, mock_classes


# ──── Init & Class Loading ────


class TestCLHandlerInit:
    def test_requires_jvm(self, mock_initializer, mock_jpype):
        mock_initializer.is_jvm_ready.return_value = False
        with pytest.raises(RuntimeError, match="JVM"):
            CLHandler(mock_initializer)

    def test_init_success(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        assert handler._initializer_instance == mock_initializer
        assert handler._reasoner is None
        assert handler._z_reasoner is None

    def test_loads_all_classes(self, mock_initializer, mock_jpype):
        jpype_mock, classes = mock_jpype
        CLHandler(mock_initializer)
        loaded = [call.args[0] for call in jpype_mock.JClass.call_args_list]
        assert any("Conditional" in c for c in loaded)
        assert any("ClBeliefSet" in c for c in loaded)
        assert any("ClParser" in c for c in loaded)
        assert any("SimpleCReasoner" in c for c in loaded)
        assert any("Proposition" in c for c in loaded)
        assert any("Negation" in c for c in loaded)
        assert any("Conjunction" in c for c in loaded)
        assert any("Disjunction" in c for c in loaded)

    def test_class_loading_failure(self, mock_initializer):
        with patch("argumentation_analysis.agents.core.logic.cl_handler.jpype") as m:
            m.JClass.side_effect = Exception("Class not found")
            with pytest.raises(RuntimeError, match="CL classes not available"):
                CLHandler(mock_initializer)


# ──── Formula Builders ────


class TestFormulaBuilders:
    def test_proposition(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        handler.proposition("bird")
        handler._Proposition.assert_called_with("bird")

    def test_negation(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        formula = MagicMock()
        handler.negation(formula)
        handler._Negation.assert_called_once_with(formula)

    def test_conjunction_two(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        f1, f2 = MagicMock(), MagicMock()
        result = handler.conjunction(f1, f2)
        handler._Conjunction.assert_called_once_with(f1, f2)

    def test_conjunction_three(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        f1, f2, f3 = MagicMock(), MagicMock(), MagicMock()
        result = handler.conjunction(f1, f2, f3)
        assert handler._Conjunction.call_count == 2

    def test_disjunction_two(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        f1, f2 = MagicMock(), MagicMock()
        result = handler.disjunction(f1, f2)
        handler._Disjunction.assert_called_once_with(f1, f2)

    def test_disjunction_three(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        f1, f2, f3 = MagicMock(), MagicMock(), MagicMock()
        result = handler.disjunction(f1, f2, f3)
        assert handler._Disjunction.call_count == 2

    def test_conditional_with_premise(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        conclusion, premise = MagicMock(), MagicMock()
        handler.conditional(conclusion, premise)
        handler._Conditional.assert_called_once_with(conclusion, premise)

    def test_conditional_without_premise(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        conclusion = MagicMock()
        handler.conditional(conclusion)
        handler._Conditional.assert_called_once_with(conclusion)


# ──── Simple Formula Parser ────


class TestSimpleFormulaParser:
    def test_atom(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        handler._parse_simple_formula("bird")
        handler._Proposition.assert_called_with("bird")

    def test_negation(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        handler._parse_simple_formula("!flies")
        handler._Proposition.assert_called_with("flies")
        handler._Negation.assert_called_once()

    def test_conjunction(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        handler._parse_simple_formula("a&b")
        assert handler._Proposition.call_count >= 2
        handler._Conjunction.assert_called_once()

    def test_disjunction(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        handler._parse_simple_formula("a|b")
        assert handler._Proposition.call_count >= 2
        handler._Disjunction.assert_called_once()

    def test_strips_whitespace(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        handler._parse_simple_formula("  bird  ")
        handler._Proposition.assert_called_with("bird")


# ──── KB Construction ────


class TestKBConstruction:
    def test_empty_kb(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        kb = handler.create_knowledge_base()
        handler._ClBeliefSet.assert_called_once()

    def test_conditional_with_premise(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        kb = handler.create_knowledge_base(
            conditionals=[("flies", "bird")]
        )
        assert kb.add.call_count == 1
        handler._Conditional.assert_called_once()

    def test_unconditional_fact(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        kb = handler.create_knowledge_base(
            conditionals=[("bird", None)]
        )
        assert kb.add.call_count == 1

    def test_multiple_conditionals(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        kb = handler.create_knowledge_base(
            conditionals=[
                ("flies", "bird"),
                ("!flies", "penguin"),
                ("bird", None),
            ]
        )
        assert kb.add.call_count == 3

    def test_negated_conclusion(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        kb = handler.create_knowledge_base(
            conditionals=[("!flies", "penguin")]
        )
        handler._Negation.assert_called_once()


# ──── Reasoner ────


class TestReasonerLazyLoad:
    def test_lazy_load(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        assert handler._reasoner is None
        reasoner = handler._get_reasoner()
        assert handler._reasoner is not None
        handler._SimpleCReasoner.assert_called_once()

    def test_caching(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        r1 = handler._get_reasoner()
        r2 = handler._get_reasoner()
        assert r1 is r2
        handler._SimpleCReasoner.assert_called_once()


class TestZReasoner:
    def test_z_reasoner_success(self, mock_initializer, mock_jpype):
        jpype_mock, _ = mock_jpype
        handler = CLHandler(mock_initializer)
        z = handler._try_load_z_reasoner()
        assert handler._z_reasoner is not None

    def test_z_reasoner_caching(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        z1 = handler._try_load_z_reasoner()
        z2 = handler._try_load_z_reasoner()
        assert z1 is z2

    def test_z_reasoner_unavailable(self, mock_initializer, mock_jpype):
        jpype_mock, _ = mock_jpype
        # Make the ZReasoner class loading fail
        original_side_effect = jpype_mock.JClass.side_effect

        def failing_jclass(name):
            if "ZReasoner" in name:
                raise Exception("ZReasoner not found")
            return original_side_effect(name)

        handler = CLHandler(mock_initializer)
        jpype_mock.JClass.side_effect = failing_jclass

        with pytest.raises(RuntimeError, match="ZReasoner not available"):
            handler._try_load_z_reasoner()


# ──── Query Reasoning ────


class TestQuery:
    def test_accepted(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        mock_reasoner = MagicMock()
        mock_reasoner.query.return_value = True
        handler._SimpleCReasoner.return_value = mock_reasoner

        kb = MagicMock()
        result, msg = handler.query(kb, "flies", "bird")
        assert result is True
        assert "ACCEPTED" in msg

    def test_rejected(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        mock_reasoner = MagicMock()
        mock_reasoner.query.return_value = False
        handler._SimpleCReasoner.return_value = mock_reasoner

        kb = MagicMock()
        result, msg = handler.query(kb, "flies", "penguin")
        assert result is False
        assert "REJECTED" in msg

    def test_unconditional_query(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        mock_reasoner = MagicMock()
        mock_reasoner.query.return_value = True
        handler._SimpleCReasoner.return_value = mock_reasoner

        kb = MagicMock()
        result, msg = handler.query(kb, "bird")
        assert result is True
        assert "ACCEPTED" in msg

    def test_jexception(self, mock_initializer, mock_jpype):
        jpype_mock, _ = mock_jpype
        handler = CLHandler(mock_initializer)
        mock_reasoner = MagicMock()
        exc = jpype_mock.JException("CL error")
        exc.getMessage = MagicMock(return_value="CL error")
        mock_reasoner.query.side_effect = exc
        handler._SimpleCReasoner.return_value = mock_reasoner

        kb = MagicMock()
        result, msg = handler.query(kb, "flies", "bird")
        assert result is False
        assert "FUNC_ERROR" in msg

    def test_unexpected_error(self, mock_initializer, mock_jpype):
        handler = CLHandler(mock_initializer)
        mock_reasoner = MagicMock()
        mock_reasoner.query.side_effect = ValueError("unexpected")
        handler._SimpleCReasoner.return_value = mock_reasoner

        kb = MagicMock()
        result, msg = handler.query(kb, "flies", "bird")
        assert result is False
        assert "FUNC_ERROR" in msg


class TestParseAndQuery:
    def test_accepted(self, mock_initializer, mock_jpype):
        jpype_mock, _ = mock_jpype
        handler = CLHandler(mock_initializer)

        mock_parser = MagicMock()
        handler._ClParser.return_value = mock_parser

        mock_reasoner = MagicMock()
        mock_reasoner.query.return_value = True
        handler._SimpleCReasoner.return_value = mock_reasoner

        result, msg = handler.parse_and_query("kb_str", "query_str")
        assert result is True
        assert "ACCEPTED" in msg

    def test_rejected(self, mock_initializer, mock_jpype):
        jpype_mock, _ = mock_jpype
        handler = CLHandler(mock_initializer)

        mock_parser = MagicMock()
        handler._ClParser.return_value = mock_parser

        mock_reasoner = MagicMock()
        mock_reasoner.query.return_value = False
        handler._SimpleCReasoner.return_value = mock_reasoner

        result, msg = handler.parse_and_query("kb", "q")
        assert result is False
        assert "REJECTED" in msg

    def test_jexception(self, mock_initializer, mock_jpype):
        jpype_mock, _ = mock_jpype
        handler = CLHandler(mock_initializer)

        mock_parser = MagicMock()
        mock_parser.parseBeliefBase.side_effect = jpype_mock.JException("parse error")
        handler._ClParser.return_value = mock_parser

        result, msg = handler.parse_and_query("bad", "q")
        assert result is False
        assert "FUNC_ERROR" in msg

    def test_unexpected_error(self, mock_initializer, mock_jpype):
        jpype_mock, _ = mock_jpype
        handler = CLHandler(mock_initializer)

        mock_parser = MagicMock()
        mock_parser.parseBeliefBase.side_effect = ValueError("unexpected")
        handler._ClParser.return_value = mock_parser

        result, msg = handler.parse_and_query("bad", "q")
        assert result is False
        assert "FUNC_ERROR" in msg


# ──── Static Methods ────


class TestStaticMethods:
    def test_supported_reasoners(self):
        reasoners = CLHandler.supported_reasoners()
        assert "simple" in reasoners
        assert "z_reasoner" in reasoners
        assert len(reasoners) == 2
