"""JVM-free structural insights over the bipolar SUPPORT relation.

The bipolar axis's singular contribution (issue #1645, section A) is the support
relation, which makes two properties computable that no attack-only framework
(Dung) and no LLM fallacy detector can express:

1. support cycles — circular authority: A backs B which backs A, with no anchor
   outside the loop;
2. articulation points (future work) — removing one argument collapses the
   support of others.

These are pure graph properties of the ``supports`` edge list. They require NO
JVM and NO Tweety reasoner — the framework object ``BipolarHandler`` builds is
not needed. Computing them here keeps the insight available on the
honest-degraded (JVM-absent) path, where the handler never runs (#1670/#1677).

Verified firsthand (#1645 E pass 1): before this module, a planted support
cycle ``prop_alpha <-> prop_beta`` was rendered by ``_bipolar_finding`` as two
innocuous ``appuie`` pairs — byte-for-byte identical to an acyclic control pair.
The cycle was structurally present in the input and invisible in the prose
(anti-théâtre #1019). This module makes it nameable.
"""

from __future__ import annotations

from typing import Dict, List, Sequence

# A support edge is a [source, target] pair of opaque argument identifiers.
SupportEdge = Sequence[str]


def _build_adjacency(supports: Sequence[SupportEdge]) -> Dict[str, List[str]]:
    """Build an adjacency list (source -> targets) from [src, tgt] edges.

    Every node mentioned (as source or target) gets a key, so isolated targets
    and cycle-closing nodes are represented. Malformed edges (wrong arity,
    empty identifiers) are dropped — they carry no structural meaning.
    """
    adj: Dict[str, List[str]] = {}
    for edge in supports:
        if len(edge) != 2:
            continue
        src = str(edge[0]).strip()
        tgt = str(edge[1]).strip()
        if not src or not tgt:
            continue
        adj.setdefault(src, []).append(tgt)
        adj.setdefault(tgt, [])
    return adj


def detect_support_cycles(supports: Sequence[SupportEdge]) -> List[List[str]]:
    """Groups of arguments locked in a mutual-support cycle (circular authority).

    A group is a **non-trivial strongly connected component** of the support
    digraph: size >= 2, or a single node with a self-loop. Every node in such a
    component participates in a cycle — it is supported (directly or
    transitively) by something it itself supports, with nothing outside the loop
    grounding it. That is the structural signature of *circular authority*,
    invisible to attack-only frameworks (the argument is unattacked, so Dung
    accepts it) and to LLM fallacy detection (the vocabulary "support cycle"
    is not in the fallacy register).

    Pure graph theory — iterative Tarjan SCC, no recursion, no JVM, no reasoner.
    Returns one sorted node-list per cyclic group; the list of groups is itself
    sorted, so the result is deterministic for a given input.

    Examples:
        >>> detect_support_cycles([["a", "b"], ["b", "a"]])
        [['a', 'b']]
        >>> detect_support_cycles([["a", "b"], ["b", "c"], ["c", "a"]])
        [['a', 'b', 'c']]
        >>> detect_support_cycles([["a", "b"]])
        []
        >>> detect_support_cycles([["a", "a"]])
        [['a']]
    """
    adj = _build_adjacency(supports)

    # Iterative Tarjan strongly-connected-components.
    index_counter = [0]
    stack: List[str] = []
    on_stack: set[str] = set()
    index_of: Dict[str, int] = {}
    lowlink: Dict[str, int] = {}
    result: List[List[str]] = []

    for root in adj:
        if root in index_of:
            continue
        # Iterative DFS over two parallel stacks: work_nodes holds the path of
        # nodes being explored; work_idx holds the next-neighbor index to scan
        # for each. (Parallel stacks keep the types homogeneous for mypy.)
        work_nodes: List[str] = [root]
        work_idx: List[int] = [0]
        while work_nodes:
            v = work_nodes[-1]
            pi = work_idx[-1]
            if pi == 0:
                index_of[v] = index_counter[0]
                lowlink[v] = index_counter[0]
                index_counter[0] += 1
                stack.append(v)
                on_stack.add(v)
            neighbors = adj[v]
            recursed = False
            i = pi
            while i < len(neighbors):
                w = neighbors[i]
                if w not in index_of:
                    work_idx[-1] = i + 1
                    work_nodes.append(w)
                    work_idx.append(0)
                    recursed = True
                    break
                if w in on_stack:
                    lowlink[v] = min(lowlink[v], index_of[w])
                i += 1
            if recursed:
                continue
            # All neighbors scanned: is v an SCC root?
            if lowlink[v] == index_of[v]:
                component: List[str] = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    component.append(w)
                    if w == v:
                        break
                # Non-trivial SCC: a real cycle. A lone node counts only if it
                # self-supports (v in its own out-neighbors).
                if len(component) >= 2 or (
                    len(component) == 1 and component[0] in adj.get(component[0], [])
                ):
                    result.append(sorted(component))
            work_nodes.pop()
            work_idx.pop()
            if work_nodes:
                parent = work_nodes[-1]
                lowlink[parent] = min(lowlink[parent], lowlink[v])
    result.sort()
    return result
