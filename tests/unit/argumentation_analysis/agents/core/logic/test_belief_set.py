# tests/unit/argumentation_analysis/agents/core/logic/test_belief_set.py
"""Tests for BeliefSet hierarchy — PropositionalBeliefSet, FirstOrderBeliefSet, ModalBeliefSet."""

import pytest

from argumentation_analysis.agents.core.logic.belief_set import (
    BeliefSet,
    PropositionalBeliefSet,
    FirstOrderBeliefSet,
    ModalBeliefSet,
)

# ── PropositionalBeliefSet ──


class TestPropositionalBeliefSet:
    def test_init(self):
        bs = PropositionalBeliefSet("a && b")
        assert bs.content == "a && b"
        assert bs.logic_type == "propositional"
        assert bs.propositions == []

    def test_init_with_propositions(self):
        bs = PropositionalBeliefSet("a && b", propositions=["a", "b"])
        assert bs.propositions == ["a", "b"]

    def test_to_dict(self):
        bs = PropositionalBeliefSet("a || b", propositions=["a", "b"])
        d = bs.to_dict()
        assert d["logic_type"] == "propositional"
        assert d["content"] == "a || b"
        assert d["propositions"] == ["a", "b"]

    def test_to_dict_empty_propositions(self):
        bs = PropositionalBeliefSet("p")
        d = bs.to_dict()
        assert d["propositions"] == []


# ── FirstOrderBeliefSet ──


class TestFirstOrderBeliefSet:
    def test_init(self):
        bs = FirstOrderBeliefSet("forall(X, p(X))")
        assert bs.content == "forall(X, p(X))"
        assert bs.logic_type == "first_order"
        assert bs.java_object is None

    def test_init_with_java_object(self):
        fake_java = object()
        bs = FirstOrderBeliefSet("content", java_object=fake_java)
        assert bs.java_object is fake_java

    def test_to_dict_excludes_java(self):
        bs = FirstOrderBeliefSet("content", java_object=object())
        d = bs.to_dict()
        assert d["logic_type"] == "first_order"
        assert d["content"] == "content"
        assert "java_object" not in d


# ── ModalBeliefSet ──


class TestModalBeliefSet:
    def test_init(self):
        bs = ModalBeliefSet("[]p => <>q")
        assert bs.content == "[]p => <>q"
        assert bs.logic_type == "modal"

    def test_to_dict(self):
        bs = ModalBeliefSet("K(a)")
        d = bs.to_dict()
        assert d["logic_type"] == "modal"
        assert d["content"] == "K(a)"


# ── BeliefSet.is_empty ──


class TestIsEmpty:
    def test_none_content(self):
        bs = PropositionalBeliefSet(None)
        assert bs.is_empty() is True

    def test_empty_string(self):
        bs = PropositionalBeliefSet("")
        assert bs.is_empty() is True

    def test_whitespace_only(self):
        bs = PropositionalBeliefSet("   ")
        assert bs.is_empty() is True

    def test_empty_braces(self):
        bs = PropositionalBeliefSet("{}")
        assert bs.is_empty() is True

    def test_empty_braces_with_spaces(self):
        bs = PropositionalBeliefSet(" { } ")
        assert bs.is_empty() is True

    def test_non_empty(self):
        bs = PropositionalBeliefSet("a && b")
        assert bs.is_empty() is False

    def test_content_with_braces(self):
        bs = PropositionalBeliefSet("{a, b}")
        assert bs.is_empty() is False


# ── BeliefSet.from_dict ──


class TestFromDict:
    def test_propositional(self):
        data = {"logic_type": "propositional", "content": "a && b"}
        bs = BeliefSet.from_dict(data)
        assert isinstance(bs, PropositionalBeliefSet)
        assert bs.content == "a && b"

    def test_propositional_with_propositions(self):
        data = {"logic_type": "propositional", "content": "a", "propositions": ["a"]}
        bs = BeliefSet.from_dict(data)
        assert isinstance(bs, PropositionalBeliefSet)
        assert bs.propositions == ["a"]

    def test_first_order(self):
        data = {"logic_type": "first_order", "content": "forall(X, p(X))"}
        bs = BeliefSet.from_dict(data)
        assert isinstance(bs, FirstOrderBeliefSet)
        assert bs.content == "forall(X, p(X))"

    def test_modal(self):
        data = {"logic_type": "modal", "content": "[]p"}
        bs = BeliefSet.from_dict(data)
        assert isinstance(bs, ModalBeliefSet)
        assert bs.content == "[]p"

    def test_unknown_type_returns_none(self):
        data = {"logic_type": "unknown", "content": "stuff"}
        assert BeliefSet.from_dict(data) is None

    def test_none_input_returns_none(self):
        assert BeliefSet.from_dict(None) is None

    def test_empty_dict_returns_none(self):
        assert BeliefSet.from_dict({}) is None

    def test_case_insensitive(self):
        data = {"logic_type": "PROPOSITIONAL", "content": "a"}
        bs = BeliefSet.from_dict(data)
        assert isinstance(bs, PropositionalBeliefSet)

    def test_missing_content_uses_empty(self):
        data = {"logic_type": "modal"}
        bs = BeliefSet.from_dict(data)
        assert isinstance(bs, ModalBeliefSet)
        assert bs.content == ""


# ── Abstract class ──


class TestAbstractBeliefSet:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BeliefSet("content")

    def test_is_abstract(self):
        import inspect

        assert inspect.isabstract(BeliefSet)
