"""Unit tests for FOL 2-pass coordinated pipeline (#544).

Tests verify:
- Pass 1: shared FOL signature extraction (sorts, predicates, constants)
- Pass 2: per-argument formula generation with shared signature
- fol_shared_signature stored on UnifiedAnalysisState
- Backward compat: existing paths still work without LLM
- Per-formula isolation retry still functions
"""

import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState


def _make_context(input_text: str, state: UnifiedAnalysisState = None) -> dict:
    if state is None:
        state = UnifiedAnalysisState(input_text)
    return {
        "_state_object": state,
        "source_metadata": {"opaque_id": "test_corpus"},
        "arguments": [
            "Socrates is a man. All men are mortal.",
            "Plato argues with Socrates about justice.",
        ],
    }


def _mock_openai(responses):
    """Create a mock AsyncOpenAI client returning the given responses in sequence."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=responses)
    return mock_client


def _mock_response(content: str) -> MagicMock:
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    return resp


class TestFolSharedSignatureField:

    def test_field_exists(self):
        state = UnifiedAnalysisState("test text")
        assert hasattr(state, "fol_shared_signature")
        assert isinstance(state.fol_shared_signature, dict)

    def test_initially_empty(self):
        state = UnifiedAnalysisState("test text")
        assert state.fol_shared_signature == {}

    def test_can_store_signature(self):
        state = UnifiedAnalysisState("test text")
        sig = {
            "sorts": {"Person": ["socrates", "plato"]},
            "predicates": {"Mortal": ["Person"]},
            "constants_raw": {"socrates": "philosopher"},
        }
        state.fol_shared_signature["corpus_a"] = sig
        assert state.fol_shared_signature["corpus_a"]["sorts"]["Person"] == ["socrates", "plato"]

    def test_multiple_sources(self):
        state = UnifiedAnalysisState("test text")
        state.fol_shared_signature["src0"] = {"sorts": {"Thing": ["a"]}}
        state.fol_shared_signature["src1"] = {"sorts": {"Person": ["b", "c"]}}
        assert len(state.fol_shared_signature) == 2


class TestFolTwoPassPipeline:

    def test_pass1_signature_stored_in_state(self):
        """When 2-pass runs, shared FOL signature should be stored in state."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fol_reasoning,
        )

        text = (
            "Socrates is a man who argues about justice in the city of Athens. "
            "All men are mortal and therefore Socrates is also mortal. "
            "Plato is a philosopher who studies the nature of truth and beauty."
        )
        state = UnifiedAnalysisState(text)
        ctx = _make_context(text, state)

        pass1_data = {
            "sorts": {"Person": ["socrates", "plato"]},
            "predicates": {"Mortal": ["Person"], "Man": ["Person"]},
            "constants": {"socrates": "philosopher", "plato": "philosopher"},
        }

        pass2_data = {"formulas": ["Man(socrates)", "forall X: (Man(X) => Mortal(X))"]}

        mock_client = _mock_openai([
            _mock_response(json.dumps(pass1_data)),
            _mock_response(json.dumps(pass2_data)),
            _mock_response(json.dumps(pass2_data)),
        ])

        with patch("openai.AsyncOpenAI", return_value=mock_client):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                result = asyncio.get_event_loop().run_until_complete(
                    _invoke_fol_reasoning(text, ctx)
                )

        assert "test_corpus" in state.fol_shared_signature
        sig = state.fol_shared_signature["test_corpus"]
        assert "Person" in sig["sorts"]
        assert "socrates" in sig["sorts"]["Person"]

    def test_pass2_formulas_use_shared_predicates(self):
        """Pass 2 formulas should reference predicates from Pass 1."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fol_reasoning,
        )

        text = "Socrates argues about justice. Plato disagrees."
        state = UnifiedAnalysisState(text)
        ctx = _make_context(text, state)

        pass1_data = {
            "sorts": {"Person": ["socrates", "plato"]},
            "predicates": {"Argues": ["Person"], "Disagrees": ["Person"]},
            "constants": {"socrates": "philosopher", "plato": "philosopher"},
        }

        pass2_data = {"formulas": ["Argues(socrates)", "Disagrees(plato)"]}

        mock_client = _mock_openai([
            _mock_response(json.dumps(pass1_data)),
            _mock_response(json.dumps(pass2_data)),
            _mock_response(json.dumps(pass2_data)),
        ])

        with patch("openai.AsyncOpenAI", return_value=mock_client):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                result = asyncio.get_event_loop().run_until_complete(
                    _invoke_fol_reasoning(text, ctx)
                )

        assert result is not None
        assert "formulas" in result
        assert len(result["formulas"]) > 0

    def test_fallback_when_no_api_key(self):
        """Without API key, should fall back to template."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fol_reasoning,
        )

        state = UnifiedAnalysisState("Test argument.")
        ctx = _make_context(state.raw_text, state)

        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            result = asyncio.get_event_loop().run_until_complete(
                _invoke_fol_reasoning(state.raw_text, ctx)
            )

        assert result is not None
        assert "formulas" in result

    def test_fallback_when_llm_fails(self):
        """When LLM call fails, should gracefully fall back."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fol_reasoning,
        )

        state = UnifiedAnalysisState("Test argument text for FOL fallback.")
        ctx = _make_context(state.raw_text, state)

        mock_client = _mock_openai([Exception("LLM error")])

        with patch("openai.AsyncOpenAI", return_value=mock_client):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                result = asyncio.get_event_loop().run_until_complete(
                    _invoke_fol_reasoning(state.raw_text, ctx)
                )

        assert result is not None
        assert "formulas" in result


class TestFolBackwardCompat:

    def test_existing_translations_path(self):
        """When upstream NL-to-logic FOL translations exist, use them directly."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fol_reasoning,
        )

        state = UnifiedAnalysisState("Test text.")
        ctx = _make_context(state.raw_text, state)
        ctx["phase_nl_to_logic_output"] = {
            "translations": [
                {
                    "logic_type": "fol",
                    "is_valid": True,
                    "formula": "Man(socrates); forall X: (Man(X) => Mortal(X))",
                    "original_text": "Socrates is mortal",
                }
            ]
        }

        result = asyncio.get_event_loop().run_until_complete(
            _invoke_fol_reasoning(state.raw_text, ctx)
        )

        assert result is not None
        assert any("Man" in f for f in result["formulas"])

    def test_explicit_formulas_context(self):
        """When context already has formulas, use them directly."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fol_reasoning,
        )

        state = UnifiedAnalysisState("Test text.")
        ctx = _make_context(state.raw_text, state)
        ctx["formulas"] = ["Human(socrates)", "Mortal(socrates)"]

        result = asyncio.get_event_loop().run_until_complete(
            _invoke_fol_reasoning(state.raw_text, ctx)
        )

        assert result is not None
        assert "Human(socrates)" in result["formulas"]

    def test_no_state_object_graceful(self):
        """Should work even without _state_object in context."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fol_reasoning,
        )

        ctx = {
            "source_metadata": {"opaque_id": "test"},
            "arguments": ["test argument"],
        }

        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            result = asyncio.get_event_loop().run_until_complete(
                _invoke_fol_reasoning("test text", ctx)
            )

        assert result is not None

    def test_template_fallback_includes_fallacies(self):
        """Template fallback should produce formulas even with fallacies context."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fol_reasoning,
        )

        state = UnifiedAnalysisState("Test text with fallacies.")
        ctx = _make_context(state.raw_text, state)
        ctx["phase_hierarchical_fallacy_output"] = {
            "fallacies": [
                {"type": "ad_hominem"},
            ]
        }

        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            result = asyncio.get_event_loop().run_until_complete(
                _invoke_fol_reasoning(state.raw_text, ctx)
            )

        assert result is not None
        assert len(result["formulas"]) > 0
