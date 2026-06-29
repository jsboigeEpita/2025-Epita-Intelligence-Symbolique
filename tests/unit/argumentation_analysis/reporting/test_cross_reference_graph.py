"""Unit tests for CrossReferenceGraph."""

import json
import pytest
from unittest.mock import MagicMock
from argumentation_analysis.reporting.cross_reference_graph import (
    CrossReferenceGraph,
    CrossReferenceReport,
    Edge,
    EdgeType,
    Node,
)


def _make_mock_state():
    """Create a mock UnifiedAnalysisState with realistic data."""
    state = MagicMock()
    state.identified_arguments = {
        "arg_0": {"text": "First argument about climate"},
        "arg_1": {"text": "Second argument about economy"},
        "arg_2": {"text": "Third argument about health"},
    }
    state.identified_fallacies = {
        "fal_0": {"fallacy_type": "ad_hominem", "target_argument_id": "arg_0"},
        "fal_1": {"fallacy_type": "straw_man", "target_argument_id": "arg_1"},
    }
    state.jtms_beliefs = {
        "jtms_0": {"name": "climate_is_real", "valid": True, "justifications": []},
        "jtms_1": {"name": "economy_growing", "valid": False, "justifications": []},
    }
    state.jtms_retraction_chain = [
        {"fallacy_id": "fal_0", "belief_id": "jtms_1"},
    ]
    state.belief_revision_results = [
        {"id": "rev_0", "belief_id": "jtms_0", "description": "Revised after new evidence"},
    ]
    state.counter_arguments = [
        {"id": "ca_0", "target_arg_id": "arg_0", "counter_content": "Counter to first"},
        {"id": "ca_1", "target_arg_id": "arg_2", "counter_content": "Counter to third"},
    ]
    state.argument_quality_scores = {
        "arg_0": {"overall": 7.5, "scores": {}},
        "arg_1": {"overall": 4.2, "scores": {}},
    }
    state.debate_transcripts = [
        {"id": "debate_0", "topic": "Climate debate", "exchanges": [], "winner": "pro"},
    ]
    state.governance_decisions = [
        {"id": "gov_0", "method": "copeland", "winner": "pro", "scores": {},
         "debate_id": "debate_0"},
    ]
    return state


class TestNodeEdgeCreation:
    """Test basic node and edge operations."""

    def test_add_node(self):
        graph = CrossReferenceGraph()
        graph.add_node(Node(id="n1", label="Test", node_type="argument"))
        assert "n1" in graph.nodes
        assert graph.nodes["n1"].node_type == "argument"

    def test_add_edge(self):
        graph = CrossReferenceGraph()
        graph.add_edge(Edge(source="n1", target="n2", edge_type=EdgeType.ARGUMENT_COUNTER))
        assert len(graph.edges) == 1
        assert graph.edges[0].edge_type == EdgeType.ARGUMENT_COUNTER

    def test_clear(self):
        graph = CrossReferenceGraph()
        graph.add_node(Node(id="n1", label="T", node_type="argument"))
        graph.add_edge(Edge(source="n1", target="n2", edge_type=EdgeType.ARGUMENT_QUALITY))
        graph.clear()
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0


class TestBuildFromState:
    """Test graph construction from mock state."""

    def test_builds_nodes_from_all_dimensions(self):
        state = _make_mock_state()
        graph = CrossReferenceGraph()
        graph.build_from_state(state)
        assert len(graph.nodes) > 0
        node_types = {n.node_type for n in graph.nodes.values()}
        assert "argument" in node_types
        assert "fallacy" in node_types
        assert "jtms_belief" in node_types

    def test_builds_edges_for_all_types(self):
        state = _make_mock_state()
        graph = CrossReferenceGraph()
        graph.build_from_state(state)
        edge_types = {e.edge_type for e in graph.edges}
        assert EdgeType.ARGUMENT_FALLACY in edge_types
        assert EdgeType.FALLACY_JTMS_RETRACTION in edge_types
        assert EdgeType.JTMS_BELIEF_REVISION in edge_types
        assert EdgeType.ARGUMENT_COUNTER in edge_types
        assert EdgeType.ARGUMENT_QUALITY in edge_types
        assert EdgeType.GOVERNANCE_DEBATE in edge_types

    def test_handles_none_state(self):
        graph = CrossReferenceGraph()
        graph.build_from_state(None)
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_handles_empty_attrs(self):
        state = MagicMock()
        state.identified_arguments = None
        state.identified_fallacies = None
        state.jtms_beliefs = None
        state.jtms_retraction_chain = None
        state.belief_revision_results = None
        state.counter_arguments = None
        state.argument_quality_scores = None
        state.debate_transcripts = None
        state.governance_decisions = None
        graph = CrossReferenceGraph()
        graph.build_from_state(state)
        assert len(graph.nodes) == 0


class TestMetrics:
    """Test density and orphan node computation."""

    def test_density_empty_graph(self):
        graph = CrossReferenceGraph()
        assert graph.density() == 0.0

    def test_density_with_edges(self):
        state = _make_mock_state()
        graph = CrossReferenceGraph()
        graph.build_from_state(state)
        d = graph.density()
        assert 0.0 <= d <= 1.0

    def test_orphan_nodes(self):
        graph = CrossReferenceGraph()
        graph.add_node(Node(id="lonely", label="No edges", node_type="argument"))
        graph.add_node(Node(id="connected_a", label="A", node_type="argument"))
        graph.add_node(Node(id="connected_b", label="B", node_type="fallacy"))
        graph.add_edge(Edge(source="connected_a", target="connected_b",
                            edge_type=EdgeType.ARGUMENT_FALLACY))
        orphans = graph.orphan_nodes()
        assert "lonely" in orphans
        assert "connected_a" not in orphans


class TestRenderers:
    """Test JSON, DOT, and Mermaid output."""

    def test_to_json_valid(self):
        state = _make_mock_state()
        graph = CrossReferenceGraph()
        graph.build_from_state(state)
        j = graph.to_json()
        data = json.loads(j)
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) > 0

    def test_to_dot_format(self):
        state = _make_mock_state()
        graph = CrossReferenceGraph()
        graph.build_from_state(state)
        dot = graph.to_dot()
        assert "digraph CrossReference {" in dot
        assert "->" in dot

    def test_to_mermaid_format(self):
        state = _make_mock_state()
        graph = CrossReferenceGraph()
        graph.build_from_state(state)
        md = graph.to_mermaid()
        assert "graph LR" in md
        assert "-->" in md


class TestReport:
    """Test CrossReferenceReport generation."""

    def test_report_has_all_fields(self):
        state = _make_mock_state()
        graph = CrossReferenceGraph()
        graph.build_from_state(state)
        report = graph.report()
        assert report.total_nodes > 0
        assert report.total_edges > 0
        assert 0.0 <= report.density <= 1.0
        assert isinstance(report.edge_type_counts, dict)
        assert isinstance(report.node_type_counts, dict)

    def test_report_markdown(self):
        state = _make_mock_state()
        graph = CrossReferenceGraph()
        graph.build_from_state(state)
        report = graph.report()
        md = report.to_markdown()
        assert "## Cross-Reference Graph Report" in md
        assert "Nodes" in md
        assert "Edges" in md

    def test_report_edge_type_counts(self):
        state = _make_mock_state()
        graph = CrossReferenceGraph()
        graph.build_from_state(state)
        report = graph.report()
        # Should have multiple edge types from the mock state
        assert len(report.edge_type_counts) >= 4


class TestIntegration:
    """Integration test combining balance analyzer and cross-reference graph."""

    def test_full_pipeline_on_mock_state(self):
        from argumentation_analysis.reporting.conversation_balance import ConversationBalanceAnalyzer

        state = _make_mock_state()
        conv_log = [
            {"agent": "PM", "content": "Starting analysis", "phase": "extraction"},
            {"agent": "InformalAgent", "content": "Found fallacies", "phase": "extraction"},
            {"agent": "FormalAgent", "content": "Formalizing", "phase": "formal"},
            {"agent": "PM", "content": "Summary", "phase": "synthesis"},
        ]

        # Cross-reference graph
        graph = CrossReferenceGraph()
        graph.build_from_state(state)
        report = graph.report()
        assert report.total_nodes >= 8

        # Balance analyzer
        analyzer = ConversationBalanceAnalyzer()
        balance = analyzer.analyze(conv_log)
        assert balance.active_agents == 3
        assert balance.total_turns == 4

        # Render both outputs
        dot = graph.to_dot()
        mermaid = graph.to_mermaid()
        balance_md = balance.to_markdown()
        assert len(dot) > 50
        assert len(mermaid) > 50
        assert "Balance score" in balance_md
