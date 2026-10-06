"""#2967 — the units a writer is asked to DISCUSS reach it whole.

A fixed 220-character head cut showed the Act II narrative and the
deep-synthesis briefing the *setup* of a long unit and dropped what it
*concludes*: on the 06/10 authorized pass, the governance winner kept 31 %
of its text and its operative clause (past character 340) never reached any
writer (#1914).

The budget becomes an ALLOCATION: cited units (the ones a writer is asked
to discuss — attack targets, counter-argument targets, the governance
winner) get their full text up to ``CITED_UNIT_TEXT_CAP``; every other unit
keeps the short cap, so the prompt does not grow with N.

Calibration of the cap (doc_A, 94 units, measured by the coordinator on
the saved state — no saved state lives on a worker seat): median 422,
71/94 longer than 220 (the 75th percentile sits above 220), longest 2 142.
The exact p90 is pending (asked of the coordinator); 2 000 covers the
issue's witness (a cited 700-character unit, whole) with wide margin and
stays under the observed max.

This module carries no heavy imports on purpose: ``deep_synthesis_agent``
imports it, and it must not pull the narrative plugins in.
"""

from __future__ import annotations

from typing import Any, Optional, Set

# Budget for a CITED unit's text — see the module docstring for the
# calibration and what remains pending.
CITED_UNIT_TEXT_CAP = 2000

# Visible cut marker — the same convention the Act II plugin already used,
# so a reader of either surface meets one marker, and no cut is silent
# (#2967 Expected 3: the briefing used to cut with a bare slice).
CUT_MARKER = " […]"

# A sentence boundary is only used when it preserves at least this share of
# the budget — otherwise a lone early period would throw away almost the
# whole budget to honour the boundary.
_MIN_BOUNDARY_SHARE = 0.5

_SENTENCE_ENDS = (".", "!", "?", "…")


def truncate_at_boundary(text: Any, cap: int, marker: str = CUT_MARKER) -> str:
    """Cap length, cutting at a boundary — never mid-word (#2967 Expected 4).

    Preference order: the last sentence boundary inside the head (if it
    keeps at least half the budget), then the last word boundary, then a
    hard cut when the head carries no boundary at all. Every cut carries
    the visible marker; text within the cap is returned untouched.
    """
    if not text:
        return ""
    s = str(text).strip()
    if len(s) <= cap:
        return s
    head = s[:cap]
    sent = max(head.rfind(end) for end in _SENTENCE_ENDS)
    if sent >= int(cap * _MIN_BOUNDARY_SHARE):
        # keep the sentence delimiter — cutting AT it must not swallow it
        return head[: sent + 1].rstrip() + marker
    word = head.rfind(" ")
    if word > 0:
        return head[:word].rstrip() + marker
    return head.rstrip() + marker


def governance_winner_id(state: Any) -> Optional[str]:
    """The last non-trivial governance decision's winner.

    Mirrors act2's ``_collect_governance`` for the single question "who
    wins" (same trivial guard: a winner needs a method, a value, and not
    the placeholder). Kept here so consumers that must not import the
    narrative plugins (the deep-synthesis briefing) read the same answer.
    """
    decisions = getattr(state, "governance_decisions", None)
    if not isinstance(decisions, list):
        return None
    winner: Optional[str] = None
    for d in decisions:
        if not isinstance(d, dict):
            continue
        method = str(d.get("method", "")).strip()
        w = str(d.get("winner", "")).strip()
        if not method or not w or w == "N/A":
            continue
        winner = w
    return winner


def cited_unit_ids(state: Any) -> Set[str]:
    """Ids of the units a writer is asked to DISCUSS (#2967 Expected 2).

    Three populations, all opaque ``arg_N`` ids already in the state:
    attack targets (a fallacy names its ``target_argument_id``),
    counter-argument targets (``target_arg_id``), and the governance
    winner. On doc_A the ranked-salience items overlap these three
    populations (issue #2965's measured table); #2965's Act III slice
    extends this set when it wires the excerpts to the citations.
    """
    ids: Set[str] = set()
    fallacies = getattr(state, "identified_fallacies", None)
    if isinstance(fallacies, dict):
        for fdata in fallacies.values():
            if isinstance(fdata, dict):
                tid = str(fdata.get("target_argument_id") or "").strip()
                if tid:
                    ids.add(tid)
    counters = getattr(state, "counter_arguments", None)
    if isinstance(counters, list):
        for ca in counters:
            if isinstance(ca, dict):
                tid = str(ca.get("target_arg_id") or "").strip()
                if tid:
                    ids.add(tid)
    winner = governance_winner_id(state)
    if winner:
        ids.add(winner)
    return ids
