"""The harness renders the bridge's verdict, it does not generate acts twice (#3471)."""

import importlib

import pytest

mod = importlib.import_module("scripts.compare_orchestration_modes")


class _State:
    act1_framing = "acte I déjà écrit par la phase du pont"
    act2_narrative = "acte II"
    act3_conclusion = "acte III"


def test_panel_renders_the_acts_the_bridge_planned(monkeypatch):
    """Render-only: the generate-and-render entry point must not be reached.

    Calling it would run every act a second time (three paid LLM calls) on an
    engine whose plan already produced them.
    """
    from argumentation_analysis.reporting.restitution import conversational_adapter

    def _no_double_generation(*args, **kwargs):
        raise AssertionError(
            "the acts were generated again after the bridge planned them"
        )

    monkeypatch.setattr(
        conversational_adapter,
        "generate_and_render_for_conversational_state",
        _no_double_generation,
    )
    from argumentation_analysis.reporting.restitution import pipeline_adapter

    calls = []

    def _render(state, *args, **kwargs):
        calls.append(state)
        return "rapport rendu"

    monkeypatch.setattr(pipeline_adapter, "render_spectacular_restitution", _render)

    state = _State()
    result = {}
    mod.attach_bridge_restitution(result, state, panel_mode=True)

    assert calls == [state]
    assert result["restitution_report"] == "rapport rendu"


def test_render_failure_is_named_not_raised(monkeypatch):
    from argumentation_analysis.reporting.restitution import pipeline_adapter

    def _boom(*args, **kwargs):
        raise RuntimeError("renderer exploded")

    monkeypatch.setattr(pipeline_adapter, "render_spectacular_restitution", _boom)

    result = {}
    mod.attach_bridge_restitution(result, _State(), panel_mode=True)
    assert result["restitution_report"] is None


@pytest.mark.parametrize("panel_mode, state", [(False, _State()), (True, None)])
def test_nothing_happens_outside_the_panel(monkeypatch, panel_mode, state):
    from argumentation_analysis.reporting.restitution import (
        conversational_adapter,
        pipeline_adapter,
    )

    def _boom(*args, **kwargs):
        raise AssertionError("restitution work ran where it should not")

    monkeypatch.setattr(pipeline_adapter, "render_spectacular_restitution", _boom)
    monkeypatch.setattr(
        conversational_adapter,
        "generate_and_render_for_conversational_state",
        _boom,
    )

    result = {}
    mod.attach_bridge_restitution(result, state, panel_mode=panel_mode)
    assert result == {}
