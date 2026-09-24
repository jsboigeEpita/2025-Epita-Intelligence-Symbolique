"""#2344 — a numeric knob set in the environment either parses or stops the run.

``invoke_callables`` reads five numeric knobs from the environment:
``LLM_CALL_BUDGET``, ``LLM_CALL_TIMEOUT_S``, ``DUNG_TIMEOUT_S``,
``EXTRACTION_MAX_ATTEMPTS`` and ``EXTRACTION_MAX_TOKENS``. Each read caught
``ValueError`` and went on with its default, so ``LLM_CALL_TIMEOUT_S=thirty``
ran with 300 s and nothing said the value had been dropped. The value comes
from whoever launched the run, so a bad one now raises, naming the key and
what it held. Unset or blank still means the default.
"""

import ast
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from argumentation_analysis.orchestration import invoke_callables as mod

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT / "argumentation_analysis" / "orchestration" / "invoke_callables.py"
)

KNOBS = {
    "LLM_CALL_BUDGET",
    "LLM_CALL_TIMEOUT_S",
    "DUNG_TIMEOUT_S",
    "EXTRACTION_MAX_ATTEMPTS",
    "EXTRACTION_MAX_TOKENS",
}
# The four the module reads while it is imported; LLM_CALL_BUDGET is read per run.
IMPORT_TIME_KNOBS = sorted(KNOBS - {"LLM_CALL_BUDGET"})


def _env(values):
    """Patch the module's ``os.environ.get``; a ``None`` value means unset."""
    real_get = mod.os.environ.get

    def side_effect(key, default=None):
        if key in values:
            return default if values[key] is None else values[key]
        return real_get(key, default)

    return patch.object(mod.os.environ, "get", side_effect=side_effect)


class TestEnvNumber:
    def test_blank_reads_as_unset(self):
        with _env({"_TEST_KNOB": "  "}):
            assert mod._env_number("_TEST_KNOB", 7.5, float) == 7.5

    def test_integer_knob_rejects_a_fraction(self):
        with _env({"_TEST_KNOB": "3.5"}):
            with pytest.raises(ValueError, match=r"_TEST_KNOB='3\.5'"):
                mod._env_number("_TEST_KNOB", 3, int)

    def test_integer_knob_parses_to_int(self):
        with _env({"_TEST_KNOB": "12"}):
            value = mod._env_number("_TEST_KNOB", 3, int)
        assert value == 12 and type(value) is int


class TestLLMCallBudget:
    def test_word_raises_naming_the_key(self):
        with _env({"LLM_CALL_BUDGET": "five hundred"}):
            with pytest.raises(ValueError, match=r"LLM_CALL_BUDGET='five hundred'"):
                mod._default_llm_call_budget()

    def test_blank_reads_as_unset(self):
        with _env({"LLM_CALL_BUDGET": ""}):
            assert mod._default_llm_call_budget() == 500


def test_import_refuses_each_malformed_knob():
    """Import the module with each knob set to a word, then with every knob valid.

    One interpreter for all five imports: a failed import leaves the module out
    of ``sys.modules``, so the next attempt re-runs its body while the heavy
    dependencies it pulled in stay cached. The last import, with valid values,
    is the positive control: it shows the refusals come from the knobs.
    """
    script = textwrap.dedent(f"""
        import importlib, os, sys
        name = "argumentation_analysis.orchestration.invoke_callables"
        for key in {IMPORT_TIME_KNOBS!r}:
            os.environ[key] = "thirty"
            try:
                importlib.import_module(name)
            except ValueError as exc:
                print("REFUSED", key, str(exc) if key in str(exc) else "<no key>")
            else:
                print("ACCEPTED", key)
                sys.modules.pop(name, None)
            del os.environ[key]
        os.environ.update(
            LLM_CALL_TIMEOUT_S="30", DUNG_TIMEOUT_S="0",
            EXTRACTION_MAX_ATTEMPTS="2", EXTRACTION_MAX_TOKENS="0",
        )
        m = importlib.import_module(name)
        print("VALUES", m._LLM_CALL_TIMEOUT_S, m._DUNG_TIMEOUT_S,
              m._EXTRACTION_MAX_ATTEMPTS, m._EXTRACTION_MAX_TOKENS)
        """)
    env = {k: v for k, v in os.environ.items() if k not in KNOBS}
    # The worktree first: an editable install would otherwise resolve the
    # package to another checkout.
    env["PYTHONPATH"] = str(REPO_ROOT)
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    lines = [
        line
        for line in proc.stdout.splitlines()
        if line.split(" ")[0] in {"REFUSED", "ACCEPTED", "VALUES"}
    ]
    assert proc.returncode == 0, proc.stderr[-2000:]
    for key in IMPORT_TIME_KNOBS:
        refusal = [line for line in lines if line.startswith(f"REFUSED {key} ")]
        assert refusal, f"{key}=thirty was accepted: {lines}"
        assert f"{key}='thirty'" in refusal[0], refusal[0]
    assert "VALUES 30.0 0.0 2 0" in lines, lines


def _is_env_read(node):
    """``os.environ.get(...)``, ``os.getenv(...)`` or ``os.environ[...]``."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        target = ast.unparse(node.func)
        return target in {"os.environ.get", "os.getenv"}
    if isinstance(node, ast.Subscript):
        return ast.unparse(node.value) == "os.environ"
    return False


def test_every_numeric_knob_goes_through_the_one_reader():
    """No ``int(...)``/``float(...)`` wraps an env read; the five keys use ``_env_number``."""
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8-sig"))
    bypasses = [
        f"line {node.lineno}: {ast.unparse(node)}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"int", "float"}
        and any(_is_env_read(inner) for inner in ast.walk(node))
    ]
    assert bypasses == [], bypasses
    read_through_helper = {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_env_number"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }
    assert read_through_helper == KNOBS
