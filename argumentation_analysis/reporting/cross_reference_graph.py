#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Cross-reference graph for UnifiedAnalysisState dimensions.

Builds a directed graph with 7 edge types connecting the state's analysis
dimensions (arguments, fallacies, JTMS beliefs, counter-arguments, quality
scores, debate outcomes, governance decisions). Provides JSON, DOT, and
Mermaid renderers plus a density metric.

Edge types:
    1. argument -> fallacy       (target_arg_id links)
    2. fallacy -> jtms_retraction (retraction chain)
    3. jtms_belief -> belief_revision (revision references)
    4. argument -> counter_argument (target_arg_id)
    5. argument -> quality_score  (quality_scores keyed by arg_id)
    6. argument -> debate_outcome (debate transcripts referencing args)
    7. governance -> debate_outcome (governance decisions referencing debates)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class EdgeType(str, Enum):
    ARGUMENT_FALLACY = "argument->fallacy"
    FALLACY_JTMS_RETRACTION = "fallacy->jtms_retraction"
    JTMS_BELIEF_REVISION = "jtms->belief_revision"
    ARGUMENT_COUNTER = "argument->counter_argument"
    ARGUMENT_QUALITY = "argument->quality_score"
    ARGUMENT_DEBATE = "argument->debate_outcome"
    GOVERNANCE_DEBATE = "governance->debate_outcome"


@dataclass
class Node:
    """Graph node representing a state dimension element."""

    id: str
    label: str
    node_type: str  # argument, fallacy, jtms_belief, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    """Directed edge between two nodes."""

    source: str
    target: str
    edge_type: EdgeType
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CrossReferenceReport:
    """Summary report for the cross-reference graph."""

    total_nodes: int
    total_edges: int
    edge_type_counts: Dict[str, int]
    node_type_counts: Dict[str, int]
    density: float
    orphan_nodes: List[str]

    def to_markdown(self) -> str:
        lines = [
            "## Cross-Reference Graph Report",
            "",
            f"- **Nodes**: {self.total_nodes}",
            f"- **Edges**: {self.total_edges}",
            f"- **Density**: {self.density:.4f}",
            "",
            "### Nodes by Type",
            "",
        ]
        for ntype, count in sorted(self.node_type_counts.items()):
            lines.append(f"- {ntype}: {count}")
        lines.append("")
        lines.append("### Edges by Type")
        lines.append("")
        for etype, count in sorted(self.edge_type_counts.items()):
            lines.append(f"- {etype}: {count}")
        if self.orphan_nodes:
            lines.append("")
            lines.append(f"### Orphan Nodes ({len(self.orphan_nodes)})")
            lines.append("")
            for oid in self.orphan_nodes[:20]:
                lines.append(f"- {oid}")
            if len(self.orphan_nodes) > 20:
                lines.append(f"- ... and {len(self.orphan_nodes) - 20} more")
        lines.append("")
        return "\n".join(lines)


class CrossReferenceGraph:
    """Build and render a cross-reference graph from UnifiedAnalysisState.

    Usage::

        graph = CrossReferenceGraph()
        graph.build_from_state(state)
        print(graph.to_mermaid())
        report = graph.report()
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self._node_ids_by_type: Dict[str, Set[str]] = {}

    def clear(self) -> None:
        self.nodes.clear()
        self.edges.clear()
        self._node_ids_by_type.clear()

    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node
        self._node_ids_by_type.setdefault(node.node_type, set()).add(node.id)

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

    def build_from_state(self, state: Any) -> None:
        """Build the full cross-reference graph from a UnifiedAnalysisState."""
        self.clear()
        if state is None:
            return

        # 1. Arguments
        arguments = getattr(state, "identified_arguments", None) or {}
        if isinstance(arguments, dict):
            for arg_id, arg_data in arguments.items():
                label = str(arg_data)[:60] if not isinstance(arg_data, dict) else arg_data.get("text", arg_id)[:60]
                self.add_node(Node(id=str(arg_id), label=label, node_type="argument",
                                   metadata={"data": arg_data} if isinstance(arg_data, dict) else {}))
        elif isinstance(arguments, list):
            for i, arg in enumerate(arguments):
                arg_id = getattr(arg, "id", None) or f"arg_{i}"
                label = getattr(arg, "text", str(arg))[:60]
                self.add_node(Node(id=str(arg_id), label=label, node_type="argument"))

        # 2. Fallacies
        fallacies = getattr(state, "identified_fallacies", None) or {}
        if isinstance(fallacies, dict):
            for f_id, f_data in fallacies.items():
                label = str(f_data)[:60] if not isinstance(f_data, dict) else f_data.get("fallacy_type", f_id)[:60]
                self.add_node(Node(id=str(f_id), label=label, node_type="fallacy",
                                   metadata={"data": f_data} if isinstance(f_data, dict) else {}))
                # Edge: argument -> fallacy (via target_arg_id)
                if isinstance(f_data, dict) and "target_arg_id" in f_data:
                    target = str(f_data["target_arg_id"])
                    self.add_edge(Edge(source=target, target=str(f_id),
                                       edge_type=EdgeType.ARGUMENT_FALLACY))
        elif isinstance(fallacies, list):
            for i, f in enumerate(fallacies):
                f_id = getattr(f, "id", None) or f"fal_{i}"
                label = getattr(f, "fallacy_type", str(f))[:60]
                self.add_node(Node(id=str(f_id), label=label, node_type="fallacy"))
                target = getattr(f, "target_arg_id", None)
                if target:
                    self.add_edge(Edge(source=str(target), target=str(f_id),
                                       edge_type=EdgeType.ARGUMENT_FALLACY))

        # 3. JTMS beliefs
        beliefs = getattr(state, "jtms_beliefs", None) or {}
        for b_id, b_data in beliefs.items():
            label = b_data.get("name", str(b_id))[:60] if isinstance(b_data, dict) else str(b_id)[:60]
            self.add_node(Node(id=str(b_id), label=label, node_type="jtms_belief",
                               metadata={"data": b_data} if isinstance(b_data, dict) else {}))

        # Edge: fallacy -> jtms_retraction (via retraction chain)
        retraction_chain = getattr(state, "jtms_retraction_chain", None) or []
        for entry in retraction_chain:
            if isinstance(entry, dict):
                fallacy_id = str(entry.get("fallacy_id", ""))
                belief_id = str(entry.get("belief_id", ""))
                if fallacy_id and belief_id:
                    self.add_edge(Edge(source=fallacy_id, target=belief_id,
                                       edge_type=EdgeType.FALLACY_JTMS_RETRACTION))

        # 4. Belief revisions
        revisions = getattr(state, "belief_revision_results", None) or []
        for i, rev in enumerate(revisions):
            rev_id = rev.get("id", f"rev_{i}") if isinstance(rev, dict) else f"rev_{i}"
            label = rev.get("description", rev_id)[:60] if isinstance(rev, dict) else str(rev)[:60]
            self.add_node(Node(id=str(rev_id), label=label, node_type="belief_revision"))
            # Edge: jtms_belief -> belief_revision
            if isinstance(rev, dict) and "belief_id" in rev:
                self.add_edge(Edge(source=str(rev["belief_id"]), target=str(rev_id),
                                   edge_type=EdgeType.JTMS_BELIEF_REVISION))

        # 5. Counter-arguments
        counters = getattr(state, "counter_arguments", None) or []
        for ca in counters:
            if isinstance(ca, dict):
                ca_id = ca.get("id", f"ca_{len(self.edges)}")
                label = ca.get("counter_content", ca_id)[:60]
                self.add_node(Node(id=str(ca_id), label=label, node_type="counter_argument"))
                target = ca.get("target_arg_id")
                if target:
                    self.add_edge(Edge(source=str(target), target=str(ca_id),
                                       edge_type=EdgeType.ARGUMENT_COUNTER))

        # 6. Quality scores
        quality = getattr(state, "argument_quality_scores", None) or {}
        for arg_id, q_data in quality.items():
            q_id = f"qual_{arg_id}"
            overall = q_data.get("overall", 0) if isinstance(q_data, dict) else 0
            self.add_node(Node(id=q_id, label=f"Q:{overall:.1f}", node_type="quality_score"))
            self.add_edge(Edge(source=str(arg_id), target=q_id,
                               edge_type=EdgeType.ARGUMENT_QUALITY))

        # 7. Debate transcripts
        debates = getattr(state, "debate_transcripts", None) or []
        for dt in debates:
            if isinstance(dt, dict):
                dt_id = dt.get("id", f"debate_{len(self.edges)}")
                label = dt.get("topic", dt_id)[:60]
                self.add_node(Node(id=str(dt_id), label=label, node_type="debate_outcome"))

        # 8. Governance decisions
        governance = getattr(state, "governance_decisions", None) or []
        for gd in governance:
            if isinstance(gd, dict):
                gd_id = gd.get("id", f"gov_{len(self.edges)}")
                winner = gd.get("winner", "?")
                self.add_node(Node(id=str(gd_id), label=f"Vote:{winner}", node_type="governance"))
                # Edge: governance -> debate_outcome
                debate_ref = gd.get("debate_id")
                if debate_ref:
                    self.add_edge(Edge(source=str(gd_id), target=str(debate_ref),
                                       edge_type=EdgeType.GOVERNANCE_DEBATE))

    def density(self) -> float:
        """Compute graph density: ``|E| / (|V| * (|V| - 1))`` for directed graph."""
        n = len(self.nodes)
        if n < 2:
            return 0.0
        return len(self.edges) / (n * (n - 1))

    def orphan_nodes(self) -> List[str]:
        """Find nodes with no incoming or outgoing edges."""
        connected: Set[str] = set()
        for edge in self.edges:
            connected.add(edge.source)
            connected.add(edge.target)
        return [nid for nid in self.nodes if nid not in connected]

    def report(self) -> CrossReferenceReport:
        """Generate a summary report."""
        edge_type_counts: Dict[str, int] = {}
        node_type_counts: Dict[str, int] = {}
        for edge in self.edges:
            key = edge.edge_type.value
            edge_type_counts[key] = edge_type_counts.get(key, 0) + 1
        for node in self.nodes.values():
            node_type_counts[node.node_type] = node_type_counts.get(node.node_type, 0) + 1

        return CrossReferenceReport(
            total_nodes=len(self.nodes),
            total_edges=len(self.edges),
            edge_type_counts=edge_type_counts,
            node_type_counts=node_type_counts,
            density=self.density(),
            orphan_nodes=self.orphan_nodes(),
        )

    def to_json(self) -> str:
        """Serialize graph to JSON."""
        data = {
            "nodes": [
                {"id": n.id, "label": n.label, "type": n.node_type, "metadata": n.metadata}
                for n in self.nodes.values()
            ],
            "edges": [
                {"source": e.source, "target": e.target, "type": e.edge_type.value,
                 "weight": e.weight}
                for e in self.edges
            ],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def to_dot(self) -> str:
        """Render graph in Graphviz DOT format."""
        type_colors = {
            "argument": "#4CAF50",
            "fallacy": "#F44336",
            "jtms_belief": "#2196F3",
            "belief_revision": "#9C27B0",
            "counter_argument": "#FF9800",
            "quality_score": "#00BCD4",
            "debate_outcome": "#607D8B",
            "governance": "#795548",
        }
        lines = ["digraph CrossReference {", '  rankdir=LR;', '  node [shape=box, style=filled];', ""]
        for nid, node in self.nodes.items():
            color = type_colors.get(node.node_type, "#E0E0E0")
            safe_id = nid.replace(" ", "_").replace("-", "_").replace(".", "_")
            safe_label = node.label.replace('"', '\\"').replace("\n", " ")
            lines.append(f'  {safe_id} [label="{safe_label}", fillcolor="{color}"];')
        lines.append("")
        for edge in self.edges:
            src = edge.source.replace(" ", "_").replace("-", "_").replace(".", "_")
            tgt = edge.target.replace(" ", "_").replace("-", "_").replace(".", "_")
            label = edge.edge_type.value.split("->")[-1]
            lines.append(f'  {src} -> {tgt} [label="{label}"];')
        lines.append("}")
        return "\n".join(lines)

    def to_mermaid(self) -> str:
        """Render graph in Mermaid flowchart format."""
        type_shapes = {
            "argument": ("([", "])"),
            "fallacy": ("{{", "}}"),
            "jtms_belief": ("[/", "/]"),
            "belief_revision": ("[\\", "\\]"),
            "counter_argument": (">", "]"),
            "quality_score": ("[[", "]]"),
            "debate_outcome": ("(", ")"),
            "governance": ("{", "}"),
        }
        lines = ["graph LR"]
        for nid, node in self.nodes.items():
            safe_id = nid.replace(" ", "_").replace("-", "_").replace(".", "_").replace("/", "_")
            safe_label = node.label.replace('"', "'").replace("\n", " ")[:30]
            open_b, close_b = type_shapes.get(node.node_type, ("[", "]"))
            lines.append(f"  {safe_id}{open_b}\"{safe_label}\"{close_b}")
        for edge in self.edges:
            src = edge.source.replace(" ", "_").replace("-", "_").replace(".", "_").replace("/", "_")
            tgt = edge.target.replace(" ", "_").replace("-", "_").replace(".", "_").replace("/", "_")
            label = edge.edge_type.value.split("->")[-1]
            lines.append(f"  {src} -->|{label}| {tgt}")
        return "\n".join(lines)
