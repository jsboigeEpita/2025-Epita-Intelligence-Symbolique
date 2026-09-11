# Fichier: tests/agents/concrete_agents/test_informal_fallacy_agent.py

import pytest
from unittest.mock import MagicMock

from semantic_kernel.kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.connectors.ai.prompt_execution_settings import (
    PromptExecutionSettings,
)

from argumentation_analysis.agents.concrete_agents.informal_fallacy_agent import (
    INFORMAL_AGENT_CONFIGS,
)
from argumentation_analysis.agents.factory import AgentFactory, AgentType
from argumentation_analysis.config.settings import AppSettings


@pytest.fixture
def kernel():
    """A real kernel with a mocked chat service — enough for the plugin gates."""
    kernel = Kernel()
    mock_service = MagicMock(spec=ChatCompletionClientBase)
    mock_service.get_prompt_execution_settings_class.return_value = (
        PromptExecutionSettings
    )
    mock_service.service_id = "test_service"
    kernel.add_service(mock_service)
    return kernel


def test_unknown_config_name_raises_instead_of_mounting_no_plugins(kernel):
    """#2121 — an invented config name must not silently yield a plugin-less agent.

    Before the fix, ``config_name`` was matched against three independent
    ``in`` gates and an unmatched value fell through all of them: the agent
    mounted zero plugins and nothing raised. The caller could not tell that
    agent apart from a correctly configured one — the web API logged
    "created and configured successfully" while serving an agent with no
    detection, taxonomy or workflow capability.

    ``"default_with_plugins"`` is the value the web API actually passed.
    """
    factory = AgentFactory(kernel, AppSettings())

    with pytest.raises(ValueError, match="default_with_plugins"):
        factory.create_agent(
            AgentType.INFORMAL_FALLACY, config_name="default_with_plugins"
        )


def test_every_advertised_config_mounts_at_least_one_plugin(kernel):
    """No accepted config may yield an empty plugin set (#2121).

    ``test_agent_factory_configurations`` in
    ``tests/integration/triage/test_fallacy_agent_workflow.py`` pins the exact
    plugin set per config; this asserts the weaker property the web API
    depended on, so it stays meaningful if those sets are revisited.
    """
    factory = AgentFactory(kernel, AppSettings())
    for config_name in INFORMAL_AGENT_CONFIGS:
        agent = factory.create_agent(
            AgentType.INFORMAL_FALLACY, config_name=config_name
        )
        assert agent.get_agent_capabilities()[
            "plugins"
        ], f"config {config_name!r} is advertised but mounts no plugin"
