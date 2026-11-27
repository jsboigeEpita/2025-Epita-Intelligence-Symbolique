"""#3386 (re-scope of 13/11) — the count that decided the annex.

The coordinator's rule: electors are built from the document's OWN players
(``strategic_read``), each voting its recorded ranking of the strategist's
framings, and the count is the documents on which a coalition of those
electors changes the outcome (``play_sensitivity`` → ``outcome_changed``).
At least one means the play is wired into the render; zero means annex —
the machinery runs and is recorded on the state, but no sentence reads it.

This instrument takes the count through the PRODUCTION seams — the same
``_derive_player_profile`` the governance phase calls, the same
``play_sensitivity`` + ``_aggregate_governance_votes`` — so the figure the
audit row carries is the one the wired pipeline produces, not a re-derivation
that could drift from it.

#3692 — the counter also prints, per document, how many ballots rank the
DECLARED winner first, and its summary names how many documents have none.
That count is the reachable half of the #3386 re-open trigger: the play family
can only change the outcome through a declared winner nobody ranks first
(``uniform_winner`` is the same other framing under every play), and on the
recorded population that never occurred (the declared winner holds 1 to 6
first places on 143 of 143 documents). A document whose declared winner holds
0 is inside the envelope the pipeline does produce, so the trigger can fire
without waiting for the planted 9 x 7 profile. The count is a number, never a
framing name.

Privacy: stdout carries counts and the opaque state ids ONLY. The players'
names and the framings they rank are corpus-derived French; none of them
reaches any output this script can produce.

Usage (repo root):

    python scripts/panel/count_player_play_3386.py [--states-dir DIR]

Default states dir: the recorded cycle-6 states.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, List, Optional, Sequence

if str(Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.panel import _common as c  # noqa: E402

DEFAULT_STATES = c.RESULTS_ROOT / "panel_cycles" / "c6" / "states"


def declared_first_places(
    winner: Any, ballots: Sequence[Sequence[str]]
) -> Optional[int]:
    """How many ballots rank the declared winner FIRST — a count, never a name.

    #3692: this is the reachable signal the #3386 re-open trigger gains. On the
    recorded population the declared winner holds at least one first place on
    143 of 143 documents (25/11 State on #3386), which is WHY the play family
    never changes the outcome there: a flip needs a declared winner nobody
    ranks first, and the profile's first places are what rule that shape out.
    A document whose count reads 0 is inside the envelope the pipeline can
    produce, so the trigger can fire without waiting for the planted profile.

    ``None`` when no winner is declared: the signal is not defined there, and a
    0 would read as "a winner nobody ranks first".
    """
    if winner is None:
        return None
    return sum(1 for ballot in ballots if ballot and ballot[0] == winner)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--states-dir",
        type=Path,
        default=DEFAULT_STATES,
        help="directory of recorded state_full_*.json dumps",
    )
    args = parser.parse_args(argv)

    # Imported here so ``--help`` (and any import of this module by tooling)
    # never pays the orchestration import surface.
    from argumentation_analysis.agents.core.governance.coalition_play import (
        play_sensitivity,
    )
    from argumentation_analysis.orchestration.invoke_callables import (
        _aggregate_governance_votes,
        _derive_player_profile,
    )

    docs = c.docs_in(args.states_dir)
    if not docs:
        print(f"no state_full_*.json under {args.states_dir}")
        return 1

    runnable = 0
    changed = 0
    stance_dependent = 0
    first_places: List[Optional[int]] = []
    for doc in docs:
        state = c.load_state(args.states_dir, doc)
        read: Any = state.get("strategic_read")
        _options, _ballots, agents, derivable, reason = _derive_player_profile(read)
        if not derivable:
            print(f"{doc}: not runnable ({reason})")
            continue
        runnable += 1
        sensitivity = play_sensitivity(
            agents, _options, _ballots, _aggregate_governance_votes
        )
        changed += bool(sensitivity["outcome_changed"])
        stance_dependent += bool(sensitivity["stance_dependent"])
        firsts = declared_first_places(sensitivity["winner_declared"], _ballots)
        first_places.append(firsts)
        # Counts only: no player name, no framing string (privacy — the
        # winners ARE the framings, so they are never printed).
        print(
            f"{doc}: {len(agents)} player electors over {len(_options)} framings | "
            f"plays={sensitivity['plays']} "
            f"outcome_changed={bool(sensitivity['outcome_changed'])} "
            f"stance_dependent={bool(sensitivity['stance_dependent'])} "
            f"uniform_winner_present={sensitivity['uniform_winner'] is not None} "
            f"declared_winner_firsts={'-' if firsts is None else firsts} "
            f"ballots_moved={sum(sensitivity['ballots_moved'])}"
        )

    decided = [value for value in first_places if value is not None]
    zero_firsts = sum(1 for value in decided if value == 0)
    print(
        f"TOTAL: outcome_changed on {changed} of {runnable} runnable documents "
        f"({len(docs) - runnable} not runnable); "
        f"stance_dependent on {stance_dependent} of {runnable}; "
        f"declared winner with 0 first-place votes on {zero_firsts} of "
        f"{len(decided)} documents that declare one "
        f"({runnable - len(decided)} without a declared winner)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
