"""#3692 — the positive control of the #3386 count.

The count the #3386 re-open trigger watches is ``outcome_changed`` from
:func:`play_sensitivity` on the players' profile: 0 of 9 runnable documents
at cycle 6 and 0 of 8 at cycle 7 (the 14/11 annex), and 0 of 143 runnable
documents over 17 cycles (the 25/11 re-count, State on #3386). A zero counts
only once the same instrument has returned a positive
(``docs/guides/MEASUREMENT_DISCIPLINE.md`` §1.1), and until this file no
tracked test ever made the predicate say True: the sibling tests pin the
declared winner, the absence of a uniform flip and the honest absences,
never a flip.

The planted profile is synthetic — opaque labels, no document, no LLM, no
JVM — and it runs through the three seams the producer uses
(``_derive_player_profile`` → ``_aggregate_governance_votes`` →
``play_sensitivity``), then through the real handler (``_invoke_governance``,
client patched to None) so the record itself is pinned, not just the library
call.

The shape, in counts: nine electors over seven framings. Four electors rank
``opt_x`` first and ``opt_w`` second; five electors each rank a different
``opt_s*`` first, then ``opt_w``, then ``opt_x``. ``opt_w`` beats every
other framing on a majority of ballots — the strict Condorcet winner — and
nobody ranks it first. It is the smallest flip of the construction sweep
recorded on #3692 (9 x 7); it is not proven minimal, and restating the
trigger itself stays the coordinator's decision (``Refs #3692``).

What the flip can and cannot mean is pinned too: ``outcome_changed`` needs a
UNIFORM family (``uniform_winner`` is that winner, else ``None``), so it can
never be True together with ``stance_dependent``; and ``ballots_moved``
lists the electors that moved in EVERY play — empty here, on a flip, which
is why the panel's zeros on that field were never read as "nothing moved".
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from argumentation_analysis.agents.core.governance.coalition_play import (
    play_sensitivity,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.invoke_callables import (
    _aggregate_governance_votes,
    _derive_player_profile,
    _invoke_governance,
)


def _planted_read(x_firsts: int, singles: int) -> Dict[str, Any]:
    """The planted strategist read: ``x_firsts`` electors top ``opt_x`` with
    ``opt_w`` second; ``singles`` electors each top a distinct ``opt_s*`` with
    ``opt_w`` second and ``opt_x`` third. Every ballot is a FULL ranking over
    the options (the derivation's own rule: a partial ranking costs its
    player, never the play) — a planted profile with an option left out of
    some ballots would let ``condorcet_winner`` crown an option absent from
    most ballots, which is a malformed input, not a witness."""
    options = ["opt_w", "opt_x"] + [f"opt_s{j}" for j in range(singles)]
    rest = options[2:]
    players: List[Dict[str, str]] = []
    preferences: Dict[str, List[str]] = {}
    for i in range(x_firsts):
        name = f"joueur_{i}"
        players.append({"name": name, "role": "parti", "stance": "uncommitted"})
        preferences[name] = ["opt_x", "opt_w"] + rest
    for j in range(singles):
        name = f"joueur_{x_firsts + j}"
        top = f"opt_s{j}"
        players.append({"name": name, "role": "parti", "stance": "uncommitted"})
        preferences[name] = [top, "opt_w", "opt_x"] + [o for o in rest if o != top]
    return {
        "players": players,
        "options": options,
        "preferences": preferences,
        "status": "ok",
    }


def _profile(x_firsts: int, singles: int) -> Any:
    options, ballots, agents, derivable, reason = _derive_player_profile(
        _planted_read(x_firsts, singles)
    )
    assert derivable, reason
    return options, ballots, agents


def _aggregate_without_the_condorcet_tier(
    agents: List[Any], options: List[str], ballots: List[List[str]]
) -> Dict[str, Any]:
    """The production aggregate with its first tier neutralised — the control
    of :meth:`TestWhatTheFlipNeeds.test_without_the_condorcet_tier_no_flip`:
    the flip hinges on the only tier that can declare a winner nobody ranks
    first (``majority_voting`` returns the most common first-place vote)."""
    out = dict(_aggregate_governance_votes(agents, options, ballots))
    if out.get("winner_basis") == "condorcet":
        per_method = out.get("winners_per_method") or {}
        fallback = "majority" if per_method.get("majority") else "plurality"
        out["winner"] = per_method.get(fallback)
        out["winner_basis"] = fallback if out["winner"] else None
    return out


class TestThePlantedProfile:
    def test_the_declared_winner_is_a_condorcet_winner_nobody_ranks_first(
        self,
    ) -> None:
        """The precondition of any flip: the declared aggregate is decided by
        the Condorcet tier and its winner holds zero first-place votes — a
        majority-tier winner is always some elector's first vote, so this is
        the only region where ``outcome_changed`` is reachable at all."""
        options, ballots, agents = _profile(4, 5)
        assert (len(agents), len(options)) == (9, 7)
        declared = _aggregate_governance_votes(agents, options, ballots)
        assert declared["winner"] == "opt_w"
        assert declared["winner_basis"] == "condorcet"
        assert declared["condorcet_winner"] == "opt_w"
        assert sum(1 for b in ballots if b[0] == "opt_w") == 0


class TestThePlayFamilyChangesTheOutcome:
    def test_every_play_of_the_family_elects_the_same_other_framing(self) -> None:
        """The positive the count has never returned on a recorded cycle:
        all 27 plays — 9 seat rotations x 3 stance shifts — elect ``opt_x``
        while the declared winner is ``opt_w``, so ``outcome_changed`` is
        True. Unanimity is a REQUIREMENT of the predicate, not a detail: a
        flip that varies with the seat order or the shift is not a flip, so
        ``stance_dependent`` is False here by construction."""
        options, ballots, agents = _profile(4, 5)
        sensitivity = play_sensitivity(
            agents, options, ballots, _aggregate_governance_votes
        )
        assert (
            sensitivity["plays"],
            sensitivity["rotations"],
            sensitivity["shifts"],
        ) == (27, 9, 3)
        assert sensitivity["winner_declared"] == "opt_w"
        flat = {w for row in sensitivity["winners"] for w in row}
        assert flat == {"opt_x"}
        assert sensitivity["uniform_winner"] == "opt_x"
        assert sensitivity["outcome_changed"] is True
        assert sensitivity["stance_dependent"] is False
        # The stable-mover reading, pinned ON A FLIP: every elector is
        # flexible in exactly one stance shift, so no elector moves in every
        # play and ``ballots_moved`` is empty while the outcome changed —
        # the field is an intersection, never a sum (R1219's caveat).
        assert sensitivity["ballots_moved"] == []


class TestWhatTheFlipNeeds:
    def test_without_the_condorcet_tier_no_flip(self) -> None:
        """Control (a): neuter the tier that can crown a zero-first winner
        and the same profile declares ``opt_x`` by majority — the plays then
        split over several framings, no uniform winner exists, and the
        predicate reads False. The flip is a property of the declared
        aggregate and the casts together, not of the ballots alone."""
        options, ballots, agents = _profile(4, 5)
        control = _aggregate_without_the_condorcet_tier
        declared = control(agents, options, ballots)
        assert declared["winner"] == "opt_x"
        assert declared["winner_basis"] == "majority"
        sensitivity = play_sensitivity(agents, options, ballots, control)
        assert sensitivity["uniform_winner"] is None
        assert sensitivity["stance_dependent"] is True
        assert sensitivity["outcome_changed"] is False

    def test_one_elector_fewer_in_the_same_construction_does_not_flip(
        self,
    ) -> None:
        """Control (b) — the boundary. One elector and one framing fewer
        (3 + 4 instead of 4 + 5) still lands in the zero-first Condorcet
        region, but the play family splits: a flexible elector copying a
        single-first framing's top gives it enough firsts to win that cast,
        so no uniform winner exists and the predicate reads False. 9 x 7 is
        the smallest flipping shape of this construction, not a generic
        threshold."""
        options, ballots, agents = _profile(3, 4)
        assert (len(agents), len(options)) == (7, 6)
        declared = _aggregate_governance_votes(agents, options, ballots)
        assert declared["winner"] == "opt_w"
        assert declared["winner_basis"] == "condorcet"
        assert sum(1 for b in ballots if b[0] == "opt_w") == 0
        sensitivity = play_sensitivity(
            agents, options, ballots, _aggregate_governance_votes
        )
        assert sensitivity["uniform_winner"] is None
        assert sensitivity["stance_dependent"] is True
        assert sensitivity["outcome_changed"] is False


async def _handler_output(strategic_read: Dict[str, Any]) -> Dict[str, Any]:
    """Run the REAL producer (no LLM) with a state carrying the read."""
    state = UnifiedAnalysisState(
        initial_text="filler text for the witness, no corpus content."
    )
    state.strategic_read = strategic_read
    context: Dict[str, Any] = {
        "phase_extract_output": {"arguments": ["s1", "s2"]},
        "phase_quality_output": {
            "per_argument_scores": {
                "arg_1": {"scores_par_vertu": {"vertu_a": 2.0}},
                "arg_2": {"scores_par_vertu": {"vertu_a": 1.0}},
            }
        },
        "_state_object": state,
    }
    with patch(
        "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
        return_value=(None, ""),
    ):
        return await _invoke_governance("synthetic neutral text", context)


class TestTheProducerRecordsIt:
    @pytest.mark.asyncio
    async def test_the_players_play_carries_the_flip_not_the_verdict(self) -> None:
        """The record the re-open trigger reads is the producer's own: on the
        planted read, ``players_play`` carries the flip (uniform ``opt_x``
        against a declared ``opt_w``), while the verdict's winner stays the
        virtue vote's — the annex discipline the 14/11 decision set, with the
        predicate now measured True on the same record a future cycle reads."""
        output = await _handler_output(_planted_read(4, 5))
        play = output["governance_verdict"]["players_play"]
        assert play["outcome_changed"] is True
        assert play["uniform_winner"] == "opt_x"
        assert play["winner_declared"] == "opt_w"
        assert play["stance_dependent"] is False
        assert play["electors"] == [f"joueur_{i}" for i in range(9)]
        assert play["derivation_reason"] == (
            "9 player electors over 7 framings (strategist read)"
        )
        # The flip does not become the verdict: the winner the pipeline
        # renders comes from the virtue aggregate, a different population.
        assert output["governance_verdict"]["winner"] != play["uniform_winner"]
