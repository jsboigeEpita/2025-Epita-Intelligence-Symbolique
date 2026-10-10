# -*- coding: utf-8 -*-
"""#2968 — census guard over the counter-target linkage idioms (#1842 shape).

A target link is an identity that travels — the unit's own id — never a
position and never an unrestricted substring. This guard re-derives, by AST,
the census of live linkage idioms across the two orchestration modules and
reddens when a site of a banned idiom appears that the census does not
carry: the next positional or substring resolver cannot land silently.

Banned idioms (a hit reddens unless the census carries it with a reason):

* **D1 min-positional** — ``min(<enum var…>, len(<arg list>) …)``: a target
  index derived from an enumeration position.
* **D2 positional subscript** — ``<arg list>[<bare enum var>]``: a target
  read at the enumeration position (an id-resolved index — a name like
  ``target_idx`` assigned from a lookup — is an identity read, not this).
* **D3 unrestricted target substring** — a function that reads a
  ``target_argument``/``target_text`` key AND lowers one side of an ``in``
  compare AND carries no ``>= 20`` length guard.

Deliberately NOT banned, and why (measured, not assumed):

* id mints ``f"arg_{i+1}"`` on stateless fallback paths — where no caller
  supplies ids, the positional mint is the only identity that exists (the
  documented extract-era convention); none of them resolves a counter
  target. A mint that fed a target lookup would trip D3/D2 first.
* ``arguments[index]`` inside ``_resolve_target_argument_id`` — the index
  comes from parsing an ``arg_N`` identifier, i.e. it IS the identity.
"""

import ast
import inspect
import textwrap
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest

from argumentation_analysis.orchestration import invoke_callables, state_writers

_MODULES = {
    "invoke_callables.py": Path(inspect.getfile(invoke_callables)),
    "state_writers.py": Path(inspect.getfile(state_writers)),
}

_ARG_LISTS = {"arg_names", "arg_beliefs", "arguments", "args", "arg_ids"}
_ENUM_VARS = {"i", "idx"}
_TARGET_KEYS = ("target_argument", "target_text")

# The live sites. A site leaves this census only by changing code — editing
# this map to absorb a new hit is the failure mode this guard exists for.
_CENSUS: Dict[Tuple[str, str, str], str] = {
    (
        "invoke_callables.py",
        "_invoke_atms",
        "D1",
    ): (
        "claims support slice arg_names[: min(i+2, len(arg_names))] — a "
        "heuristic SUPPORT relation (no claim↔unit identity exists in this "
        "phase's inputs); named debt, not a target resolution"
    ),
    (
        "invoke_callables.py",
        "_generate_hypotheses",
        "D2",
    ): (
        "arg_ids[idx] score-key read — #2896's own-id-first lookup; "
        "positional only when the caller passes no arg_ids at all (the "
        "stateless convention where index and id coincide)"
    ),
    (
        "invoke_callables.py",
        "_enrich_ranking_with_justification",
        "D3",
    ): (
        "post-resolution member-prefix check — the needle comes from "
        "_resolve_target_argument_id (the id resolver), not from free text; "
        "pinned by the ranking tests"
    ),
}


def _functions(tree: ast.AST) -> List[Tuple[str, int, int]]:
    return [
        (n.name, n.lineno, n.end_lineno or n.lineno)
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def _enclosing(lineno: int, fns: List[Tuple[str, int, int]]) -> str:
    best = "<module>"
    best_start = -1
    for name, start, end in fns:
        if start <= lineno <= end and start > best_start:
            best, best_start = name, start
    return best


def _min_positional_hits(tree: ast.AST, fns: List[Tuple[str, int, int]]):
    """D1: min(<enum var …>, len(<arg list>) …)."""
    hits: Set[Tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id != "min":
            continue
        names = {x.id for x in ast.walk(node) if isinstance(x, ast.Name)}
        lens = [
            x
            for x in ast.walk(node)
            if isinstance(x, ast.Call)
            and isinstance(x.func, ast.Name)
            and x.func.id == "len"
            and x.args
            and isinstance(x.args[0], ast.Name)
            and x.args[0].id in _ARG_LISTS
        ]
        if names & _ENUM_VARS and lens:
            hits.add((_enclosing(node.lineno, fns), "D1"))
    return hits


def _positional_subscript_hits(tree: ast.AST, fns: List[Tuple[str, int, int]]):
    """D2: <arg list>[<bare enum var>]."""
    hits: Set[Tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        if not (isinstance(node.value, ast.Name) and node.value.id in _ARG_LISTS):
            continue
        if isinstance(node.slice, ast.Name) and node.slice.id in _ENUM_VARS:
            hits.add((_enclosing(node.lineno, fns), "D2"))
    return hits


def _unrestricted_substring_hits(tree: ast.AST, src: str):
    """D3: reads a target key, lowers one side of an `in` compare, no guard."""
    hits: Set[Tuple[str, str]] = set()
    lines = src.splitlines()
    for name, start, end in _functions(tree):
        fsrc = textwrap.dedent("\n".join(lines[start - 1 : end]))
        reads_target = any(k in fsrc for k in _TARGET_KEYS)
        if not reads_target:
            continue
        lowered_in = False
        for node in ast.walk(ast.parse(fsrc)):
            if isinstance(node, ast.Compare) and any(
                isinstance(op, ast.In) for op in node.ops
            ):
                operands = [node.left, *node.comparators]
                has_lower = any(
                    isinstance(x, ast.Call)
                    and isinstance(x.func, ast.Attribute)
                    and x.func.attr == "lower"
                    for operand in operands
                    for x in ast.walk(operand)
                )
                if has_lower:
                    lowered_in = True
                    break
        if lowered_in and not (">= 20" in fsrc or ">=20" in fsrc):
            hits.add((name, "D3"))
    return hits


def _derive_census() -> Set[Tuple[str, str, str]]:
    derived: Set[Tuple[str, str, str]] = set()
    for fname, path in _MODULES.items():
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        fns = _functions(tree)
        for fn_name, detector in (
            _min_positional_hits(tree, fns)
            | _positional_subscript_hits(tree, fns)
            | _unrestricted_substring_hits(tree, src)
        ):
            derived.add((fname, fn_name, detector))
    return derived


class TestLinkageIdiomCensus:
    def test_every_live_site_is_carried_with_a_reason(self):
        """The derived census equals the recorded one — a new site of a
        banned idiom (positional fallback, positional subscript,
        unrestricted target substring) reddens here with its location."""
        derived = _derive_census()
        recorded = set(_CENSUS)
        undeclared = derived - recorded
        assert not undeclared, (
            f"new linkage-idiom site(s) not in the #2968 census: "
            f"{sorted(undeclared)} — link by id, or add the site to the "
            "census WITH a reason if it is legitimate"
        )

    def test_census_entries_all_still_exist(self):
        """A census entry whose site disappeared is stale — the map only
        shrinks by changing code, never by leaving drift behind."""
        derived = _derive_census()
        stale = set(_CENSUS) - derived
        assert not stale, f"stale census entries: {sorted(stale)}"

    def test_detectors_do_flag_the_banned_shapes(self):
        """Self-test: the detectors are not vacuous — a synthetic function
        carrying each banned idiom is flagged (a guard that cannot redden
        proves nothing, #1019)."""
        # D1 shape:
        tree = ast.parse("def f(i, arg_names):\n    x = min(i, len(arg_names) - 1)\n")
        fns = _functions(tree)
        assert _min_positional_hits(tree, fns) == {("f", "D1")}
        # D2 shape:
        tree = ast.parse("def f(i, arg_names):\n    return arg_names[i]\n")
        fns = _functions(tree)
        assert _positional_subscript_hits(tree, fns) == {("f", "D2")}
        # D3 shape:
        src3 = (
            "def f(ca, arg_names):\n"
            '    target = ca.get("target_argument", "")\n'
            "    return [a for a in arg_names if target.lower() in a.lower()]\n"
        )
        tree = ast.parse(src3)
        assert _unrestricted_substring_hits(tree, src3) == {("f", "D3")}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
