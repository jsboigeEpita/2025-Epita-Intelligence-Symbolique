"""Tests for #568: FallacyWorkflowPlugin instrumentation + InformalAgent instruction update."""

import inspect
import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argumentation_analysis.orchestration.conversational_orchestrator import (
    AGENT_CONFIG,
)


class TestInformalAgentInstructions:
    """Verify InformalAgent instructions prioritize run_guided_analysis."""

    def test_instructions_mention_run_guided_first(self):
        """run_guided_analysis should be mentioned as OBLIGATOIRE."""
        instructions = AGENT_CONFIG["InformalAgent"]["instructions"]
        assert "run_guided_analysis" in instructions
        assert "OBLIGATOIRE" in instructions

    def test_instructions_prioritize_guided_over_heuristic(self):
        """run_guided_analysis should be prioritized over detect_fallacies."""
        instructions = AGENT_CONFIG["InformalAgent"]["instructions"]
        guided_pos = instructions.find("run_guided_analysis")
        detect_pos = instructions.find("detect_fallacies")
        assert (
            guided_pos < detect_pos
        ), "run_guided_analysis should appear before detect_fallacies in instructions"

    def test_instructions_mention_per_argument(self):
        """Instructions must say to run on EACH argument."""
        instructions = AGENT_CONFIG["InformalAgent"]["instructions"]
        assert "CHAQUE" in instructions or "TOUT" in instructions


class TestFallacyWorkflowTrace:
    """Verify _persist_trace method exists and produces correct output."""

    def test_persist_trace_method_exists(self):
        """FallacyWorkflowPlugin should have _persist_trace method."""
        from argumentation_analysis.plugins.fallacy_workflow_plugin import (
            FallacyWorkflowPlugin,
        )

        assert hasattr(FallacyWorkflowPlugin, "_persist_trace")

    def test_persist_trace_skips_without_path(self):
        """_persist_trace should be a no-op when trace_log_path is None."""
        from argumentation_analysis.plugins.fallacy_workflow_plugin import (
            FallacyWorkflowPlugin,
        )

        plugin = MagicMock(spec=FallacyWorkflowPlugin)
        # Call the real method on a mock — should not raise
        FallacyWorkflowPlugin._persist_trace(plugin, None, MagicMock(), "test")
        # No file written (no side effects)

    def test_run_guided_analysis_has_trace_log_path_param(self):
        """run_guided_analysis should accept trace_log_path parameter."""
        from argumentation_analysis.plugins.fallacy_workflow_plugin import (
            FallacyWorkflowPlugin,
        )

        sig = inspect.signature(FallacyWorkflowPlugin.run_guided_analysis)
        assert "trace_log_path" in sig.parameters

    def test_persist_trace_writes_json(self, tmp_path):
        """_persist_trace should write a valid JSON file with traversal paths."""
        from argumentation_analysis.plugins.fallacy_workflow_plugin import (
            FallacyWorkflowPlugin,
        )
        from argumentation_analysis.plugins.identification_models import (
            IdentifiedFallacy,
            FallacyAnalysisResult,
        )

        # Create minimal plugin mock
        mock_navigator = MagicMock()
        mock_navigator.get_node.return_value = {
            "PK": "adhominem_abusive",
            "path": "Sophismes > Attaque > Ad hominem > Abusif",
        }

        result = FallacyAnalysisResult(
            fallacies=[
                IdentifiedFallacy(
                    fallacy_type="Ad hominem abusif",
                    taxonomy_pk="adhominem_abusive",
                    taxonomy_path="Sophismes > Attaque > Ad hominem > Abusif",
                    explanation="Personal attack instead of argument",
                    confidence=0.9,
                    navigation_trace=[
                        "root",
                        "attaque",
                        "adhominem",
                        "adhominem_abusive",
                    ],
                )
            ],
            exploration_method="iterative_deepening",
            branches_explored=2,
            total_iterations=4,
        )

        trace_file = tmp_path / "trace.json"
        plugin = MagicMock(spec=FallacyWorkflowPlugin)
        plugin.taxonomy_navigator = mock_navigator
        plugin.logger = MagicMock()

        FallacyWorkflowPlugin._persist_trace(
            plugin, str(trace_file), result, "Some argument text here"
        )

        assert trace_file.exists()
        data = json.loads(trace_file.read_text(encoding="utf-8"))
        assert data["exploration_method"] == "iterative_deepening"
        assert len(data["traversal_paths"]) == 1
        entry = data["traversal_paths"][0]
        assert entry["taxonomy_node_id"] == "adhominem_abusive"
        assert entry["parent_chain"] == ["Sophismes", "Attaque", "Ad hominem", "Abusif"]
        assert entry["navigation_trace"] == [
            "root",
            "attaque",
            "adhominem",
            "adhominem_abusive",
        ]
        assert entry["decision_rationale"] == "Personal attack instead of argument"
        assert entry["confidence"] == 0.9


class TestTraceLogPathRobustness1722:
    """#1722: run_guided_analysis must not crash on a trace_log_path whose
    parent directory is missing or non-creatable — the silent loss of the
    hierarchical taxonomy descent on Windows conversational runs (#1019 family)."""

    @staticmethod
    def _make_plugin():
        """A bare FallacyWorkflowPlugin instance with only the attributes
        ``_attach_trace_handler`` touches (logger). No kernel/navigator needed:
        the method is pure filesystem + logging."""
        from argumentation_analysis.plugins.fallacy_workflow_plugin import (
            FallacyWorkflowPlugin,
        )

        plugin = FallacyWorkflowPlugin.__new__(FallacyWorkflowPlugin)
        plugin.logger = logging.getLogger("test_1722_fallacy_trace")
        return plugin

    def test_creates_missing_parent_dir_then_attaches_handler(self, tmp_path):
        """The original bug: a path whose parent does not exist raised
        FileNotFoundError before the fix (the LLM-improvised POSIX path on a
        Windows host). The parent is now created and a real handler is attached."""
        plugin = self._make_plugin()
        plugin.logger.handlers = []  # isolate from any inherited handlers
        trace_path = tmp_path / "does_not_exist_yet" / "nested" / "trace.log"
        assert not trace_path.parent.exists()

        handler = plugin._attach_trace_handler(str(trace_path))

        try:
            assert handler is not None
            # Parent was created and the trace file is openable (write mode)
            assert trace_path.parent.exists()
            assert trace_path.exists()
            # The handler was attached to the plugin logger
            assert handler in plugin.logger.handlers
        finally:
            plugin.logger.removeHandler(handler)
            handler.close()

    def test_returns_none_for_empty_or_null_path(self):
        """Empty / None / literal-null paths are a no-op (guard preserved)."""
        plugin = self._make_plugin()
        for empty in (None, "", "   ", "None", "null"):
            assert plugin._attach_trace_handler(empty) is None  # type: ignore[arg-type]

    def test_falls_back_to_none_with_warning_when_parent_uncreatable(
        self, tmp_path, caplog
    ):
        """When the parent genuinely cannot be created (a file sits where a
        directory is expected), the trace file is optional: fall back to no
        handler + WARNING, never propagate. This is the #1019 guard — a
        non-creatable debug path must not degrade the analysis."""
        plugin = self._make_plugin()
        plugin.logger.handlers = []
        plugin.logger.propagate = True
        blocker = tmp_path / "blocker_file"
        blocker.write_text("x")
        # blocker is a FILE, so mkdir(blocker / "sub") raises NotADirectoryError
        bad_path = str(blocker / "sub" / "trace.log")

        with caplog.at_level(logging.WARNING, logger="test_1722_fallacy_trace"):
            handler = plugin._attach_trace_handler(bad_path)

        try:
            assert handler is None
            assert not Path(bad_path).exists()
            # No handler was attached
            assert plugin.logger.handlers == []
            # A WARNING named the unusable path so the degradation is visible
            assert any(
                "trace_log_path" in rec.getMessage() and "unusable" in rec.getMessage()
                for rec in caplog.records
            ), [rec.getMessage() for rec in caplog.records]
        finally:
            plugin.logger.propagate = False
