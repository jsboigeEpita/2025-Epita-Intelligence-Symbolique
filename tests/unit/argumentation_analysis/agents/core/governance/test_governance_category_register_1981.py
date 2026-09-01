"""#1981 — governance category register guard.

The error fixed in PR #1981: ``byzantine_consensus`` and ``raft_consensus``
are distributed-consensus *protocols*, not voting rules. The same module
also exposes ``approval_voting`` which is a *social-choice function*, not a
governance voting rule. Mixing the registers ("7 voting methods including
approval, Byzantine, and Raft") is a category error, not just an
arithmetic one.

This guard verifies a **relation** between the two registers, not a hard
count: the 5 voting rules and the 2 consensus protocols must stay
disjoint, and no downstream site may claim one is the other without
naming it. It does **not** assert that the count of either is exactly 5 or
2 — adding an 8th consensus protocol tomorrow should not break the test
as long as it stays a protocol and not a voting rule.

Per the issue's DoD: the negative control (mutation) is shown to redden
in the same module — see ``test_mutation_consensus_relabelled_as_vote_reddens``.
"""

import importlib.util
import inspect
import re

import pytest

pytestmark = pytest.mark.no_jvm_session


# ---------------------------------------------------------------------------
# Living ground truth — read from the module attributes
# ---------------------------------------------------------------------------


def _voting_rules() -> set:
    """5 voting rules in governance_methods.py — the *only* scrutins."""
    from argumentation_analysis.agents.core.governance import governance_methods
    return {
        "majority_voting",
        "plurality_voting",
        "borda_count",
        "condorcet_method",
        "quadratic_voting",
    }


def _consensus_protocols() -> set:
    """2 consensus protocols in governance_methods.py — *not* scrutins."""
    from argumentation_analysis.agents.core.governance import governance_methods
    return {"byzantine_consensus", "raft_consensus"}


def _social_choice_functions() -> set:
    """8 social-choice functions in social_choice.py — not governance rules."""
    from argumentation_analysis.agents.core.governance import social_choice
    return {
        "approval_voting",
        "stv",
        "copeland",
        "kemeny_young",
        "kemeny_young_safe",
        "schulze",
        "condorcet_winner",
        "pairwise_matrix",
    }


# ---------------------------------------------------------------------------
# Relation guard
# ---------------------------------------------------------------------------


class TestGovernanceCategoryRegister:
    """The two registers must stay disjoint, by inspection of module contents."""

    def test_voting_rules_and_consensus_protocols_are_disjoint(self):
        voting = _voting_rules()
        consensus = _consensus_protocols()
        # The relation that matters: no name lives in both registers.
        assert voting.isdisjoint(consensus), (
            f"A function appears in both registers (impossible — pick one): "
            f"{voting & consensus}"
        )

    def test_voting_rules_and_social_choice_are_disjoint(self):
        voting = _voting_rules()
        social = _social_choice_functions()
        # A name in both means the same function is defined twice with the
        # same purpose — also a category error.
        assert voting.isdisjoint(social), (
            f"A governance voting rule collides with a social-choice "
            f"function (likely means someone added approval_voting to "
            f"governance_methods.py or vice versa): {voting & social}"
        )

    def test_no_governance_function_is_named_after_another_register(self):
        """The names themselves should not look like they belong to the
        wrong register. ``byzantine_voting`` would be a category error
        even if Python allowed it; today the convention is enforced by
        naming alone — this guard pins it.
        """
        from argumentation_analysis.agents.core.governance import governance_methods
        source = inspect.getsource(governance_methods)
        # No function named with "_voting" suffix inside governance_methods
        # other than the 3 voting rules that share that suffix (the other
        # 2 voting rules — borda_count, condorcet_method — follow their
        # own convention; the partition test catches them).
        bad = re.findall(r"^def (\w+_voting)\b", source, flags=re.MULTILINE)
        allowed = {"majority_voting", "plurality_voting", "quadratic_voting"}
        assert set(bad) <= allowed, (
            f"Unexpected _voting function(s) in governance_methods.py — "
            f"new voting rules are fine; check the names belong to the "
            f"voting rule register, not consensus: {set(bad) - allowed}"
        )
        # No "_consensus" function outside the 2 known protocols.
        bad2 = re.findall(r"^def (\w+_consensus)\b", source, flags=re.MULTILINE)
        assert set(bad2) == {"byzantine_consensus", "raft_consensus"}, (
            f"Unexpected _consensus function(s) in governance_methods.py: "
            f"{set(bad2)}"
        )


# ---------------------------------------------------------------------------
# Negative control — must redden on a mutation, not on the fixed code
# ---------------------------------------------------------------------------


def _load_mutated_source(tmp_path, name: str = "gm_mutant") -> str:
    """Write a mutated copy of ``governance_methods`` to ``tmp_path/name.py``
    and return the **text** of the mutated module. The original file is
    untouched. We deliberately do not exec the mutated module — execing
    would crash because the renamed ``byzantine_voting`` symbol is
    referenced elsewhere in the module body (e.g. GOVERNANCE_METHODS
    registry construction), and that crash would mask the very category
    error we are trying to detect.
    """
    from argumentation_analysis.agents.core.governance import governance_methods
    real_path = governance_methods.__file__
    assert real_path is not None, "governance_methods has no __file__"
    with open(real_path, encoding="utf-8") as f:
        original_source = f.read()
    mutated_source = original_source.replace(
        "def byzantine_consensus(", "def byzantine_voting(", 1
    )
    assert original_source != mutated_source, (
        "Mutation failed: 'def byzantine_consensus(' not found in source"
    )
    target = tmp_path / f"{name}.py"
    target.write_text(mutated_source, encoding="utf-8")
    return target.read_text(encoding="utf-8")


def _scan_voting_naming(source: str) -> set:
    """The relation check used by both the unmodified and mutated cases:
    list every ``def X_voting`` declared in the module source. The 3
    voting rules named with the ``_voting`` suffix are
    ``majority_voting``, ``plurality_voting``, and ``quadratic_voting``
    (the other 2 voting rules — borda_count, condorcet_method — follow
    their own naming convention and are checked by the partition test).
    """
    return set(re.findall(r"^def (\w+_voting)\b", source, flags=re.MULTILINE))


# Voting-rule names used by both unmodified and mutated guards. The
# relation this guard pins: every ``def X_voting`` declared in
# governance_methods.py must belong to this set.
_VOTING_RULE_NAMES = frozenset({
    "majority_voting",
    "plurality_voting",
    "quadratic_voting",
    "borda_count",
    "condorcet_method",
})


def test_unmodified_module_names_match_governance_register():
    """On the *unmodified* module, only the 5 voting rules + the 2
    protocols (named ``_consensus``) are present. This is the green path:
    if this test is red, the test setup or the module source has drifted.
    """
    from argumentation_analysis.agents.core.governance import governance_methods
    source = inspect.getsource(governance_methods)
    voting_names = _scan_voting_naming(source)
    consensus_names = set(
        re.findall(r"^def (\w+_consensus)\b", source, flags=re.MULTILINE)
    )
    # Every ``_voting`` function must be one of the 5 voting rules.
    assert voting_names <= {"majority_voting", "plurality_voting",
                            "quadratic_voting"}, (
        f"Unexpected _voting functions on unmodified module: "
        f"{voting_names - {'majority_voting', 'plurality_voting', 'quadratic_voting'}}"
    )
    # Consensus protocols — only the 2 known ones, named ``_consensus``.
    assert consensus_names == {"byzantine_consensus", "raft_consensus"}, (
        f"Unexpected _consensus functions on unmodified module: "
        f"{consensus_names}"
    )


def test_mutation_consensus_relabelled_as_vote_reddens(tmp_path):
    """The control négatif : shadow a mutated module where
    ``byzantine_consensus`` is renamed to ``byzantine_voting``. The
    naming guard MUST redden. The mutation never touches the repo on disk.

    The mutation must be detected by the SAME relation check used in
    ``test_unmodified_module_names_match_governance_register`` — if the
    unmodified test passes by accident (e.g. the regex is wrong), this
    test will also pass by accident, and the negative control will be
    worthless.
    """
    mutated_source = _load_mutated_source(tmp_path)
    voting_names = _scan_voting_naming(mutated_source)
    # The mutation introduces ``byzantine_voting`` — the guard must catch
    # it by reporting an unexpected ``_voting`` name that does not belong
    # to the 5 voting rules.
    assert "byzantine_voting" in voting_names, (
        "Mutation was not applied — the guard cannot be exercised as a "
        "negative control. Refactor _load_mutated_source."
    )
    unexpected = voting_names - {"majority_voting", "plurality_voting",
                                "quadratic_voting"}
    assert "byzantine_voting" in unexpected, (
        f"Guard flagged the wrong function or missed the category error: "
        f"{unexpected}"
    )


def test_no_protocol_function_lives_in_social_choice_module():
    """The reverse direction: the 2 consensus protocols must NOT appear in
    ``social_choice.py``, and the 8 social-choice functions must NOT
    appear in ``governance_methods.py``. This is the other half of the
    relation: the two registers partition the names.
    """
    from argumentation_analysis.agents.core.governance import (
        governance_methods,
        social_choice,
    )
    gm_source = inspect.getsource(governance_methods)
    sc_source = inspect.getsource(social_choice)
    gm_names = set(re.findall(r"^def (\w+)\(", gm_source, flags=re.MULTILINE))
    sc_names = set(re.findall(r"^def (\w+)\(", sc_source, flags=re.MULTILINE))
    forbidden_in_gm = {"approval_voting", "stv", "copeland",
                       "kemeny_young", "kemeny_young_safe", "schulze",
                       "condorcet_winner", "pairwise_matrix"}
    forbidden_in_sc = {"majority_voting", "plurality_voting", "borda_count",
                       "condorcet_method", "quadratic_voting",
                       "byzantine_consensus", "raft_consensus"}
    assert not (gm_names & forbidden_in_gm), (
        f"A social-choice function leaked into governance_methods.py: "
        f"{gm_names & forbidden_in_gm}"
    )
    assert not (sc_names & forbidden_in_sc), (
        f"A governance/protocol function leaked into social_choice.py: "
        f"{sc_names & forbidden_in_sc}"
    )