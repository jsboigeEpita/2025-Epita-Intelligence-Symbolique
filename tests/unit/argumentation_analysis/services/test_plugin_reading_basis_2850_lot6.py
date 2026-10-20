"""#2850 lot 6 — the LLM translation call and the fallacy plugin name their reading.

Two surfaces that can never reach the restitution acts (a service without
the shared state, a plugin whose callers are conversational) still owe their
reader the bound: the translation result says which head of the argument the
LLM call actually read (_NL_TO_LOGIC_WINDOW, retry at the shorter window),
counts only — the lot-4/5 payload idiom, prompts untouched.

Witnesses are born red on the pre-fix tree: the result's
``validation_message`` carries no k of N there.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.services.nl_to_logic import (
    _NL_TO_LOGIC_RETRY_WINDOW,
    _NL_TO_LOGIC_WINDOW,
    NLToLogicTranslator,
    TranslationResult,
)

_SERVICE = "argumentation_analysis.services.nl_to_logic"

# Longer than the window so the truncation is real.
LONG_ARG = "Une phrase d'argument distincte et dense. " * 200
assert len(LONG_ARG) > _NL_TO_LOGIC_WINDOW, len(LONG_ARG)


def _llm_result(attempts: int = 1, message: str = "ok") -> TranslationResult:
    return TranslationResult(
        original_text="x",
        formula="p => q",
        logic_type="propositional",
        is_valid=True,
        validation_message=message,
        attempts=attempts,
        variables={},
        confidence=0.7,
    )


class TestTranslationResultNamesItsReading:
    """Rows ``selected_text[_NL_TO_LOGIC_WINDOW]#1`` /
    ``[_NL_TO_LOGIC_RETRY_WINDOW]#1`` — the LLM call's read head."""

    @staticmethod
    def _translator() -> NLToLogicTranslator:
        translator = NLToLogicTranslator.__new__(NLToLogicTranslator)
        translator.logic_type = "propositional"
        translator.max_retries = 3
        return translator

    def test_the_result_pairs_the_window_with_the_argument(self) -> None:
        translator = self._translator()
        with patch.object(
            NLToLogicTranslator,
            "_translate_with_llm",
            AsyncMock(return_value=_llm_result(attempts=1)),
        ):
            import asyncio

            result = asyncio.run(translator.translate(LONG_ARG, "propositional"))
        assert f"{_NL_TO_LOGIC_WINDOW} des {len(LONG_ARG)}" in (
            result.validation_message or ""
        ), (
            "the LLM call read a bounded head of the argument — the result "
            "must pair the window with the argument's length (counts only), "
            f"got: {result.validation_message!r}"
        )

    def test_a_retry_names_the_shorter_window(self) -> None:
        translator = self._translator()
        with patch.object(
            NLToLogicTranslator,
            "_translate_with_llm",
            AsyncMock(return_value=_llm_result(attempts=2)),
        ):
            import asyncio

            result = asyncio.run(translator.translate(LONG_ARG, "propositional"))
        assert f"{_NL_TO_LOGIC_RETRY_WINDOW} des" in (
            result.validation_message or ""
        ), "the retry read the SHORTER window — the result must say so"

    def test_a_short_argument_is_not_claimed_truncated(self) -> None:
        """Control: a text at or under the window is read whole — no clause."""
        translator = self._translator()
        short = "Un argument court mais suffisant pour le temoin."
        with patch.object(
            NLToLogicTranslator,
            "_translate_with_llm",
            AsyncMock(return_value=_llm_result(attempts=1)),
        ):
            import asyncio

            result = asyncio.run(translator.translate(short, "propositional"))
        assert "des" not in (
            result.validation_message or ""
        ), f"a short text is fully read; got: {result.validation_message!r}"

    def test_the_heuristic_path_carries_no_window_claim(self) -> None:
        """Control: the heuristic translator never calls the LLM — the
        window clause must not appear on its result either."""
        translator = self._translator()
        heuristic = _llm_result(attempts=0, message="Heuristic (no LLM)")
        with patch.object(
            NLToLogicTranslator,
            "_translate_with_llm",
            AsyncMock(side_effect=RuntimeError("no-key-witness")),
        ), patch.object(
            NLToLogicTranslator,
            "_translate_heuristic",
            MagicMock(return_value=heuristic),
        ):
            import asyncio

            result = asyncio.run(translator.translate(LONG_ARG, "propositional"))
        assert "des" not in (result.validation_message or ""), (
            "the heuristic path made no LLM call — no window to disclose; "
            f"got: {result.validation_message!r}"
        )
