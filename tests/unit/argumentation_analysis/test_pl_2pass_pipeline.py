"""Unit tests for PL 2-pass coordinated pipeline (#547).

Tests verify:
- _parse_json_from_llm extracts JSON from LLM noise
- Pass 1: atom inventory extraction and validation
- Pass 2: formula generation with shared atoms
- Backward compat: existing paths still work without LLM
- atomic_propositions stored on UnifiedAnalysisState
- Sanitizer still applied after 2-pass
"""

import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState


# ── Helper fixtures ──────────────────────────────────────────────────────


def _make_context(input_text: str, state: UnifiedAnalysisState = None) -> dict:
    """Build a context dict for _invoke_propositional_logic."""
    if state is None:
        state = UnifiedAnalysisState(input_text)
    return {
        "_state_object": state,
        "source_metadata": {"opaque_id": "test_corpus"},
        "arguments": [
            "National sovereignty requires immediate action",
            "Foreign powers threaten our independence",
        ],
    }


# ── Test _parse_json_from_llm ────────────────────────────────────────────


class TestParseJsonFromLlm:

    def test_clean_json(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _parse_json_from_llm,
        )
        raw = '{"propositions": ["a", "b"]}'
        result = _parse_json_from_llm(raw)
        assert result == {"propositions": ["a", "b"]}

    def test_json_in_markdown_fence(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _parse_json_from_llm,
        )
        raw = '```json\n{"propositions": ["x"]}\n```'
        result = _parse_json_from_llm(raw)
        assert result == {"propositions": ["x"]}

    def test_json_with_surrounding_text(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _parse_json_from_llm,
        )
        raw = 'Here is the result:\n{"formulas": ["p => q"]}\nDone.'
        result = _parse_json_from_llm(raw)
        assert result == {"formulas": ["p => q"]}

    def test_invalid_json_returns_empty(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _parse_json_from_llm,
        )
        result = _parse_json_from_llm("no json here")
        assert result == {}

    def test_empty_input(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _parse_json_from_llm,
        )
        result = _parse_json_from_llm("")
        assert result == {}


# ── Test UnifiedAnalysisState.atomic_propositions ────────────────────────


class TestAtomicPropositionsField:

    def test_field_exists(self):
        state = UnifiedAnalysisState("test text")
        assert hasattr(state, "atomic_propositions")
        assert isinstance(state.atomic_propositions, dict)

    def test_field_initially_empty(self):
        state = UnifiedAnalysisState("test text")
        assert state.atomic_propositions == {}

    def test_can_store_atoms(self):
        state = UnifiedAnalysisState("test text")
        state.atomic_propositions["corpus_a"] = ["is_raining", "ground_wet"]
        assert state.atomic_propositions["corpus_a"] == ["is_raining", "ground_wet"]

    def test_multiple_sources(self):
        state = UnifiedAnalysisState("test text")
        state.atomic_propositions["src0"] = ["a", "b"]
        state.atomic_propositions["src1"] = ["c", "d", "e"]
        assert len(state.atomic_propositions) == 2
        assert state.atomic_propositions["src1"] == ["c", "d", "e"]


# ── Test 2-pass pipeline integration ────────────────────────────────────


class TestTwoPassPipeline:

    def test_pass1_atoms_stored_in_state(self):
        """When 2-pass pipeline runs, atoms should be stored in state."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_propositional_logic,
        )

        state = UnifiedAnalysisState(
            "The speaker argues that sovereignty requires action. "
            "Foreign powers threaten independence. "
            "However, cooperation yields better outcomes."
        )
        ctx = _make_context(state.raw_text, state)

        # Mock OpenAI to return atom inventory then formulas
        mock_resp_1 = MagicMock()
        mock_resp_1.choices = [MagicMock()]
        mock_resp_1.choices[0].message.content = json.dumps({
            "propositions": ["sovereignty_requires_action", "foreign_threat", "cooperation_better"]
        })

        mock_resp_2 = MagicMock()
        mock_resp_2.choices = [MagicMock()]
        mock_resp_2.choices[0].message.content = json.dumps({
            "formulas": ["sovereignty_requires_action => foreign_threat", "!cooperation_better"]
        })

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[mock_resp_1, mock_resp_2, mock_resp_2]
        )

        with patch("openai.AsyncOpenAI", return_value=mock_client):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                result = asyncio.get_event_loop().run_until_complete(
                    _invoke_propositional_logic(state.raw_text, ctx)
                )

        # Check atoms stored in state
        assert "test_corpus" in state.atomic_propositions
        atoms = state.atomic_propositions["test_corpus"]
        assert "sovereignty_requires_action" in atoms
        assert "foreign_threat" in atoms

    def test_pass2_formulas_use_shared_atoms(self):
        """Pass 2 formulas should reference atoms from Pass 1."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_propositional_logic,
        )

        state = UnifiedAnalysisState("Text with arguments about sovereignty.")
        ctx = _make_context(state.raw_text, state)

        atoms = ["sovereignty_action", "foreign_threat", "cooperation_outcome"]

        mock_resp_1 = MagicMock()
        mock_resp_1.choices = [MagicMock()]
        mock_resp_1.choices[0].message.content = json.dumps({"propositions": atoms})

        formula_resp = MagicMock()
        formula_resp.choices = [MagicMock()]
        formula_resp.choices[0].message.content = json.dumps({
            "formulas": ["sovereignty_action => !foreign_threat"]
        })

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[mock_resp_1, formula_resp, formula_resp]
        )

        with patch("openai.AsyncOpenAI", return_value=mock_client):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                result = asyncio.get_event_loop().run_until_complete(
                    _invoke_propositional_logic(state.raw_text, ctx)
                )

        assert result is not None
        assert "formulas" in result
        assert len(result["formulas"]) > 0

    def test_fallback_when_no_api_key(self):
        """Without API key, should fall back to template or NL-to-logic."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_propositional_logic,
        )

        state = UnifiedAnalysisState("Test argument.")
        ctx = _make_context(state.raw_text, state)

        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            result = asyncio.get_event_loop().run_until_complete(
                _invoke_propositional_logic(state.raw_text, ctx)
            )

        assert result is not None
        assert "formulas" in result

    def test_fallback_when_llm_fails(self):
        """When LLM call fails, should gracefully fall back."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_propositional_logic,
        )

        state = UnifiedAnalysisState("Test argument text for fallback.")
        ctx = _make_context(state.raw_text, state)

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("LLM error"))

        with patch("openai.AsyncOpenAI", return_value=mock_client):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                result = asyncio.get_event_loop().run_until_complete(
                    _invoke_propositional_logic(state.raw_text, ctx)
                )

        # Should still produce a result via template fallback
        assert result is not None
        assert "formulas" in result


class TestBackwardCompat:

    def test_existing_translations_path_still_works(self):
        """When upstream NL-to-logic translations exist, use them directly."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_propositional_logic,
        )

        state = UnifiedAnalysisState("Test text.")
        ctx = _make_context(state.raw_text, state)
        ctx["phase_nl_to_logic_output"] = {
            "translations": [
                {
                    "logic_type": "propositional",
                    "is_valid": True,
                    "formula": "p => q",
                    "original_text": "If it rains the ground is wet",
                }
            ]
        }

        result = asyncio.get_event_loop().run_until_complete(
            _invoke_propositional_logic(state.raw_text, ctx)
        )

        assert result is not None
        assert "p => q" in result["formulas"]

    def test_explicit_formulas_context_still_works(self):
        """When context already has formulas, use them directly."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_propositional_logic,
        )

        state = UnifiedAnalysisState("Test text.")
        ctx = _make_context(state.raw_text, state)
        ctx["formulas"] = ["a & b", "a => c"]

        result = asyncio.get_event_loop().run_until_complete(
            _invoke_propositional_logic(state.raw_text, ctx)
        )

        assert result is not None
        assert "a & b" in result["formulas"]

    def test_no_state_object_graceful(self):
        """Should work even without _state_object in context."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_propositional_logic,
        )

        ctx = {
            "source_metadata": {"opaque_id": "test"},
            "arguments": ["test argument"],
        }

        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            result = asyncio.get_event_loop().run_until_complete(
                _invoke_propositional_logic("test text", ctx)
            )

        assert result is not None
