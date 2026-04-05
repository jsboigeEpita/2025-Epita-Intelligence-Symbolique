"""
Tests for ATMSPlugin — 4 kernel functions wrapping atms_core.ATMS.

No JVM, no async sessions. Pure Python ATMS core.
"""

import json
import pytest

from argumentation_analysis.plugins.atms_plugin import ATMSPlugin


@pytest.fixture
def plugin():
    return ATMSPlugin()


def _parse(result: str) -> dict:
    return json.loads(result)


# ---------------------------------------------------------------------------
# atms_create_assumption
# ---------------------------------------------------------------------------


class TestCreateAssumption:
    def test_basic_creation(self, plugin):
        result = _parse(plugin.atms_create_assumption("rain", "It is raining"))
        assert result["success"] is True
        assert result["node"] == "rain"
        assert result["is_assumption"] is True
        assert result["environments"] == [["rain"]]

    def test_multiple_assumptions(self, plugin):
        plugin.atms_create_assumption("a")
        plugin.atms_create_assumption("b")
        result = _parse(plugin.atms_create_assumption("c"))
        assert result["success"] is True

    def test_duplicate_assumption(self, plugin):
        plugin.atms_create_assumption("a")
        result = _parse(plugin.atms_create_assumption("a"))
        assert result["success"] is True
        assert result["environments"] == [["a"]]


# ---------------------------------------------------------------------------
# atms_add_justification
# ---------------------------------------------------------------------------


class TestAddJustification:
    def test_simple_derivation(self, plugin):
        plugin.atms_create_assumption("a")
        plugin.atms_create_assumption("b")
        plugin.atms_add_justification("c", "a,b")
        result = _parse(plugin.atms_enumerate_labels("c"))
        assert result["success"] is True
        assert ["a", "b"] in result["minimal_environments"]

    def test_auto_creates_nodes(self, plugin):
        plugin.atms_create_assumption("a")
        result = _parse(plugin.atms_add_justification("c", "a"))
        assert result["success"] is True
        assert result["consequent"] == "c"

    def test_with_out_nodes(self, plugin):
        plugin.atms_create_assumption("a")
        plugin.atms_create_assumption("b")
        plugin.atms_create_assumption("c")
        result = _parse(plugin.atms_add_justification("d", "a", "b"))
        assert result["success"] is True

    def test_empty_antecedents(self, plugin):
        result = _parse(plugin.atms_add_justification("tautology", ""))
        assert result["success"] is True


# ---------------------------------------------------------------------------
# atms_check_environment
# ---------------------------------------------------------------------------


class TestCheckEnvironment:
    def test_derivable_belief(self, plugin):
        plugin.atms_create_assumption("a")
        plugin.atms_create_assumption("b")
        plugin.atms_add_justification("c", "a,b")
        result = _parse(plugin.atms_check_environment("a,b"))
        assert result["success"] is True
        assert result["is_consistent"] is True
        derivable = result["derivable_beliefs"]
        assert any(b["belief"] == "c" for b in derivable)

    def test_insufficient_assumptions(self, plugin):
        plugin.atms_create_assumption("a")
        plugin.atms_create_assumption("b")
        plugin.atms_add_justification("c", "a,b")
        result = _parse(plugin.atms_check_environment("a"))
        assert result["success"] is True
        derivable = result["derivable_beliefs"]
        assert not any(b["belief"] == "c" for b in derivable)

    def test_empty_assumptions(self, plugin):
        result = _parse(plugin.atms_check_environment(""))
        assert result["success"] is True
        assert result["derivable_beliefs"] == []

    def test_contradiction_removes_nogood_env(self, plugin):
        """After a → ⊥, the nogood environment is invalidated from all labels."""
        plugin.atms_create_assumption("a")
        plugin.atms_create_assumption("b")
        plugin.atms_add_justification("c", "a,b")
        # Now make "a" lead to contradiction
        plugin.atms_add_justification("\u22a5", "a")
        # Node "c" should lose the nogood environment {a,b}
        result = _parse(plugin.atms_enumerate_labels("c"))
        assert result["success"] is True
        # After invalidation, c should have no valid environments
        assert result["minimal_environments"] == []


# ---------------------------------------------------------------------------
# atms_enumerate_labels
# ---------------------------------------------------------------------------


class TestEnumerateLabels:
    def test_assumption_label(self, plugin):
        plugin.atms_create_assumption("a")
        result = _parse(plugin.atms_enumerate_labels("a"))
        assert result["success"] is True
        assert result["is_assumption"] is True
        assert [["a"]] == result["minimal_environments"]

    def test_derived_label(self, plugin):
        plugin.atms_create_assumption("a")
        plugin.atms_add_justification("c", "a")
        result = _parse(plugin.atms_enumerate_labels("c"))
        assert result["success"] is True
        assert result["is_assumption"] is False
        assert ["a"] in result["minimal_environments"]

    def test_nonexistent_node(self, plugin):
        result = _parse(plugin.atms_enumerate_labels("ghost"))
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_justifications_in_result(self, plugin):
        plugin.atms_create_assumption("a")
        plugin.atms_create_assumption("b")
        plugin.atms_add_justification("c", "a,b")
        result = _parse(plugin.atms_enumerate_labels("c"))
        assert result["success"] is True
        assert len(result["justifications"]) == 1
        assert "a" in result["justifications"][0]["in_nodes"]


# ---------------------------------------------------------------------------
# Multi-instance isolation
# ---------------------------------------------------------------------------


class TestMultiInstance:
    def test_separate_instances(self, plugin):
        plugin.atms_create_assumption("x", instance_id="inst1")
        result = _parse(plugin.atms_enumerate_labels("x", instance_id="inst1"))
        assert result["success"] is True

        # "x" doesn't exist in default instance
        result = _parse(plugin.atms_enumerate_labels("x"))
        assert result["success"] is False

    def test_isolated_justifications(self, plugin):
        plugin.atms_create_assumption("a", instance_id="i1")
        plugin.atms_add_justification("c", "a", instance_id="i1")

        # Default instance shouldn't have "a" or "c"
        result = _parse(plugin.atms_check_environment("a"))
        assert result["success"] is True
        assert result["derivable_beliefs"] == []
