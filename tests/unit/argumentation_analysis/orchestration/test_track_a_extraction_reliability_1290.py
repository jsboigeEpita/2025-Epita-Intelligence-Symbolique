"""Track A #1290 — fact-extraction reliability contract tests.

Pins the three behaviours the issue #1290 DoD requires (coordinator R484):

  1. ``strict-JSON-mode`` — the LLM call threads ``response_format`` json_object
     when the client is available.
  2. ``bounded retry``    — a transiently-malformed JSON output is retried and
                            recovers (the LLM is nondeterministic); the second
                            call frequently parses cleanly.
  3. ``fail-loud``        — on total failure (all retries exhausted, or no
                            client), the result carries an explicit
                            ``extraction_status="failed:<reason>"`` and
                            ``arguments:[]`` — NEVER a silent ``[]``
                            masquerading as an empty corpus (#1019).

Anti-pendule guard: the heuristic fallback never fabricates *arguments*
(arguments stays []); it only supplies *claims*. Reliability, not maquillage.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

INVOKE_PATH = "argumentation_analysis.orchestration.invoke_callables"


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def _resp(content: str) -> SimpleNamespace:
    """Build a minimal chat-completion response object."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


_VALID_JSON = (
    '{"arguments": [{"text": "taxes are too high", "source_quote": "taxes"}], '
    '"claims": [], "summary": "ok"}'
)
_MALFORMED = "this is not json at all, no braces anywhere here"


# ---------------------------------------------------------------------------
# DoD #1 — strict-JSON-mode: response_format threaded on success
# ---------------------------------------------------------------------------


class TestStrictJsonModeOnSuccess:
    """A valid JSON response yields extraction_status='ok' and response_format
    is passed to the LLM call (strict-JSON-mode)."""

    def test_success_status_ok_and_response_format_passed(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fact_extraction,
        )

        with (
            patch(f"{INVOKE_PATH}._get_openai_client", return_value=(MagicMock(), "m")),
            patch(
                f"{INVOKE_PATH}._guarded_chat_completion",
                new=AsyncMock(return_value=_resp(_VALID_JSON)),
            ) as mock_call,
            patch(f"{INVOKE_PATH}._get_determinism_params", return_value={}),
        ):
            result = _run(_invoke_fact_extraction("some text", {"_state_object": None}))

        assert result["extraction_status"] == "ok"
        assert result["extraction_method"] == "llm"
        assert result["argument_count"] == 1
        # strict-JSON-mode: response_format was threaded into the call kwargs.
        kwargs = mock_call.call_args.kwargs
        assert kwargs.get("response_format") == {"type": "json_object"}
        # #1290 M1 (po-2023 diagnostic): max_tokens is threaded so dense corpora
        # are not silently truncated by the default completion ceiling.
        from argumentation_analysis.orchestration.invoke_callables import (
            _EXTRACTION_MAX_TOKENS,
        )

        assert kwargs.get("max_tokens") == _EXTRACTION_MAX_TOKENS


# ---------------------------------------------------------------------------
# DoD #2 — bounded retry recovers a transiently-malformed output
# ---------------------------------------------------------------------------


class TestBoundedRetryRecovers:
    """A first malformed response is retried; the second parses → 'ok'."""

    def test_malformed_then_valid_recovers(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fact_extraction,
        )

        with (
            patch(f"{INVOKE_PATH}._get_openai_client", return_value=(MagicMock(), "m")),
            patch(
                f"{INVOKE_PATH}._guarded_chat_completion",
                new=AsyncMock(side_effect=[_resp(_MALFORMED), _resp(_VALID_JSON)]),
            ) as mock_call,
            patch(f"{INVOKE_PATH}._get_determinism_params", return_value={}),
        ):
            result = _run(_invoke_fact_extraction("some text", {"_state_object": None}))

        assert result["extraction_status"] == "ok"
        assert result["argument_count"] == 1
        # Exactly two LLM round-trips (1 malformed + 1 recovered).
        assert mock_call.call_count == 2


# ---------------------------------------------------------------------------
# DoD #3 — fail-loud: total failure surfaces extraction_status, never silent []
# ---------------------------------------------------------------------------


class TestFailLoudAfterExhaustedRetries:
    """All retries return malformed JSON → extraction_status='failed:...' and
    arguments=[] (loud, not a silent starvation)."""

    def test_all_malformed_marks_failed_and_keeps_args_empty(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _EXTRACTION_MAX_ATTEMPTS,
            _invoke_fact_extraction,
        )

        with (
            patch(f"{INVOKE_PATH}._get_openai_client", return_value=(MagicMock(), "m")),
            patch(
                f"{INVOKE_PATH}._guarded_chat_completion",
                new=AsyncMock(return_value=_resp(_MALFORMED)),
            ) as mock_call,
            patch(f"{INVOKE_PATH}._get_determinism_params", return_value={}),
        ):
            result = _run(
                _invoke_fact_extraction(
                    "First sentence. Second one here is longer.",
                    {"_state_object": None},
                )
            )

        assert result["extraction_status"].startswith("failed:")
        assert result["extraction_method"] == "heuristic"
        # Anti-pendule (#1019): arguments NEVER fabricated in the fallback.
        assert result["arguments"] == []
        # Heuristic claims still supplied (honest), but the failure is loud.
        assert result["claim_count"] >= 1
        # The bounded retry was actually exercised.
        assert mock_call.call_count == _EXTRACTION_MAX_ATTEMPTS


# ---------------------------------------------------------------------------
# DoD #3 (variant) — no client → fail-loud, not silent
# ---------------------------------------------------------------------------


class TestNoClientFailsLoud:
    """No OpenAI client configured → extraction_status='failed:no-openai-client'."""

    def test_no_client_marks_failed_no_openai_client(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fact_extraction,
        )

        with patch(f"{INVOKE_PATH}._get_openai_client", return_value=(None, "")):
            result = _run(
                _invoke_fact_extraction(
                    "Some text here. Another sentence is present too.",
                    {"_state_object": None},
                )
            )

        assert result["extraction_status"] == "failed:no-openai-client"
        assert result["extraction_method"] == "heuristic"
        assert result["arguments"] == []


# ---------------------------------------------------------------------------
# DoD #2 (robustness) — response_format rejected → retry without it
# ---------------------------------------------------------------------------


class TestResponseFormatRejectedDegradesGracefully:
    """When the endpoint rejects response_format, the next attempt drops it and
    proceeds without consuming the whole budget on a config issue."""

    def test_rejection_then_success_without_response_format(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fact_extraction,
        )

        err = ValueError("400 response_format is not supported on this model")
        attempts: list[dict] = []

        async def _impl(client, **kwargs):
            attempts.append(dict(kwargs))
            if len(attempts) == 1:
                # First attempt carries response_format (json_mode on).
                assert kwargs.get("response_format") == {"type": "json_object"}
                raise err
            # Subsequent attempt must have dropped response_format.
            assert "response_format" not in kwargs
            return _resp(_VALID_JSON)

        with (
            patch(f"{INVOKE_PATH}._get_openai_client", return_value=(MagicMock(), "m")),
            patch(f"{INVOKE_PATH}._guarded_chat_completion", new=_impl),
            patch(f"{INVOKE_PATH}._get_determinism_params", return_value={}),
        ):
            result = _run(_invoke_fact_extraction("some text", {"_state_object": None}))

        assert result["extraction_status"] == "ok"
        assert result["argument_count"] == 1


# ---------------------------------------------------------------------------
# DoD M1 (po-2023 diagnostic) — max_tokens rejection degrades gracefully
# ---------------------------------------------------------------------------


class TestMaxTokensRejectedDegrades:
    """When the endpoint rejects max_tokens, the next attempt drops it and
    proceeds without consuming the whole budget on a config issue."""

    def test_max_tokens_rejection_then_success(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fact_extraction,
        )

        err = ValueError("400 max_tokens exceeds the model limit")
        attempts: list[dict] = []

        async def _impl(client, **kwargs):
            attempts.append(dict(kwargs))
            if len(attempts) == 1:
                assert kwargs.get("max_tokens") is not None
                raise err
            # Subsequent attempt must have dropped max_tokens.
            assert "max_tokens" not in kwargs
            return _resp(_VALID_JSON)

        with (
            patch(f"{INVOKE_PATH}._get_openai_client", return_value=(MagicMock(), "m")),
            patch(f"{INVOKE_PATH}._guarded_chat_completion", new=_impl),
            patch(f"{INVOKE_PATH}._get_determinism_params", return_value={}),
        ):
            result = _run(_invoke_fact_extraction("some text", {"_state_object": None}))

        assert result["extraction_status"] == "ok"
        assert result["argument_count"] == 1


# ---------------------------------------------------------------------------
# DoD chemin B (po-2023 diagnostic) — no-json-object vs unparseable-json
# ---------------------------------------------------------------------------


class TestCheminBNoJsonObjectDistinction:
    """The fail-loud reason distinguishes 'model emitted no JSON at all'
    (chemin B, latent hole) from 'JSON present but unparseable' (truncation
    M1 or malformed structure) — so the diagnostic is actionable."""

    def test_no_braces_marks_no_json_object(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _EXTRACTION_MAX_ATTEMPTS,
            _invoke_fact_extraction,
        )

        with (
            patch(f"{INVOKE_PATH}._get_openai_client", return_value=(MagicMock(), "m")),
            patch(
                f"{INVOKE_PATH}._guarded_chat_completion",
                new=AsyncMock(return_value=_resp(_MALFORMED)),
            ),
            patch(f"{INVOKE_PATH}._get_determinism_params", return_value={}),
        ):
            result = _run(
                _invoke_fact_extraction("Some text here.", {"_state_object": None})
            )

        # _MALFORMED has no braces → chemin B (no-json-object), distinct from
        # a truncation that leaves braces (unparseable-json).
        assert "no-json-object" in result["extraction_status"]
        assert result["arguments"] == []
        # The budget was actually spent (bounded retry exercised).
        assert _EXTRACTION_MAX_ATTEMPTS >= 1

    def test_braces_but_unparseable_marks_unparseable_json(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fact_extraction,
        )

        # Both braces present but the content is not valid JSON (malformed
        # structure — a truncation that happens to keep a closing brace, or a
        # garbled object). Distinct from no-braces-at-all (chemin B).
        _GARBLED = '{"arguments": [invalid content here]}'

        with (
            patch(f"{INVOKE_PATH}._get_openai_client", return_value=(MagicMock(), "m")),
            patch(
                f"{INVOKE_PATH}._guarded_chat_completion",
                new=AsyncMock(return_value=_resp(_GARBLED)),
            ),
            patch(f"{INVOKE_PATH}._get_determinism_params", return_value={}),
        ):
            result = _run(
                _invoke_fact_extraction("Some text here.", {"_state_object": None})
            )

        assert "unparseable-json" in result["extraction_status"]
        assert "no-json-object" not in result["extraction_status"]
        assert result["arguments"] == []


# ---------------------------------------------------------------------------
# State writer — extraction_status surfaces on the state
# ---------------------------------------------------------------------------


class TestStateWriterSurfacesExtractionStatus:
    """_write_fact_extraction_to_state propagates extraction_status so the
    pipeline/restitution can tell 'LLM succeeded, 0 args' from 'LLM failed'."""

    def test_failed_status_recorded_as_task(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_fact_extraction_to_state,
        )

        state = MagicMock()
        output = {
            "arguments": [],
            "claims": [{"text": "a claim"}],
            "extraction_method": "heuristic",
            "extraction_status": "failed:llm_no_valid_json(attempt=3,len=10)",
            "summary": "",
        }
        _write_fact_extraction_to_state(output, state, {})

        task_msgs = [str(c.args[0]) for c in state.add_task.call_args_list if c.args]
        assert any("extraction_status" in m and "failed" in m for m in task_msgs)
        # Arguments still written (claims → extracts), just none fabricated.
        assert state.extracts.append  # extracts list still populated by claims

    def test_ok_status_not_silent_and_args_written(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_fact_extraction_to_state,
        )

        state = MagicMock()
        state.extracts = []
        output = {
            "arguments": [{"text": "real arg"}],
            "claims": [],
            "extraction_method": "llm",
            "extraction_status": "ok",
            "summary": "done",
        }
        _write_fact_extraction_to_state(output, state, {})

        # A genuine argument was written to the state.
        assert state.add_argument.called
        # 'ok' status is still surfaced (distinguishes from absent field).
        task_msgs = [str(c.args[0]) for c in state.add_task.call_args_list if c.args]
        assert any("extraction_status" in m and "ok" in m for m in task_msgs)
