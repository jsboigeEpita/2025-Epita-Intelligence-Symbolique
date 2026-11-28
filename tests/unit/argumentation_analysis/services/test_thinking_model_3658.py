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
