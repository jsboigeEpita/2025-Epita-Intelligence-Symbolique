"""Unit tests for ConversationBalanceAnalyzer."""

import pytest
from argumentation_analysis.reporting.conversation_balance import (
    AgentStats,
    BalanceReport,
    ConversationBalanceAnalyzer,
)


def _make_log(entries):
    """Helper to build conversation log entries."""
    return [{"agent": a, "content": c, "phase": p} for a, c, p in entries]


class TestEntropyScore:
    """Test entropy-based balance score computation."""

    def test_perfectly_balanced(self):
        log = _make_log([
            ("A", "msg", "p1"),
            ("B", "msg", "p1"),
            ("A", "msg", "p1"),
            ("B", "msg", "p1"),
        ])
        analyzer = ConversationBalanceAnalyzer()
        report = analyzer.analyze(log)
        assert report.balance_score == pytest.approx(1.0)

    def test_single_agent_dominates(self):
        log = _make_log([
            ("A", "msg", "p1"),
            ("A", "msg", "p1"),
            ("A", "msg", "p1"),
            ("B", "msg", "p1"),
        ])
        analyzer = ConversationBalanceAnalyzer()
        report = analyzer.analyze(log)
        # A has 75%, B has 25% → not balanced
        assert 0.0 < report.balance_score < 1.0

    def test_single_agent_only(self):
        log = _make_log([
            ("A", "msg", "p1"),
            ("A", "msg", "p1"),
        ])
        analyzer = ConversationBalanceAnalyzer()
        report = analyzer.analyze(log)
        assert report.balance_score == 0.0

    def test_empty_log(self):
        analyzer = ConversationBalanceAnalyzer()
        report = analyzer.analyze([])
        assert report.balance_score == 0.0
        assert report.total_turns == 0

    def test_three_agents_balanced(self):
        log = _make_log([
            ("A", "msg", "p1"),
            ("B", "msg", "p1"),
            ("C", "msg", "p1"),
        ])
        analyzer = ConversationBalanceAnalyzer()
        report = analyzer.analyze(log)
        assert report.balance_score == pytest.approx(1.0)


class TestAgentStats:
    """Test per-agent statistics extraction."""

    def test_turn_counts(self):
        log = _make_log([
            ("PM", "msg1", "extraction"),
            ("PM", "msg2", "extraction"),
            ("InformalAgent", "msg3", "extraction"),
        ])
        analyzer = ConversationBalanceAnalyzer()
        report = analyzer.analyze(log)
        assert report.agent_stats["PM"].turn_count == 2
        assert report.agent_stats["InformalAgent"].turn_count == 1

    def test_char_counts(self):
        log = _make_log([
            ("A", "short", "p1"),
            ("B", "a much longer message here", "p1"),
        ])
        analyzer = ConversationBalanceAnalyzer()
        report = analyzer.analyze(log)
        assert report.agent_stats["A"].total_chars == 5
        assert report.agent_stats["B"].total_chars == 26

    def test_phase_distribution(self):
        log = _make_log([
            ("PM", "msg", "extraction"),
            ("PM", "msg", "formal"),
            ("PM", "msg", "extraction"),
        ])
        analyzer = ConversationBalanceAnalyzer()
        report = analyzer.analyze(log)
        stats = report.agent_stats["PM"]
        assert stats.turns_per_phase["extraction"] == 2
        assert stats.turns_per_phase["formal"] == 1


class TestDominanceAlerts:
    """Test dominance detection."""

    def test_dominance_alert_triggered(self):
        log = _make_log([
            ("A", "msg", "p1")] * 8 + [("B", "msg", "p1")] * 2)
        analyzer = ConversationBalanceAnalyzer(dominance_threshold=0.5)
        report = analyzer.analyze(log)
        assert any("A dominates" in a for a in report.dominance_alerts)

    def test_no_dominance_alert_balanced(self):
        log = _make_log([
            ("A", "msg", "p1"),
            ("B", "msg", "p1"),
        ])
        analyzer = ConversationBalanceAnalyzer(dominance_threshold=0.5)
        report = analyzer.analyze(log)
        assert report.dominance_alerts == []

    def test_custom_threshold(self):
        log = _make_log([
            ("A", "msg", "p1")] * 6 + [("B", "msg", "p1")] * 4)
        # With threshold 0.55, A (60%) triggers; with 0.65 it doesn't
        analyzer_strict = ConversationBalanceAnalyzer(dominance_threshold=0.55)
        analyzer_loose = ConversationBalanceAnalyzer(dominance_threshold=0.65)
        report_strict = analyzer_strict.analyze(log)
        report_loose = analyzer_loose.analyze(log)
        assert any("dominates" in a for a in report_strict.dominance_alerts)
        assert not any("dominates" in a for a in report_loose.dominance_alerts)


class TestStructuralEntries:
    """Test handling of structural (non-agent) entries."""

    def test_skips_conflict_resolution(self):
        log = [
            {"agent": "A", "content": "msg", "phase": "p1"},
            {"type": "conflict_resolution", "resolutions": []},
            {"agent": "B", "content": "msg", "phase": "p1"},
        ]
        analyzer = ConversationBalanceAnalyzer()
        report = analyzer.analyze(log)
        assert report.total_turns == 2
        assert len(report.agent_stats) == 2


class TestMarkdownOutput:
    """Test markdown report generation."""

    def test_report_has_header(self):
        log = _make_log([("A", "msg", "p1")])
        analyzer = ConversationBalanceAnalyzer()
        report = analyzer.analyze(log)
        md = report.to_markdown()
        assert "## Conversation Balance Report" in md
        assert "Balance score" in md

    def test_report_includes_agents(self):
        log = _make_log([
            ("PM", "msg", "extraction"),
            ("InformalAgent", "msg", "extraction"),
        ])
        analyzer = ConversationBalanceAnalyzer()
        report = analyzer.analyze(log)
        md = report.to_markdown()
        assert "PM" in md
        assert "InformalAgent" in md


class TestAnalyzeFromState:
    """Test state-enriched analysis."""

    def test_enriched_with_state_dimensions(self):
        from unittest.mock import MagicMock
        state = MagicMock()
        state.identified_arguments = {"a1": {}, "a2": {}}
        state.identified_fallacies = {"f1": {}}
        log = _make_log([("A", "msg", "p1")])
        analyzer = ConversationBalanceAnalyzer()
        report = analyzer.analyze_from_state(state, log)
        assert "__state__" in report.agent_stats
        assert report.agent_stats["__state__"].turns_per_phase["arguments_extracted"] == 2
        assert report.agent_stats["__state__"].turns_per_phase["fallacies_detected"] == 1

    def test_none_state(self):
        log = _make_log([("A", "msg", "p1")])
        analyzer = ConversationBalanceAnalyzer()
        report = analyzer.analyze_from_state(None, log)
        assert "__state__" not in report.agent_stats
