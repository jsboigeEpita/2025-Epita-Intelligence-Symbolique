"""
Tests for SelfHostedLLMFallacyDetector (#297).

Covers:
- Availability check (env vars configured vs not)
- Detection with mocked httpx response
- JSON parsing (valid, markdown-wrapped, malformed)
- Integration with FrenchFallacyAdapter
- Graceful degradation when endpoint unreachable
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.adapters.french_fallacy_adapter import (
    SelfHostedLLMFallacyDetector,
    FrenchFallacyAdapter,
    FallacyDetection,
)

# -- Availability Tests -----------------------------------------------------


class TestSelfHostedLLMAvailability:
    def test_available_when_configured(self):
        det = SelfHostedLLMFallacyDetector(
            endpoint="https://api.example.com/v1",
            model="test-model",
        )
        assert det.is_available() is True

    def test_not_available_without_endpoint(self):
        with patch.dict("os.environ", {}, clear=True):
            det = SelfHostedLLMFallacyDetector(endpoint="", model="test-model")
            assert det.is_available() is False

    def test_not_available_without_model(self):
        with patch.dict("os.environ", {}, clear=True):
            det = SelfHostedLLMFallacyDetector(
                endpoint="https://api.example.com/v1", model=""
            )
            assert det.is_available() is False

    def test_not_available_defaults(self):
        """With no args and no env vars, not available."""
        with patch.dict("os.environ", {}, clear=True):
            det = SelfHostedLLMFallacyDetector()
            assert det.is_available() is False

    def test_available_from_env(self):
        with patch.dict(
            "os.environ",
            {
                "SELF_HOSTED_LLM_ENDPOINT": "https://api.test.com/v1",
                "SELF_HOSTED_LLM_MODEL": "test-model",
            },
        ):
            det = SelfHostedLLMFallacyDetector()
            assert det.is_available() is True


# -- Detection Tests --------------------------------------------------------


class TestSelfHostedLLMDetection:
    """Test detection with mocked httpx."""

    @pytest.fixture
    def detector(self):
        return SelfHostedLLMFallacyDetector(
            endpoint="https://api.test.com/v1",
            api_key="test-key",
            model="test-model",
        )

    def _make_mock_client(self, mock_response_data):
        """Create a mock AsyncClient that works as async context manager.

        The real code does:
            async with httpx.AsyncClient(timeout=...) as client:
                response = await client.post(...)
                response.raise_for_status()
                data = response.json()

        So we need:
        - client.post() returns a response-like object
        - response.json() returns our mock data
        - response.raise_for_status() is a no-op
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        return mock_client

    def _mock_response(self, fallacies):
        return {
            "choices": [{"message": {"content": json.dumps({"fallacies": fallacies})}}]
        }

    @pytest.mark.asyncio
    async def test_detect_single_fallacy(self, detector):
        mock_client = self._make_mock_client(
            self._mock_response(
                [
                    {
                        "type": "Appel à la popularité (Ad Populum)",
                        "confidence": 0.92,
                        "explanation": "Test",
                    }
                ]
            )
        )
        with patch("httpx.AsyncClient", return_value=mock_client):
            results = await detector.detect_async(
                "Tout le monde le fait donc c'est bien"
            )
        assert len(results) == 1
        assert results[0].fallacy_type == "Appel à la popularité (Ad Populum)"
        assert results[0].confidence == 0.92
        assert results[0].source == "self_hosted_llm"

    @pytest.mark.asyncio
    async def test_detect_multiple_fallacies(self, detector):
        mock_client = self._make_mock_client(
            self._mock_response(
                [
                    {"type": "Ad Hominem", "confidence": 0.85, "explanation": "Attack"},
                    {
                        "type": "Pente glissante",
                        "confidence": 0.78,
                        "explanation": "Slope",
                    },
                ]
            )
        )
        with patch("httpx.AsyncClient", return_value=mock_client):
            results = await detector.detect_async("Test text")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_detect_no_fallacies(self, detector):
        mock_client = self._make_mock_client(self._mock_response([]))
        with patch("httpx.AsyncClient", return_value=mock_client):
            results = await detector.detect_async("Un texte normal sans sophisme")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_detect_json_in_markdown(self, detector):
        """LLM returns JSON wrapped in markdown code block."""
        content = '```json\n{"fallacies": [{"type": "Ad Hominem", "confidence": 0.9, "explanation": "test"}]}\n```'
        mock_data = {"choices": [{"message": {"content": content}}]}
        mock_client = self._make_mock_client(mock_data)
        with patch("httpx.AsyncClient", return_value=mock_client):
            results = await detector.detect_async("Test")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_detect_endpoint_unreachable(self, detector):
        """Graceful degradation when endpoint unreachable."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch("httpx.AsyncClient", return_value=mock_client):
            results = await detector.detect_async("Test text")
        assert results == []

    @pytest.mark.asyncio
    async def test_detect_malformed_json(self, detector):
        """Handle malformed JSON from LLM."""
        mock_data = {"choices": [{"message": {"content": "This is not JSON at all"}}]}
        mock_client = self._make_mock_client(mock_data)
        with patch("httpx.AsyncClient", return_value=mock_client):
            results = await detector.detect_async("Test text")
        assert results == []


# -- FrenchFallacyAdapter Integration --------------------------------------


class TestFrenchFallacyAdapterSelfHosted:
    """Test FrenchFallacyAdapter with self-hosted LLM tier."""

    def test_adapter_creates_self_hosted_by_default(self):
        adapter = FrenchFallacyAdapter(
            enable_self_hosted_llm=True,
            enable_camembert=False,
            enable_nli=False,
            enable_llm=False,
            self_hosted_endpoint="https://api.test.com/v1",
            self_hosted_model="test-model",
        )
        assert adapter._self_hosted_llm is not None

    def test_adapter_self_hosted_in_tiers(self):
        adapter = FrenchFallacyAdapter(
            enable_self_hosted_llm=True,
            enable_camembert=False,
            enable_nli=False,
            enable_llm=False,
            self_hosted_endpoint="https://api.test.com/v1",
            self_hosted_model="test-model",
        )
        tiers = adapter.get_available_tiers()
        assert "self_hosted_llm" in tiers

    def test_adapter_camembert_skipped_when_self_hosted_enabled(self):
        """CamemBERT not instantiated when self-hosted LLM is enabled."""
        adapter = FrenchFallacyAdapter(
            enable_self_hosted_llm=True,
            enable_camembert=True,
            enable_nli=False,
            enable_llm=False,
            self_hosted_endpoint="https://api.test.com/v1",
            self_hosted_model="test-model",
        )
        assert adapter._camembert is None

    def test_adapter_falls_back_to_camembert_without_self_hosted(self):
        """CamemBERT used when self-hosted LLM not enabled."""
        adapter = FrenchFallacyAdapter(
            enable_self_hosted_llm=False,
            enable_camembert=True,
            enable_nli=False,
            enable_llm=False,
        )
        assert adapter._camembert is not None
        assert adapter._self_hosted_llm is None
