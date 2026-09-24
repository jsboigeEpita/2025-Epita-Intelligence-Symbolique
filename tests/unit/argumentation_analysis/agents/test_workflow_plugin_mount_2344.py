"""#2344 — a workflow config that cannot mount its workflow plugin fails to build.

``InformalFallacyAgent`` imports ``FallacyWorkflowPlugin`` dynamically for the
``workflow_only`` and ``full`` configs. A ``ModuleNotFoundError`` or
``AttributeError`` there was logged and dropped: the agent was built without
the plugin its config names, the one the web API asks for with ``"full"``.
The plugin module is ours and imports nothing optional, so a failure there is
a defect of the tree, and building the agent now raises it.
"""

import importlib
from unittest.mock import MagicMock, patch

import pytest
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.connectors.ai.prompt_execution_settings import (
    PromptExecutionSettings,
)
from semantic_kernel.kernel import Kernel

from argumentation_analysis.agents.concrete_agents.informal_fallacy_agent import (
    InformalFallacyAgent,
)

PLUGIN_MODULE = "argumentation_analysis.plugins.fallacy_workflow_plugin"


@pytest.fixture
def kernel():
    kernel = Kernel()
    service = MagicMock(spec=ChatCompletionClientBase)
    service.get_prompt_execution_settings_class.return_value = PromptExecutionSettings
    service.service_id = "test_service"
    kernel.add_service(service)
    return kernel


def _import_failing_for_the_plugin(error):
    real_import = importlib.import_module

    def fake(name, *args, **kwargs):
        if name == PLUGIN_MODULE:
            raise error
        return real_import(name, *args, **kwargs)

    return patch.object(importlib, "import_module", side_effect=fake)


def _build(kernel, config_name):
    return InformalFallacyAgent(
        kernel=kernel, config_name=config_name, llm_service_id="test_service"
    )


@pytest.mark.parametrize("config_name", ["workflow_only", "full"])
def test_missing_plugin_module_stops_the_build(kernel, config_name):
    error = ModuleNotFoundError(f"No module named {PLUGIN_MODULE!r}")
    with _import_failing_for_the_plugin(error):
        with pytest.raises(ModuleNotFoundError, match="fallacy_workflow_plugin"):
            _build(kernel, config_name)


def test_plugin_module_without_the_class_stops_the_build(kernel):
    empty_module = MagicMock(spec=[])
    real_import = importlib.import_module

    def fake(name, *args, **kwargs):
        if name == PLUGIN_MODULE:
            return empty_module
        return real_import(name, *args, **kwargs)

    with patch.object(importlib, "import_module", side_effect=fake):
        with pytest.raises(AttributeError, match="FallacyWorkflowPlugin"):
            _build(kernel, "workflow_only")


def test_the_real_plugin_mounts(kernel):
    """Control: with the real module, the config mounts what it names."""
    agent = _build(kernel, "workflow_only")
    assert "FallacyWorkflowPlugin" in agent.get_agent_capabilities()["plugins"]
