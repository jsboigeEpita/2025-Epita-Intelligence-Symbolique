"""#2747 — one malformed LLM confidence must not discard valid detections.

Both LLM tiers of the French fallacy adapter parsed each entry's confidence
inside a whole-response try: ``float(f.get("confidence", 0.5))`` raising on
ONE entry jumped to the except that returns ``[]`` — every valid detection
already appended was thrown away, and the tier-1 signal said "whole response
degraded" for a single bad entry (#2747).

The witnesses feed each tier a synthetic TWO-entry response — one valid, one
unreadable — through the tier's real parsing code with the HTTP client
doubled. No network, no LLM.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.adapters.french_fallacy_adapter import (
    FrenchFallacyAdapter,
    LLMFallacyDetector,
    SelfHostedLLMFallacyDetector,
)

VALID_ENTRY = {
    "type": "Ad Hominem",
    "confidence": 0.9,
    "explanation": "attaque la personne",
    "target_text": "Tu es stupide",
}
MALFORMED_ENTRY = {
    "type": "Appel a l'emotion",
    "confidence": "tres elevee",
    "explanation": "emotion comme operateur",
}


def _openai_double(payload):
    """An OpenAI-compatible client double answering ``payload``.

    ``create`` is awaited by detect_async, so it must be an AsyncMock — a
    plain MagicMock raises "can't be used in 'await' expression", which lands
    in the whole-response except and fakes the very degradation under test.
    """
    response = MagicMock()
    response.choices[0].message.content = json.dumps(payload)
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": json.dumps(self._payload)}}]}


class _FakeAsyncClient:
    payload = None

    def __init__(self, *args, **kwargs):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, *args, **kwargs):
        return _FakeResponse(type(self).payload)


class TestLLMFallacyDetectorPartialRejection:
    def _detector(self):
        return LLMFallacyDetector(confidence_threshold=0.4)

    async def test_valid_detection_survives_a_malformed_sibling(self):
        detector = self._detector()
        client = _openai_double({"fallacies": [VALID_ENTRY, MALFORMED_ENTRY]})
        with patch.object(
            detector,
            "_get_openai_client",
            return_value=(client, "gpt-test"),
        ):
            result = await detector.detect_async("Tu es stupide donc tort.")
        assert [d.fallacy_type for d in result] == ["Ad Hominem"], (
            "#2747: the malformed sibling threw away the valid detection — "
            f"got {[d.fallacy_type for d in result]}"
        )
        assert result[0].confidence == 0.9

    async def test_partial_rejection_is_exposed_and_not_global(self):
        detector = self._detector()
        client = _openai_double({"fallacies": [VALID_ENTRY, MALFORMED_ENTRY]})
        with patch.object(
            detector,
            "_get_openai_client",
            return_value=(client, "gpt-test"),
        ):
            await detector.detect_async("Tu es stupide donc tort.")
        assert detector.last_degraded is False, (
            "a single bad entry must not mark the whole response degraded — "
            "the valid detections are reliable"
        )
        assert (
            len(detector.last_rejected) == 1
        ), "the rejected entry must be exposed to consumers, not swallowed"
        assert "tres elevee" in detector.last_rejected[0]

    async def test_non_object_entry_is_rejected_by_name(self):
        detector = self._detector()
        client = _openai_double({"fallacies": [VALID_ENTRY, "not-an-object"]})
        with patch.object(
            detector,
            "_get_openai_client",
            return_value=(client, "gpt-test"),
        ):
            result = await detector.detect_async("Tu es stupide donc tort.")
        assert [d.fallacy_type for d in result] == ["Ad Hominem"]
        assert len(detector.last_rejected) == 1
        assert "not-an-object" in detector.last_rejected[0]

    async def test_whole_response_failure_still_degrades(self):
        """Anti-'empty the guard': a broken response is still [] + degraded."""
        detector = self._detector()
        client = MagicMock()
        client.chat.completions.create = MagicMock(side_effect=Exception("API error"))
        with patch.object(
            detector,
            "_get_openai_client",
            return_value=(client, "gpt-test"),
        ):
            result = await detector.detect_async("Texte.")
        assert result == []
        assert detector.last_degraded is True
        assert detector.last_error


class TestSelfHostedPartialRejection:
    def _detector(self):
        return SelfHostedLLMFallacyDetector(
            endpoint="http://llm-double.invalid", model="m"
        )

    async def test_valid_detection_survives_a_malformed_sibling(self):
        detector = self._detector()
        _FakeAsyncClient.payload = {"fallacies": [VALID_ENTRY, MALFORMED_ENTRY]}
        # ``import httpx`` lives INSIDE detect_async (line 1080), so the
        # double is patched on the httpx module itself.
        with patch("httpx.AsyncClient", _FakeAsyncClient):
            result = await detector.detect_async("Tu es stupide donc tort.")
        assert [d.fallacy_type for d in result] == [
            "Ad Hominem"
        ], "#2747: the self-hosted tier threw away the valid detection"
        assert result[0].source == "self_hosted_llm"

    async def test_partial_rejection_is_exposed(self):
        detector = self._detector()
        _FakeAsyncClient.payload = {"fallacies": [VALID_ENTRY, MALFORMED_ENTRY]}
        with patch("httpx.AsyncClient", _FakeAsyncClient):
            await detector.detect_async("Tu es stupide donc tort.")
        assert len(detector.last_rejected) == 1
        assert "tres elevee" in detector.last_rejected[0]


class TestAdapterSurfacesRejections:
    """#2747 DoD: the rejection reaches the CONSUMER, not just the detector.

    ``FrenchFallacyAdapter.detect`` is the only production reader of the two
    detectors (coordinator review on PR #2831): it must route
    ``last_rejected`` / ``last_degraded`` into
    ``FallacyAnalysisResult.tier_warnings``, which ``to_dict()`` exports and
    ``FrenchFallacyPlugin.detect_fallacies`` returns to the agent.
    """

    def test_llm_partial_rejection_reaches_tier_warnings(self):
        adapter = FrenchFallacyAdapter(
            enable_symbolic=False, enable_self_hosted_llm=False
        )
        client = _openai_double({"fallacies": [VALID_ENTRY, MALFORMED_ENTRY]})
        with patch.object(
            adapter._llm,
            "_get_openai_client",
            return_value=(client, "gpt-test"),
        ):
            result = adapter.detect("Tu es stupide donc tort.")
        assert (
            "Ad Hominem" in result["detected_fallacies"]
        ), "#2747: the valid detection must survive at the adapter level"
        warning = result["tier_warnings"]["llm"]
        assert (
            "1/2" in warning and "tres elevee" in warning
        ), f"the partial rejection must be visible to the consumer, got {warning!r}"

    def test_self_hosted_partial_rejection_reaches_tier_warnings(self):
        adapter = FrenchFallacyAdapter(
            enable_symbolic=False,
            enable_llm=False,
            self_hosted_endpoint="http://llm-double.invalid",
            self_hosted_model="m",
        )
        _FakeAsyncClient.payload = {"fallacies": [VALID_ENTRY, MALFORMED_ENTRY]}
        with patch("httpx.AsyncClient", _FakeAsyncClient):
            result = adapter.detect("Tu es stupide donc tort.")
        assert "Ad Hominem" in result["detected_fallacies"]
        warning = result["tier_warnings"]["self_hosted_llm"]
        assert "1/2" in warning and "tres elevee" in warning

    def test_llm_whole_tier_failure_reaches_tier_warnings(self):
        """A failed tier must not read as "tier ran, found nothing" (#1019)."""
        adapter = FrenchFallacyAdapter(
            enable_symbolic=False, enable_self_hosted_llm=False
        )
        client = MagicMock()
        client.chat.completions.create = AsyncMock(side_effect=Exception("API error"))
        with patch.object(
            adapter._llm,
            "_get_openai_client",
            return_value=(client, "gpt-test"),
        ):
            result = adapter.detect("Texte.")
        assert result["detected_fallacies"] == {}
        assert result["tier_warnings"]["llm"] == "tier failed: API error"
        assert "llm" not in result["tiers_used"]
