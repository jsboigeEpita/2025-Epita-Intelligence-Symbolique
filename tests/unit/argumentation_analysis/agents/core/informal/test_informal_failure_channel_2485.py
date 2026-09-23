# -*- coding: utf-8 -*-
"""
#2485 — a failed fallacy analysis is not a result.

`InformalAnalysisAgent.analyze_fallacies` reports a failed LLM call or an
unreadable reply as a list entry carrying an ``"error"`` key (its documented
contract). `analyze_text` returned that list under ``fallacies`` with no
top-level ``error``, so every reader counting ``len(result["fallacies"])``
counted the failure as one detected fallacy, and `_real_llm_analysis`
published it as an authentic result.

The agent is wired by the production path (`setup_agent_components`) on a
fake chat service: no LLM, no network. The analysed text is fabricated.
"""

import json
from typing import Any, List
from unittest.mock import patch

import pytest
import semantic_kernel as sk
from pydantic import SecretStr
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from argumentation_analysis.agents.core.informal import informal_agent as module
from argumentation_analysis.agents.core.informal.informal_agent import (
    InformalAnalysisAgent,
    fallacy_analysis_failure,
)

FABRICATED_TEXT = (
    "Le comité de quartier doit rejeter ce projet de fontaine, car son "
    "architecte collectionne les parapluies verts."
)
SERVICE_ID = "fake_service_2485"
ONE_FALLACY = {"sophismes": [{"nom": "ad hominem", "confidence": 0.9}]}


class ScriptedChatCompletion(ChatCompletionClientBase):
    """Answers every prompt with one scripted behaviour."""

    behaviour: str = "valid"

    async def _inner_get_chat_message_contents(
        self, chat_history: ChatHistory, settings: Any
    ) -> List[ChatMessageContent]:
        if self.behaviour == "raises":
            raise RuntimeError("simulated 401 from the provider")
        content = {
            "valid": json.dumps(ONE_FALLACY),
            "empty": json.dumps({"sophismes": []}),
            "non_json": "Je ne peux pas répondre en JSON.",
            "arguments": "Premier argument\nSecond argument",
        }[self.behaviour]
        return [
            ChatMessageContent(
                role="assistant", content=content, ai_model_id=self.ai_model_id
            )
        ]


def _agent(behaviour: str) -> InformalAnalysisAgent:
    service = ScriptedChatCompletion(
        ai_model_id="fake-model-2485", service_id=SERVICE_ID, behaviour=behaviour
    )
    kernel = sk.Kernel()
    kernel.add_service(service)
    agent = InformalAnalysisAgent(kernel=kernel, agent_name="InformalAgent2485")
    agent.setup_agent_components(llm_service_id=SERVICE_ID)
    return agent


# --- analyze_text: DoD 1, on values -----------------------------------------


@pytest.mark.parametrize(
    "behaviour, names",
    [("raises", "semantic_AnalyzeFallacies"), ("non_json", "non JSON")],
)
async def test_a_failed_analysis_carries_a_top_level_error(behaviour, names):
    """Born red: ``main`` returned ``{"fallacies": [{"error": ...}]}`` and no
    top-level ``error``."""
    result = await _agent(behaviour).analyze_text(FABRICATED_TEXT)

    assert names in result.get("error", ""), result
    # The list entry stays for the direct readers of analyze_fallacies.
    assert fallacy_analysis_failure(result["fallacies"]) == result["error"]


@pytest.mark.parametrize("behaviour, count", [("valid", 1), ("empty", 0)])
async def test_a_valid_reply_has_no_error(behaviour, count):
    """Control: the same harness, a reply the agent can read."""
    result = await _agent(behaviour).analyze_text(FABRICATED_TEXT)

    assert "error" not in result, result
    assert len(result["fallacies"]) == count


async def test_a_failed_argument_identification_is_not_zero_arguments():
    result = await _agent("raises").analyze_text(
        FABRICATED_TEXT, analysis_type="arguments"
    )

    assert result["arguments"] is None
    assert "semantic_IdentifyArguments" in result.get("error", ""), result


async def test_identified_arguments_have_no_error():
    """Control for the arguments branch."""
    result = await _agent("arguments").analyze_text(
        FABRICATED_TEXT, analysis_type="arguments"
    )

    assert "error" not in result, result
    assert result["arguments"] == ["Premier argument", "Second argument"]


# --- the agent's other aggregators ------------------------------------------


async def test_analyze_argument_lifts_the_failure():
    result = await _agent("raises").analyze_argument(FABRICATED_TEXT)

    assert "semantic_AnalyzeFallacies" in result.get("error", ""), result


async def test_the_complete_analysis_categorises_no_failure():
    """``main`` categorised the error entry as a fallacy type."""
    result = await _agent("non_json").perform_complete_analysis(FABRICATED_TEXT)

    assert result.get("error") == "Résultat non JSON", result
    assert result["categories"] == {}


async def test_a_failure_has_no_fallacy_count():
    """``main`` reported ``total_fallacies: 1``. A failure has no count, not
    even 0: 0 would read "no fallacy found"."""
    result = await _agent("raises").analyze_and_categorize(FABRICATED_TEXT)

    assert result["summary"]["total_fallacies"] is None
    assert result["categories"] == {}
    assert "semantic_AnalyzeFallacies" in result.get("error", ""), result


@pytest.mark.parametrize(
    "method",
    ["analyze_argument", "perform_complete_analysis", "analyze_and_categorize"],
)
async def test_the_aggregators_report_no_error_on_a_valid_reply(method):
    """Control for the three aggregators."""
    result = await getattr(_agent("valid"), method)(FABRICATED_TEXT)

    assert "error" not in result, result
    assert len(result["fallacies"]) == 1


async def test_a_valid_reply_is_counted():
    result = await _agent("valid").analyze_and_categorize(FABRICATED_TEXT)

    assert result["summary"]["total_fallacies"] == 1


# --- the helper ---------------------------------------------------------------


@pytest.mark.parametrize(
    "fallacies, expected",
    [
        ([{"error": "Résultat non JSON", "details": "..."}], "Résultat non JSON"),
        ([{"error": "a"}, {"error": "b"}], "a; b"),
        ([{"nom": "ad hominem"}], None),
        ([], None),
        (None, None),
        ("not a list", None),
    ],
)
def test_fallacy_analysis_failure(fallacies, expected):
    assert fallacy_analysis_failure(fallacies) == expected


# --- readers: DoD 3 -----------------------------------------------------------


def test_the_conversation_orchestrator_counts_a_lifted_failure_once():
    """The top-level ``error`` and the list entry name the same failure."""
    from argumentation_analysis.orchestration.conversation_orchestrator import (
        ConversationOrchestrator,
    )

    failure = "Résultat non JSON"
    adapted = ConversationOrchestrator(mode="demo")._adapt_real_result(
        "informal",
        {"fallacies": [{"error": failure, "details": "..."}], "error": failure},
    )

    assert adapted["analysis_errors"] == [failure]
    assert adapted["fallacies_count"] == 0
    assert "sophistication_score" not in adapted


class _FailingAgent:
    """The informal agent as `_real_llm_analysis` builds it, failing."""

    def __init__(self, *args, **kwargs):
        pass

    def setup_agent_components(self, llm_service_id):
        pass

    async def analyze_text(self, text):
        return {
            "fallacies": [{"error": "Résultat non JSON"}],
            "error": "Résultat non JSON",
        }


@pytest.mark.parametrize("fallback", [False, True], ids=["no-fallback", "fallback"])
async def test_the_pipeline_never_publishes_a_failure_as_authentic(fallback):
    """``main`` returned ``authentic: True`` with the failure as its result,
    and the pipeline said ``completed``."""
    from argumentation_analysis.utils import analysis_config
    from argumentation_analysis.utils.analysis_config import (
        AnalysisConfig,
        AnalysisMode,
        UnifiedAnalysisPipeline,
    )

    config = AnalysisConfig(
        analysis_modes=[AnalysisMode.FALLACIES],
        retry_count=1,
        enable_fallback=fallback,
        require_real_llm=True,
    )
    pipeline = UnifiedAnalysisPipeline(config)
    with patch.object(module, "InformalAnalysisAgent", _FailingAgent), patch.object(
        analysis_config.settings.openai, "api_key", SecretStr("fake-key-2485")
    ):
        result = await pipeline.analyze_text(FABRICATED_TEXT)

    if fallback:
        mode_result = result.results[AnalysisMode.FALLACIES.value]
        assert mode_result["authentic"] is False
        assert mode_result["fallback"] is True
    else:
        assert result.status == "error"
        assert any("Résultat non JSON" in e for e in result.errors), result.errors
