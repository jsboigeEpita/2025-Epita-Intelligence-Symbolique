"""#2295 — the text-ordered sequence of argumentative moves.

The state flattens the argumentative construction: the trace orders
entries by execution clock, which is the phase DAG's order and says
nothing about the order the TEXT brings the moves. This module is the
deciding reader of the #2295 sequence fields (``move`` + ``anchor`` on
trace entries): it keeps only the anchored move-bearing entries and
orders them by their character position in the source text.

``order_differs`` is the honest verdict the DoD asks for: whether the
text order differs from the analysis (append/timestamp) order. None when
fewer than two anchored moves — an order that cannot be compared is not
compared (tri-state #1019).

Privacy HARD: everything rendered from here is opaque ids, closed
vocabulary and integers — no source text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

# French labels for the conducted prompt — Walton-Krabbe vocabulary.
MOVE_LABELS_FR = {
    "assert": "pose",
    "concede": "concède",
    "retract": "se rétracte",
    "challenge": "conteste",
    "withdraw": "retire",
}


@dataclass(frozen=True)
class TraceMove:
    """One anchored argumentative move, at its text position."""

    move: str
    offset: int
    length: int
    arg_ref: str  # opaque id ("arg_7"); "" when the entry references nothing


@dataclass(frozen=True)
class TextSequence:
    """The move sequence ordered by TEXT position (not execution clock)."""

    moves: Tuple[TraceMove, ...]
    # None when fewer than two anchored moves (no comparable order).
    order_differs: Optional[bool]


def collect_text_sequence(state: Any) -> Optional[TextSequence]:
    """Collect the anchored move-bearing trace entries, ordered by text.

    Returns None when the state carries no anchored move at all (honest
    absence — an uninstrumented run renders no sequence, never a
    fabricated one). Entries without an anchor never enter the sequence:
    an absent anchor is the tri-state "no anchor available", NOT offset 0.
    """
    trace = getattr(state, "analysis_trace", None)
    if not isinstance(trace, list):
        return None
    anchored: List[TraceMove] = []
    for e in trace:
        if not isinstance(e, dict) or not e.get("move"):
            continue
        a = e.get("anchor")
        if not isinstance(a, dict) or not isinstance(a.get("offset"), int):
            continue
        reacts = e.get("reacts_to")
        arg_ref = ""
        if isinstance(reacts, list) and reacts:
            arg_ref = str(reacts[0])
        anchored.append(
            TraceMove(
                move=str(e["move"]),
                offset=a["offset"],
                length=int(a.get("length", 0)),
                arg_ref=arg_ref,
            )
        )
    if not anchored:
        return None
    by_text = sorted(anchored, key=lambda m: m.offset)
    order_differs: Optional[bool] = None
    if len(by_text) >= 2:
        order_differs = [m.arg_ref for m in by_text] != [m.arg_ref for m in anchored]
    return TextSequence(moves=tuple(by_text), order_differs=order_differs)
