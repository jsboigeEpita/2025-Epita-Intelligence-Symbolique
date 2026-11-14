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
from typing import Any

if str(Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.panel import _common as c  # noqa: E402

DEFAULT_STATES = c.RESULTS_ROOT / "panel_cycles" / "c6" / "states"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--states-dir",
        type=Path,
        default=DEFAULT_STATES,
        help="directory of recorded state_full_*.json dumps",
    )
    args = parser.parse_args()

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
        # Counts only: no player name, no framing string (privacy — the
        # winners ARE the framings, so they are never printed).
        print(
            f"{doc}: {len(agents)} player electors over {len(_options)} framings | "
            f"plays={sensitivity['plays']} "
            f"outcome_changed={bool(sensitivity['outcome_changed'])} "
            f"stance_dependent={bool(sensitivity['stance_dependent'])} "
            f"uniform_winner_present={sensitivity['uniform_winner'] is not None} "
            f"ballots_moved={sum(sensitivity['ballots_moved'])}"
        )

    print(
        f"TOTAL: outcome_changed on {changed} of {runnable} runnable documents "
        f"({len(docs) - runnable} not runnable); "
        f"stance_dependent on {stance_dependent} of {runnable}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
