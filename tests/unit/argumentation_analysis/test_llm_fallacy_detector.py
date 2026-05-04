"""Tests for #297 — LLM-based fallacy detection replacing CamemBERT.

Verifies that:
1. LLMFallacyDetector calls the OpenAI-compatible API
2. Parses structured JSON response into FallacyDetection objects
3. Respects confidence threshold
4. FrenchFallacyAdapter defaults to CamemBERT disabled
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestLLMFallacyDetector:
    """Tests for LLMFallacyDetector (#297)."""

    def _make_detector(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            LLMFallacyDetector,
        )

        return LLMFallacyDetector(confidence_threshold=0.4)

    def test_is_available_with_api_key(self):
        """Detector available when OPENAI_API_KEY is set."""
        detector = self._make_detector()
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            detector._available = None  # reset cache
            assert detector.is_available()

    def test_is_not_available_without_api_key(self):
        """Detector unavailable without OPENAI_API_KEY."""
        detector = self._make_detector()
        with patch.dict("os.environ", {}, clear=True):
            detector._available = None
            assert not detector.is_available()

    async def test_detect_async_parses_response(self):
        """detect_async returns FallacyDetection objects from LLM JSON."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            LLMFallacyDetector,
        )

        llm_response = json.dumps(
            {
                "fallacies": [
                    {
                        "type": "Argument d'autorite (Appeal to Authority)",
                        "confidence": 0.85,
                        "explanation": "Utilise une autorite non pertinente",
                        "target_text": "Elon Musk a dit que",
                    },
                    {
                        "type": "Generalisation hative (Hasty Generalization)",
                        "confidence": 0.3,  # below threshold
                        "explanation": "Pas assez d'exemples",
                        "target_text": "Tous les...",
                    },
                ]
            }
        )

        mock_message = MagicMock()
        mock_message.content = llm_response
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        detector = LLMFallacyDetector(confidence_threshold=0.4)

        with patch.object(
            detector, "_get_openai_client", return_value=(mock_client, "gpt-5-mini")
        ):
            result = await detector.detect_async(
                "L'IA est dangereuse car Elon Musk l'a dit."
            )

        # First fallacy above threshold
        assert len(result) == 1
        assert result[0].fallacy_type == "Argument d'autorite (Appeal to Authority)"
        assert result[0].confidence == 0.85
        assert result[0].source == "llm"
        assert result[0].description == "Utilise une autorite non pertinente"

    async def test_detect_async_handles_markdown_fences(self):
        """detect_async strips markdown code fences from LLM response."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            LLMFallacyDetector,
        )

        llm_response = '```json\n{"fallacies": [{"type": "Ad Hominem", "confidence": 0.9, "explanation": "test"}]}\n```'

        mock_message = MagicMock()
        mock_message.content = llm_response
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        detector = LLMFallacyDetector(confidence_threshold=0.3)

        with patch.object(
            detector, "_get_openai_client", return_value=(mock_client, "gpt-5-mini")
        ):
            result = await detector.detect_async("Tu es stupide donc tu as tort.")

        assert len(result) == 1
        assert result[0].fallacy_type == "Ad Hominem"

    async def test_detect_async_handles_empty_fallacies(self):
        """detect_async returns empty list when no fallacies detected."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            LLMFallacyDetector,
        )

        llm_response = '{"fallacies": []}'

        mock_message = MagicMock()
        mock_message.content = llm_response
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        detector = LLMFallacyDetector()

        with patch.object(
            detector, "_get_openai_client", return_value=(mock_client, "test")
        ):
            result = await detector.detect_async("Le ciel est bleu.")

        assert result == []

    async def test_detect_async_handles_api_error(self):
        """detect_async returns empty list on API error."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            LLMFallacyDetector,
        )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API error")
        )

        detector = LLMFallacyDetector()

        with patch.object(
            detector, "_get_openai_client", return_value=(mock_client, "test")
        ):
            result = await detector.detect_async("Test text.")

        assert result == []


class TestFrenchFallacyAdapterDefaults:
    """Tests for FrenchFallacyAdapter default configuration (#297)."""

    def test_camembert_disabled_by_default(self):
        """CamemBERT is disabled by default after #297."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        adapter = FrenchFallacyAdapter()
        assert adapter._camembert is None

    def test_llm_tier_enabled_by_default(self):
        """LLM tier is enabled by default."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        adapter = FrenchFallacyAdapter()
        assert adapter._llm is not None

    def test_symbolic_tier_enabled_by_default(self):
        """Symbolic tier is enabled by default."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        adapter = FrenchFallacyAdapter()
        assert adapter._symbolic is not None

    def test_can_still_enable_camembert(self):
        """CamemBERT can still be explicitly enabled."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        adapter = FrenchFallacyAdapter(enable_camembert=True)
        assert adapter._camembert is not None
