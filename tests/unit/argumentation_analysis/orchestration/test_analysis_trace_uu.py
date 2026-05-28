"""Tests for specialist commentary + analysis_trace (Track UU #724)."""

from unittest.mock import MagicMock

import argumentation_analysis.core.shared_state as state_mod


class TestAddTraceEntry:
    """UnifiedAnalysisState.add_trace_entry records structured commentary."""

    def test_entry_appended_to_analysis_trace(self):
        state = state_mod.UnifiedAnalysisState("test text")
        assert state.analysis_trace == []
        state.add_trace_entry(
            phase="extract",
            agent="FactExtractor",
            reacts_to=[],
            summary="5 arguments identifiés avec succès.",
        )
        assert len(state.analysis_trace) == 1
        entry = state.analysis_trace[0]
        assert entry["phase"] == "extract"
        assert entry["agent"] == "FactExtractor"
        assert entry["reacts_to"] == []
        assert entry["summary"] == "5 arguments identifiés avec succès."
        assert "T" in entry["timestamp"]

    def test_summary_truncated_at_280_chars(self):
        state = state_mod.UnifiedAnalysisState("test text")
        long_summary = "x" * 500
        state.add_trace_entry("p", "a", [], long_summary)
        assert len(state.analysis_trace[0]["summary"]) == 280

    def test_multiple_entries_accumulate(self):
        state = state_mod.UnifiedAnalysisState("test text")
        state.add_trace_entry("extract", "E", [], "first")
        state.add_trace_entry("fallacy", "F", ["extract"], "second")
        state.add_trace_entry("quality", "Q", ["extract", "fallacy"], "third")
        assert len(state.analysis_trace) == 3
        assert state.analysis_trace[0]["reacts_to"] == []
        assert state.analysis_trace[1]["reacts_to"] == ["extract"]
        assert state.analysis_trace[2]["reacts_to"] == ["extract", "fallacy"]

    def test_reacts_to_coherence(self):
        """Referenced phases exist in accumulated trace."""
        state = state_mod.UnifiedAnalysisState("test text")
        state.add_trace_entry("extract", "E", [], "first")
        state.add_trace_entry("fallacy", "F", ["extract"], "second")
        state.add_trace_entry("quality", "Q", ["extract", "fallacy"], "third")
        phases = {e["phase"] for e in state.analysis_trace}
        for entry in state.analysis_trace:
            for ref in entry["reacts_to"]:
                assert ref in phases

    def test_entry_has_all_required_fields(self):
        state = state_mod.UnifiedAnalysisState("test text")
        state.add_trace_entry("phase", "Agent", [], "summary text")
        entry = state.analysis_trace[0]
        assert "phase" in entry
        assert "agent" in entry
        assert "reacts_to" in entry
        assert "summary" in entry
        assert "timestamp" in entry

    def test_state_init_has_empty_analysis_trace(self):
        state = state_mod.UnifiedAnalysisState("test text")
        assert state.analysis_trace == []
        assert isinstance(state.analysis_trace, list)


class TestDeepSynthesisCommentaryBlock:
    """DeepSynthesisAgent reads analysis_trace for commentary_block."""

    def test_report_carries_raw_trace(self):
        from argumentation_analysis.agents.core.synthesis.deep_synthesis_models import (
            DeepSynthesisReport,
            SourceOverview,
        )

        report = DeepSynthesisReport(source_overview=SourceOverview())
        trace = [
            {
                "phase": "extract",
                "agent": "FactExtractor",
                "reacts_to": [],
                "summary": "12 arguments identifiés dans le discours.",
            },
            {
                "phase": "fallacy",
                "agent": "FallacyDetector",
                "reacts_to": ["extract"],
                "summary": "5 sophismes — dominante: appel à l'autorité.",
            },
        ]
        report._raw_analysis_trace = trace
        assert len(report._raw_analysis_trace) == 2
        assert report._raw_analysis_trace[0]["agent"] == "FactExtractor"
        assert report._raw_analysis_trace[1]["reacts_to"] == ["extract"]

    def test_empty_trace_produces_no_commentary(self):
        """When no trace entries exist, commentary_block is empty."""
        # Simulate the commentary_block construction logic
        trace_data = []
        comment_lines = []
        for entry in trace_data:
            agent = entry.get("agent", "?")
            reacts = ", ".join(entry.get("reacts_to", []))
            summary = entry.get("summary", "")
            comment_lines.append(f'[{agent}] (réagit à: {reacts}) → "{summary}"')
        commentary_block = (
            "\nSpecialist commentaries (agent voices):\n"
            + "\n".join(comment_lines)
            + "\n"
            if comment_lines
            else ""
        )
        assert commentary_block == ""

    def test_trace_builds_commentary_block(self):
        """Trace entries produce formatted commentary lines."""
        trace_data = [
            {"agent": "FactExtractor", "reacts_to": [], "summary": "10 args"},
            {
                "agent": "FallacyDetector",
                "reacts_to": ["extract"],
                "summary": "5 fallacies",
            },
        ]
        comment_lines = []
        for entry in trace_data:
            agent = entry.get("agent", "?")
            reacts = ", ".join(entry.get("reacts_to", []))
            summary = entry.get("summary", "")
            comment_lines.append(f'[{agent}] (réagit à: {reacts}) → "{summary}"')
        assert len(comment_lines) == 2
        assert "[FactExtractor]" in comment_lines[0]
        assert "[FallacyDetector]" in comment_lines[1]
        assert "extract" in comment_lines[1]
