"""#1224 — the modal KB must be built from ``nl_to_logic`` translations, not
the raw corpus.

``_invoke_modal_logic`` previously read ``context.get("formulas", [input_text])``.
The spectacular DAG executor never populates ``context["formulas"]``
(``_store_phase_result`` sets only ``phase_*_output``/``_result``), so the modal
phase fell back to ``[input_text]`` — the **raw corpus paragraph**. ``MlParser``
then raised ``ParserException`` on URL fragments / prose-as-sort-declarations
and ``is_modal_kb_consistent`` honestly returned ``(None, "parse error")`` →
the modal cell was ``degraded`` on every corpus.

The fix mirrors PL/FOL: when ``phase_nl_to_logic_output`` carries valid
translations, the KB is built from those (sanitized to propositional atoms +
``type(prop)`` declarations per FP-11 #1214), never from the raw corpus. The
direct ``{"formulas": ...}`` path (hand-written, pre-typed KBs) is left as-is
so existing ``type(...)`` declarations are not duplicated.

These are STRUCTURAL tests (no JVM): they patch the solver route
(``asyncio.to_thread``, same pattern as ``test_value_gates``) and assert the KB
*source*. The real-decision proof lives in the integration test
``test_invoke_modal_logic_reaches_solver`` (added ``test_nl_translations_*``).
"""

from unittest.mock import patch

from argumentation_analysis.orchestration.invoke_callables import _invoke_modal_logic

# Sentinel distinct from any logic token — must never appear in the KB source.
_RAW_CORPUS = "RAW UNPARSED CORPUS PARAGRAPH with a url http://x/y?s=2.25"


class TestInvokeModalLogicNLKB:
    """#1224: the modal KB source follows the nl_to_logic translations."""

    async def test_kb_source_is_nl_translations_not_raw_corpus(self):
        """When ``phase_nl_to_logic_output`` has valid translations, the modal
        formulas come from THOSE — the raw ``[input_text]`` corpus must not
        leak (the #1224 bug that fed MlParser URL fragments / prose)."""
        nl_out = {
            "translations": [
                {"formula": "rain => wet", "is_valid": True, "logic_type": "propositional"},
                {"formula": "rain", "is_valid": True, "logic_type": "propositional"},
                {"formula": "", "is_valid": False, "logic_type": "propositional"},
            ],
            "valid_count": 2,
        }
        # Patch the solver route so the real KB-building runs but no JVM call
        # is made (the KB source is decided before the solver is reached).
        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("stop solver route"),
        ):
            result = await _invoke_modal_logic(
                _RAW_CORPUS, {"phase_nl_to_logic_output": nl_out}
            )

        formulas = result.get("formulas", [])
        # The raw corpus MUST NOT be the KB source anymore (#1224).
        assert _RAW_CORPUS not in formulas, (
            f"#1224 REGRESSION: the raw corpus leaked into the modal KB source "
            f"({formulas!r}). The KB must be built from nl_to_logic translations."
        )
        assert all(_RAW_CORPUS not in str(f) for f in formulas)
        # The valid translations ARE the source; the invalid one is dropped.
        assert "rain => wet" in formulas
        assert "rain" in formulas
        assert "" not in formulas

    async def test_invalid_translations_fall_through_honestly(self):
        """When nl_to_logic produced NO valid formula, the KB must NOT be empty
        (which would crash) — it falls to the formulas/``[input_text]`` path and
        the solver then fail-louds honestly (``valid=None``), never a fabricated
        verdict (#1019)."""
        nl_out = {"translations": [
            {"formula": "", "is_valid": False},
        ], "valid_count": 0}
        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("stop solver route"),
        ):
            result = await _invoke_modal_logic(
                _RAW_CORPUS, {"phase_nl_to_logic_output": nl_out}
            )
        # No valid translations → falls to [input_text]; solver route patched →
        # honest unavailable. Crucially: NOT valid=True (no fabricated verdict).
        assert result.get("valid") is not True
        assert result.get("solver") == "unavailable"

    async def test_direct_formulas_path_unchanged(self):
        """Regression guard: the direct ``{"formulas": ...}`` path (hand-written
        KBs with existing ``type(...)`` declarations, as the reaches-solver
        integration tests pass them) must be UNCHANGED — no duplicate
        declarations injected that MlParser would reject."""
        hand_written = ["type(rain)", "type(wet)", "[](rain => wet)", "rain"]
        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("stop solver route"),
        ):
            result = await _invoke_modal_logic("ignored", {"formulas": hand_written})
        assert result.get("formulas") == hand_written, (
            "The direct-formulas path must pass hand-written KBs through verbatim "
            "(no re-sanitization / duplicate type declarations)."
        )
