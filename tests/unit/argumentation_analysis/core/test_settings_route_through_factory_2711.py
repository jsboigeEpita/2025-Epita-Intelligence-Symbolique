# -*- coding: utf-8 -*-
"""Kernel-path sites that read ``settings.openai`` took the OpenAI route (#2711).

``create_llm_service`` is the one kernel-path factory: it honours the OpenRouter
toggle (``OPENROUTER_BASE_URL`` + ``OPENROUTER_API_KEY``) and substitutes
obsolete model ids (#1930). The analysis pipeline and the Cluedo entry point
built their own ``OpenAIChatCompletion`` from ``settings.openai`` instead, so
on a seat routed through OpenRouter they called ``api.openai.com`` with the
OpenAI key, and without an OpenAI key they refused to run at all.

The seat below routes through OpenRouter. Each site must hand its kernel a
service whose client points at that base URL, whether or not an OpenAI key is
also configured. No request leaves the process: the agent and the game are
replaced by captures.

On a seat with no key at all, ``settings.openai.api_key`` is not ``None``: the
field defaults to ``"sk-dummy-key-for-testing"``, so a presence test on it
passes and the site builds a service that sends the dummy key. The factory
refuses that seat instead.
"""

from unittest.mock import patch

import pytest
from pydantic import SecretStr

OPENROUTER_URL = "https://openrouter.example.test/api/v1"


@pytest.fixture
def openrouter_seat(monkeypatch):
    monkeypatch.setenv("OPENROUTER_BASE_URL", OPENROUTER_URL)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-2711")
    monkeypatch.setenv("OPENROUTER_CHAT_MODEL_ID", "openai/gpt-5.6-luna")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)


@pytest.fixture
def keyless_seat(monkeypatch):
    for name in (
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "OPENROUTER_BASE_URL",
        "OPENAI_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)


def _keyless_settings_key():
    """What ``settings.openai.api_key`` holds on a seat with no key and no .env."""
    from argumentation_analysis.config.settings import OpenAISettings

    return OpenAISettings(_env_file=None).api_key


def _base_url(service) -> str:
    return str(service.client.base_url)


@pytest.mark.parametrize(
    "settings_key", [None, "sk-openai-2711"], ids=["no-openai-key", "openai-key-too"]
)
async def test_the_analysis_pipeline_takes_the_openrouter_route(
    openrouter_seat, settings_key
):
    from argumentation_analysis.agents.core.informal import informal_agent
    from argumentation_analysis.config.settings import settings
    from argumentation_analysis.utils.analysis_config import (
        AnalysisConfig,
        AnalysisMode,
        UnifiedAnalysisPipeline,
    )

    seen = {}

    class _CapturingAgent:
        def __init__(self, kernel, agent_name):
            seen["kernel"] = kernel

        def setup_agent_components(self, llm_service_id):
            seen["service_id"] = llm_service_id

        async def analyze_text(self, text):
            return {"fallacies": []}

    key = SecretStr(settings_key) if settings_key else None
    pipeline = UnifiedAnalysisPipeline(AnalysisConfig(require_real_llm=True))
    with patch.object(
        informal_agent, "InformalAnalysisAgent", _CapturingAgent
    ), patch.object(settings.openai, "api_key", key):
        result = await pipeline._real_llm_analysis(
            "Un texte fabriqué pour le témoin.", AnalysisMode.FALLACIES
        )

    assert result["authentic"] is True
    service = seen["kernel"].get_service(seen["service_id"])
    assert _base_url(service).startswith(OPENROUTER_URL), _base_url(service)


@pytest.mark.parametrize(
    "settings_key", [None, "sk-openai-2711"], ids=["no-openai-key", "openai-key-too"]
)
async def test_the_cluedo_entry_point_takes_the_openrouter_route(
    openrouter_seat, settings_key
):
    from argumentation_analysis.config.settings import settings
    from argumentation_analysis.orchestration import (
        cluedo_extended_orchestrator as entry,
    )

    seen = {}

    async def _capturing_game(kernel, **kwargs):
        seen["kernel"] = kernel
        raise RuntimeError("#2711 witness: the game is not played")

    key = SecretStr(settings_key) if settings_key else None
    with patch.object(entry, "run_cluedo_oracle_game", _capturing_game), patch.object(
        settings, "use_mock_llm", False
    ), patch.object(settings.openai, "api_key", key):
        await entry.main()

    services = list(seen["kernel"].services.values())
    assert len(services) == 1, services
    assert _base_url(services[0]).startswith(OPENROUTER_URL), _base_url(services[0])


async def test_a_keyless_seat_is_refused_by_the_analysis_pipeline(keyless_seat):
    from argumentation_analysis.agents.core.informal import informal_agent
    from argumentation_analysis.config.settings import settings
    from argumentation_analysis.utils.analysis_config import (
        AnalysisConfig,
        AnalysisMode,
        AuthenticAnalysisUnavailable,
        UnifiedAnalysisPipeline,
    )

    class _NeverBuilt:
        def __init__(self, *args, **kwargs):
            raise AssertionError("an agent was built on a seat with no key")

    key = _keyless_settings_key()
    assert key is not None  # the premise: the dummy default, not None
    pipeline = UnifiedAnalysisPipeline(AnalysisConfig(require_real_llm=True))
    with patch.object(
        informal_agent, "InformalAnalysisAgent", _NeverBuilt
    ), patch.object(settings.openai, "api_key", key):
        with pytest.raises(AuthenticAnalysisUnavailable, match="OPENAI_API_KEY"):
            await pipeline._real_llm_analysis(
                "Un texte fabriqué pour le témoin.", AnalysisMode.FALLACIES
            )


async def test_a_keyless_seat_is_refused_by_the_cluedo_entry_point(keyless_seat):
    from argumentation_analysis.config.settings import settings
    from argumentation_analysis.orchestration import (
        cluedo_extended_orchestrator as entry,
    )

    async def _never_played(kernel, **kwargs):
        raise AssertionError("the game started on a seat with no key")

    with patch.object(entry, "run_cluedo_oracle_game", _never_played), patch.object(
        settings, "use_mock_llm", False
    ), patch.object(settings.openai, "api_key", _keyless_settings_key()):
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            await entry.main()


def test_the_cluedo_runner_carries_no_standalone_entry():
    """``cluedo_runner.main`` built an empty kernel, then called the runner's
    own ``run_cluedo_oracle_game`` without its required ``settings``: it could
    only print that no service was configured, or raise ``TypeError``."""
    from argumentation_analysis.orchestration import cluedo_runner

    assert not hasattr(cluedo_runner, "main")
