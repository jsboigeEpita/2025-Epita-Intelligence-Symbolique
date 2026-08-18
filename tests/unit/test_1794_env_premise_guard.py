"""#1794 — guards for the env-premise pollution family.

The gate's two surviving real POSTs (#1591 residual) were caused by tests
doing ``patch("<any-module>.os.environ", {...})``: mock resolves the module,
then ``setattr(os, "environ", dict)`` — a GLOBAL identity swap, not a scoped
one. During the swap window ``os.environ`` is a plain dict: dict writes never
reach ``putenv`` (the C env block desynchronizes), and a later test's
``patch.dict`` can resolve the swapped object instead of the process env.
Measured by trap + identity probe in the same run: POST fired with
``os.environ`` = ``builtins.dict``.

Two guards:
- source guard: the identity-swap motif is banned from the gate tree
  (it was red before the fix — 9 sites);
- execution guard: after a predecessor enters AND EXITS a rebind (the
  historical polluter, simulated here forever), the pl_2pass no-key scenario
  emits zero watched-LLM request, observed by the #1787 counter.
"""

import asyncio
import re
from pathlib import Path
from unittest.mock import patch

import pytest

import tests.llm_egress_counter as egress_module

_TESTS_ROOT = Path(__file__).resolve().parents[1]

# patch("<module>.os.environ", ...), patch("os.environ", ...) and
# patch.object(os, "environ", ...) all setattr the environ ATTRIBUTE of the
# os module — a global identity swap. patch.dict(...) mutates the object and
# is the only legitimate form.
_SWAP_MOTIF = re.compile(
    r"patch\(\s*[\"'](?:[\w.]+\.)?os\.environ[\"']"
    r"|patch\.object\(\s*os\s*,\s*[\"']environ[\"']"
)


def _gate_test_files():
    files = []
    for sub in ("unit", "scripts"):
        files.extend((Path(_TESTS_ROOT) / sub).rglob("*.py"))
    return sorted(files)


def test_no_os_environ_identity_swap_in_gate_tree():
    """Source guard: patch("<mod>.os.environ", {...}) rebinds the process env
    globally (#1794) — mutation via patch.dict(..., clear=True) is the only
    legitimate form. Fails on any reintroduction of the swap motif."""
    offenders = []
    for f in _gate_test_files():
        if f.name == Path(__file__).name:
            # this guard deliberately performs one round-trip swap (execution
            # guard below) — it asserts the restoration itself.
            continue
        try:
            src = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(src.splitlines(), start=1):
            if _SWAP_MOTIF.search(line):
                offenders.append(f"{f.relative_to(_TESTS_ROOT)}:{i}: {line.strip()}")
    assert not offenders, (
        "os.environ identity-swap patch(es) found — these rebind the process "
        "env globally and leak provider keys into other tests' premises "
        "(#1794). Convert to patch.dict('os.environ', {...}, clear=True):\n"
        + "\n".join(offenders)
    )


def test_no_api_key_scenario_emits_nothing_after_a_rebind_roundtrip():
    """Execution guard: a predecessor that entered and exited an os.environ
    rebind (the historical polluter shape) must leave the no-key premise
    enforceable — the #1787 counter must attribute zero watched-LLM request
    to the pl_2pass no-key scenario run right after it."""
    counter = egress_module.get_counter()
    if counter is None:  # pragma: no cover - counter not active in this session
        pytest.skip("LLM egress counter not active")

    # The polluter's shape, kept on purpose: swap the process env, then let
    # mock restore it. A leaking exit would leave os.environ a plain dict and
    # the scenario below would fire (measured in the trap run of #1794).
    sentinel = {"OPENROUTER_API_KEY": "sk-leak-should-not-survive-the-exit"}
    with patch("os.environ", sentinel):
        assert os_env_get("OPENROUTER_API_KEY") == "sk-leak-should-not-survive-the-exit"
    assert (
        os_env_get("OPENROUTER_API_KEY") != "sk-leak-should-not-survive-the-exit"
    ), "the rebind outlived its with-block — process env is still the swapped dict"

    from argumentation_analysis.core.shared_state import UnifiedAnalysisState
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_propositional_logic,
    )

    state = UnifiedAnalysisState("Test argument for the guard scenario.")
    ctx = {
        "_state_object": state,
        "source_metadata": {"opaque_id": "guard_1794"},
        "arguments": ["National sovereignty requires immediate action"],
    }

    before = counter.total()
    with patch.dict(
        "os.environ",
        {"OPENAI_API_KEY": "", "OPENROUTER_API_KEY": "", "OPENROUTER_BASE_URL": ""},
    ):
        asyncio.get_event_loop().run_until_complete(
            _invoke_propositional_logic(state.raw_text, ctx)
        )

    attributed = [
        r
        for r in counter.snapshot()["requests"]
        if r["test"].endswith(
            "test_no_api_key_scenario_emits_nothing_after_a_rebind_roundtrip"
        )
        and r["class"] == "llm"
    ]
    assert not attributed, (
        "the no-key scenario emitted watched-LLM request(s) after a clean "
        "rebind roundtrip — the env premise is again decided outside the "
        f"test: {attributed}"
    )
    assert (
        counter.total() <= before + 1
    )  # at most the counter's own control, never ours


def os_env_get(key):
    import os

    return os.environ.get(key)
