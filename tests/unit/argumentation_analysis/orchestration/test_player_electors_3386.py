"""#3386 (re-scope of 13/11) — electors built from the document's players.

The coordinator's decision, measured first: the virtue electors rank the
ARGUMENTS the quality phase scored, while the players the strategist read
(``strategic_read.players``, stances anchored per #3430) rank the FRAMINGS
in competition (``strategic_read.options``). The players' own profile is
the strategy engine the user named on 03/11 (« il ne vote qu'entre
réponses ») — the electors are the document's players, voting the ranking
the strategist recorded for each of them.

The free witnesses the decision asks for:

* the SYNTHETIC two-player profile: a stance shift changes the cast winner
  — the play machinery runs on player electors, and the recorded
  sensitivity says so (red on ``main``: the derivation does not exist
  there);
* a partial or absent ranking costs ITS player, never the play;
* through the REAL handler, the verdict carries the players' play under
  ``players_play`` — and carries nothing when no player has a full ranking.

The count the decision rules on (recorded cycle-6 states) is a producer
under ``scripts/panel/``, not a unit test: its measured figure —
``outcome_changed`` on 0 of 9 runnable documents — is why the record is an
ANNEX (measured fact on the state, never a rendered sentence) and the
render keeps reading only the virtue play.

No JVM, no LLM (client patched to None), privacy HARD (opaque player names
and framings only).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict
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

# The synthetic two-player read: two players, three framings, opposite
# orders — the smallest profile on which a stance shift can move anything.
_PLAYERS_READ: Dict[str, Any] = {
    "players": [
        {
            "name": "joueur_un",
            "role": "premier parti",
            "stance": "for",
            "interests": "opaque",
            "basis": "model_knowledge",
        },
        {
            "name": "joueur_deux",
            "role": "second parti",
            "stance": "against",
            "interests": "opaque",
            "basis": "model_knowledge",
        },
    ],
    "options": ["opt_a", "opt_b", "opt_c"],
    "preferences": {
        "joueur_un": ["opt_a", "opt_c", "opt_b"],
        "joueur_deux": ["opt_b", "opt_c", "opt_a"],
    },
    "status": "ok",
}


class TestTheDocumentPlayersBecomeElectors:
    def test_two_players_with_full_rankings_are_the_electors(self) -> None:
        """The derivation exists and builds the players' own profile: the
        options are the strategist's framings, the electors are the players
        in salience order, each voting its recorded ranking. Red on ``main``
        — the function is not there."""
        options, ballots, agents, derivable, reason = _derive_player_profile(
            _PLAYERS_READ
        )
        assert derivable, reason
        assert options == ["opt_a", "opt_b", "opt_c"]
        assert [a.name for a in agents] == ["joueur_un", "joueur_deux"]
        assert ballots == [
            ["opt_a", "opt_c", "opt_b"],
            ["opt_b", "opt_c", "opt_a"],
        ]

    def test_a_partial_ranking_costs_its_player_not_the_play(self) -> None:
        """Same rule as the strategist engine's ballot completion: a player
        whose recorded preference is not a full ranking over the options
        cannot be scored and is excluded — the OTHER players still play."""
        read = {
            "players": _PLAYERS_READ["players"]
            + [{"name": "joueur_trois", "role": "r", "stance": "uncommitted"}],
            "options": _PLAYERS_READ["options"],
            "preferences": {
                **_PLAYERS_READ["preferences"],
                "joueur_trois": ["opt_c"],  # partial: cannot be scored
                "absent_from_players": ["opt_c", "opt_b", "opt_a"],
            },
        }
        _options, _ballots, agents, derivable, reason = _derive_player_profile(read)
        assert derivable, reason
        assert [a.name for a in agents] == ["joueur_un", "joueur_deux"]

    def test_a_duplicate_name_is_claimed_at_first_sight_by_salience(self) -> None:
        """Review fix 5 — the docstring's contract (« duplicates keep the
        first ») is enforced at the NAME, in the strategist's salience
        order, before any ballot check: a first occurrence with a partial
        ballot costs its own player, never hands the seat to a later
        duplicate. The two placements are indistinguishable while the
        ballot is looked up BY NAME (a duplicate reads the same ranking);
        this pins the invariant for the day the ballot source becomes
        per-player."""
        read = {
            "players": [
                {"name": "joueur_un", "stance": "for"},
                {"name": "joueur_un", "stance": "for"},  # duplicate
                {"name": "joueur_deux", "stance": "against"},
                {"name": "joueur_trois", "stance": "uncommitted"},
            ],
            "options": ["opt_a", "opt_b"],
            "preferences": {
                "joueur_un": ["opt_a"],  # partial — costs its own player
                "joueur_deux": ["opt_b", "opt_a"],
                "joueur_trois": ["opt_a", "opt_b"],
            },
        }
        _options, _ballots, agents, derivable, reason = _derive_player_profile(read)
        assert derivable, reason
        assert [a.name for a in agents] == ["joueur_deux", "joueur_trois"]

    def test_under_two_full_rankings_is_honest_not_degraded_silently(self) -> None:
        """The honest-degraded contract mirrors the virtue derivation: the
        reason names what was missing, and ``derivable`` is False."""
        empty_cases: list[Dict[str, Any]] = [
            {"players": [], "options": [], "preferences": {}},  # doc_A's shape
            {**_PLAYERS_READ, "options": ["opt_a"]},  # one framing: no play
            {
                **_PLAYERS_READ,
                "preferences": {"joueur_un": ["opt_a"]},  # nobody full
            },
        ]
        for read in empty_cases:
            _o, _b, _a, derivable, reason = _derive_player_profile(read)
            assert not derivable
            assert reason


class TestAStanceShiftChangesTheCastWinner:
    def test_the_sensitivity_records_the_two_players_play(self) -> None:
        """The decision's own witness: on the synthetic two-player profile,
        a stance shift changes the cast winner (opt_a ↔ opt_b across the
        family). The sensitivity is the honest record — no uniform flip, so
        no rendered claim, which is exactly what the 0-of-9 count measured
        on the panel states."""
        options, ballots, agents, _derivable, _reason = _derive_player_profile(
            _PLAYERS_READ
        )
        declared = _aggregate_governance_votes(agents, options, ballots)
        # No Condorcet winner (every pair splits 1-1); the majority tier
        # decides the declared aggregate.
        assert declared["condorcet_winner"] is None
        assert declared["winner_basis"] == "majority"
        sensitivity = play_sensitivity(
            agents, options, ballots, _aggregate_governance_votes
        )
        # 2 seats × 3 stance shifts, measured: each player's own top wins
        # somewhere — the stance assignment is the fabricated input, and the
        # record says so instead of claiming a flip.
        assert (
            sensitivity["plays"],
            sensitivity["rotations"],
            sensitivity["shifts"],
        ) == (6, 2, 3)
        assert sensitivity["winners"] == [
            ["opt_a", "opt_b", "opt_a"],
            ["opt_b", "opt_a", "opt_b"],
        ]
        flat = {w for row in sensitivity["winners"] for w in row}
        assert flat == {"opt_a", "opt_b"}, "a stance shift changed no winner"
        assert sensitivity["stance_dependent"] is True
        assert sensitivity["uniform_winner"] is None
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


class TestTheVerdictCarriesThePlayersPlay:
    @pytest.mark.asyncio
    async def test_the_record_names_the_player_electors(self) -> None:
        output = await _handler_output(_PLAYERS_READ)
        verdict = output["governance_verdict"]
        play = verdict["players_play"]
        assert play["electors"] == ["joueur_un", "joueur_deux"]
        assert play["derivation_reason"] == (
            "2 player electors over 3 framings (strategist read)"
        )
        assert play["plays"] == 6
        assert play["stance_dependent"] is True
        assert play["outcome_changed"] is False
        # The annex discipline: the record exists, the RENDER does not read
        # it — the verdict's own winner stays the virtue vote's declared
        # aggregate, and no key here feeds a sentence.
        assert verdict["derivation"].startswith("formal-vote-aggregation")

    @pytest.mark.asyncio
    async def test_no_full_ranking_no_record(self) -> None:
        """The honest absence: a read whose players hold no full ranking
        (doc_A's empty shape) leaves the key out entirely — a missing
        measurement would be indistinguishable from a play that never
        ran."""
        output = await _handler_output(
            {"players": [], "options": [], "preferences": {}, "status": "no_llm"}
        )
        assert "players_play" not in output["governance_verdict"]

    @pytest.mark.asyncio
    async def test_mutation_without_the_derivation_the_record_is_gone(self) -> None:
        """The mutation control: the record comes from THIS derivation and
        nothing else — neuter it and the play is absent again."""
        from argumentation_analysis.orchestration import invoke_callables as ic

        original = ic._derive_player_profile
        ic._derive_player_profile = lambda read: ([], [], [], False, "neutered")
        try:
            output = await _handler_output(_PLAYERS_READ)
        finally:
            ic._derive_player_profile = original
        assert "players_play" not in output["governance_verdict"]

    @pytest.mark.asyncio
    async def test_a_degraded_virtue_vote_keeps_the_players_play(self) -> None:
        """Review fix 1 (14/11) — the champ-sans-lecteur repair, through the
        REAL handler then the REAL writer: on a degraded virtue profile
        (fewer than 2 evaluated arguments) the players still hold full
        rankings, the producer still records the play on the verdict — but
        no ``vote_result`` exists to carry it (it is built outside degraded
        only), and the deliberation's conflicts keep the writer running.
        The writer must read the annex off the verdict itself, or the
        measure lives nowhere."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_governance_to_state,
        )

        state = UnifiedAnalysisState(
            initial_text="filler text for the witness, no corpus content."
        )
        state.strategic_read = _PLAYERS_READ
        context: Dict[str, Any] = {
            "phase_extract_output": {"arguments": ["s1", "s2"]},
            "phase_quality_output": {"per_argument_scores": {}},  # degraded
            "_state_object": state,
        }
        with patch(
            "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
            return_value=(None, ""),
        ):
            output = await _invoke_governance("synthetic neutral text", context)
        # The producer's degraded shape, as measured: verdict degraded, play
        # recorded, no vote_result — and conflicts present, so the writer
        # records a decision on the conflict-resolution branch.
        assert output["governance_verdict"]["degraded"] is True
        assert "players_play" in output["governance_verdict"]
        assert "vote_result" not in output
        assert output["conflicts"]
        _write_governance_to_state(output, state, {})
        assert len(state.governance_decisions) == 1
        decision = state.governance_decisions[0]
        assert decision["players_play"]["electors"] == ["joueur_un", "joueur_deux"]
        # The decision fields stay honest: no vote decided anything — the
        # winner comes from the conflict-resolution branch, never from a
        # vote aggregate that does not exist.
        assert decision["winner_provenance"] == "conflict_resolution"


def test_the_writer_payload_keeps_the_players_play() -> None:
    """The writer is the only path to ``state.governance_decisions`` (the
    #3511(b) revision's finding 1 taught that lesson): the players' play
    must survive it, or the annex measure lives nowhere. The output shape
    is the PRODUCER's (``vote_result["results"]`` is the verdict itself,
    invoke_callables.py) — the writer reads it there, never recomputes."""
    from argumentation_analysis.orchestration.state_writers import (
        _write_governance_to_state,
    )

    verdict = {
        "degraded": False,
        "winner": "opt_a",
        "players_play": {"plays": 6, "electors": ["joueur_un", "joueur_deux"]},
    }
    state = UnifiedAnalysisState(initial_text="filler")
    _write_governance_to_state(
        {
            "governance_verdict": verdict,
            "governance_decided_firsthand": True,
            "vote_result": {
                "winner": "opt_a",
                "votes": ["opt_a", "opt_b"],
                "method": "formal-aggregation",
                "results": verdict,
            },
        },
        state,
        {},
    )
    assert len(state.governance_decisions) == 1
    assert state.governance_decisions[0]["players_play"]["electors"] == [
        "joueur_un",
        "joueur_deux",
    ]
    # And the control: a verdict without the play writes no phantom key.
    bare = {"degraded": False, "winner": "opt_a"}
    state2 = UnifiedAnalysisState(initial_text="filler")
    _write_governance_to_state(
        {
            "governance_verdict": bare,
            "governance_decided_firsthand": True,
            "vote_result": {
                "winner": "opt_a",
                "votes": ["opt_a"],
                "method": "formal-aggregation",
                "results": bare,
            },
        },
        state2,
        {},
    )
    assert len(state2.governance_decisions) == 1
    assert "players_play" not in state2.governance_decisions[0]
