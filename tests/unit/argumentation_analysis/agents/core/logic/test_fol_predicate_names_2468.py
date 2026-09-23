# -*- coding: utf-8 -*-
"""
#2468 — every FOL belief set declares names the Tweety parser accepts, and its
formulas use the names it declares.

Measured on the real JVM (``TweetyBridge.check_consistency(..., "first_order")``):
a predicate declaration must match ``[A-Za-z][A-Za-z0-9]*`` (``A_Fait`` is
rejected, ``AFait`` and ``isvalid`` are accepted); a constant must start with a
letter (``_t_`` is rejected, ``jean_paul``, ``ren_`` and ``c_42`` are accepted).

Two defects on ``main``:
- ``extract_fol_metadata`` sanitised predicate names to ``_``, the one
  character the declaration grammar rejects, and an accented first letter of a
  constant to ``_`` (``été`` → ``_t_``);
- the belief sets built by the agent (``build_signature_prefixed_formulas``) and
  by the external-solver phase prepended the signature to the formulas without
  renaming them, so a sanitised declaration never matched its uses.

One function now returns the signature and the formulas renamed to it
(``extract_fol_metadata(...)["formulas"]``). The tests below read every belief
set a call site sends to the solver, through a bridge double: no JVM, no LLM.
"""

import ast
import asyncio
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent

TWEETY_BRIDGE_PATH = (
    "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge"
)

# LLM-shaped formulas: an underscore, accented predicates, a hyphenated
# constant, and a constant whose first letter is accented.
LLM_FORMULAS = [
    "forall X: (A_Fait(X) => Mortel(X))",
    "A_Fait(socrate)",
    "forall X: (Évalue(X) => EstPrésident(X))",
    "Évalue(jean-paul)",
    "est_valide(été)",
]

_PRED_DECL = re.compile(r"^type\((?P<name>[^()]+)\((?P<sorts>[^()]*)\)\)$")
_SORT_DECL = re.compile(r"^(?P<sort>\w+)\s*=\s*\{(?P<consts>[^}]*)\}$")
_LEGAL_PREDICATE = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
_LEGAL_CONSTANT = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_APPLICATION = re.compile(r"([^\s(),:!&|=>]+)\(([^()]*)\)")


def grammar_violations(belief_set: str):
    """What the Tweety FOL parser would refuse in ``belief_set``: an illegal
    predicate or constant declaration, and a predicate or constant used in a
    formula without being declared."""
    predicates, constants, body, found = set(), set(), [], []
    for line in (raw.strip() for raw in belief_set.splitlines()):
        if not line:
            continue
        decl = _PRED_DECL.match(line)
        if decl:
            predicates.add(decl["name"])
            if not _LEGAL_PREDICATE.match(decl["name"]):
                found.append(f"illegal predicate declaration {decl['name']!r}")
            continue
        sort = _SORT_DECL.match(line)
        if sort:
            for const in filter(None, (c.strip() for c in sort["consts"].split(","))):
                constants.add(const)
                if not _LEGAL_CONSTANT.match(const):
                    found.append(f"illegal constant declaration {const!r}")
            continue
        body.append(line)
    for formula in body:
        for app in _APPLICATION.finditer(formula):
            if app.group(1) not in predicates:
                found.append(f"undeclared predicate {app.group(1)!r}")
            for arg in (a.strip() for a in app.group(2).split(",")):
                if arg and not arg[0].isupper() and arg not in constants:
                    found.append(f"undeclared constant {arg!r}")
    return found


def _recording_bridge(verdict):
    """A bridge double that keeps every belief set it is asked to check."""
    seen = []

    def check(belief_set, logic_type):
        seen.append(belief_set)
        return verdict, "bridge double"

    def check_by(belief_set, solver=None):
        seen.append(belief_set)
        return verdict, "bridge double", "tweety"

    bridge = MagicMock()
    bridge.check_consistency.side_effect = check
    # #2482: the external FOL phase asks the handler, which names its solver.
    bridge.fol_handler.check_consistency_by.side_effect = check_by
    return bridge, seen


def test_the_checker_sees_what_the_parser_refuses():
    """Control: the checker flags each case measured on the real parser."""
    assert (
        grammar_violations("thing = {socrate}\ntype(AFait(thing))\n\nAFait(socrate)")
        == []
    )
    assert grammar_violations(
        "thing = {socrate}\ntype(A_Fait(thing))\n\nA_Fait(socrate)"
    )
    assert grammar_violations("thing = {_t_}\ntype(Homme(thing))\n\nHomme(_t_)")
    assert grammar_violations(
        "thing = {socrate}\ntype(AFait(thing))\n\nA_Fait(socrate)"
    )


def test_the_agent_belief_set_parses():
    lines = FOLLogicAgent.build_signature_prefixed_formulas(LLM_FORMULAS)
    assert grammar_violations("\n".join(lines)) == []
    # Nothing is dropped: one formula line per input formula.
    assert (
        lines[-len(LLM_FORMULAS) :]
        == FOLLogicAgent.extract_fol_metadata(LLM_FORMULAS)["formulas"]
    )


def test_accents_are_folded_not_dropped():
    meta = FOLLogicAgent.extract_fol_metadata(LLM_FORMULAS)
    assert meta["predicate_map"]["Évalue"] == "Evalue"
    assert meta["predicate_map"]["EstPrésident"] == "EstPresident"
    assert meta["predicate_map"]["A_Fait"] == "AFait"
    assert meta["constant_map"]["été"] == "ete"
    # A name the grammar accepts keeps itself.
    assert meta["predicate_map"]["Mortel"] == "Mortel"
    assert meta["constant_map"]["socrate"] == "socrate"


def test_renaming_never_merges_two_names():
    """``A_Fait`` folds to ``AFait``, which the formulas already use: the two
    stay distinct predicates, so ``A_Fait(b)`` / ``!AFait(b)`` stays
    consistent instead of becoming a contradiction."""
    formulas = ["A_Fait(b)", "!AFait(b)", "P(jean-paul)", "!P(jean_paul)"]
    meta = FOLLogicAgent.extract_fol_metadata(formulas)

    assert meta["predicate_map"]["AFait"] == "AFait"
    assert meta["predicate_map"]["A_Fait"] != "AFait"
    assert meta["constant_map"]["jean_paul"] == "jean_paul"
    assert meta["constant_map"]["jean-paul"] != "jean_paul"
    renamed = meta["formulas"]
    assert renamed[0] != renamed[1].lstrip("!")
    assert renamed[2] != renamed[3].lstrip("!")
    assert grammar_violations("\n".join(meta["signature_lines"] + [""] + renamed)) == []


def test_renaming_is_idempotent():
    meta = FOLLogicAgent.extract_fol_metadata(LLM_FORMULAS)
    again = FOLLogicAgent.extract_fol_metadata(meta["formulas"])
    assert again["formulas"] == meta["formulas"]
    assert all(k == v for k, v in again["predicate_map"].items())
    assert all(k == v for k, v in again["constant_map"].items())


def test_constant_collisions_resolve_in_a_fixed_order():
    """The constants are a set; their renaming used to follow its iteration
    order, which string hashing randomises per process."""
    meta = FOLLogicAgent.extract_fol_metadata(["P(a-b, a b, a_b)"])
    assert meta["constant_map"] == {"a_b": "a_b", "a b": "a_b_v2", "a-b": "a_b_v3"}


@pytest.mark.parametrize("verdict", [True, None], ids=["decided", "isolation"])
def test_the_pipeline_phase_sends_parseable_belief_sets(verdict):
    """``_invoke_fol_reasoning`` checks the combined belief set, and on a
    ``None`` verdict re-checks each formula alone (#1630). Every one of those
    belief sets must parse."""
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_fol_reasoning,
    )

    context = {
        "phase_extract_output": {"arguments": [{"text": "an argument"}]},
        "formulas": list(LLM_FORMULAS),
        "_state_object": None,
    }
    bridge, seen = _recording_bridge(verdict)
    with patch(TWEETY_BRIDGE_PATH, return_value=bridge):
        result = asyncio.new_event_loop().run_until_complete(
            _invoke_fol_reasoning("text", context)
        )

    assert seen
    if verdict is None:
        assert len(seen) > 1, "the isolation net did not run"
    for belief_set in seen:
        assert grammar_violations(belief_set) == [], belief_set
    reported = "\n".join(result["fol_signature"] + [""] + result["formulas"])
    assert grammar_violations(reported) == []


def test_the_external_solver_phase_sends_a_parseable_belief_set():
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_external_fol_solver,
    )

    context = {
        "fol_solver": "tweety",
        "phase_fol_output": {"formulas": list(LLM_FORMULAS), "fol_signature": []},
    }
    bridge, seen = _recording_bridge(True)
    with patch(TWEETY_BRIDGE_PATH, return_value=bridge):
        result = asyncio.new_event_loop().run_until_complete(
            _invoke_external_fol_solver("text", context)
        )

    assert result["solver"] == "tweety"
    assert len(seen) == 1
    assert grammar_violations(seen[0]) == [], seen[0]


def test_one_function_renames():
    """The pipeline used to carry its own renaming loop over
    ``predicate_map``/``constant_map``. It now reads the renamed formulas from
    ``extract_fol_metadata``: no call site reads those maps to rename again."""
    source = (
        Path(__file__).resolve().parents[6]
        / "argumentation_analysis"
        / "orchestration"
        / "invoke_callables.py"
    ).read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    readers = [
        node.lineno
        for node in ast.walk(tree)
        if (
            isinstance(node, ast.Constant)
            and node.value in ("predicate_map", "constant_map")
        )
        or (isinstance(node, ast.Name) and node.id in ("predicate_map", "constant_map"))
    ]
    assert readers == []
