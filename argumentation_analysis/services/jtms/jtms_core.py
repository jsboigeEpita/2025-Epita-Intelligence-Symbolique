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


def _validity_label(value: Optional[bool]) -> str:
    """Render a tri-state validity for display: `None` is « unknown », never
    « invalid » — same contrast `Belief.__str__` already draws (#2094)."""
    if value is None:
        return "unknown"
    return "valid" if value else "invalid"


class Belief:
    """A named belief with tri-state truth value and justification support."""

    def __init__(self, name: str):
        self.name = name
        self.valid: Optional[bool] = None  # None=unknown, True=valid, False=invalid
        self.non_monotonic: bool = False
        self.justifications: List["Justification"] = []
        self.implications: List["Justification"] = []
        self._propagating: bool = False  # Guard against re-entrant propagation cycles

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
        if self._propagating:
            return  # Break re-entrant cycle

        old_valid = self.valid
        self.valid = None
        for justification in self.justifications:
            if all(b.valid for b in justification.in_list) and not any(
                b.valid for b in justification.out_list
            ):
                self.valid = True
                break

        if self.valid != old_valid:
            self.propagate()

    def propagate(self):
        self._propagating = True
        try:
            for justification in self.implications:
                conclusion = justification.conclusion
                old_valid = conclusion.valid
                conclusion.compute_truth_statement()
                # Track cascade: conclusion was valid, now retracted
                if (
                    hasattr(self, "_jtms_ref")
                    and self._jtms_ref is not None
                    and self._jtms_ref._tracing_enabled
                    and old_valid is True
                    and conclusion.valid is not True
                    and self._jtms_ref._retraction_trace
                ):
                    self._jtms_ref._retraction_trace[-1]["cascaded"].append(
                        conclusion.name
                    )
        finally:
            self._propagating = False


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
        self._retraction_trace: List[Dict] = []
        self._tracing_enabled: bool = False

    def add_belief(self, name: str):
        """Add a new belief to the system."""
        if name not in self.beliefs:
            belief = Belief(name)
            belief._jtms_ref = self
            self.beliefs[name] = belief

    def remove_belief(self, belief_name: str):
        """Remove a belief and tear down every justification touching it.

        Both directions are detached (#2094): justifications concluding toward
        the removed belief leave their premises' `implications`, and
        justifications where the removed belief was a premise leave both the
        conclusion's `justifications` and the co-premises' `implications`.
        A dangling reference would let a later propagation walk — and trace
        (#2094: `_retraction_trace`) — a conclusion that no longer exists.
        """
        if belief_name not in self.beliefs:
            raise KeyError(f"Unknown belief: {belief_name}")

        belief = self.beliefs[belief_name]

        # Justifications concluding toward the removed belief: premises keep
        # no reference to a vanished conclusion.
        for justification in belief.justifications:
            for premise in justification.in_list + justification.out_list:
                if premise is not belief and justification in premise.implications:
                    premise.remove_implication(justification)

        # Justifications where the removed belief is a premise: tear the rule
        # down completely — from the conclusion AND from the co-premises.
        for justification in list(belief.implications):
            conclusion = justification.conclusion
            if justification in conclusion.justifications:
                conclusion.remove_justification(justification)
            for premise in justification.in_list + justification.out_list:
                if premise is not belief and justification in premise.implications:
                    premise.remove_implication(justification)

        self.beliefs.pop(belief_name)

    def set_belief_validity(self, belief_name: str, validity: Optional[bool]):
        """Set the truth value of a belief and propagate."""
        if belief_name not in self.beliefs:
            raise KeyError(f"Unknown belief: {belief_name}")
        belief = self.beliefs[belief_name]
        old_valid = belief.valid
        if self._tracing_enabled and old_valid is True and validity is not True:
            self._retraction_trace.append(
                {
                    "trigger": belief_name,
                    "retracted": [belief_name],
                    "cascaded": [],
                    "reason": f"directly set to {validity}",
                }
            )
        belief.set_truth_value(validity)

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

    def enable_tracing(self):
        """Enable retraction cascade tracing."""
        self._tracing_enabled = True
        self._retraction_trace = []

    def get_retraction_chain(self) -> List[Dict]:
        """Return the accumulated retraction cascade trace.

        Each entry is:
            {trigger: str, retracted: [str], cascaded: [str], reason: str}
        """
        return list(self._retraction_trace)

    def explain_belief(self, belief_name: str) -> str:
        """Return a formatted explanation of a belief's justifications."""
        if belief_name not in self.beliefs:
            raise KeyError(f"Unknown belief: {belief_name}")

        belief = self.beliefs[belief_name]
        if not belief.justifications:
            return "No justification"

        explanations = []
        for j in belief.justifications:
            in_status = [f"{b.name} ({_validity_label(b.valid)})" for b in j.in_list]
            out_status = [f"{b.name} ({_validity_label(b.valid)})" for b in j.out_list]

            valid = all(b.valid for b in j.in_list) and all(
                not b.valid for b in j.out_list
            )
            # Tri-state verdict: an indeterminate premise makes the
            # justification « Unknown », only a refuting premise makes it
            # « Invalid » (#2094).
            refuted = any(b.valid is False for b in j.in_list) or any(
                b.valid is True for b in j.out_list
            )
            result = "Valid" if valid else ("Invalid" if refuted else "Unknown")

            block = (
                f"Justification:\n"
                f"  IN: {', '.join(in_status) or '-'}\n"
                f"  OUT: {', '.join(out_status) or '-'}\n"
                f"  Result: {result}\n"
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
            # Tri-state color: `None` (indeterminate) is grey, never red —
            # same display fix as explain_belief (#2094).
            if belief.non_monotonic:
                color = "orange"
            elif belief.valid is True:
                color = "green"
            elif belief.valid is False:
                color = "red"
            else:
                color = "grey"
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
