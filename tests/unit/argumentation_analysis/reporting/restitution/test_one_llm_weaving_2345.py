"""#2345 — the three restitution acts call the LLM through one function.

Actes I, II and III each carried the same call: ``try: raw = await
llm_callable(prompt)``, ``except``: log a warning, return ``""``. The caller,
seeing ``""``, recorded *« le LLM n'a rien produit »* — including when the call
had raised. ``llm_weaving.weave`` is now the only site that awaits the injected
callable, and it returns the observed cause alongside the empty narrative.

Two guards:

* ``TestWeave`` — the behaviour: a raised call and a mute call are told apart,
  and the exception's message never enters the motif.
* ``TestOneSite`` — the census, on the AST of every module of the restitution
  package: exactly one ``await llm_callable(...)`` and one ``LlmCallable``
  assignment, both in ``llm_weaving.py``. A fourth copy of the call reddens the
  second test; a fourth ``LlmCallable = ...`` reddens the third. Every module is
  parsed or the test fails — a file skipped on a parse error would be a module
  the census cannot see.

The per-act consequences (``degraded`` motif of ``build_act{1,2,3}_*`` on the
raised vs mute path) are asserted next to each act's own tests
(``TestWeaveFailLoud.test_raised_call_is_not_recorded_as_mute``).
"""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path

import pytest

from argumentation_analysis.reporting.restitution import llm_weaving
from argumentation_analysis.reporting.restitution.llm_weaving import (
    MUTE_FAILURE,
    WeaveOutcome,
    weave,
)

_PACKAGE_DIR = Path(llm_weaving.__file__).parent


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _returning(value):
    async def _call(_prompt: str):
        return value

    return _call


def _raising(exc: BaseException):
    async def _call(_prompt: str):
        raise exc

    return _call


class TestWeave:
    def test_text_is_returned_stripped_without_failure(self) -> None:
        assert _run(weave("p", _returning("  récit  "), "Acte X")) == WeaveOutcome(
            "récit"
        )

    @pytest.mark.parametrize("raw", [None, "", "   \n"])
    def test_mute_call_records_the_mute_motif(self, raw) -> None:
        assert _run(weave("p", _returning(raw), "Acte X")) == WeaveOutcome(
            "", MUTE_FAILURE
        )

    def test_raised_call_names_the_exception_type_not_the_mute_motif(self) -> None:
        out = _run(weave("p", _raising(ConnectionError("x")), "Acte X"))
        assert out.narrative == ""
        assert "ConnectionError" in out.failure
        assert out.failure != MUTE_FAILURE

    def test_exception_message_stays_out_of_the_motif(self, caplog) -> None:
        with caplog.at_level("WARNING", logger=llm_weaving.__name__):
            out = _run(weave("p", _raising(ValueError("sk-SENTINEL-2345")), "Acte X"))
        assert "sk-SENTINEL-2345" not in out.failure
        # ...but it is not lost: the log still carries it for the operator.
        assert "sk-SENTINEL-2345" in caplog.text

    def test_the_prompt_reaches_the_callable(self) -> None:
        seen = []

        async def _call(prompt: str) -> str:
            seen.append(prompt)
            return "ok"

        _run(weave("le prompt", _call, "Acte X"))
        assert seen == ["le prompt"]


def _parse_package():
    """Every module of the package, parsed — or the test fails naming it."""
    trees, unparsed = {}, []
    for path in sorted(_PACKAGE_DIR.glob("*.py")):
        try:
            trees[path.name] = ast.parse(path.read_text(encoding="utf-8-sig"))
        except SyntaxError as exc:  # pragma: no cover — reported, never skipped
            unparsed.append(f"{path.name}: {exc}")
    return trees, unparsed


def _awaited_llm_calls(tree: ast.AST) -> int:
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.Await)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "llm_callable"
    )


def _llm_callable_assignments(tree: ast.AST) -> int:
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        count += sum(
            1 for t in targets if isinstance(t, ast.Name) and t.id == "LlmCallable"
        )
    return count


class TestOneSite:
    def test_every_module_of_the_package_is_parsed(self) -> None:
        trees, unparsed = _parse_package()
        assert unparsed == []
        # Non-vacuity: the three acts and the weaving module are in the census.
        assert {
            "act1_framing_plugin.py",
            "act2_narrative_plugin.py",
            "act3_conclusion_plugin.py",
            "llm_weaving.py",
        } <= set(trees)

    def test_one_await_of_the_injected_callable(self) -> None:
        trees, _ = _parse_package()
        sites = {name: n for name, t in trees.items() if (n := _awaited_llm_calls(t))}
        assert sites == {"llm_weaving.py": 1}

    def test_one_llm_callable_alias(self) -> None:
        trees, _ = _parse_package()
        sites = {
            name: n for name, t in trees.items() if (n := _llm_callable_assignments(t))
        }
        assert sites == {"llm_weaving.py": 1}
