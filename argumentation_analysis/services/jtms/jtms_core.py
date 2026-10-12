"""
Core JTMS implementation — integrated from student project 1.4.1-JTMS.

This module provides a Justification-based Truth Maintenance System (JTMS)
with support for non-monotonic reasoning via strongly-connected component
detection.

Original author: @ThomasLeguere (student project 1.4.1-JTMS)
Integrated into argumentation_analysis framework.
"""

import importlib.util
import logging
from typing import Dict, List, Optional, Set

logger = logging.getLogger("JTMS")

# Optional visualization deps — graceful degradation
try:
    import networkx as nx

    _HAS_NETWORKX = True
except ImportError:
    _HAS_NETWORKX = False
    logger.debug("networkx not available, SCC detection disabled")

# ``pyvis`` is imported at call time in ``JTMS.visualize``: importing it here
# dragged IPython (111 modules) and jsonpickle into every process that touched
# the JTMS core, ``api.main`` included (#2855). ``_HAS_PYVIS`` stays a cheap
# find_spec hint for callers that want to skip early — the authoritative check
# is the call-time import, which also survives a broken install.
try:
    _HAS_PYVIS = importlib.util.find_spec("pyvis") is not None
except (ImportError, ValueError):
    _HAS_PYVIS = False


def _pyvis_network():
    """Resolve ``pyvis.network.Network`` at call time (#2855).

    Importing pyvis at module level dragged IPython and jsonpickle into every
    process that touched the JTMS core. Kept as a module-level seam so tests
    can substitute a fake without pyvis installed.
    """
    from pyvis.network import Network

    return Network


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
        # Belief-level assignment, kept for API compatibility. The
        # network-level entry point is ``JTMS.set_belief_validity``, which
        # records the assignment as a fact and re-runs the well-founded
        # labeling (#3018); a direct call here bypasses that bookkeeping and
        # the next structural change realigns the labels.
        self.valid = value
        self.propagate()

    def compute_truth_statement(self):
        # #3013: ``non_monotonic`` is an SCC marker, not a label override. The
        # old branch forced ``None`` without looking at the justifications —
        # so a belief with an unconditional justification stayed unknown on an
        # odd loop — and returned before the change-propagation below, leaving
        # dependents on a stale label. A belief is True iff some justification
        # is satisfied, loop or no loop; the flag only marks the topology.
        # #3018: this stays the LOCAL satisfaction operator — idempotent at
        # the well-founded fixpoint the network computes after every
        # structural change; it no longer decides the final labels.
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
        # #3018: the retraction-cascade trace moved to
        # ``JTMS.set_belief_validity`` — labels are produced by the global
        # well-founded computation, so the cascade is traced by diffing the
        # labels around it, not by intercepting this local walk.
        self._propagating = True
        try:
            for justification in self.implications:
                justification.conclusion.compute_truth_statement()
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
        # Direct assignments (set_belief_validity) — the facts the
        # well-founded labeling iterates from (#3018).
        self._facts: Dict[str, bool] = {}

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
        self._facts.pop(belief_name, None)
        self.update_non_monotonic_beliefs()
        self._recompute_well_founded()

    def set_belief_validity(self, belief_name: str, validity: Optional[bool]):
        """Set the truth value of a belief as a fact and relabel globally.

        The assignment is recorded in ``_facts`` and the whole network is
        relabeled by the well-founded computation (#3018): every label comes
        from the same fixpoint, whatever the order the justifications were
        added in.
        """
        if belief_name not in self.beliefs:
            raise KeyError(f"Unknown belief: {belief_name}")
        belief = self.beliefs[belief_name]
        old_labels = {name: b.valid for name, b in self.beliefs.items()}
        tracing_entry = None
        if self._tracing_enabled and belief.valid is True and validity is not True:
            tracing_entry = {
                "trigger": belief_name,
                "retracted": [belief_name],
                "cascaded": [],
                "reason": f"directly set to {validity}",
            }
            self._retraction_trace.append(tracing_entry)
        if validity is None:
            self._facts.pop(belief_name, None)
        else:
            self._facts[belief_name] = validity
        self._recompute_well_founded()
        if tracing_entry is not None:
            self._trace_cascaded_drops(belief, old_labels)

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
        self._recompute_well_founded()

    def update_non_monotonic_beliefs(self) -> None:
        """Mark beliefs on a cycle passing through at least one out-list edge.

        #3018: the flag is exact — recomputed from scratch on every call
        (marks left over from an earlier topology are cleared), a positive
        cycle (in-list edges only) is monotone and stays unflagged, and a
        self-loop counts when its edge is an out-list edge (``a ← ¬a``).
        Every member of such a cycle lies on it, so the whole SCC is marked.
        """
        for belief in self.beliefs.values():
            belief.non_monotonic = False
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
            members = set(scc)
            has_out_edge = any(
                premise.name in members
                for name in members
                if name in self.beliefs
                for j in self.beliefs[name].justifications
                for premise in j.out_list
            )
            if has_out_edge:
                for belief_name in members:
                    if belief_name in self.beliefs:
                        self.beliefs[belief_name].non_monotonic = True

    def _recompute_well_founded(self) -> None:
        """Relabel every belief by the well-founded computation (#3018).

        Van Gelder's alternating fixpoint, on the rule reading the JTMS
        already gives its out-lists (``not p`` holds unless ``p`` is True):
        ``T`` is the least set of beliefs rule derivation supports, ``S``
        the greatest unfounded set — beliefs no rule can still support,
        where a belief's own loop does not count as support. Facts — direct
        assignments — seed the iteration and are exempt from ``S``. At the
        fixpoint:
        ``True`` for members of ``T``, ``False`` only for False facts, and
        ``None`` for the rest — one labeling, whatever the order the
        justifications were added in.
        """
        facts = {name for name in self._facts if name in self.beliefs}
        facts_true = {name for name in facts if self._facts[name] is True}
        facts_false = facts - facts_true
        s = set(facts_false)
        while True:
            t = self._least_supported_model(facts_true, s)
            s_next = facts_false | self._unsupported(t, facts_true, facts)
            if s_next == s:
                break
            s = s_next
        for name, belief in self.beliefs.items():
            if name in facts_true:
                belief.valid = True
            elif name in facts_false:
                belief.valid = False
            elif name in t:
                belief.valid = True
            else:
                belief.valid = None

    def _least_supported_model(self, seed: Set[str], s: Set[str]) -> Set[str]:
        """Least set containing ``seed`` closed under rule firing: a rule
        fires when every in-premise is in the set and every out-premise is
        in ``s`` (assumed not-true)."""
        t = set(seed)
        changed = True
        while changed:
            changed = False
            for name, belief in self.beliefs.items():
                if name in t:
                    continue
                for justification in belief.justifications:
                    if all(p.name in t for p in justification.in_list) and all(
                        p.name in s for p in justification.out_list
                    ):
                        t.add(name)
                        changed = True
                        break
        return t

    def _unsupported(
        self, t: Set[str], facts_true: Set[str], facts: Set[str]
    ) -> Set[str]:
        """Beliefs (facts excluded) outside the least possibly-supported
        set: the least set containing the True facts and closed under rules
        that could still fire — every in-premise possibly supported, no
        out-premise already derived True in ``t``. A belief whose only
        support runs through itself never enters it, so self-support counts
        as no support (Van Gelder's greatest unfounded set). The one-step
        reading this replaces missed exactly that clause: it required every
        justification to be already dead, so a self-supporting loop kept
        its members out of ``S`` and a rule reading ``not loop`` never
        fired (#3020 review)."""
        possible = set(facts_true)
        changed = True
        while changed:
            changed = False
            for name, belief in self.beliefs.items():
                if name in possible or name in facts:
                    continue
                for justification in belief.justifications:
                    if all(
                        p.name in possible for p in justification.in_list
                    ) and not any(p.name in t for p in justification.out_list):
                        possible.add(name)
                        changed = True
                        break
        return {
            name for name in self.beliefs if name not in facts and name not in possible
        }

    def _trace_cascaded_drops(
        self, trigger: Belief, old_labels: Dict[str, Optional[bool]]
    ) -> None:
        """Depth-first post-order walk from the retracted belief: every
        conclusion whose label dropped from True is recorded as cascaded —
        the same order the propagation cascade used to produce (deepest
        first)."""
        cascaded = self._retraction_trace[-1]["cascaded"]
        visited = set()

        def visit(belief: Belief) -> None:
            visited.add(belief.name)
            for justification in belief.implications:
                conclusion = justification.conclusion
                if conclusion.name in visited:
                    continue
                visit(conclusion)
                if (
                    old_labels.get(conclusion.name) is True
                    and conclusion.valid is not True
                ):
                    cascaded.append(conclusion.name)

        visit(trigger)

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
        try:
            Network = _pyvis_network()
        except ImportError:
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
