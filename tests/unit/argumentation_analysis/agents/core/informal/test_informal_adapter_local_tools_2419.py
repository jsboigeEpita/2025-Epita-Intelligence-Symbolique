# -*- coding: utf-8 -*-
"""The informal adapter analyses with its local tools only (#2419).

The adapter used to build an ``InformalAnalysisAgent`` in a ``try`` and file the
failure as "mode dégradé". The construction could not succeed: the SK agent
requires a ``kernel`` and takes no ``tools``. Had it succeeded, the delegation
would have returned a coroutine, since the SK agent's ``analyze_text`` is async.
These tests pin the repaired contract: no construction is attempted, nothing is
logged as a degradation, and ``analyze_text`` returns the local tools' dict even
when the SK agent is constructible.
"""

import ast
import logging
from pathlib import Path
from unittest.mock import MagicMock

import argumentation_analysis.agents.core.informal.informal_agent_adapter as adapter_module
from argumentation_analysis.agents.core.informal.informal_agent import (
    InformalAnalysisAgent,
)
from argumentation_analysis.agents.core.informal.informal_agent_adapter import (
    InformalAgent,
)


class _Collect(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append(record)


def test_construction_does_not_build_the_sk_agent(monkeypatch):
    calls = []

    def spy(self, *args, **kwargs):
        calls.append((args, kwargs))
        raise TypeError("spy: construction attempted")

    monkeypatch.setattr(InformalAnalysisAgent, "__init__", spy)
    InformalAgent(tools={"fallacy_detector": MagicMock()})
    assert calls == []


def test_construction_logs_no_degradation():
    agent_id = "Adapter2419"
    logger = logging.getLogger(f"{adapter_module.__name__}.{agent_id}")
    handler = _Collect()
    logger.addHandler(handler)
    previous_level = logger.level
    logger.setLevel(logging.DEBUG)
    try:
        agent = InformalAgent(
            agent_id=agent_id, tools={"fallacy_detector": MagicMock()}
        )
        at_construction = [r for r in handler.records if r.levelno >= logging.WARNING]
        # Positive control: the handler sees a warning from this logger.
        agent.logger.warning("control-2419")
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
    assert [r.getMessage() for r in handler.records][-1] == "control-2419"
    assert at_construction == []


def test_analyze_text_returns_local_result_even_if_sk_agent_is_constructible(
    monkeypatch,
):
    # A constructible SK agent must not change the adapter's answer: the old
    # delegation would have returned the coroutine of the async analyze_text.
    monkeypatch.setattr(InformalAnalysisAgent, "__init__", lambda self, *a, **k: None)
    fallacy = {"fallacy_type": "Ad Hominem", "confidence": 0.9}
    detector = MagicMock()
    detector.detect = MagicMock(return_value=[fallacy])
    agent = InformalAgent(tools={"fallacy_detector": detector})

    result = agent.analyze_text("some text")

    assert isinstance(result, dict)
    assert result["fallacies"] == [fallacy]
    detector.detect.assert_called_once_with("some text")


def test_adapter_module_does_not_reference_the_sk_agent():
    source = Path(adapter_module.__file__).read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    imported = {
        alias.asname or alias.name
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom)
        for alias in n.names
    }
    assert "InformalAnalysisAgent" not in names | imported
    assert "categorize_fallacy_types" in imported  # control: the census sees imports
