"""Reasoning-starved completion guard (#1929) — CI guard, zero network.

A reasoning model can spend its whole completion budget on invisible
reasoning tokens and still answer HTTP 200 — empty content,
finish_reason == "length". Two production sites pin a budget and are
wired to the shared guard ``llm_completion_guard``:

- ``argumentation_analysis/services/ai_shield/layers/llm_validator.py``
  (direct openai call, budget 200) — a starved call used to collapse into
  the silent score-0.0 "no threat" default;
- ``argumentation_analysis/agents/core/logic/watson_logic_assistant.py``
  (Semantic Kernel, budget 400) — a starved call used to masquerade as a
  fabricated fallback answer.

DoD mapping (#1929):
- starved (length + empty) raises at BOTH call points — synthetic
  fixtures, no network, no API key;
- discrimination: an empty answer with finish_reason == "stop" is
  legitimate and must NOT raise, at the helper and at both sites;
- the SK site reads the finish_reason off ``FunctionResult.value[0]``
  (the connector carries it on ChatMessageContent).

Tests are fixture-free on purpose: each one monkey-patches by hand
(save/restore), so the file also runs outside pytest (the local CI-less
environment skips the whole session when the JVM cannot start).
"""

import openai

from argumentation_analysis.core.utils.llm_completion_guard import (
    ReasoningStarvedError,
    assert_not_reasoning_starved,
)


class _FakeCompletions:
    def __init__(self, response):
        self._response = response

    def create(self, **kwargs):
        return self._response


class _FakeOpenAIClient:
    def __init__(self, response):
        self.chat = type("FakeChat", (), {"completions": _FakeCompletions(response)})()


def _completion_response(finish_reason, content):
    """One openai-shaped choice: only the fields the site consults."""
    message = type("FakeMessage", (), {"content": content})()
    choice = type(
        "FakeChoice", (), {"finish_reason": finish_reason, "message": message}
    )()
    return type("FakeResponse", (), {"choices": [choice]})()


# --- helper-level discrimination -------------------------------------------


def test_starved_completion_raises():
    for finish, content in [("length", ""), ("length", None), ("length", "   ")]:
        try:
            assert_not_reasoning_starved(finish, content, site="unit")
        except ReasoningStarvedError:
            pass
        else:
            raise AssertionError(f"({finish!r}, {content!r}) should raise")


def test_legitimate_completions_pass():
    # Empty answer with stop is legitimate — the discriminator is the
    # finish reason, never the length (#1929 DoD: no red on stop+empty).
    assert_not_reasoning_starved("stop", "", site="unit")
    assert_not_reasoning_starved("stop", None, site="unit")
    assert_not_reasoning_starved(None, "", site="unit")
    # Truncated but non-empty is a degraded answer, not a starved call.
    assert_not_reasoning_starved("length", "partial answer", site="unit")


# --- site 1: ai_shield LLM validator (direct openai call) -------------------


def test_validator_site_raises_on_starved_budget():
    from argumentation_analysis.services.ai_shield.layers.llm_validator import (
        LLMValidatorLayer,
    )

    real_openai = openai.OpenAI
    openai.OpenAI = lambda **kwargs: _FakeOpenAIClient(
        _completion_response("length", None)
    )
    try:
        layer = LLMValidatorLayer(api_key="test-key")
        try:
            layer.validate("some user text to classify")
        except ReasoningStarvedError:
            pass
        else:
            raise AssertionError(
                "starved budget must raise through validate() — the generic "
                "error fallback must not swallow it"
            )
    finally:
        openai.OpenAI = real_openai


def test_validator_site_passes_on_legitimate_empty():
    from argumentation_analysis.services.ai_shield.layers.llm_validator import (
        LLMValidatorLayer,
    )

    real_openai = openai.OpenAI
    openai.OpenAI = lambda **kwargs: _FakeOpenAIClient(_completion_response("stop", ""))
    try:
        layer = LLMValidatorLayer(api_key="test-key")
        result = layer.validate("some user text to classify")
        assert result.score == 0.0
        assert result.passed
        assert "reasoning" not in str(result.details)
    finally:
        openai.OpenAI = real_openai


# --- site 2: Watson logic assistant (Semantic Kernel) -----------------------


def _watson_agent(starved):
    from semantic_kernel import Kernel
    from semantic_kernel.connectors.ai.chat_completion_client_base import (
        ChatCompletionClientBase,
    )
    from unittest.mock import AsyncMock, MagicMock
    from argumentation_analysis.agents.core.logic.watson_logic_assistant import (
        WatsonLogicAssistant,
    )

    kernel = Kernel()
    # Same pattern as the tests/conftest.py mock_chat_completion_service
    # fixture: a spec'd mock service so BaseAgent's construction-time
    # get_service() finds one. invoke() is overridden below anyway.
    mock_service = MagicMock(spec=ChatCompletionClientBase)
    mock_service.service_id = "test_llm_service"
    mock_service.ai_model_id = "test-model"
    kernel.add_service(mock_service)

    fake_completion = type(
        "FakeCompletion",
        (),
        {"finish_reason": "length" if starved else "stop", "content": ""},
    )()
    fake_result = type("FakeFunctionResult", (), {"value": [fake_completion]})()
    # Pydantic V2 frozen kernel — same pattern as tests/agents watson tests.
    object.__setattr__(kernel, "invoke", AsyncMock(return_value=fake_result))

    # PropositionalLogicAgent (the parent) always constructs a fresh
    # TweetyBridge, which starts the JVM — patch the module-level reference
    # so the guard runs wherever the JVM/Jars are unavailable (CI builds
    # them, a plain checkout cannot).
    import argumentation_analysis.agents.core.logic.propositional_logic_agent as _pla
    from unittest.mock import patch

    fake_bridge = MagicMock()
    fake_bridge.initializer.is_jvm_ready.return_value = True
    with patch.object(_pla, "TweetyBridge", lambda: fake_bridge):
        agent = WatsonLogicAssistant(
            kernel=kernel,
            agent_name="Watson",
            tweety_bridge=MagicMock(),
        )
    return agent


def test_watson_site_raises_on_starved_budget():
    import asyncio
    from semantic_kernel.contents.chat_history import ChatHistory

    agent = _watson_agent(starved=True)
    history = ChatHistory()
    history.add_user_message("Valide ce raisonnement: si A alors B, A, donc B ?")
    try:
        asyncio.run(agent.invoke_custom(history))
    except ReasoningStarvedError:
        pass
    else:
        raise AssertionError(
            "starved budget must raise through invoke_custom() — the "
            "fabricated fallback answer was the mask"
        )


def test_watson_site_passes_on_legitimate_empty():
    import asyncio
    from semantic_kernel.contents.chat_history import ChatHistory

    agent = _watson_agent(starved=False)
    history = ChatHistory()
    history.add_user_message("Valide ce raisonnement: si A alors B, A, donc B ?")
    response = asyncio.run(agent.invoke_custom(history))
    assert response is not None
    assert response.content  # the existing fallback path still answers
