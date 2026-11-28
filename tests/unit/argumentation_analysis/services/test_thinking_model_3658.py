"""The endpoint's thinking vocabulary is model-specific (#3658 item 46i)."""

import pytest

from argumentation_analysis.services.llm_cache import anthropic_thinking_override


@pytest.mark.parametrize("value", ["disabled", "enabled"])
def test_haiku_accepts_measured_values(monkeypatch, value):
    monkeypatch.setenv("LLM_ANTHROPIC_THINKING", value)
    assert anthropic_thinking_override("claude-haiku-5-5") == {"type": value}


def test_haiku_rejects_sonnet_only_value(monkeypatch):
    monkeypatch.setenv("LLM_ANTHROPIC_THINKING", "between_tools")
    with pytest.raises(ValueError, match="claude-haiku-5-5"):
        anthropic_thinking_override("claude-haiku-5-5")


def test_unmeasured_model_names_probe(monkeypatch):
    monkeypatch.setenv("LLM_ANTHROPIC_THINKING", "disabled")
    with pytest.raises(ValueError, match="scripts/.*thinking"):
        anthropic_thinking_override("claude-unmeasured")


def test_budget_is_carried_and_recorded(monkeypatch):
    from argumentation_analysis.evaluation.env_manifest import environment_manifest

    monkeypatch.setenv("LLM_ANTHROPIC_THINKING", "enabled")
    monkeypatch.setenv("LLM_ANTHROPIC_THINKING_BUDGET", "1024")
    assert anthropic_thinking_override("claude-haiku-5-5") == {
        "type": "enabled", "budget_tokens": 1024
    }
    assert environment_manifest()["overrides"]["pinned_overrides"][
        "LLM_ANTHROPIC_THINKING_BUDGET"
    ] == "1024"


@pytest.mark.parametrize("budget", ["0", "-1", "invalid"])
def test_invalid_budget_is_refused(monkeypatch, budget):
    monkeypatch.setenv("LLM_ANTHROPIC_THINKING", "enabled")
    monkeypatch.setenv("LLM_ANTHROPIC_THINKING_BUDGET", budget)
    with pytest.raises(ValueError, match="LLM_ANTHROPIC_THINKING_BUDGET"):
        anthropic_thinking_override("claude-haiku-5-5")
