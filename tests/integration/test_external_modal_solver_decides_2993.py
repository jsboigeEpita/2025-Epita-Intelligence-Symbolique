"""Real (non-mocked) external-modal-lane integration test — #2993.

The #2993 defect (paid run 07/10): ``_invoke_external_modal_solver`` sent the
modal phase's translated formulas to SPASS / TweetyBridge as a raw
``"\\n".join(formulas)``. ``MlParser`` reads the OPENING lines of a belief
base as its signature section, so the first formula parsed as a sort
declaration and the WHOLE KB was rejected (``Illegal characters in sort
definition``) — the external lane returned ``valid=None`` (degraded) on
every NL-translated base, forever, while the very same formulas decided
fine on the reasoning lane (which builds through ``build_modal_kb``).

This file runs the REAL ``_invoke_external_modal_solver`` (live JVM, real
SPASS when registered) on NL-SHAPED formulas — underscored compound atoms,
``=>`` connectives, NO declarations — and asserts a DECIDED verdict
(``valid`` is ``True``/``False``, never ``None``).

Anti-théâtre #1019: where the JVM is available (ai-01, po-2025, CI) this
must pass GREEN; the ``jvm_session`` autouse fixture in conftest skips
cleanly where the JVM cannot start. A skip-everywhere outcome = re-théâtre.

Privacy HARD: synthetic atoms only (``heavy_rain``, ``wet_ground``), 0
corpus.
"""

import pytest

from argumentation_analysis.core.jvm_setup import initialize_jvm
from argumentation_analysis.orchestration.invoke_callables import (
    _invoke_external_modal_solver,
)


@pytest.fixture(scope="module")
def jvm():
    """Start the JVM once (idempotent). The ``jvm_session`` autouse fixture in
    conftest skips this module when the JVM cannot start."""
    initialize_jvm()
    return True


# NL-shaped translations: compound underscored atoms + symbolic connectives,
# exactly what the modal phase emits from nl_to_logic — and NO declarations
# (the pre-#2993 lane sent exactly this shape, raw).
NL_CONSISTENT_FORMULAS = [
    "[](heavy_rain => wet_ground)",
    "[](rain => heavy_rain)",
    "rain",
]
NL_INCONSISTENT_FORMULAS = [
    "heavy_rain",
    "!heavy_rain",
]


class TestExternalModalSolverDecidesNlShapedKb:
    """The external lane decides an NL-translated base instead of degrading."""

    async def test_consistent_nl_kb_decides_true(self, jvm):
        result = await _invoke_external_modal_solver(
            "ignored raw corpus",
            {"phase_modal_output": {"formulas": NL_CONSISTENT_FORMULAS}},
        )
        assert result.get("valid") is True, (
            f"#2993 REGRESSION: a consistent NL-shaped KB must DECIDE True on "
            f"the external lane; got valid={result.get('valid')!r}, "
            f"solver={result.get('solver')!r}, message={result.get('message')!r}. "
            f"A None means the KB reached the parser without its declarations "
            f"(raw join — MlParser reads the first formula as a sort "
            f"definition)."
        )
        assert result.get("solver") in {"spass", "tweety"}, (
            f"a genuine reasoner must have decided, got "
            f"solver={result.get('solver')!r}."
        )

    async def test_inconsistent_nl_kb_decides_false(self, jvm):
        result = await _invoke_external_modal_solver(
            "ignored raw corpus",
            {"phase_modal_output": {"formulas": NL_INCONSISTENT_FORMULAS}},
        )
        assert result.get("valid") is False, (
            f"#2993 REGRESSION: an inconsistent NL-shaped KB must DECIDE False "
            f"— a real rejection, not a parse-degraded None; got "
            f"valid={result.get('valid')!r}, solver={result.get('solver')!r}, "
            f"message={result.get('message')!r}."
        )
        assert result.get("solver") in {"spass", "tweety"}

    async def test_no_translation_sends_nothing(self, jvm):
        """End-to-end honest-absent: no translated formulas → no solver call,
        the lane says WHY (unavailable:no-translation) instead of feeding
        prose to MlParser (#2993/#2970)."""
        result = await _invoke_external_modal_solver(
            "raw prose paragraph — not a KB",
            {"phase_modal_output": {"formulas": []}},
        )
        assert result.get("valid") is None
        assert result.get("modal_status") == "unavailable:no-translation"


class TestTweetyFallbackDecidesConsistency:
    """R1076 rework: WITHOUT SPASS registered, the fallback branch decides
    CONSISTENCY — the pre-rework call was ``execute_modal_query(kb, kb)``:
    the KB (declarations included) passed as the QUERY formula failed to
    parse ("Constant 'principles' has not been declared", measured on doc_A
    by the coordinator), and deeper, KB ⊨ KB holds for EVERY KB — the call
    could never render a consistency verdict even when it parsed. The
    fallback now routes through the bridge's modal consistency check."""

    async def test_fallback_decides_true_on_consistent_kb(self, jvm, monkeypatch):
        import argumentation_analysis.core.jvm_setup as jvm_setup

        monkeypatch.delitem(jvm_setup.EXTERNAL_TOOL_PATHS, "spass", raising=False)
        # One boxed implication + its antecedent: the first formula carries
        # ``=>`` (the issue's discriminant) and a modal operator. Two nested
        # boxes OOM SimpleMlReasoner's heap — the #1279 limit that makes the
        # lane PREFER SPASS; an OOM stays an honest None there (fail-loud),
        # it is not this branch's defect.
        result = await _invoke_external_modal_solver(
            "ignored raw corpus",
            {"phase_modal_output": {"formulas": ["[](rain => wet_ground)", "rain"]}},
        )
        assert result.get("solver") == "tweety", (
            f"the fallback branch must have run (no SPASS registered); got "
            f"solver={result.get('solver')!r}."
        )
        assert result.get("valid") is True, (
            f"R1076 REGRESSION: the Tweety fallback must DECIDE a consistent "
            f"NL-shaped KB (first formula carries =>); got "
            f"valid={result.get('valid')!r}, message={result.get('message')!r}. "
            f"A None means the fallback still sends a query instead of asking "
            f"consistency."
        )

    async def test_fallback_decides_false_on_inconsistent_kb(self, jvm, monkeypatch):
        import argumentation_analysis.core.jvm_setup as jvm_setup

        monkeypatch.delitem(jvm_setup.EXTERNAL_TOOL_PATHS, "spass", raising=False)
        result = await _invoke_external_modal_solver(
            "ignored raw corpus",
            {"phase_modal_output": {"formulas": ["p", "!p"]}},
        )
        assert result.get("solver") == "tweety"
        assert result.get("valid") is False, (
            f"R1076 REGRESSION: the Tweety fallback must DECIDE p/!p "
            f"inconsistent (a real rejection); got "
            f"valid={result.get('valid')!r}, message={result.get('message')!r}."
        )
