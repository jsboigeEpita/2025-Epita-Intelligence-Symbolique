"""Tests for the ``--mode`` wiring of ``scripts/run_real_analysis.py`` (#1668).

The runner gained ``--mode pipeline|conversational`` (#1668 item 5-bis Temps 1)
so the cluster can drive the conversational voie — the one the
``("UNDERCUT","REBUT","REBUTTAL")`` gate lives on — without confining corpus
measurement to one machine.

These tests cover the WIRING only (mode → workflow_name routing + silent-fallback
detection), not the conversational verdict itself (that needs a live corpus run,
~450-720 s + API credits — #1668 item 5-bis Temps 2). The routing is exercised
by mocking ``run_unified_analysis``; no API call is made. Anti-#1019: a mock is
legitimate here because the unit under test is *our routing code*, not the
orchestrator behaviour — the live run (Temps 2) validates the voie executes.
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import AsyncMock, patch

import pytest

from scripts.run_real_analysis import (
    MODE_TO_WORKFLOW,
    is_conversational_fallback,
)


class TestModeToWorkflowMapping:
    """The mode→workflow_name mapping is the routing contract."""

    def test_pipeline_is_the_default_and_unchanged(self) -> None:
        # Historic behaviour: pipeline → spectacular. Must not change without a
        # deliberate decision (the spectacular workflow is what FB-37 ran).
        assert MODE_TO_WORKFLOW["pipeline"] == "spectacular"

    def test_conversational_routes_through_run_conversational_analysis(self) -> None:
        # conversational → workflow_name="conversational", which run_unified_analysis
        # routes to run_conversational_analysis (unified_pipeline.py:207-217).
        assert MODE_TO_WORKFLOW["conversational"] == "conversational"

    def test_choices_match_the_mapping_keys(self) -> None:
        # The argparse choices=list(MODE_TO_WORKFLOW) — kept in sync by construction.
        assert set(MODE_TO_WORKFLOW) == {"pipeline", "conversational"}


class TestIsConversationalFallback:
    """The silent fallback detector — pure function, no I/O.

    run_unified_analysis swallows a conversational exception back to ``standard``.
    A mode-conversational run whose result carries NO conversational key is a
    pipeline verdict mislabelled — the exact #1019 defect this gate prevents
    (reading a fallback as the asked-for mode would measure the wrong voie).
    """

    def test_pipeline_mode_never_reports_fallback(self) -> None:
        # Pipeline is the fallback target — it cannot "fall back to itself".
        assert is_conversational_fallback("pipeline", {}) is False
        assert is_conversational_fallback("pipeline", {"conversation_log": []}) is False

    def test_conversational_with_conv_keys_is_genuine(self) -> None:
        # A genuine conversational result carries execution_path and/or
        # conversation_log — not a fallback.
        assert (
            is_conversational_fallback(
                "conversational", {"execution_path": "agent_group_chat"}
            )
            is False
        )
        assert (
            is_conversational_fallback("conversational", {"conversation_log": []})
            is False
        )

    def test_conversational_without_conv_keys_is_fallback(self) -> None:
        # The conversational path raised inside run_unified_analysis and was
        # swallowed back to standard — the result is a pipeline verdict.
        assert is_conversational_fallback("conversational", {"summary": {}}) is True

    def test_conversational_with_non_dict_result_is_fallback(self) -> None:
        assert is_conversational_fallback("conversational", None) is True


class TestMainAsyncRouting:
    """main_async passes the right workflow_name and warns on the silent fallback.

    ``run_unified_analysis`` and ``load_corpus`` are mocked — no API call, no
    dataset decrypt. The assertion is on the workflow_name our routing passes
    (captured by the mock), not on the orchestrator's behaviour.
    """

    @staticmethod
    def _fake_corpus() -> Dict[str, Any]:
        return {"text": "x", "raw_len": 1, "meta": {"src": "opaque"}}

    @pytest.mark.asyncio
    async def test_pipeline_mode_passes_spectacular_workflow(self) -> None:
        from scripts.run_real_analysis import main_async

        captured: Dict[str, Any] = {}

        async def fake_run(
            text: str, workflow_name: str, context: Any
        ) -> Dict[str, Any]:
            captured["workflow_name"] = workflow_name
            return {"unified_state": None, "summary": {}}

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new=AsyncMock(side_effect=fake_run),
        ), patch(
            "scripts.run_real_analysis.load_corpus",
            return_value=self._fake_corpus(),
        ), patch(
            "scripts.run_real_analysis.RESULTS_DIR"
        ), patch(
            "builtins.open", new=mock_open_noop()
        ):
            await main_async("A", mode="pipeline")

        assert captured["workflow_name"] == "spectacular"

    @pytest.mark.asyncio
    async def test_conversational_mode_passes_conversational_workflow(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from scripts.run_real_analysis import main_async

        captured: Dict[str, Any] = {}

        async def fake_run(
            text: str, workflow_name: str, context: Any
        ) -> Dict[str, Any]:
            captured["workflow_name"] = workflow_name
            # A genuine conversational result carries execution_path.
            return {"unified_state": None, "execution_path": "agent_group_chat"}

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new=AsyncMock(side_effect=fake_run),
        ), patch(
            "scripts.run_real_analysis.load_corpus",
            return_value=self._fake_corpus(),
        ), patch(
            "scripts.run_real_analysis.RESULTS_DIR"
        ), patch(
            "builtins.open", new=mock_open_noop()
        ):
            await main_async("A", mode="conversational")

        assert captured["workflow_name"] == "conversational"
        out = capsys.readouterr().out
        # Genuine conversational ⇒ no fallback WARNING printed.
        assert "WARNING" not in out

    @pytest.mark.asyncio
    async def test_conversational_fallback_prints_warning(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The silent fallback is detected and printed — fail-loud, anti-#1019.

        run_unified_analysis swallowed the conversational exception and returned
        a pipeline result (no conversation_log / execution_path). The runner
        must say so, not hand back a pipeline verdict labelled conversational.
        """
        from scripts.run_real_analysis import main_async

        async def fake_run(
            text: str, workflow_name: str, context: Any
        ) -> Dict[str, Any]:
            # Note: workflow_name IS "conversational" (we routed correctly), but
            # the RESULT is a pipeline fallback (no conv keys) — the swallow.
            return {"unified_state": None, "summary": {"completed_phases": ["extract"]}}

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new=AsyncMock(side_effect=fake_run),
        ), patch(
            "scripts.run_real_analysis.load_corpus",
            return_value=self._fake_corpus(),
        ), patch(
            "scripts.run_real_analysis.RESULTS_DIR"
        ), patch(
            "builtins.open", new=mock_open_noop()
        ):
            await main_async("A", mode="conversational")

        out = capsys.readouterr().out
        assert "WARNING" in out
        assert "fell back to the pipeline" in out


def mock_open_noop() -> Any:
    """A context-manager mock for ``open`` that discards writes (the runner
    dumps JSON + Markdown to a gitignored path; the test does not assert on
    file content, only on routing + the printed fallback warning)."""
    from unittest.mock import MagicMock

    m = MagicMock()
    m.return_value.__enter__.return_value = MagicMock()
    m.return_value.__exit__.return_value = False
    return m
