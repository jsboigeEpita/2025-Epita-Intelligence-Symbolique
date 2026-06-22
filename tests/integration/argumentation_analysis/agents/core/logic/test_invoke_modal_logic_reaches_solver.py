"""Real (non-mocked) modal-pipeline integration test — #1219.

The modal pipeline gap (#1219) stayed hidden because the existing modal unit
tests are 100% mocked/patched: ``test_external_solvers`` asserts only the
``modalities`` field; ``test_value_gates`` patches ``asyncio.to_thread`` so the
real ``ModalHandler`` never runs. Neither proves the production path
``_invoke_modal_logic`` actually reaches ``SimpleMlReasoner`` and returns a
real verdict. This file closes that hole with ONE non-mocked integration test
that runs the REAL ``_invoke_modal_logic`` (live JVM, configured TWEETY solver)
and asserts a real consistency verdict (``valid`` is ``True``/``False``, NOT
``None``).

Anti-théâtre #1019: the test must EXECUTE the real reasoner — NOT be "green by
skipping everywhere". Where the JVM is available (ai-01, po-2025, CI) it must
pass GREEN; the ``jvm_session`` autouse fixture in conftest skips cleanly where
the JVM cannot start. A skip-everywhere outcome = re-théâtre and defeats the
regression guard.

#1219 regression guard — this test FAILS if someone:
  * reintroduces the unconditional ``settings.modal_solver = SPASS`` force-set
    (routes to the absent SPASS binary → ``valid=None``); OR
  * removes the ``initializer.initialize_modal_components()`` call (bare
    ``TweetyInitializer`` leaves the modal parser None → ModalHandler raises
    → ``valid=None``).
Both bugs were surfaced by FP-13's matrix and fixed; this test prevents their
return. Verify-the-verification (FP-13 lesson): trust the runtime path, not
the patched unit tests.

Privacy HARD: synthetic atoms only (``type(rain)``, ``type(wet)``), 0 corpus.
"""

import pytest

from argumentation_analysis.core.config import ModalSolverChoice, settings
from argumentation_analysis.core.jvm_setup import initialize_jvm
from argumentation_analysis.orchestration.invoke_callables import _invoke_modal_logic


@pytest.fixture(scope="module")
def jvm():
    """Start the JVM once (idempotent). The ``jvm_session`` autouse fixture in
    conftest skips this module when the JVM cannot start."""
    initialize_jvm()
    return True


@pytest.fixture
def tweety_solver():
    """Force the pure-Java default (TWEETY / SimpleMlReasoner) — the
    always-available, always-deciding modal path (no external binary)."""
    previous = settings.modal_solver
    settings.modal_solver = ModalSolverChoice.TWEETY
    try:
        yield
    finally:
        settings.modal_solver = previous


# Parseable modal KBs (FP-11 grammar: type(prop) declarations, MlParser).
CONSISTENT_KB = ["type(rain)", "type(wet)", "[](rain => wet)", "rain"]
INCONSISTENT_KB = ["type(rain)", "rain", "!rain"]


class TestInvokeModalLogicReachesSolver:
    """The pipeline ``modal`` phase must reach SimpleMlReasoner and decide —
    not silently fall to ``valid=None`` (#1219)."""

    async def test_consistent_kb_decides_true(self, jvm, tweety_solver):
        """A consistent modal KB yields ``valid=True`` via the REAL pipeline
        path (``_invoke_modal_logic`` → ``ModalHandler.is_modal_kb_consistent``
        → ``SimpleMlReasoner``)."""
        result = await _invoke_modal_logic("ignored", {"formulas": CONSISTENT_KB})
        assert result.get("valid") is True, (
            f"#1219 REGRESSION: consistent KB must decide True via "
            f"SimpleMlReasoner; got valid={result.get('valid')!r}, "
            f"solver={result.get('solver')!r}. A None verdict means the "
            f"pipeline did not reach the solver (force-SPASS override or "
            f"missing initialize_modal_components)."
        )
        assert result.get("solver") == "tweety", (
            f"solver must be 'tweety' (SimpleMlReasoner reached), got "
            f"{result.get('solver')!r}."
        )

    async def test_inconsistent_kb_decides_false(self, jvm, tweety_solver):
        """An inconsistent modal KB yields ``valid=False`` via the REAL pipeline
        path — a real rejection, not a fabricated one."""
        result = await _invoke_modal_logic("ignored", {"formulas": INCONSISTENT_KB})
        assert result.get("valid") is False, (
            f"#1219 REGRESSION: inconsistent KB must decide False via "
            f"SimpleMlReasoner; got valid={result.get('valid')!r}."
        )
        assert (
            result.get("solver") == "tweety"
        ), f"solver must be 'tweety', got {result.get('solver')!r}."

    async def test_nl_translations_consistent_decides_true(self, jvm, tweety_solver):
        """#1224: a modal KB built from nl_to_logic translations (sanitized to
        propositional atoms + type(prop) declarations) reaches SimpleMlReasoner
        and decides True — NOT the raw-corpus ``valid=None`` of the pre-#1224
        pipeline. ``input_text`` is ignored when translations are present."""
        result = await _invoke_modal_logic(
            "ignored raw corpus", {"phase_nl_to_logic_output": NL_CONSISTENT_OUT}
        )
        assert result.get("valid") is True, (
            f"#1224 REGRESSION: a consistent nl_to_logic-derived KB must decide "
            f"True via SimpleMlReasoner; got valid={result.get('valid')!r}, "
            f"solver={result.get('solver')!r}, message={result.get('message')!r}. "
            f"A None means the nl→modal-KB translation is still malformed."
        )
        assert result.get("solver") == "tweety"

    async def test_nl_translations_inconsistent_decides_false(self, jvm, tweety_solver):
        """#1224: an inconsistent nl_to_logic-derived KB decides False — a real
        rejection on sanitized translations, not a fabricated one."""
        result = await _invoke_modal_logic(
            "ignored raw corpus", {"phase_nl_to_logic_output": NL_INCONSISTENT_OUT}
        )
        assert result.get("valid") is False, (
            f"#1224 REGRESSION: an inconsistent nl_to_logic-derived KB must "
            f"decide False via SimpleMlReasoner; got valid={result.get('valid')!r}, "
            f"message={result.get('message')!r}."
        )
        assert result.get("solver") == "tweety"


# #1224 — nl_to_logic translation output (the shape _invoke_nl_to_logic returns).
# The spectacular pipeline builds the modal KB from these translations (mirroring
# PL/FOL), NOT from the raw corpus. These prove the fix end-to-end: a KB derived
# from nl_to_logic formulas (sanitized to propositional atoms + type(prop)
# declarations) reaches SimpleMlReasoner and DECIDES — the pre-#1224 pipeline
# fed MlParser the raw corpus and got valid=None (degraded) on every corpus.
NL_CONSISTENT_OUT = {
    "translations": [
        {"formula": "rain => wet", "is_valid": True, "logic_type": "propositional"},
        {"formula": "rain", "is_valid": True, "logic_type": "propositional"},
    ],
    "valid_count": 2,
}
NL_INCONSISTENT_OUT = {
    "translations": [
        {"formula": "rain", "is_valid": True, "logic_type": "propositional"},
        {"formula": "!rain", "is_valid": True, "logic_type": "propositional"},
    ],
    "valid_count": 2,
}
