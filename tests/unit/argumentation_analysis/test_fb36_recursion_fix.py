"""FB-36 #1123 — per-argument fallacy harness recursion fix.

The ``_invoke_hierarchical_fallacy_per_argument`` harness used to fall back to
``_invoke_hierarchical_fallacy`` when ``_extract_arguments_for_parallel``
returned no arguments. Since the wide-net "llm" path that re-enters CALLS the
per-argument harness again, this was an infinite recursion whenever no arguments
could be extracted (no state args, no ``phase_extract_output``, and no ``\\n\\n``
paragraph breaks — e.g. an encrypted corpus loaded as a single block). That
loop is the doc_A ``spectacular``+``full`` >2h hang (the descent was ruled out
by FB-35; the per-arg recursion is the real cause).

The fix: return fail-loud (degraded + last_error, wide-net result retained by
the caller) instead of recursing. These tests pin that behavior.
"""
import pytest

from unittest.mock import AsyncMock, patch

import argumentation_analysis.orchestration.invoke_callables as ic


# A single block of text (>20 chars, NO double-newline paragraph breaks) — this
# is the trigger condition (Source 3 of _extract_arguments_for_parallel returns
# nothing), mimicking an encrypted corpus loaded as one block.
SINGLE_BLOCK = (
    "This is one continuous paragraph with no double newline breaks anywhere. "
    "It is long enough to exceed the 20-character minimum filter. "
) * 3

MULTI_BLOCK = (
    "First argument paragraph that is long enough to pass the filter.\n\n"
    "Second argument paragraph that is also long enough to pass.\n\n"
    "Third argument paragraph likewise above the threshold."
)


class TestExtractArgumentsTrigger:
    """Pin the recursion TRIGGER condition (no args for a single block)."""

    def test_single_block_empty_context_yields_no_args(self):
        args = ic._extract_arguments_for_parallel(SINGLE_BLOCK, {})
        assert args == [], (
            "a single-block text with an empty context must yield no arguments "
            "(the recursion trigger) — Source 3 needs \\n\\n breaks"
        )

    def test_multi_block_yields_args(self):
        args = ic._extract_arguments_for_parallel(MULTI_BLOCK, {})
        assert len(args) >= 2, "paragraph-split (Source 3) must still extract args"

    def test_state_identified_arguments_source(self):
        class _FakeState:
            identified_arguments = {"arg_1": "A real argument long enough.", "arg_2": "x"}

        args = ic._extract_arguments_for_parallel(
            SINGLE_BLOCK, {"_state_object": _FakeState()}
        )
        # Only arg_1 passes the >20-char filter (Source 1).
        assert len(args) == 1
        assert args[0][0] == "arg_1"


class TestPerArgNoRecursion:
    """The core FB-36 fix: per-arg returns fail-loud, does NOT recurse."""

    @pytest.mark.asyncio
    async def test_no_recursion_on_single_block(self):
        """A single-block text + empty context must NOT recurse into
        _invoke_hierarchical_fallacy (the pre-FB-36 infinite loop)."""
        with patch.object(
            ic, "_invoke_hierarchical_fallacy", new_callable=AsyncMock
        ) as spy_hier:
            result = await ic._invoke_hierarchical_fallacy_per_argument(
                SINGLE_BLOCK, {}
            )

        # The recursion target must NEVER be called.
        assert spy_hier.call_count == 0, (
            "per-argument harness recursed into _invoke_hierarchical_fallacy "
            "(the FB-36 #1123 >2h hang root cause) — must return fail-loud instead"
        )
        # Fail-loud return contract.
        assert isinstance(result, dict)
        assert result.get("fallacies") == []
        assert result.get("exploration_method") == "per_argument_skipped_no_args"
        assert result.get("per_argument_skipped") is True
        assert result.get("degraded") is True
        assert "no arguments" in result.get("last_error", "").lower()

    @pytest.mark.asyncio
    async def test_no_recursion_is_fast_not_infinite(self):
        """Regression guard: before the fix this call infinite-looped (the >2h
        hang). With the spy it would have returned after one mock call; the
        decisive check is that we reach the assert (no hang) AND the spy is
        untouched — proving the early fail-loud return path, not the recursion."""
        import time

        t0 = time.time()
        with patch.object(
            ic, "_invoke_hierarchical_fallacy", new_callable=AsyncMock
        ) as spy_hier:
            result = await ic._invoke_hierarchical_fallacy_per_argument(
                SINGLE_BLOCK, {}
            )
        elapsed = time.time() - t0
        assert spy_hier.call_count == 0
        assert elapsed < 5.0, (
            f"per-arg took {elapsed:.1f}s — should be instant (early fail-loud "
            "return), not looping"
        )
        assert result.get("per_argument_skipped") is True


class TestPerArgNormalPathUntouched:
    """When arguments ARE available, the per-arg harness still proceeds
    (recursion fix only changes the 0-args branch). We verify the args are
    detected; the full plugin path needs an LLM and is covered by the
    integration harness, not here."""

    def test_multi_block_would_proceed(self):
        args = ic._extract_arguments_for_parallel(MULTI_BLOCK, {})
        assert args, "multi-block text yields args → per-arg harness proceeds (not the fix path)"
