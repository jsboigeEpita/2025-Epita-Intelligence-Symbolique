"""#2631: the pedagogical analysis demo uses the agent API it advertises."""

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

DEMO_DIR = (
    Path(__file__).resolve().parents[3]
    / "examples"
    / "02_core_system_demos"
    / "scripts_demonstration"
)


@pytest.fixture
def demo(monkeypatch):
    monkeypatch.syspath_prepend(str(DEMO_DIR))
    spec = importlib.util.spec_from_file_location(
        "demo_analyse_argumentation_2631",
        DEMO_DIR / "modules" / "demo_analyse_argumentation.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("choice,config", [("informal", "simple"), ("full", "full")])
async def test_demo_builds_requested_agent_and_analyzes(
    demo, monkeypatch, tmp_path, choice, config, capsys
):
    taxonomy = tmp_path / "taxonomy.json"
    taxonomy.write_text("{}", encoding="utf-8")
    agent = Mock()
    agent.analyze_text = AsyncMock(return_value="analysis-result")
    factory = Mock()
    factory.create_informal_fallacy_agent.return_value = agent
    monkeypatch.setattr(
        demo, "_create_kernel_and_factory", lambda: (Mock(), factory, "service")
    )

    assert (
        await demo._run_analysis(Mock(), choice, str(taxonomy), "A sample argument")
        is True
    )
    factory.create_informal_fallacy_agent.assert_called_once_with(
        config_name=config, taxonomy_file_path=str(taxonomy)
    )
    agent.analyze_text.assert_awaited_once_with("A sample argument")
    assert "analysis-result" in capsys.readouterr().out


def test_quick_demo_uses_vendored_taxonomy_and_real_agent(demo, monkeypatch, capsys):
    from semantic_kernel import Kernel
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
    from argumentation_analysis.agents.factory import AgentFactory
    from argumentation_analysis.utils.taxonomy_loader import get_taxonomy_path

    service = OpenAIChatCompletion(
        service_id="openai", ai_model_id="demo-model", api_key="unused-demo-key"
    )
    monkeypatch.setattr(demo, "create_llm_service", lambda **kwargs: service)
    prompt = AsyncMock(return_value="demo-analysis-result")
    monkeypatch.setattr(Kernel, "invoke_prompt", prompt)

    create_agent = AgentFactory.create_informal_fallacy_agent
    taxonomy_files = []

    def record_taxonomy(self, *args, **kwargs):
        taxonomy_files.append(kwargs["taxonomy_file_path"])
        return create_agent(self, *args, **kwargs)

    monkeypatch.setattr(AgentFactory, "create_informal_fallacy_agent", record_taxonomy)
    assert demo.run_demo_rapide("full", None) is True

    assert len(taxonomy_files) == 1
    taxonomy_file = taxonomy_files[0]
    assert taxonomy_file == str(get_taxonomy_path())
    assert Path(taxonomy_file).is_file()
    assert "demo-analysis-result" in capsys.readouterr().out
    prompt.assert_awaited_once()


async def test_unknown_demo_agent_type_fails_before_constructing(demo, monkeypatch):
    monkeypatch.setattr(
        demo,
        "_create_kernel_and_factory",
        lambda: pytest.fail("built a service for an invalid type"),
    )
    with pytest.raises(ValueError, match="unknown"):
        await demo._run_analysis(Mock(), "unknown", None, "A sample argument")
