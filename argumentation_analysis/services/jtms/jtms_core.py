"""
Core JTMS implementation — integrated from student project 1.4.1-JTMS.

This module provides a Justification-based Truth Maintenance System (JTMS)
with support for non-monotonic reasoning via strongly-connected component
detection.

Original author: @ThomasLeguere (student project 1.4.1-JTMS)
Integrated into argumentation_analysis framework.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger("JTMS")

# Optional visualization deps — graceful degradation
try:
    import networkx as nx

    _HAS_NETWORKX = True
except ImportError:
    _HAS_NETWORKX = False
    logger.debug("networkx not available, SCC detection disabled")

try:
    from pyvis.network import Network

    _HAS_PYVIS = True
except ImportError:
    _HAS_PYVIS = False
    logger.debug("pyvis not available, visualization disabled")


class Belief:
    """A named belief with tri-state truth value and justification support."""

    def __init__(self, name: str):
        self.name = name
        self.valid: Optional[bool] = None  # None=unknown, True=valid, False=invalid
        self.non_monotonic: bool = False
        self.justifications: List["Justification"] = []
        self.implications: List["Justification"] = []

    def __str__(self):
        status = (
            "UNKNOWN" if self.valid is None else ("VALID" if self.valid else "INVALID")
        )
        return f"{self.name} -> {status}"

    def __repr__(self):
        return f"{self.name}"

    def add_justification(self, justification: "Justification"):
        self.justifications.append(justification)
        self.compute_truth_statement()

    def remove_justification(self, justification: "Justification"):
        self.justifications.remove(justification)
        self.compute_truth_statement()

    def add_implication(self, justification: "Justification"):
        self.implications.append(justification)

    def remove_implication(self, justification: "Justification"):
        self.implications.remove(justification)

    def set_truth_value(self, value: Optional[bool]):
        self.valid = value
        self.propagate()

    def compute_truth_statement(self):
        if self.non_monotonic:
            self.valid = None
            return

        self.valid = None
        for justification in self.justifications:
            if all(b.valid for b in justification.in_list) and not any(
                b.valid for b in justification.out_list
            ):
                self.valid = True
                break

        self.propagate()

    def propagate(self):
        for justification in self.implications:
            justification.conclusion.compute_truth_statement()


class Justification:
    """A rule relating premises to a conclusion in a JTMS."""

    def __init__(
        self,
        in_list: List[Belief],
        out_list: List[Belief],
        conclusion: Belief,
    ):
        self.in_list = in_list
        self.out_list = out_list
        self.conclusion = conclusion


class JTMS:
    """
    Justification-based Truth Maintenance System.

    Manages a network of beliefs connected by justifications.
    Supports non-monotonic reasoning via SCC detection.

    Usage:
        jtms = JTMS()
        jtms.add_belief("A")
        jtms.add_belief("B")
        jtms.set_belief_validity("A", True)
        jtms.add_justification(["A"], [], "B")  # A justifies B
        assert jtms.beliefs["B"].valid is True
    """

    def __init__(self, strict: bool = False):
        self.beliefs: Dict[str, Belief] = {}
        self.strict = strict

    def add_belief(self, name: str):
        """Add a new belief to the system."""
        if name not in self.beliefs:
            self.beliefs[name] = Belief(name)

    def remove_belief(self, belief_name: str):
        """Remove a belief and clean up its implications."""
        if belief_name not in self.beliefs:
            raise KeyError(f"Unknown belief: {belief_name}")

        for justification in self.beliefs[belief_name].implications:
            self.beliefs[repr(justification.conclusion)].remove_justification(
                justification
            )

        self.beliefs.pop(belief_name)

    def set_belief_validity(self, belief_name: str, validity: Optional[bool]):
        """Set the truth value of a belief and propagate."""
        if belief_name not in self.beliefs:
            raise KeyError(f"Unknown belief: {belief_name}")
        self.beliefs[belief_name].set_truth_value(validity)

    def add_justification(
        self,
        in_list: List[str],
        out_list: List[str],
        conclusion_name: str,
    ):
        """Add a justification rule. Creates missing beliefs in non-strict mode."""
        for b in in_list + out_list + [conclusion_name]:
            if b not in self.beliefs:
                if self.strict:
                    raise KeyError(f"Unknown belief: {b}")
                else:
                    self.add_belief(b)

        justification = Justification(
            [self.beliefs[name] for name in in_list],
            [self.beliefs[name] for name in out_list],
            self.beliefs[conclusion_name],
        )
        self.beliefs[conclusion_name].add_justification(justification)
        for in_belief in justification.in_list:
            self.beliefs[in_belief.name].add_implication(justification)
        for out_belief in justification.out_list:
            self.beliefs[out_belief.name].add_implication(justification)

        self.update_non_monotonic_beliefs()

    def update_non_monotonic_beliefs(self):
        """Detect strongly-connected components and mark beliefs as non-monotonic."""
        if not _HAS_NETWORKX:
            return

        vertices = []
        for belief in self.beliefs.values():
            for justification in belief.justifications:
                for statement in justification.in_list + justification.out_list:
                    vertices.append((statement.name, belief.name))
        if not vertices:
            return
        graph = nx.DiGraph(vertices)
        sccs = nx.strongly_connected_components(graph)
        for scc in sccs:
            if len(scc) > 1:
                for belief_name in scc:
                    if belief_name in self.beliefs:
                        self.beliefs[belief_name].non_monotonic = True

    def show(self):
        """Print all beliefs and their truth values."""
        for b in self.beliefs.values():
            print(b)

    def explain_belief(self, belief_name: str) -> str:
        """Return a formatted explanation of a belief's justifications."""
        if belief_name not in self.beliefs:
            raise KeyError(f"Unknown belief: {belief_name}")

        belief = self.beliefs[belief_name]
        if not belief.justifications:
            return "No justification"

        explanations = []
        for j in belief.justifications:
            in_status = [
                f"{b.name} ({'valid' if b.valid else 'invalid'})" for b in j.in_list
            ]
            out_status = [
                f"{b.name} ({'valid' if b.valid else 'invalid'})" for b in j.out_list
            ]

            valid = all(b.valid for b in j.in_list) and all(
                not b.valid for b in j.out_list
            )

            block = (
                f"Justification:\n"
                f"  IN: {', '.join(in_status) or '-'}\n"
                f"  OUT: {', '.join(out_status) or '-'}\n"
                f"  Result: {'Valid' if valid else 'Invalid'}\n"
            )
            explanations.append(block)

        return "".join(explanations)

    def visualize(self, output_file: str = "jtms_graph.html") -> Optional[str]:
        """Generate interactive HTML visualization. Returns output path or None."""
        if not _HAS_PYVIS:
            logger.warning("pyvis not installed, cannot visualize")
            return None

        net = Network(directed=True, notebook=False)
        net.barnes_hut()

        for belief in self.beliefs.values():
            color = (
                "orange" if belief.non_monotonic else "green" if belief.valid else "red"
            )
            explanation = self.explain_belief(belief.name)
            net.add_node(belief.name, label=belief.name, color=color, title=explanation)

        for belief in self.beliefs.values():
            for j in belief.justifications:
                for source in j.in_list:
                    net.add_edge(source.name, belief.name, color="green", title="IN")
                for source in j.out_list:
                    net.add_edge(
                        source.name,
                        belief.name,
                        color="red",
                        dashes=True,
                        title="OUT",
                    )

        net.write_html(output_file)
        return output_file
