"""Tests for W1 input-shaping helpers (#1169).

Validates the deterministic mapping from spectacular's canonical context
(arguments: List[str], attacks: List[List[str]] pairs) into the typed
structures each Dung-family Tweety handler expects. These contract tests
capture the exact format the handlers require — same regression-guard
pattern as E1b's ``test_dict_arguments_passed_as_list_of_dicts`` (#1168).

Without these mappers the handlers raised on signature/type mismatch
(setaf wanted Dict{attackers,target}, weighted wanted Tuple triples,
aba wanted {head,body} dicts, eaf wanted Dict[agent,List] not floats).
"""

import pytest

from argumentation_analysis.orchestration.invoke_callables import (
    _setaf_attacks_from_pairs,
    _weighted_attacks_from_pairs,
    _aba_rules_from_context,
    _adf_conditions_from_context,
    _eaf_beliefs_from_context,
)


# ============================================================
# _setaf_attacks_from_pairs
# ============================================================


class TestSetafShaping:
    def test_pairs_become_singleton_attacker_sets(self):
        out = _setaf_attacks_from_pairs([["b", "a"], ["c", "b"]])
        assert out == [
            {"attackers": ["b"], "target": "a"},
            {"attackers": ["c"], "target": "b"},
        ]

    def test_empty_input(self):
        assert _setaf_attacks_from_pairs([]) == []

    def test_malformed_pairs_skipped(self):
        out = _setaf_attacks_from_pairs([["only_one"], ["b", "a"]])
        assert out == [{"attackers": ["b"], "target": "a"}]


# ============================================================
# _weighted_attacks_from_pairs
# ============================================================


class TestWeightedShaping:
    def test_pairs_become_triples_with_default_weight(self):
        out = _weighted_attacks_from_pairs([["b", "a"]])
        assert out == [("b", "a", 0.5)]

    def test_explicit_weights_by_pair_key(self):
        weights = {"b->a": 0.9}
        out = _weighted_attacks_from_pairs([["b", "a"], ["c", "b"]], weights)
        assert out == [("b", "a", 0.9), ("c", "b", 0.5)]

    def test_custom_default_weight(self):
        out = _weighted_attacks_from_pairs([["b", "a"]], default_weight=0.7)
        assert out == [("b", "a", 0.7)]


# ============================================================
# _aba_rules_from_context
# ============================================================


class TestAbaShaping:
    def test_derives_assumptions_and_rules_from_arguments(self):
        # 4 args: first 3 become assumptions, 4th gets a supporting rule.
        assumptions, rules = _aba_rules_from_context(
            ["claim_a", "claim_b", "claim_c", "claim_d"], {}
        )
        assert assumptions == ["claim_a", "claim_b", "claim_c"]
        # Non-assumption arg gets a rule concluding it from an assumption.
        assert {"head": "claim_d", "body": ["claim_a"]} in rules

    def test_all_assumptions_still_gets_a_rule(self):
        # When every arg is an assumption, at least one self-rule keeps the
        # theory non-empty (so the reasoner has something to compute).
        assumptions, rules = _aba_rules_from_context(["only_one"], {})
        assert assumptions == ["only_one"]
        assert len(rules) >= 1

    def test_explicit_rules_win(self):
        ctx = {
            "assumptions": ["x"],
            "rules": [{"head": "y", "body": ["x", "z"]}],
        }
        assumptions, rules = _aba_rules_from_context(["a", "b"], ctx)
        assert assumptions == ["x"]
        assert rules == [{"head": "y", "body": ["x", "z"]}]


# ============================================================
# _adf_conditions_from_context
# ============================================================


class TestAdfShaping:
    def test_attacked_statements_get_contradiction(self):
        ctx = {"attacks": [["b", "a"]]}
        statements, conditions = _adf_conditions_from_context(
            ["a", "b"], ctx
        )
        assert statements == ["a", "b"]
        assert conditions["a"] == "F"  # a is attacked -> contradiction
        assert conditions["b"] == "T"  # b is not attacked -> tautology

    def test_explicit_conditions_override(self):
        ctx = {"acceptance_conditions": {"a": "b && c"}}
        _, conditions = _adf_conditions_from_context(["a"], ctx)
        assert conditions == {"a": "b && c"}


# ============================================================
# _eaf_beliefs_from_context
# ============================================================


class TestEafShaping:
    def test_returns_none_when_no_beliefs(self):
        # None is the valid baseline — handler defaults to "all believed".
        assert _eaf_beliefs_from_context(["a", "b"], {}) is None

    def test_float_beliefs_become_thresholded_agent(self):
        ctx = {"epistemic_beliefs": {"a": 0.9, "b": 0.3}}
        out = _eaf_beliefs_from_context(["a", "b"], ctx)
        # Only beliefs >= 0.5 are kept (no fabricated confidence).
        assert out == {"agent_0": ["a"]}

    def test_already_correct_shape_passes_through(self):
        ctx = {"epistemic_beliefs": {"agent1": ["a", "b"]}}
        out = _eaf_beliefs_from_context(["a", "b"], ctx)
        assert out == {"agent1": ["a", "b"]}
