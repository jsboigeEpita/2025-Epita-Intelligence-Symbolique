"""#3658 item 36c — the shared phase cap reaches every uncapped call path.

The witnesses capture kwargs/settings at the REAL call sites. No model or
solver is contacted: the FOL replies are synthetic, and its empty-formula
fallback is replaced by an empty result so the two captures return before any
Java bridge is touched.
"""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIChatCompletion,
    OpenAIPromptExecutionSettings,
)

import argumentation_analysis.orchestration.invoke_callables as ic
from argumentation_analysis.agents.core.counter_argument.counter_agent import (
    CounterArgumentAgent,
)
from argumentation_analysis.agents.core.counter_argument.definitions import (
    CounterArgumentType,
    RhetoricalStrategy,
)
from argumentation_analysis.plugins.fallacy_workflow_plugin import (
    FallacyWorkflowPlugin,
)

_SYNTHETIC_TEXT = (
    "A synthetic speaker advances one claim for a fictional decision. "
    "A second sentence supplies its invented reason, solely for this test."
)


def _reply(payload):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
    )


async def _capture_fol(monkeypatch, determinism, cap):
    calls = []
    answers = [
        {"sorts": {"Thing": ["item"]}, "predicates": {}, "constants": {}},
        {"formulas": []},
    ]

    async def completion(_client, **kwargs):
        calls.append(kwargs)
        return _reply(answers[len(calls) - 1])

    class _EmptyTranslator:
        def __init__(self, **_kwargs):
            pass

        async def translate_batch(self, *_args, **_kwargs):
            return SimpleNamespace(translations=[])

    monkeypatch.setattr(ic, "_PHASE_MAX_TOKENS", cap)
    monkeypatch.setattr(ic, "_get_determinism_params", lambda: dict(determinism))
    monkeypatch.setattr(ic, "_get_openai_client", lambda: (object(), "synthetic"))
    monkeypatch.setattr(ic, "_guarded_chat_completion", completion)
    monkeypatch.setattr(
        "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator",
        _EmptyTranslator,
    )
    await ic._invoke_fol_reasoning(
        _SYNTHETIC_TEXT,
        {"phase_extract_output": {"arguments": [{"text": _SYNTHETIC_TEXT}]}},
    )
    assert len(calls) == 2, "both the signature and formula passes must be captured"
    return calls


@pytest.mark.parametrize(
    "determinism, cap, expected",
    [
        ({}, 8192, 8192),
        ({"max_completion_tokens": 321}, 8192, 321),
        ({}, 0, None),
    ],
)
def test_fol_both_passes_share_the_cap(monkeypatch, determinism, cap, expected):
    calls = asyncio.run(_capture_fol(monkeypatch, determinism, cap))
    for call in calls:
        assert call.get("max_completion_tokens") == expected


def _descent_plugin():
    return FallacyWorkflowPlugin(
        master_kernel=MagicMock(),
        llm_service=MagicMock(),
        taxonomy_data=[
            {
                "PK": "1",
                "path": "1",
                "depth": "1",
                "text_fr": "Synthetic category",
                "text_en": "Synthetic category",
            }
        ],
    )


@pytest.mark.parametrize("creator", ["_create_slave_kernel", "_create_one_shot_kernel"])
@pytest.mark.parametrize("cap, expected", [(8192, 8192), (0, None)])
def test_descent_settings_declare_the_cap(monkeypatch, creator, cap, expected):
    monkeypatch.setattr(ic, "_PHASE_MAX_TOKENS", cap)
    plugin = _descent_plugin()
    _kernel, settings = getattr(plugin, creator)()
    assert isinstance(settings, OpenAIPromptExecutionSettings)
    assert settings.max_tokens == expected
    dumped = settings.model_dump()
    assert dumped.get("max_tokens") == expected


def test_declared_site_cap_wins_on_the_real_sk_settings(monkeypatch):
    monkeypatch.setattr(ic, "_PHASE_MAX_TOKENS", 8192)
    settings = OpenAIPromptExecutionSettings(max_tokens=321)
    assert ic._with_phase_max_tokens(settings).max_tokens == 321


@pytest.mark.parametrize("cap, expected", [(8192, 8192), (0, None)])
def test_counter_call_declares_the_cap(monkeypatch, cap, expected):
    monkeypatch.setattr(ic, "_PHASE_MAX_TOKENS", cap)
    kernel = Kernel()
    service = OpenAIChatCompletion(
        service_id="synthetic", ai_model_id="synthetic", api_key="not-a-secret"
    )
    kernel.add_service(service)
    captured = []

    async def completion(_service, **kwargs):
        captured.append(kwargs)
        return [SimpleNamespace(content="A synthetic counter-argument.")]

    monkeypatch.setattr(OpenAIChatCompletion, "get_chat_message_contents", completion)
    agent = CounterArgumentAgent(kernel=kernel)
    argument = agent.parser.parse_argument(_SYNTHETIC_TEXT)
    vulnerabilities = agent.parser.identify_vulnerabilities(argument)
    content = asyncio.run(
        agent._generate_via_kernel(
            argument,
            vulnerabilities,
            CounterArgumentType.DIRECT_REFUTATION,
            RhetoricalStrategy.SOCRATIC_QUESTIONING,
        )
    )
    assert content == "A synthetic counter-argument."
    assert len(captured) == 1
    settings = captured[0]["settings"]
    assert isinstance(settings, OpenAIPromptExecutionSettings)
    assert settings.max_tokens == expected
