"""#1678 — ASPIC+ attack scopes (undercut/rebut/undermine) via genuine Negation.

Pre-fix ``ASPICHandler.analyze_aspic_framework`` could only build ``Proposition``
heads — never a ``Negation`` — so the theory could never express a contrary.
An ASPIC+ attack requires a formula AND its negation; without ``Negation`` the
theory renders a single extension containing every argument (the vacuous-
evaluated trap of #1671/#1674: "non-empty" read as "arbitrated").

Coordinator #1678 measured firsthand on JVM ``83362fee`` that the three attack
scopes are reachable through ``Negation``:
  - rebutting    : conclusion negated            (``d2 : arg_b => !concl_x``)
  - undermining  : premise negated               (``d2 : arg_c => !arg_a``)
  - undercutting : rule-formula negated          (``arg_d => !d_main``)

and that the scope is **derivable from the framework structure** — never from
keywords. These tests pin that contract on the real JVM (no mock): the handler
must produce a non-empty, *justified* attack set, and qualify each by scope.

Privacy: synthetic atoms only (arg_a, concl_x, d_main) — no corpus content.
"""

from __future__ import annotations

import pytest

from argumentation_analysis.agents.core.logic.aspic_handler import ASPICHandler

pytestmark = [pytest.mark.jpype, pytest.mark.tweety]


def _handler() -> ASPICHandler:
    return ASPICHandler()  # type: ignore[no-untyped-call]


class TestAspicNegationProducesAttacks:
    """Without negation the theory is mute; with it, genuine attacks appear."""

    def test_no_negation_single_extension_no_attack(self):
        """Baseline: a positive-only theory renders ONE extension, ZERO attack.

        This is the vacuous-evaluated state #1671/#1674 label honestly — the
        axis is 'evaluated' but has arbitrated nothing. The fix must not
        regress this baseline (positive rules stay positive).
        """
        out = _handler().analyze_aspic_framework(
            strict_rules=[],
            defeasible_rules=[
                {"head": "concl_x", "body": ["arg_a"], "name": "d_main"},
            ],
            axioms=["arg_a"],
        )
        assert out["statistics"]["attacks_count"] == 0
        # One extension (the single argument is acceptable, uncontested).
        assert out["statistics"]["extensions_count"] == 1
        assert out["attacks"] == []

    def test_rebut_negated_conclusion_produces_attack(self):
        """A rule negating another rule's CONCLUSION ⇒ a rebut (symmetric pair).

        d_main : arg_a => concl_x
        d_rebut: arg_b => !concl_x   (head_negated, targets concl_x which is a head)
        """
        out = _handler().analyze_aspic_framework(
            strict_rules=[],
            defeasible_rules=[
                {"head": "concl_x", "body": ["arg_a"], "name": "d_main"},
                {
                    "head": "concl_x",
                    "body": ["arg_b"],
                    "name": "d_rebut",
                    "head_negated": True,
                },
            ],
            axioms=["arg_a", "arg_b"],
        )
        scopes = [a["scope"] for a in out["attacks"]]
        assert "rebut" in scopes, f"expected a rebut, got {scopes}"
        assert out["statistics"]["attacks_count"] >= 1
        # Two competing extensions (the rebut splits acceptability).
        assert out["statistics"]["extensions_count"] >= 2

    def test_undermine_negated_premise_produces_attack(self):
        """A rule negating another rule's PREMISE ⇒ an undermine.

        d_main     : arg_a => concl_x
        d_undermine: arg_c => !arg_a   (head_negated, targets arg_a which is a body atom)

        The attacked premise (arg_a) must be AVAILABLE for d_main to derive
        concl_x — otherwise d_main is mute and there is nothing to attack. In
        production _invoke_aspic derives leaf body atoms as ordinary premises
        (#1678 manque 1); here arg_a is supplied directly as an axiom.
        """
        out = _handler().analyze_aspic_framework(
            strict_rules=[],
            defeasible_rules=[
                {"head": "concl_x", "body": ["arg_a"], "name": "d_main"},
                {
                    "head": "arg_a",
                    "body": ["arg_c"],
                    "name": "d_undermine",
                    "head_negated": True,
                },
            ],
            axioms=["arg_a", "arg_c"],
        )
        scopes = [a["scope"] for a in out["attacks"]]
        assert "undermine" in scopes, f"expected an undermine, got {scopes}"
        assert out["statistics"]["dung_attacks_count"] >= 1

    def test_undercut_negated_rule_name_produces_attack(self):
        """A rule negating another rule's NAME ⇒ an undercut (asymmetric).

        PlFormulaGenerator.getRuleFormula(d_main) renders a Proposition named
        ``d_main``; negating that name attacks the inference itself.
        d_main    : arg_a => concl_x
        d_undercut: arg_d => !d_main   (head_negated, targets the rule name)
        """
        out = _handler().analyze_aspic_framework(
            strict_rules=[],
            defeasible_rules=[
                {"head": "concl_x", "body": ["arg_a"], "name": "d_main"},
                {
                    "head": "d_main",
                    "body": ["arg_d"],
                    "name": "d_undercut",
                    "head_negated": True,
                },
            ],
            axioms=["arg_a", "arg_d"],
        )
        scopes = [a["scope"] for a in out["attacks"]]
        assert "undercut" in scopes, f"expected an undercut, got {scopes}"

    def test_three_scopes_coexist_and_are_distinguished(self):
        """DoD item 2 — all three scopes in one framework, each distinguishable.

        Mirrors the coordinator's probe D2 (8 args / 6 attacks / 2 extensions).
        The qualification must label each negated head by its structural role,
        not collapse them.
        """
        out = _handler().analyze_aspic_framework(
            strict_rules=[],
            defeasible_rules=[
                {"head": "concl_x", "body": ["arg_a"], "name": "d_main"},
                {
                    "head": "concl_x",
                    "body": ["arg_b"],
                    "name": "d_rebut",
                    "head_negated": True,
                },
                {
                    "head": "arg_a",
                    "body": ["arg_c"],
                    "name": "d_undermine",
                    "head_negated": True,
                },
                {
                    "head": "d_main",
                    "body": ["arg_d"],
                    "name": "d_undercut",
                    "head_negated": True,
                },
            ],
            axioms=["arg_a", "arg_b", "arg_c", "arg_d"],
        )
        scopes = {a["scope"] for a in out["attacks"]}
        assert {"rebut", "undermine", "undercut"}.issubset(
            scopes
        ), f"the three scopes must coexist and be distinguished, got {scopes}"
