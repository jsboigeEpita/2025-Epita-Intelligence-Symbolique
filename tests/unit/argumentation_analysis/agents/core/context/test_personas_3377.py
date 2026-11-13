"""#3377 — the historian and the strategist, and the two consumers that read them.

The mandate (Epic #3374): the pipeline may not forbid itself what the model
knows. On an undated document the render says the date "is only a deduction
from the content" and a place "remains to be verified elsewhere"; the
same-model zero-shot of #2841 dates and situates it. The gap is real, and
closing it is only safe with the line the renderer already keeps: the personas'
output is MODEL KNOWLEDGE, labelled in the state and in the render, never read
as the text's own content.

What this file pins, in the order the DoD asks:

- every item a persona writes carries ``basis="model_knowledge"`` — INCLUDING
  when the model claims otherwise (the label is stamped, never read from the
  reply), because that is the one guarantee the module exists for;
- the strategist's outcome is COMPUTED, not stated: the engine derives the
  Condorcet winner and the pivots the model's profile allows, and the pair case
  below is a profile where no individual can move the outcome but a pair can —
  the reason the coalition test is not decoration;
- both consumers read what the producer wrote: Acte I's prompt carries the
  computed read, labelled, and no longer asks the writer to invent one; the
  NL→KB translator forwards the historian's note, and sends the previous prompt
  byte for byte when there is none.

Everything is synthetic: invented players, invented options, opaque ids. No
LLM, no JVM, no network — the fakes are plain async callables.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from argumentation_analysis.agents.core.context import (
    MODEL_KNOWLEDGE_BASIS,
    stamp_basis,
)
from argumentation_analysis.agents.core.context.historian import (
    build_historical_context,
    context_note,
)
from argumentation_analysis.agents.core.context.strategist import (
    build_strategic_read,
    compute_manipulability,
)
from argumentation_analysis.services.nl_to_logic import NLToLogicTranslator

_EXCERPT = ("une phrase de contexte, avec des virgules; et une autre clause. " * 80)[
    :4000
]


def _state(**fields):
    base = dict(
        raw_text=_EXCERPT,
        source_metadata={"speaker": "Speaker_A", "venue": "assembly"},
        stakes_and_stakeholders={"stakes": [], "stakeholders": []},
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _llm(payload):
    """A fake model returning a fixed JSON document."""

    async def _call(prompt: str) -> str:
        return json.dumps(payload)

    return _call


_HISTORIAN_PAYLOAD = {
    "situation": "Le document appartient à une période de transition institutionnelle.",
    "items": [
        {
            "claim": "Le cadre institutionnel est celui d'une assemblée.",
            "confidence": 0.8,
        },
        {
            "claim": "Le vocabulaire situe le propos après une réforme.",
            "confidence": 0.4,
        },
    ],
}


# ============================================================================
# The historian — label, bounds, discriminated status
# ============================================================================


class TestTheHistorianLabelsWhatItWrites:
    async def test_every_item_carries_the_label(self):
        result = await build_historical_context(_state(), _llm(_HISTORIAN_PAYLOAD))

        assert result.status == "ok"
        assert [item.basis for item in result.items] == [MODEL_KNOWLEDGE_BASIS] * 2

    async def test_the_model_cannot_choose_its_own_basis(self):
        """The defect this module exists to prevent: a model answering
        ``"text"`` would launder a deduction into a quotation."""
        payload = {
            "situation": "",
            "items": [
                {"claim": "Une affirmation.", "confidence": 0.5, "basis": "text"}
            ],
        }
        result = await build_historical_context(_state(), _llm(payload))

        assert result.items[0].basis == MODEL_KNOWLEDGE_BASIS
        assert result.to_state()["items"][0]["basis"] == MODEL_KNOWLEDGE_BASIS

    async def test_stamp_basis_never_mutates_the_callers_item(self):
        original = {"claim": "Une affirmation."}
        stamped = stamp_basis([original])

        assert original == {"claim": "Une affirmation."}
        assert stamped[0]["basis"] == MODEL_KNOWLEDGE_BASIS

    async def test_an_empty_claim_is_dropped(self):
        payload = {
            "situation": "",
            "items": [{"claim": "", "confidence": 0.9}, {"claim": "Une."}],
        }
        result = await build_historical_context(_state(), _llm(payload))

        assert [item.claim for item in result.items] == ["Une."]

    async def test_confidence_is_clamped_and_unreadable_reads_zero(self):
        payload = {
            "situation": "",
            "items": [
                {"claim": "Trop sûre.", "confidence": 4},
                {"claim": "Pas de mesure.", "confidence": "n/a"},
            ],
        }
        result = await build_historical_context(_state(), _llm(payload))

        assert result.items[0].confidence == 1.0
        assert result.items[1].confidence == 0.0


class TestTheHistorianFailsLoud:
    async def test_no_llm_is_an_honest_empty(self):
        result = await build_historical_context(_state(), None)

        assert result.status == "no_llm"
        assert result.items == []

    async def test_a_parse_error_is_discriminated(self):
        async def _bad(prompt: str) -> str:
            return "pas du JSON"

        result = await build_historical_context(_state(), _bad)

        assert result.status == "parse_error"
        assert result.error

    async def test_an_empty_completion_is_an_llm_error(self):
        async def _empty(prompt: str) -> str:
            return "   "

        result = await build_historical_context(_state(), _empty)

        assert result.status == "llm_error"


class TestTheNoteTheConsumerReads:
    async def test_no_read_means_no_note(self):
        """A consumer that appended an empty header would advertise a
        provenance it does not have."""
        assert (
            context_note(_state(historical_context={"items": [], "situation": ""}))
            == ""
        )

    async def test_the_note_says_it_is_model_knowledge(self):
        state = _state(
            historical_context={
                "situation": "Une période de transition.",
                "items": [
                    {
                        "claim": "Une assemblée.",
                        "confidence": 0.8,
                        "basis": "model_knowledge",
                    }
                ],
                "status": "ok",
                "basis": "model_knowledge",
            }
        )
        note = context_note(state)

        assert "SAVOIR DU MODÈLE" in note
        assert "Une assemblée." in note
        assert "0.80" in note


# ============================================================================
# The strategist — the engine COMPUTES, the model only states the profile
# ============================================================================


class TestTheEngineComputesTheOutcome:
    def test_the_condorcet_winner_is_derived(self):
        profile = {
            "P1": ["A", "B", "C"],
            "P2": ["A", "C", "B"],
            "P3": ["B", "C", "A"],
        }
        game = compute_manipulability(profile, ["A", "B", "C"])

        assert game["status"] == "ok"
        assert game["winner"] == "A"

    def test_a_single_player_pivot_against_its_own_ballot_is_dropped(self):
        """#3524 — born red on the pre-#3524 engine, which reported ("P1","B").

        P1 ranks A first: reporting B first makes B win, but at P1's own
        expense. That is not a manipulation (Gibbard-Satterthwaite), so the
        witness is removed and counted.
        """
        profile = {
            "P1": ["A", "B", "C"],
            "P2": ["A", "B", "C"],
            "P3": ["B", "C", "A"],
        }
        game = compute_manipulability(profile, ["A", "B", "C"])

        assert game["winner"] == "A"
        assert game["single_player"] == []
        assert game["dropped_against_interest"] == 5

    def test_a_pair_that_can_move_but_prefers_the_baseline_is_dropped(self):
        """#3524 — born red: the old engine returned three coalitions here.

        Three players rank A first, one ranks B first: two of the A-first
        players together make B win 3-1. The move is real, and it costs both
        movers — they all rank A above B — so no witness is kept and the
        count carries the measurement.
        """
        profile = {
            "P1": ["A", "B", "C"],
            "P2": ["A", "B", "C"],
            "P3": ["A", "B", "C"],
            "P4": ["B", "A", "C"],
        }
        game = compute_manipulability(profile, ["A", "B", "C"])

        assert game["winner"] == "A"
        assert game["single_player"] == []
        assert game["coalitions"] == []
        assert game["dropped_against_interest"] == 3

    def test_an_insufficient_profile_computes_nothing(self):
        game = compute_manipulability({"P1": ["A"]}, ["A", "B"])

        assert game["status"] == "insufficient_profile"
        assert game["winner"] is None
        assert game["single_player"] == []

    def test_a_cyclic_profile_is_a_result_not_a_failure(self):
        profile = {
            "P1": ["A", "B", "C"],
            "P2": ["B", "C", "A"],
            "P3": ["C", "A", "B"],
        }
        game = compute_manipulability(profile, ["A", "B", "C"])

        assert game["status"] == "no_condorcet_winner"
        assert game["winner"] is None

    def test_the_computation_is_deterministic(self):
        profile = {
            "P1": ["A", "B", "C"],
            "P2": ["A", "B", "C"],
            "P3": ["A", "B", "C"],
            "P4": ["B", "A", "C"],
        }

        assert compute_manipulability(
            profile, ["A", "B", "C"]
        ) == compute_manipulability(profile, ["A", "B", "C"])

    def test_a_partial_ranking_is_completed_deterministically(self):
        """A player who named one option cannot be compared on the others
        unless the ballot is completed; the completion is stated, not random.
        #3385: the matcher now returns what matched, what did not, and what it
        had to complete — three facts, not one flattened ballot."""
        from argumentation_analysis.agents.core.context.strategist import (
            _normalise_ballot,
        )

        assert _normalise_ballot(["B"], ["A", "B", "C"]) == (
            ["B"],
            [],
            ["A", "C"],
        )
        assert _normalise_ballot(["B", "C"], ["A", "B", "C"]) == (
            ["B", "C"],
            [],
            ["A"],
        )
        # An option the player ranked twice keeps its first position only.
        assert _normalise_ballot(["C", "B", "C"], ["A", "B", "C"]) == (
            ["C", "B"],
            [],
            ["A"],
        )
        # #3385 — an entry that names no option is UNREADABLE, not silently
        # dropped: it is recorded so the read can say what it could not use.
        assert _normalise_ballot(["B", "option x"], ["A", "B", "C"]) == (
            ["B"],
            ["option x"],
            ["A", "C"],
        )


# ============================================================================
# #3385 — the ballot is matched on a normalised key, never invented
# ============================================================================


class TestTheBallotIsMatchedNotInvented:
    """Red on the R1295 head ``7582f10e3``: ``_normalise_ballot`` kept only
    EXACT matches and appended the missing options in declaration order, so a
    model writing the option names in its own casing handed the engine a
    ballot it never gave — one that favours the first-declared option — while
    ``status`` stayed ``ok`` and nothing recorded the substitution."""

    OPTIONS = ["Cadre A", "Cadre B", "Cadre C"]

    def test_casing_alone_does_not_rewrite_the_ballot(self):
        """The coordinator's probe. Two players write the options lowercase;
        the third writes them exact. The engine must score the ballots AS
        WRITTEN (winner Cadre C), not the declaration order (which made
        Cadre A win on the old head) — and casing alone invents nothing to
        record: no completion, no unmatched entry."""
        profile = {
            "P1": ["cadre c", "cadre b", "cadre a"],
            "P2": ["cadre c", "cadre a", "cadre b"],
            "P3": ["Cadre B", "Cadre C", "Cadre A"],
        }
        game = compute_manipulability(profile, self.OPTIONS)

        assert game["winner"] == "Cadre C", (
            "the ballots as written elect Cadre C; a winner of "
            f"{game['winner']!r} means the engine scored a ballot the "
            "players never gave"
        )
        assert game["status"] == "ok"
        assert game["completed"] == {}
        assert game["unmatched"] == {}

    def test_whitespace_and_end_punctuation_do_not_rewrite_it_either(self):
        profile = {
            "P1": ['"Cadre   C"', "cadre b.", "Cadre A"],
            "P2": ["Cadre C", "Cadre A", "Cadre B"],
            "P3": ["Cadre B", "Cadre C", "Cadre A"],
        }
        game = compute_manipulability(profile, self.OPTIONS)

        assert game["winner"] == "Cadre C"
        assert game["completed"] == {}
        assert game["unmatched"] == {}

    def test_a_partial_ballot_is_completed_and_the_record_carries_it(self):
        """A genuinely partial ballot is completed (declaration order for the
        missing) — and the completion is RECORDED, with a status that says
        so: the winner is computed on a profile partly built by us."""
        profile = {
            "P1": ["Cadre C"],
            "P2": ["Cadre C", "Cadre A", "Cadre B"],
            "P3": ["Cadre B", "Cadre C", "Cadre A"],
        }
        game = compute_manipulability(profile, self.OPTIONS)

        assert game["winner"] == "Cadre C"
        assert game["status"] == "ok_completed"
        assert game["completed"] == {"P1": ["Cadre A", "Cadre B"]}
        assert game["unmatched"] == {}

    def test_a_player_whose_nothing_matches_is_excluded_not_completed(self):
        """A player none of whose entries match is EXCLUDED from the profile:
        completing them would score the declaration order — a strict
        preference the player never stated. The exclusion is recorded with
        the unreadable entries, and the rest of the profile is computed."""
        profile = {
            "P1": ["Cadre C", "Cadre B", "Cadre A"],
            "P2": ["Cadre C", "Cadre A", "Cadre B"],
            "P3": ["Cadre B", "Cadre C", "Cadre A"],
            "P4": ["option x", "option y"],
        }
        game = compute_manipulability(profile, self.OPTIONS)

        assert game["players"] == ["P1", "P2", "P3"]
        assert game["excluded_players"] == [
            {"player": "P4", "entries": ["option x", "option y"]}
        ]
        assert "P4" not in game["completed"]
        assert game["winner"] == "Cadre C"

    def test_exclusion_below_two_players_is_insufficient(self):
        profile = {
            "P1": ["Cadre A", "Cadre B", "Cadre C"],
            "P2": ["option x", "option y"],
        }
        game = compute_manipulability(profile, self.OPTIONS)

        assert game["status"] == "insufficient_profile"
        assert game["winner"] is None
        assert game["excluded_players"] == [
            {"player": "P2", "entries": ["option x", "option y"]}
        ]


class TestTheStateSaysWhichPartIsWhose:
    async def test_the_configuration_is_model_knowledge_and_the_game_is_computed(self):
        payload = {
            "players": [
                {"name": "P1", "role": "orateur", "stance": "for"},
                {"name": "P2", "role": "opposant", "stance": "against"},
            ],
            "options": ["A", "B", "C"],
            "preferences": {"P1": ["A", "B", "C"], "P2": ["A", "C", "B"]},
            "reading": "Deux joueurs, un désaccord sur l'ordre.",
        }
        result = await build_strategic_read(_state(), _llm(payload))
        state = result.to_state()

        assert result.status == "ok"
        assert [p["basis"] for p in state["players"]] == [MODEL_KNOWLEDGE_BASIS] * 2
        assert state["game"]["engine"] == "governance.social_choice.condorcet_winner"
        assert state["game"]["status"] == "ok"

    async def test_no_llm_computes_nothing(self):
        result = await build_strategic_read(_state(), None)

        assert result.status == "no_llm"
        assert result.game == {}


# ============================================================================
# Consumer 1 — Acte I reads the strategist instead of producing its own read
# ============================================================================


def _evidence(**fields):
    from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
        Act1Evidence,
    )

    return Act1Evidence(**fields)


class TestActeIConsumesTheRead:
    def test_the_prompt_carries_the_computed_outcome_labelled(self):
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            build_act1_prompt,
        )

        evidence = _evidence(
            strategic_read={
                "players": [{"name": "P1", "role": "orateur", "stance": "for"}],
                "options": ["A", "B"],
                "reading": "Une lecture neutre.",
                "game": {
                    "status": "ok",
                    "winner": "A",
                    "single_player": [{"player": "P1", "reports": "B", "winner": "B"}],
                    "coalitions": [],
                },
                "basis": MODEL_KNOWLEDGE_BASIS,
            }
        )
        prompt = build_act1_prompt(evidence)

        assert "SAVOIR DU MODÈLE" in prompt
        assert "Gagnant CALCULÉ (Condorcet) : A" in prompt
        # #3524 — the witness is stated as an ORDERING of the mover's ballot,
        # never as the player's stance on the subject.
        assert "Pivot d'un joueur : P1 pourrait porter « B » en tête" in prompt
        assert "que son bulletin classe devant « A »" in prompt

    def test_the_prompt_carries_the_historian_with_its_confidence(self):
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            build_act1_prompt,
        )

        evidence = _evidence(
            historical_context={
                "situation": "Une transition institutionnelle.",
                "items": [
                    {
                        "claim": "Le cadre est parlementaire.",
                        "confidence": 0.6,
                        "supports": "le vocabulaire",
                        "basis": MODEL_KNOWLEDGE_BASIS,
                    }
                ],
            }
        )
        prompt = build_act1_prompt(evidence)

        assert "SITUATION HISTORIQUE" in prompt
        assert "Le cadre est parlementaire. (confiance 0.60)" in prompt

    def test_the_act_no_longer_asks_for_its_own_strategic_read(self):
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            build_act1_prompt,
        )

        prompt = build_act1_prompt(_evidence())

        assert (
            "La lecture stratégique (acteurs, intérêts, coups attendus)" not in prompt
        )
        assert "tu n'en produis pas une autre" in prompt

    def test_an_absent_read_is_said_absent(self):
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            build_act1_prompt,
        )

        prompt = build_act1_prompt(_evidence())

        assert "l'historien n'a rien rendu" in prompt
        assert "ne produis pas la tienne" in prompt

    def test_a_non_conclusive_computation_never_shows_a_winner(self):
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            build_act1_prompt,
        )

        evidence = _evidence(
            strategic_read={"game": {"status": "insufficient_profile"}, "players": []}
        )
        prompt = build_act1_prompt(evidence)

        assert "non concluant (insufficient_profile)" in prompt
        assert "Gagnant CALCULÉ" not in prompt

    def test_a_completed_profile_is_named_next_to_the_winner(self):
        """#3385 — a winner computed on a completed profile is not a clean
        computation: the block names whose ballots we completed, next to the
        winner itself, so the writer does not print it as the engine's own
        verdict on the players' ballots."""
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            build_act1_prompt,
        )

        evidence = _evidence(
            strategic_read={
                "players": [{"name": "P1", "role": "orateur", "stance": "for"}],
                "options": ["A", "B"],
                "reading": "Une lecture neutre.",
                "game": {
                    "status": "ok_completed",
                    "winner": "A",
                    "completed": {"P1": ["B"]},
                    "single_player": [],
                    "coalitions": [],
                },
                "basis": MODEL_KNOWLEDGE_BASIS,
            }
        )
        prompt = build_act1_prompt(evidence)

        assert "Gagnant CALCULÉ (Condorcet) : A — profil complété pour P1" in prompt


# ============================================================================
# Consumer 2 — the NL→KB translator forwards the historian's note
# ============================================================================


class TestTheTranslatorForwardsTheNote:
    async def test_the_note_reaches_every_translation_of_the_batch(self, monkeypatch):
        translator = NLToLogicTranslator(max_retries=1)
        seen = []

        async def _fake_translate(
            text, logic_type=None, shared_atoms=None, context_note=""
        ):
            seen.append(context_note)
            return SimpleNamespace(
                original_text=text,
                formula="",
                logic_type=logic_type or "",
                is_valid=False,
                validation_message="",
                attempts=0,
                variables={},
                confidence=0.0,
            )

        monkeypatch.setattr(translator, "translate", _fake_translate)

        await translator.translate_batch(
            ["un argument assez long", "un second argument long"],
            context_note="SITUATION HISTORIQUE — SAVOIR DU MODÈLE",
        )

        assert seen == ["SITUATION HISTORIQUE — SAVOIR DU MODÈLE"] * 2

    async def test_no_note_leaves_the_prompt_untouched(self, monkeypatch):
        translator = NLToLogicTranslator(max_retries=1)
        seen = []

        async def _fake_translate(
            text, logic_type=None, shared_atoms=None, context_note=""
        ):
            seen.append(context_note)
            return SimpleNamespace(
                original_text=text,
                formula="",
                logic_type=logic_type or "",
                is_valid=False,
                validation_message="",
                attempts=0,
                variables={},
                confidence=0.0,
            )

        monkeypatch.setattr(translator, "translate", _fake_translate)

        await translator.translate_batch(["un argument assez long"])

        assert seen == [""]


# ---------------------------------------------------------------------------
# R1142 — a read that ran and failed reaches the state through its writer.
#
# The shared ``"error" in output`` guard skipped every error-carrying payload,
# which made the failure branch unreachable: an invoke that failed left the
# ``no_llm`` default on the state, and the render said "nobody read" about a
# read that ran and failed. One father, three writers — the two personas here
# and #3395's first reading (witnessed in test_first_reading_3395.py).
# ---------------------------------------------------------------------------


def test_an_invoke_failure_reaches_the_state_through_the_historian_writer():
    """The invoke's own error dict (no shared state — its one failure shape)
    is coerced to the only honest discrimination: ``llm_error``."""
    from argumentation_analysis.orchestration.state_writers import (
        _write_historical_context_to_state,
    )

    state = SimpleNamespace(historical_context={"status": "no_llm"})
    _write_historical_context_to_state(
        {"error": "No shared state available for the historian"}, state, {}
    )

    assert state.historical_context["status"] == "llm_error"
    assert state.historical_context["situation"] == "", "nothing is fabricated"


def test_a_producer_failure_stays_persisted_historian():
    """The producer's own failure payload (discriminated status, no error
    key) already passed the old guard — pinned here so the R1142 rewrite
    cannot regress it."""
    from argumentation_analysis.orchestration.state_writers import (
        _write_historical_context_to_state,
    )

    state = SimpleNamespace(historical_context={"status": "no_llm"})
    _write_historical_context_to_state(
        {
            "situation": "",
            "items": [],
            "status": "llm_error",
            "basis": "model_knowledge",
            "degraded": True,
            "degraded_reason": "historian llm_error: TimeoutError",
        },
        state,
        {},
    )

    assert state.historical_context["status"] == "llm_error"
    assert state.historical_context["basis"] == "model_knowledge"


def test_an_invoke_failure_reaches_the_state_through_the_strategist_writer():
    from argumentation_analysis.orchestration.state_writers import (
        _write_strategic_read_to_state,
    )

    state = SimpleNamespace(strategic_read={"status": "no_llm"})
    _write_strategic_read_to_state(
        {"error": "No shared state available for the strategist"}, state, {}
    )

    assert state.strategic_read["status"] == "llm_error"
    assert state.strategic_read["players"] == [], "nothing is fabricated"
