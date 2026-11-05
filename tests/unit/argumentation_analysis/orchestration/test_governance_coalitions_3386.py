"""#3386 — the coalition play reaches the record and the Acts.

Born-red contract: the electors the derivation builds must NEGOTIATE before
they vote — the ``Agent`` machinery's personalities (never run in production
before #3386), on the derivation's own outputs, no second agent path. The
coalitions they form and the declared profile's manipulability (the #3385
engine, imported — never a second copy) reach ``state.governance_decisions``,
and both Acts carry the producer-rendered block when — and only when — the
play moved the outcome. A play that changes nothing leaves the deliberation
passage byte-identical.

The planted profile (opaque ids, no corpus content) is hand-computed:

- declared ballots → Condorcet winner ``arg_2``;
- stances rotate (stubborn, flexible, strategic) over the sorted electors;
  ``elector_vertu_b`` (flexible) rallies behind ``arg_3`` during the
  round-robin → that play's cast Condorcet winner is ``arg_3`` — a
  coalition of {b, d, e} behind ``arg_3``;
- the declared profile is pivotal: the pair (a, b) reporting ``arg_3`` first
  makes ``arg_3`` win instead of ``arg_2`` (#3385 engine, one witness).

**The verdict is the DECLARED aggregate (#3418 R1144, review 2).** TWO
arbitrary inputs decide a play, and an earlier revision varied only the
stance shift: the seat order assigns the stances AND fixes the round-robin,
so it also decides who hears which proposal last, hence where a flexible
elector's ballot lands. Rotating the elector list alone already moved the
cast winner through arg_3, arg_1 and arg_2 while the declared winner stayed
arg_2. The family is therefore ``len(agents) × len(PLAY_STANCES)`` plays —
every seat rotation against every stance shift — reported as a SENSITIVITY
(``play_sensitivity``); the verdict never consumes it.

On the planted profile the fifteen plays disagree (all three arguments win
somewhere), so the record says ``stance_dependent: true`` and NOTHING is
printed: a line printed off one arbitrary input is a fact about the alphabet,
not about the document. The wording, when a flip IS uniform, stays scoped to
what was enumerated (« sous les N attributions testées »), never « whatever
the assignment ».

No JVM, no LLM (client patched to None), privacy HARD (opaque ids only).
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import patch

import pytest

from argumentation_analysis.agents.core.context.strategist import (
    compute_manipulability,
)
from argumentation_analysis.agents.core.governance.coalition_play import (
    coalition_note,
    play_governance_rounds,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.invoke_callables import (
    _aggregate_governance_votes,
    _derive_governance_profile,
    _invoke_governance,
)
from argumentation_analysis.orchestration.state_writers import (
    _write_governance_to_state,
)
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

# The planted quality profile: per-virtue scores encode the declared ballots
# (rank 4 → the top). Sorted virtues: vertu_a..vertu_e → stances
# a=stubborn, b=flexible, c=strategic, d=stubborn, e=flexible.
_PLANTED_QUALITY: Dict[str, Any] = {
    "per_argument_scores": {
        "arg_1": {
            "scores_par_vertu": {
                "vertu_a": 4.0,
                "vertu_b": 3.0,
                "vertu_c": 2.0,
                "vertu_d": 2.0,
                "vertu_e": 2.0,
            }
        },
        "arg_2": {
            "scores_par_vertu": {
                "vertu_a": 3.0,
                "vertu_b": 4.0,
                "vertu_c": 4.0,
                "vertu_d": 3.0,
                "vertu_e": 3.0,
            }
        },
        "arg_3": {
            "scores_par_vertu": {
                "vertu_a": 2.0,
                "vertu_b": 2.0,
                "vertu_c": 3.0,
                "vertu_d": 4.0,
                "vertu_e": 4.0,
            }
        },
        "arg_4": {
            "scores_par_vertu": {
                "vertu_a": 1.0,
                "vertu_b": 1.0,
                "vertu_c": 1.0,
                "vertu_d": 1.0,
                "vertu_e": 1.0,
            }
        },
    }
}

# Unanimous top (arg_1 first for every virtue, distinct tails): the
# negotiation has nothing to move — the control case.
_CONCORDANT_QUALITY: Dict[str, Any] = {
    "per_argument_scores": {
        "arg_1": {
            "scores_par_vertu": {
                "vertu_a": 4.0,
                "vertu_b": 4.0,
                "vertu_c": 4.0,
                "vertu_d": 4.0,
                "vertu_e": 4.0,
            }
        },
        "arg_2": {
            "scores_par_vertu": {
                "vertu_a": 3.0,
                "vertu_b": 2.0,
                "vertu_c": 3.0,
                "vertu_d": 2.0,
                "vertu_e": 3.0,
            }
        },
        "arg_3": {
            "scores_par_vertu": {
                "vertu_a": 2.0,
                "vertu_b": 3.0,
                "vertu_c": 2.0,
                "vertu_d": 3.0,
                "vertu_e": 2.0,
            }
        },
        "arg_4": {
            "scores_par_vertu": {
                "vertu_a": 1.0,
                "vertu_b": 1.0,
                "vertu_c": 1.0,
                "vertu_d": 1.0,
                "vertu_e": 1.0,
            }
        },
    }
}


async def _handler_output(quality: Dict[str, Any]) -> Dict[str, Any]:
    """Run the REAL producer (no LLM) on a synthetic quality profile."""
    context: Dict[str, Any] = {
        "phase_extract_output": {"arguments": ["s1", "s2", "s3"]},
        "phase_quality_output": quality,
        "_state_object": None,
    }
    with patch(
        "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
        return_value=(None, ""),
    ):
        return await _invoke_governance("synthetic neutral text", context)


def _written_state(output: Dict[str, Any]) -> UnifiedAnalysisState:
    """The REAL writer on the REAL state class — the producer boundary."""
    state = UnifiedAnalysisState(
        initial_text="filler text for the witness, no corpus content."
    )
    _write_governance_to_state(output, state, {})
    return state


_PROMPTS = {
    "act2": lambda st: build_act2_prompt(build_act2_evidence(st)),
    "act3": lambda st: build_act3_prompt(build_act3_evidence(st)),
}


def _deliberation(prompt: str) -> str:
    start = prompt.find("DÉLIBÉRATION COLLECTIVE")
    assert start != -1, "the prompt carries no deliberation block"
    return prompt[start:]


# ---------------------------------------------------------------------------
# The play itself — the machinery runs, on the derivation's own electors
# ---------------------------------------------------------------------------


class TestThePlantedCoalitionChangesTheOutcome:
    def test_the_play_moves_a_flexible_elector_and_flips_the_winner(self) -> None:
        options, ballots, agents, derivable, _reason = _derive_governance_profile(
            _PLANTED_QUALITY
        )
        assert derivable
        play = play_governance_rounds(agents, options, ballots)
        # The flexible elector vertu_b rallies behind arg_3 (hand-computed).
        assert [m["elector"] for m in play["moved"]] == ["elector_vertu_b"]
        assert play["moved"][0]["from"] == "arg_2"
        assert play["moved"][0]["to"] == "arg_3"
        declared = _aggregate_governance_votes(agents, options, ballots)
        cast = _aggregate_governance_votes(
            play["cast_agents"], options, play["cast_ballots"]
        )
        assert declared["winner"] == "arg_2"
        assert cast["winner"] == "arg_3"
        # The winning bloc names its members — b, d, e behind arg_3.
        bloc = next(b for b in play["blocs"] if b["option"] == "arg_3")
        assert set(bloc["members"]) == {
            "elector_vertu_b",
            "elector_vertu_d",
            "elector_vertu_e",
        }

    def test_the_callers_agents_and_ballots_are_never_mutated(self) -> None:
        options, ballots, agents, _derivable, _reason = _derive_governance_profile(
            _PLANTED_QUALITY
        )
        before = [list(a.preferences) for a in agents]
        play_governance_rounds(agents, options, ballots)
        assert [list(a.preferences) for a in agents] == before
        # The declared profile stays measurable afterwards (the manipulability
        # engine and the outcome-change probe both read it).
        game = compute_manipulability(
            {a.name: list(a.preferences) for a in agents}, options
        )
        assert game["winner"] == "arg_2"


class TestTheManipulabilityFindingUsesThe3385Engine:
    def test_the_declared_profile_is_pivotal_and_the_engine_says_so(self) -> None:
        options, ballots, agents, _derivable, _reason = _derive_governance_profile(
            _PLANTED_QUALITY
        )
        game = compute_manipulability(
            {a.name: list(a.preferences) for a in agents}, options
        )
        assert game["status"] == "ok"
        assert game["winner"] == "arg_2"
        # One witness per pair, players in elector order, targets in option
        # order: the first coalition is (a, b) reporting arg_3.
        first = game["coalitions"][0]
        assert first["players"] == ["elector_vertu_a", "elector_vertu_b"]
        assert first["report"] == "arg_3"
        assert first["winner"] == "arg_3"


# ---------------------------------------------------------------------------
# Producer → verdict → record — the chain the DoD guards
# ---------------------------------------------------------------------------


class TestTheVerdictCarriesCoalitionAndManipulability:
    @pytest.mark.asyncio
    async def test_planted_profile_verdict(self) -> None:
        output = await _handler_output(_PLANTED_QUALITY)
        assert output["governance_decided_firsthand"] is True
        verdict = output["governance_verdict"]
        assert verdict["degraded"] is False
        # The verdict is the DECLARED aggregate — never the play's (#3418).
        assert verdict["winner"] == "arg_2"
        coalition = verdict["coalition"]
        assert coalition["winner_declared"] == "arg_2"
        # The family's size and its two axes are recorded: 5 seats × 3 stances.
        assert (coalition["plays"], coalition["rotations"], coalition["shifts"]) == (
            15,
            5,
            3,
        )
        assert coalition["winners"] == [
            ["arg_3", "arg_3", "arg_3"],
            ["arg_3", "arg_1", "arg_2"],
            ["arg_1", "arg_2", "arg_2"],
            ["arg_2", "arg_2", "arg_2"],
            ["arg_2", "arg_3", "arg_3"],
        ]
        # All three arguments win somewhere: the play is the fabricated input,
        # so it is reported as stance-dependent and no flip is claimed.
        assert coalition["uniform_winner"] is None
        assert coalition["outcome_changed"] is False
        assert coalition["stance_dependent"] is True
        # No elector moves under EVERY play: the stable set is empty, and the
        # per-play movers are neither summed nor averaged into one.
        assert coalition["ballots_moved"] == []
        assert coalition["blocs"] == []
        assert "winner_cast" not in coalition
        manipulability = verdict["manipulability"]
        assert manipulability["kind"] == "coalition"
        assert manipulability["players"] == ["elector_vertu_a", "elector_vertu_b"]
        assert manipulability["report"] == "arg_3"
        assert manipulability["baseline"] == "arg_2"
        assert manipulability["engine"]  # the #3385 engine, named not copied

    @pytest.mark.asyncio
    async def test_the_record_carries_both(self) -> None:
        output = await _handler_output(_PLANTED_QUALITY)
        state = _written_state(output)
        record = state.governance_decisions[-1]
        # The recorded winner is the declared one; the play sits beside it as a
        # sensitivity, never as the verdict.
        assert record["winner"] == "arg_2"
        assert record["coalition"]["stance_dependent"] is True
        assert record["coalition"]["plays"] == 15
        assert record["coalition"]["winner_declared"] == "arg_2"
        assert record["manipulability"]["players"] == [
            "elector_vertu_a",
            "elector_vertu_b",
        ]

    def test_a_vote_without_a_play_adds_no_phantom_fields(self) -> None:
        """Honest absence: a bare vote (no play keys) stores neither field."""
        state = _written_state(
            {"vote_result": {"winner": "arg_7", "method": "formal-aggregation"}}
        )
        record = state.governance_decisions[-1]
        assert "coalition" not in record
        assert "manipulability" not in record


class TestTheVerdictDoesNotDependOnTheSeatOrder:
    """#3418 R1144 witness 4 — born red against the pre-fix producer.

    Before the fix the verdict consumed the play's aggregate, whose winner
    followed the rotation of the elector list: the same profile, the same
    ballots, and arg_3, arg_3, arg_1, arg_2, arg_2 as the seats rotated.
    Permuting the electors is a change of SEAT, not of opinion — the recorded
    winner must be byte-identical under every rotation.
    """

    @pytest.mark.asyncio
    async def test_a_permutation_of_the_electors_leaves_the_winner_identical(
        self,
    ) -> None:
        options, _ballots, agents, derivable, _reason = _derive_governance_profile(
            _PLANTED_QUALITY
        )
        assert derivable
        recorded: Dict[int, str] = {}
        for k in range(len(agents)):
            rotated = agents[k:] + agents[:k]
            rotated_ballots = [a.preferences for a in rotated]
            with patch(
                "argumentation_analysis.orchestration.invoke_callables"
                "._derive_governance_profile",
                return_value=(options, rotated_ballots, rotated, True, "planted"),
            ):
                output = await _handler_output(_PLANTED_QUALITY)
            recorded[k] = _written_state(output).governance_decisions[-1]["winner"]
        # One distinct winner across every seat order, and it is the declared
        # one — the play's per-shift winners are reported, never recorded.
        assert set(recorded.values()) == {"arg_2"}

    def test_the_sensitivity_covers_every_rotation_and_every_shift(self) -> None:
        """The family is seat rotation × stance shift, not the shift alone.

        Review 2: the stance rotation reads the seat order AND the round-robin
        fixes who hears which proposal last, so varying only the offset leaves
        half the arbitrary input unmeasured. Here the family is 5 × 3 = 15 and
        the record carries both axes.

        Imported here, not at module scope: a new symbol imported for the
        whole file turns every witness red with a collection error, which
        measures the import and not the behaviour.
        """
        from argumentation_analysis.agents.core.governance.coalition_play import (
            play_sensitivity,
        )

        options, ballots, agents, _derivable, _reason = _derive_governance_profile(
            _PLANTED_QUALITY
        )
        sensitivity = play_sensitivity(
            agents, options, ballots, _aggregate_governance_votes
        )
        assert (sensitivity["plays"], sensitivity["rotations"]) == (15, 5)
        assert sensitivity["shifts"] == 3
        assert len(sensitivity["winners"]) == sensitivity["rotations"]
        assert all(len(row) == 3 for row in sensitivity["winners"])
        assert sensitivity["winner_declared"] == "arg_2"
        # Every argument wins in some play: the family is stance-dependent, so
        # no flip is claimed and the verdict stays the declared aggregate.
        assert {w for row in sensitivity["winners"] for w in row} == {
            "arg_1",
            "arg_2",
            "arg_3",
        }
        assert sensitivity["uniform_winner"] is None
        assert sensitivity["outcome_changed"] is False
        assert sensitivity["stance_dependent"] is True


# ---------------------------------------------------------------------------
# Record → render — a change prints, everything else stays byte-identical
# ---------------------------------------------------------------------------


class TestTheNotePrintsOnlyAChange:
    def test_a_robust_flip_names_both_winners_and_the_unstable_movers(self) -> None:
        """A uniform flip prints — scoped to the family that was enumerated."""
        record = {
            "coalition": {
                "plays": 15,
                "rotations": 5,
                "shifts": 3,
                "winners": [["arg_3"] * 3] * 5,
                "winner_declared": "arg_2",
                "uniform_winner": "arg_3",
                "outcome_changed": True,
                "stance_dependent": False,
                "ballots_moved": [],
                "blocs": [],
            },
            "manipulability": {
                "kind": "coalition",
                "players": ["elector_vertu_a", "elector_vertu_b"],
                "report": "arg_3",
                "winner": "arg_3",
                "baseline": "arg_2",
            },
        }
        note = coalition_note(record)
        # Scoped to what was enumerated — the family's size and its two axes.
        assert (
            "sous les 15 attributions testées (5 ordres de parole × "
            "3 décalages de posture)" in note
        )
        assert "quelle que soit" not in note
        assert "de « arg_2 » à « arg_3 »" in note
        assert "les électeurs qui bougent dépendent de l'attribution" in note
        assert "portant « arg_3 » en tête" in note

    def test_a_stable_coalition_names_its_movers_and_its_bloc(self) -> None:
        """A flip whose movers agree in every play names them, with the bloc."""
        record = {
            "coalition": {
                "plays": 15,
                "rotations": 5,
                "shifts": 3,
                "winner_declared": "arg_2",
                "uniform_winner": "arg_3",
                "outcome_changed": True,
                "stance_dependent": False,
                "ballots_moved": ["elector_vertu_b", "elector_vertu_e"],
                "blocs": [
                    {
                        "option": "arg_3",
                        "members": [
                            "elector_vertu_b",
                            "elector_vertu_d",
                            "elector_vertu_e",
                        ],
                    }
                ],
            }
        }
        note = coalition_note(record)
        assert "2 électeur(s) déplacent leur bulletin" in note
        assert "dans toutes les attributions" in note
        assert "elector_vertu_b, elector_vertu_e" in note
        assert "derrière « arg_3 »" in note

    def test_a_stance_dependent_play_prints_no_flip(self) -> None:
        """#3418 R1144 review 2: disagreeing plays are the fabricated input."""
        record = {
            "coalition": {
                "plays": 15,
                "rotations": 5,
                "shifts": 3,
                "winners": [
                    ["arg_3", "arg_3", "arg_3"],
                    ["arg_3", "arg_1", "arg_2"],
                ],
                "winner_declared": "arg_2",
                "uniform_winner": None,
                "outcome_changed": False,
                "stance_dependent": True,
                "ballots_moved": ["elector_vertu_b"],
                "blocs": [{"option": "arg_3", "members": ["elector_vertu_b"]}],
            },
            "manipulability": {
                "kind": "coalition",
                "players": ["elector_vertu_a"],
                "report": "arg_3",
                "winner": "arg_3",
                "baseline": "arg_2",
            },
        }
        note = coalition_note(record)
        assert "Jeu de coalitions" not in note
        # The pivot is a finding on the DECLARED profile — it still prints.
        assert "Manipulabilité" in note

    def test_a_bloc_that_changed_nothing_prints_nothing(self) -> None:
        record = {
            "coalition": {
                "outcome_changed": False,
                "blocs": [{"option": "arg_1", "members": ["elector_vertu_a"]}],
            }
        }
        assert coalition_note(record) == ""

    def test_an_empty_record_prints_nothing(self) -> None:
        assert coalition_note({}) == ""


@pytest.mark.parametrize("act", ["act2", "act3"])
class TestTheBlockReachesTheActs:
    @pytest.mark.asyncio
    async def test_the_planted_record_prints_only_the_pivot(self, act: str) -> None:
        """Born red on review 2 — the fifteen plays claim no flip.

        An earlier revision varied only the stance shift, and on this profile
        the three shifted plays agreed on arg_3, so the Acts printed a flip
        that seat rotation contradicts (all three arguments win somewhere in
        the real family). The coalition line must disappear; the pivot — a
        finding on the DECLARED profile, independent of any play — stays.
        """
        output = await _handler_output(_PLANTED_QUALITY)
        assert output["governance_verdict"]["coalition"]["stance_dependent"] is True
        state = _written_state(output)
        state.identified_arguments = {
            "arg_2": "Position synthétique deux.",
            "arg_3": "Position synthétique trois.",
        }
        block = _deliberation(_PROMPTS[act](state))
        assert "Jeu de coalitions" not in block
        assert "Manipulabilité" in block
        assert "elector_vertu_a et elector_vertu_b" in block  # the pivot's pair

    @pytest.mark.asyncio
    async def test_the_control_passage_is_byte_identical(self, act: str) -> None:
        """Concordant profile → the play moved nothing → dropping the
        coalition key from the record changes the prompt by zero bytes."""
        output = await _handler_output(_CONCORDANT_QUALITY)
        state = _written_state(output)
        assert output["governance_verdict"]["coalition"]["outcome_changed"] is False
        assert "manipulability" not in output["governance_verdict"]
        with_keys = _PROMPTS[act](state)
        record = state.governance_decisions[-1]
        assert "coalition" in record  # the structure is still measured…
        record.pop("coalition")  # …but rendering must not depend on it
        assert _PROMPTS[act](state) == with_keys

    def test_a_record_without_the_keys_renders_no_block(self, act: str) -> None:
        state = _written_state(
            {"vote_result": {"winner": "arg_7", "method": "formal-aggregation"}}
        )
        block = _deliberation(_PROMPTS[act](state))
        assert "Jeu de coalitions" not in block
        assert "Manipulabilité" not in block


# ---------------------------------------------------------------------------
# The control case — a negotiation with nothing to move is the identity
# ---------------------------------------------------------------------------


class TestTheConcordantControlIsTheIdentity:
    @pytest.mark.asyncio
    async def test_nothing_moves_and_the_vote_is_unchanged(self) -> None:
        options, ballots, agents, derivable, _reason = _derive_governance_profile(
            _CONCORDANT_QUALITY
        )
        assert derivable
        play = play_governance_rounds(agents, options, ballots)
        assert play["moved"] == []
        # Identity, not a copy: the cast IS the declared profile.
        assert play["cast_ballots"] == ballots
        declared = _aggregate_governance_votes(agents, options, ballots)
        cast = _aggregate_governance_votes(
            play["cast_agents"], options, play["cast_ballots"]
        )
        assert cast == declared

    @pytest.mark.asyncio
    async def test_the_concordant_profile_is_not_pivotal(self) -> None:
        options, ballots, agents, _derivable, _reason = _derive_governance_profile(
            _CONCORDANT_QUALITY
        )
        game = compute_manipulability(
            {a.name: list(a.preferences) for a in agents}, options
        )
        assert game["winner"] == "arg_1"
        assert game["single_player"] == []
        assert game["coalitions"] == []
