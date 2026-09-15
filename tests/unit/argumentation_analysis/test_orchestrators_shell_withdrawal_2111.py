"""#2111 (dispatch R1007 D3): the specialized/ wrapper shell is withdrawn and
an unknown conversation mode must warn loudly.

Born-red triple: before the change the shell package exists, the wrappers are
re-exported, and an unknown mode falls back to simulated agents with an info
log only — exactly the silent fallback #2205 forbids. All three flip with the
grain; the fourth test is the known-mode control (stays green throughout).
"""

import importlib.util

import pytest


def test_orchestrators_shell_is_gone():
    assert (
        importlib.util.find_spec(
            "argumentation_analysis.pipelines.orchestration.orchestrators"
        )
        is None
    )


def test_pipelines_orchestration_no_longer_exports_the_wrappers():
    import argumentation_analysis.pipelines.orchestration as po

    assert not hasattr(po, "CluedoOrchestratorWrapper")
    assert not hasattr(po, "ConversationOrchestratorWrapper")
    for name in ("CluedoOrchestratorWrapper", "ConversationOrchestratorWrapper"):
        assert name not in po.__all__


def test_unknown_mode_warns_loudly(caplog):
    """#2111 / #2205: an unrecognized mode must not fall back silently."""
    import logging

    from argumentation_analysis.orchestration.conversation_orchestrator import (
        ConversationOrchestrator,
    )

    with caplog.at_level(
        logging.WARNING,
        logger="argumentation_analysis.orchestration.conversation_orchestrator.ConversationOrchestrator",
    ):
        orch = ConversationOrchestrator(mode="advanced")
    assert "advanced" in caplog.text and "Unknown" in caplog.text, (
        "an unknown mode silently fell back to simulated agents — #2205 "
        f"forbids silent fallbacks; log was: {caplog.text!r}"
    )
    assert orch.agents, "fallback still configures agents"


def test_known_modes_do_not_warn(caplog):
    """Control: the documented simulated modes stay warning-free."""
    import logging

    from argumentation_analysis.orchestration.conversation_orchestrator import (
        ConversationOrchestrator,
    )

    with caplog.at_level(
        logging.WARNING,
        logger="argumentation_analysis.orchestration.conversation_orchestrator.ConversationOrchestrator",
    ):
        for mode in ("demo", "trace", "enhanced"):
            ConversationOrchestrator(mode=mode)
    assert "Unknown" not in caplog.text
