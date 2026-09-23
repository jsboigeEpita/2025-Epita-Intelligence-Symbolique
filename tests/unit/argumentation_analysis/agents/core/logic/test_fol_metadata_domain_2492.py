# -*- coding: utf-8 -*-
"""#2492: ``extract_fol_metadata(..., domain=...)`` declares a larger set's
constants next to the formula's own.

The FOL phase's isolation net checks each formula alone. Built from that
formula's constants only, a universal rule has none and its sort is
``thing = {}``, which Tweety refuses. The builder now takes the set's
constants as the domain. Pure string checks: no JVM.
"""

import pytest

from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent

RULE = "forall X: (Man(X) => Mortal(X))"


def test_the_domain_fills_the_sort_of_a_formula_without_constants():
    meta = FOLLogicAgent.extract_fol_metadata([RULE], domain={"socrates", "plato"})

    assert meta["signature_lines"][0] == "thing = {plato, socrates}"
    assert meta["constants"] == {"plato", "socrates"}


def test_the_domain_adds_no_predicate_and_renames_nothing():
    """The predicates and their arities stay the formula's own, so an arity
    another formula of the set contradicts is not charged to this one."""
    alone = FOLLogicAgent.extract_fol_metadata(["Man(socrates)"])
    with_domain = FOLLogicAgent.extract_fol_metadata(
        ["Man(socrates)"], domain={"socrates", "plato"}
    )

    assert with_domain["predicates"] == alone["predicates"] == {"Man": 1}
    assert with_domain["signature_lines"][1:] == alone["signature_lines"][1:]
    assert with_domain["formulas"] == alone["formulas"] == ["Man(socrates)"]


def test_the_domain_joins_the_formula_s_own_constants():
    meta = FOLLogicAgent.extract_fol_metadata(["Man(xanthippe)"], domain={"socrates"})

    assert meta["signature_lines"][0] == "thing = {socrates, xanthippe}"


def test_the_constants_of_a_whole_set_are_a_valid_domain():
    """What the isolation net passes: the ``constants`` of a call on the set,
    renamed names included."""
    formulas = [RULE, "Man(jean-paul)", "Man(jean_paul)"]
    set_meta = FOLLogicAgent.extract_fol_metadata(formulas)

    meta = FOLLogicAgent.extract_fol_metadata(
        [set_meta["formulas"][0]], domain=set_meta["constants"]
    )

    assert meta["constants"] == set_meta["constants"]
    assert meta["signature_lines"][0] == set_meta["signature_lines"][0]


@pytest.mark.parametrize("name", ["jean-paul", "_t_", "42", ""])
def test_a_domain_name_tweety_refuses_raises(name):
    """The domain comes from the caller's code, not from a model: a name the
    grammar refuses is the caller's defect, so it raises instead of being
    renamed or dropped."""
    with pytest.raises(ValueError, match="legal Tweety constants"):
        FOLLogicAgent.extract_fol_metadata([RULE], domain={"socrates", name})


def test_no_domain_keeps_the_formula_s_own_constants():
    meta = FOLLogicAgent.extract_fol_metadata(["Man(socrates)"])

    assert meta["signature_lines"][0] == "thing = {socrates}"
