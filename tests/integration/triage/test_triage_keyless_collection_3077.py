"""#3077 — the two scripted triage modules must exist keyless.

Both modules ran their whole subtree behind ``not REAL_GPT_AVAILABLE``:
``test_einstein_demo_real.py`` (9 tests) and
``test_cluedo_oracle_enhanced_real.py`` (9 tests) — 18 tests silently
absent from any keyless run, although **no invocation of either needs a
key**: every subprocess carries the hermetic flag (``--integration-test``
8x einstein, ``--test-mode`` 6x cluedo; the scripts' own branches say so —
``run_einstein_oracle_demo.py:197`` scripted responses, agents unused;
``run_cluedo_oracle_enhanced.py:163`` ``force_mock_llm``). Measured by the
#3074 census: the lane spent 0 with a key set.

The key term of the gate is dropped (the script-exists term stays). This
guard pins the property the issue named: imported with **no key in the
environment**, the module-level skip of each module does NOT fire.

The third ``REAL_GPT_AVAILABLE`` module of the directory is deliberately
out of scope: ``test_sherlock_watson_moriarty_real_gpt.py`` documents (#1872)
that its launcher exists only to spend real GPT — its key gate is the
deselect mechanism, not an oversight.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType
from typing import Iterator, List

import pytest
from _pytest.mark import Mark, MarkDecorator

MODULES = [
    "tests.integration.triage.test_einstein_demo_real",
    "tests.integration.triage.test_cluedo_oracle_enhanced_real",
]


def _skipif_conditions(module: ModuleType) -> List[bool]:
    """The module-level skipif conditions, as evaluated at import.

    ``pytestmark = pytest.mark.skipif(<expr>, ...)`` evaluates ``<expr>``
    eagerly at module import, so a fresh import under a chosen environment
    is the measurement of what that environment collects.
    """

    marks = getattr(module, "pytestmark", [])
    if not isinstance(marks, list):
        marks = [marks]
    conditions: List[bool] = []
    for decorator in marks:
        mark = decorator.mark if isinstance(decorator, MarkDecorator) else decorator
        if isinstance(mark, Mark) and mark.name == "skipif":
            conditions.append(bool(mark.args[0]))
    return conditions


def _import_keyless(module_name: str, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Import the module fresh with no OPENAI_API_KEY in the environment.

    pytest has already imported it at collection (under the parent's env);
    the cached module is set aside and restored, so only this measurement
    sees the keyless import.
    """

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    saved = sys.modules.pop(module_name, None)
    try:
        return importlib.import_module(module_name)
    finally:
        if saved is not None:
            sys.modules[module_name] = saved


class TestTheScriptedTriageModulesExistKeyless:
    @pytest.mark.parametrize("module_name", MODULES)
    def test_no_module_level_skip_fires_keyless(
        self, module_name: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        module = _import_keyless(module_name, monkeypatch)
        conditions = _skipif_conditions(module)
        assert conditions, (
            "no module-level skipif was found — the reader below no longer "
            "measures what it measured at #3077 (pytest internals moved?)"
        )
        assert not any(conditions), (
            f"{module_name} skips keyless: {conditions} — the scripted triage "
            "suite is again absent from any keyless run (an invocation that "
            "carries --integration-test/--test-mode never needs a key)"
        )

    def test_the_real_gpt_spender_keeps_its_gate(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Control: the deliberate gate (#1872) is not collateral damage.

        ``test_sherlock_watson_moriarty_real_gpt`` skips keyless BY DESIGN —
        its launcher exists only to spend real GPT. If this control ever
        fails, the fix reached further than #3077 intended.
        """

        module = _import_keyless(
            "tests.integration.triage.test_sherlock_watson_moriarty_real_gpt",
            monkeypatch,
        )
        conditions = _skipif_conditions(module)
        assert conditions and any(conditions), (
            "the #1872 spender gate stopped skipping keyless — it must keep "
            "deselecting the real-GPT worker from keyless/wide argv"
        )
