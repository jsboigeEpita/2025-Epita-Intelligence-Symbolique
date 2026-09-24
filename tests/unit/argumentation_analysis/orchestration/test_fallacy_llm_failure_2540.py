# -*- coding: utf-8 -*-
"""#2540: a failed LLM call is a failure, never "no fallacy found".

``FallacyWorkflowPlugin.run_guided_analysis`` does not raise when its LLM
call fails; it returns ``{"error": ..., "fallacies": []}``. Before #2540
nothing read that key, so the detector reported 0 fallacies with a clean
status (one paragraph), with ``widenet+perarg_union`` (several), or with
nothing at all (``full`` tier).

The first tests run the real plugin on the real taxonomy with a real
Semantic Kernel OpenAI service whose HTTP transport refuses every request:
the call fails the way a bad endpoint does, in process, without spending
anything. The last ones replace the plugin's answer to pin down a partial
failure, which one failing service cannot produce.
"""

import json
from unittest.mock import patch

import httpx
import pytest
from openai import AsyncOpenAI
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

from argumentation_analysis.orchestration import invoke_callables
from argumentation_analysis.orchestration.conversational_orchestrator import (
    _run_parent_harness_fallback,
)
from argumentation_analysis.orchestration.invoke_callables import (
    FallacyDetectionFailed,
    _invoke_hierarchical_fallacy,
)

ONE_PARAGRAPH = (
    "Tu dis que fumer est dangereux, mais tu fumes toi-même, donc tu as tort."
)
TWO_PARAGRAPHS = (
    "Tout le monde achète ce téléphone, donc c'est forcément le meilleur du marché.\n\n"
    "Si on autorise les trottinettes en ville, bientôt plus personne ne marchera."
)
HYBRID_ANSWER = {
    "fallacies": [
        {
            "fallacy_type": "appel à la popularité",
            "confidence": 0.7,
            "taxonomy_pk": "h1",
        }
    ],
    "extraction_method": "hybrid_neural_symbolic",
    "tier": "hybrid",
}


def _refuse(request):
    raise httpx.ConnectError("test double: the LLM endpoint refuses (#2540)")


def _failing_service(service_id="fallacy_widenet", **_ignored):
    client = AsyncOpenAI(
        api_key="test-2540",
        base_url="http://llm-double-2540.invalid/v1",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(_refuse)),
    )
    return OpenAIChatCompletion(
        ai_model_id="gpt-test-2540", async_client=client, service_id=service_id
    )


@pytest.fixture
def failing_llm():
    with patch(
        "argumentation_analysis.core.llm_service.create_llm_service",
        side_effect=_failing_service,
    ) as factory:
        yield factory


async def _hybrid_answers(text, context):
    return json.loads(json.dumps(HYBRID_ANSWER))


async def _hybrid_unavailable(text, context):
    return {"fallacies": [], "extraction_method": "unavailable", "error": "No module"}


# ---- the real plugin, with an LLM call that fails ----


async def test_one_paragraph_raises_with_the_llm_error(failing_llm):
    with pytest.raises(FallacyDetectionFailed) as caught:
        await _invoke_hierarchical_fallacy(ONE_PARAGRAPH, {"fallacy_tier": "llm"})

    message = str(caught.value)
    assert message.startswith("FALLACY_DETECTION_FAILED: tier=llm, reason=")
    assert "Connection error" in message
    assert failing_llm.called


async def test_several_paragraphs_raise_when_no_run_answered(failing_llm):
    with pytest.raises(FallacyDetectionFailed) as caught:
        await _invoke_hierarchical_fallacy(TWO_PARAGRAPHS, {"fallacy_tier": "llm"})

    message = str(caught.value)
    assert "Connection error" in message
    assert "all 2 per-argument fallacy runs got no answer" in message


async def test_full_tier_names_the_tier_that_did_not_run(failing_llm, monkeypatch):
    monkeypatch.setattr(invoke_callables, "_invoke_hybrid_fallacy", _hybrid_answers)

    result = await _invoke_hierarchical_fallacy(
        TWO_PARAGRAPHS, {"fallacy_tier": "full"}
    )

    assert result["fallacies"] == HYBRID_ANSWER["fallacies"]
    assert result["llm_count"] == 0
    assert result["degraded"] is True
    assert result["last_error"].startswith(
        "llm tier did not run: FALLACY_DETECTION_FAILED: tier=llm"
    )
    assert "Connection error" in result["last_error"]


async def test_full_tier_raises_when_no_tier_ran(failing_llm, monkeypatch):
    monkeypatch.setattr(invoke_callables, "_invoke_hybrid_fallacy", _hybrid_unavailable)

    with pytest.raises(FallacyDetectionFailed) as caught:
        await _invoke_hierarchical_fallacy(ONE_PARAGRAPH, {"fallacy_tier": "full"})

    message = str(caught.value)
    assert message.startswith("FALLACY_DETECTION_FAILED: tier=full, llm: ")
    assert message.endswith("; hybrid: No module")


async def test_full_tier_without_a_key_and_without_hybrid_is_unavailable(
    monkeypatch,
):
    """Nothing could run at all: that stays the 503 kind, not a failure."""
    monkeypatch.setattr(invoke_callables, "_invoke_hybrid_fallacy", _hybrid_unavailable)
    with patch(
        "argumentation_analysis.core.llm_service.create_llm_service",
        side_effect=ValueError("OPENAI_API_KEY is not set"),
    ):
        with pytest.raises(RuntimeError) as caught:
            await _invoke_hierarchical_fallacy(ONE_PARAGRAPH, {"fallacy_tier": "full"})

    assert not isinstance(caught.value, FallacyDetectionFailed)
    assert str(caught.value).startswith("FALLACY_DETECTION_UNAVAILABLE: tier=full")


async def test_the_conversational_harness_logs_the_failure(failing_llm):
    # Over 500 characters, so the whole-text pass runs too.
    text = "\n\n".join([TWO_PARAGRAPHS] * 4)

    entry = await _run_parent_harness_fallback(text, state=object())

    assert entry["status"] == "failed"
    assert entry["last_error"].startswith(
        "FallacyDetectionFailed: FALLACY_DETECTION_FAILED"
    )


# ---- a partial failure: the plugin's answer is replaced ----

_ANSWER = {
    "fallacies": [
        {
            "fallacy_type": "Appel à la popularité",
            "taxonomy_pk": "p1",
            "confidence": 0.8,
        }
    ],
    "exploration_method": "iterative_deepening",
}
_FAILED = {
    "error": "service failed to complete the prompt: Connection error.",
    "fallacies": [],
}


def _plugin_answering(answers):
    """``run_guided_analysis`` answering from ``answers`` by the text's first words."""

    async def run_guided_analysis(self, argument_text, **kwargs):
        for prefix, answer in answers.items():
            if argument_text.startswith(prefix):
                return json.dumps(answer)
        raise AssertionError(f"unexpected text: {argument_text[:40]!r}")

    return patch(
        "argumentation_analysis.plugins.fallacy_workflow_plugin."
        "FallacyWorkflowPlugin.run_guided_analysis",
        run_guided_analysis,
    )


async def test_a_failed_wide_net_degrades_the_per_argument_answer(failing_llm):
    # The wide-net run gets the whole text, which starts like the first paragraph.
    with _plugin_answering({"Tout le monde": _FAILED, "Si on autorise": _ANSWER}):
        result = await _invoke_hierarchical_fallacy(
            TWO_PARAGRAPHS, {"fallacy_tier": "llm"}
        )

    assert [f["taxonomy_pk"] for f in result["fallacies"]] == ["p1"]
    assert "error" not in result
    assert result["degraded"] is True
    assert result["last_error"] == (
        "wide-net fallacy pass got no answer: " + _FAILED["error"] + "; "
        "1/2 per-argument fallacy runs got no answer: " + _FAILED["error"]
    )


async def test_a_clean_run_is_not_degraded(failing_llm):
    with _plugin_answering({"Tout le monde": _ANSWER, "Si on autorise": _ANSWER}):
        result = await _invoke_hierarchical_fallacy(
            TWO_PARAGRAPHS, {"fallacy_tier": "llm"}
        )

    assert result["extraction_method"] == "widenet+perarg_union"
    assert "degraded" not in result
    assert "last_error" not in result
