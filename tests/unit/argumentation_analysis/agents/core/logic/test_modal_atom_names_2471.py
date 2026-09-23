# -*- coding: utf-8 -*-
"""
#2471 — a renamed modal atom never merges into another atom.

``MlParser`` refuses ``_`` and accented letters in an atom declaration, so the
modal paths rename such atoms (``heavy_rain`` → ``HeavyRain``). Two merges were
measured on ``main`` (real JVM, TWEETY solver), each deciding a consistent KB
inconsistent:

- the parse-point normaliser (``ModalHandler._normalize_for_parse``, behind every
  modal consistency check) did not reserve the atoms already legal in the KB, so
  ``heavy_rain`` next to ``HeavyRain`` became ``HeavyRain``;
- the nl path's inline closure (#1260) reserved them, but not the names it
  generated, so ``heavy_rain`` and ``heavy__rain`` both became ``HeavyRain``.

An accented atom was not captured whole (``_ATOM_RE`` was ASCII), so the KB kept
the accent and the parser refused it: consistency undetermined.

One builder, ``build_modal_kb``, now serves the modal paths. No JVM, no LLM: the
tests read the belief set each site hands to the parser or to the handler.
"""

import ast
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from argumentation_analysis.agents.core.logic import modal_handler as mh

REPO = Path(__file__).resolve().parents[6]
_LEGAL = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
_DECL = re.compile(r"^type\((?P<atom>[^()]*)\)$")


def declared_atoms(belief_set: str):
    """The atoms a modal belief set declares, in order."""
    matches = (_DECL.match(line.strip()) for line in belief_set.splitlines())
    return [m["atom"] for m in matches if m]


@pytest.mark.parametrize(
    "kb",
    [
        "type(heavy_rain)\ntype(HeavyRain)\n\nheavy_rain\n!HeavyRain",
        "type(HeavyRain)\ntype(heavy_rain)\n\n!HeavyRain\nheavy_rain",
    ],
    ids=["renamed-first", "legal-first"],
)
def test_the_parse_point_keeps_two_atoms_distinct(kb):
    normalized = mh.ModalHandler._normalize_for_parse(kb)
    atoms = declared_atoms(normalized)
    assert len(atoms) == len(set(atoms)) == 2, normalized
    assert "HeavyRain" in atoms
    assert all(_LEGAL.match(a) for a in atoms), atoms


def test_an_accented_atom_is_folded_whole():
    normalized = mh.ModalHandler._normalize_for_parse(
        "type(été)\ntype(ete)\n\nété\n!ete"
    )
    atoms = declared_atoms(normalized)
    assert len(atoms) == len(set(atoms)) == 2, normalized
    assert all(_LEGAL.match(a) for a in atoms), atoms


def test_the_query_keeps_its_legal_atom():
    """``execute_modal_query`` shares one normaliser between the KB and the
    query. ``HeavyRain`` in the query is a different atom from the KB's
    ``heavy_rain``, so the renamed KB atom must not take its name."""
    handler = mh.ModalHandler.__new__(mh.ModalHandler)
    parser = MagicMock()
    handler._modal_parser = parser
    fake_jpype = MagicMock()
    fake_jpype.JClass.side_effect = lambda name: (lambda value: value)
    fake_jpype.JException = type("JException", (Exception,), {})
    with patch.object(mh, "jpype", fake_jpype), patch.object(
        mh.ModalHandler, "_get_active_reasoner", return_value=MagicMock()
    ):
        handler.execute_modal_query("type(heavy_rain)\n\nheavy_rain", "HeavyRain")

    kb = parser.parseBeliefBase.call_args.args[0]
    assert parser.parseFormula.call_args.args[0] == "HeavyRain"
    assert declared_atoms(kb) != ["HeavyRain"], kb
    assert all(_LEGAL.match(a) for a in declared_atoms(kb)), kb


@pytest.mark.parametrize(
    "formulas, expected",
    [
        (["heavy_rain", "!heavy__rain"], 2),
        (["heavy_rain", "!HeavyRain"], 2),
        (["heavy_rain", "!heavy_rain"], 1),
    ],
    ids=["two-renamed", "renamed-and-legal", "control-one-atom"],
)
async def test_the_nl_path_declares_distinct_atoms(formulas, expected):
    """The pipeline's modal phase builds the KB from ``nl_to_logic``
    translations. The handler double records the belief set it receives."""
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_modal_logic,
    )

    seen = []

    class _Handler:
        def __init__(self, initializer_instance):
            pass

        def is_modal_kb_consistent(self, belief_set):
            seen.append(belief_set)
            return True, "handler double"

    context = {
        "phase_nl_to_logic_output": {
            "translations": [{"is_valid": True, "formula": f} for f in formulas]
        }
    }
    with patch.object(mh, "ModalHandler", _Handler), patch(
        "argumentation_analysis.agents.core.logic.tweety_initializer.TweetyInitializer",
        MagicMock(),
    ):
        await _invoke_modal_logic("ignored", context)

    assert len(seen) == 1
    atoms = declared_atoms(seen[0])
    assert len(atoms) == len(set(atoms)) == expected, seen[0]
    assert all(_LEGAL.match(a) for a in atoms), atoms


def test_one_legaliser_on_the_modal_paths():
    """The #1260 closure of ``invoke_callables`` and the copy in
    ``scripts/run_fp16_modal_enum.py`` call ``build_modal_kb``: no module
    defines its own ``_legal_symbol`` any more."""
    offenders = []
    for root in ("argumentation_analysis", "scripts"):
        for path in sorted((REPO / root).rglob("*.py")):
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            if "_legal_symbol" not in text:
                continue
            # A file that names the symbol must parse: no silent skip.
            offenders += [
                f"{path.relative_to(REPO).as_posix()}:{node.lineno}"
                for node in ast.walk(ast.parse(text))
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "_legal_symbol"
            ]
    assert offenders == []
