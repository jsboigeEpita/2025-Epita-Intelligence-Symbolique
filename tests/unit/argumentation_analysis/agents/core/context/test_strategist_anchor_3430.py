"""#3430 — a player's stance in the document is anchored, and Act I says whose it is.

Panel cycle 2 measured 5 M2 items on 2 documents, all from Act I's framing of the
actors: the render placed a player where the document places them otherwise. The
wording sits in ``strategic_read.players`` — a persona of #3377, whose output is
model knowledge by design — and Act I relayed it as the text's reading.

The repair keeps the two layers apart instead of choosing between them (the
anti-pendulum: the strategist is not stripped down to quotes, its value is the
game the text does not spell out):

* a position the DOCUMENT states carries its verbatim span, and the producer —
  not the model — runs the one citation rule (#3389) on it against the text it
  already holds;
* a position with no quote, or with a quote the document does not carry, is
  kept and labelled ``model_knowledge`` — the second marked ``unanchored`` so
  the render never puts the model's words between « » (the #3415/#3427 shape);
* Act I says which is which, per player, and its drafting rule gives each its
  register: « le texte présente X comme … » on an anchored stance, the
  historian's « on sait par ailleurs que … » on model knowledge.

The two documents below are synthetic and opaque: one where the text opposes two
actors head-on, one where an institution is declared part of the speaker's
resolve. A fake strategist that merges the first pair, or that disengages the
second institution, reaches Act I as the document's reading on the pre-fix tree
— that is the born red this file measures.

No LLM, no JVM, no network: the fakes are plain async callables.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from argumentation_analysis.agents.core.context import (
    MODEL_KNOWLEDGE_BASIS,
    TEXT_BASIS,
)
from argumentation_analysis.agents.core.context.strategist import (
    StrategicRead,
    build_strategic_read,
)
from argumentation_analysis.agents.core.reading import ANCHOR_UNANCHORED
from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    Act1Evidence,
    _format_strategic_block,
    build_act1_prompt,
)

#: Two actors the text opposes head-on (the shape of the second measured doc).
DOC_A = (
    "La commission a rendu son avis au début du mois. "
    "Notre ministère combat ce texte et ne siègera pas à la table de ceux qui "
    "le portent. "
    "Ceux qui le portent y voient la seule issue possible et le disent partout. "
    "Nous demandons son retrait avant la prochaine séance."
)
QUOTE_A = "combat ce texte et ne siègera pas à la table"

#: An institution the text declares part of the speaker's resolve (the first
#: measured doc). The misread says it is not engaged.
DOC_B = (
    "Le gouvernement a décidé de porter la réforme jusqu'au bout. "
    "L'assemblée s'y est jointe sans réserve et votera le budget en conséquence. "
    "Rien ne nous fera reculer."
)
QUOTE_B = "s'y est jointe sans réserve"


def _state(raw_text: str):
    return SimpleNamespace(
        raw_text=raw_text,
        source_metadata={"speaker": "Speaker_A", "venue": "assembly"},
        stakes_and_stakeholders={"stakes": [], "stakeholders": []},
    )


def _llm(payload):
    """A fake model returning a fixed JSON document."""

    async def _call(prompt: str) -> str:
        return json.dumps(payload)

    return _call


def _payload(players, options=("retrait", "maintien")):
    """A strategist answer: players, two options, a two-player profile."""
    preferences = {}
    for index, player in enumerate(players):
        preferences[player["name"]] = (
            list(options) if index % 2 == 0 else list(reversed(options))
        )
    return {
        "players": players,
        "options": list(options),
        "preferences": preferences,
        "reading": "Deux camps opposés sur le même dispositif.",
    }


async def _read(payload, raw_text):
    result = await build_strategic_read(_state(raw_text), _llm(payload))
    return result, result.to_state()


def _evidence(players_state):
    return Act1Evidence(strategic_read=players_state)


# ============================================================================
# The producer — a stance the document states carries its quote
# ============================================================================


class TestAStanceIsAnchoredOnTheDocument:
    async def test_a_stance_the_text_states_carries_its_quote(self):
        players = [
            {"name": "P1", "role": "ministère", "stance": "against", "quote": QUOTE_A},
            {"name": "P2", "role": "porteurs", "stance": "for"},
        ]
        result, state = await _read(_payload(players), DOC_A)

        assert result.status == "ok"
        anchored, model = state["players"]
        assert anchored["basis"] == TEXT_BASIS
        assert anchored["quote"] == QUOTE_A
        # The offset LOCATES the passage: it is the document's own index, not a
        # placeholder that would centre a window nowhere.
        assert isinstance(anchored["offset"], int)
        assert DOC_A[anchored["offset"] : anchored["offset"] + len(QUOTE_A)] == QUOTE_A
        # The other player carried no quote and stays ordinary model knowledge.
        assert model["basis"] == MODEL_KNOWLEDGE_BASIS
        assert "quote" not in model

    async def test_a_stance_without_a_quote_is_model_knowledge(self):
        players = [
            {"name": "P1", "role": "ministère", "stance": "against"},
            {"name": "P2", "role": "porteurs", "stance": "for"},
        ]
        _, state = await _read(_payload(players), DOC_A)

        for player in state["players"]:
            assert player["basis"] == MODEL_KNOWLEDGE_BASIS
            # Byte-identical shape: a player that carried neither a quote nor
            # an anchor gains no key it did not have before #3430.
            assert "quote" not in player
            assert "anchor" not in player

    async def test_a_quote_the_document_does_not_carry_is_kept_but_unanchored(self):
        """The pendulum this refuses: dropping the position instead of the quote."""
        players = [
            {
                "name": "P1",
                "role": "ministère",
                "stance": "against",
                "quote": "une phrase que le document ne porte pas",
            },
            {"name": "P2", "role": "porteurs", "stance": "for"},
        ]
        _, state = await _read(_payload(players), DOC_A)

        player = state["players"][0]
        assert player["name"] == "P1"  # kept
        assert player["stance"] == "against"  # kept
        assert player["basis"] == MODEL_KNOWLEDGE_BASIS
        assert player["anchor"] == ANCHOR_UNANCHORED
        # The model's words are never presented as the document's.
        assert not player.get("quote")
        assert "offset" not in player

    async def test_the_second_document_anchors_its_institution(self):
        players = [
            {"name": "P1", "role": "assemblée", "stance": "for", "quote": QUOTE_B},
            {"name": "P2", "role": "gouvernement", "stance": "for"},
        ]
        _, state = await _read(_payload(players), DOC_B)

        assert state["players"][0]["basis"] == TEXT_BASIS
        assert state["players"][0]["quote"] == QUOTE_B


# ============================================================================
# The label is computed, never chosen by the model
# ============================================================================


class TestTheModelCannotClaimTheText:
    async def test_a_model_basis_field_is_dropped_without_a_quote(self):
        players = [
            {"name": "P1", "role": "ministère", "stance": "against", "basis": "text"},
            {"name": "P2", "role": "porteurs", "stance": "for"},
        ]
        _, state = await _read(_payload(players), DOC_A)

        assert [p["basis"] for p in state["players"]] == [MODEL_KNOWLEDGE_BASIS] * 2

    async def test_a_model_cannot_bypass_the_citation_rule(self):
        """A reply claiming ``text`` with an absent quote is still unanchored."""
        players = [
            {
                "name": "P1",
                "role": "ministère",
                "stance": "against",
                "basis": "text",
                "anchor": "",
                "quote": "le document ne dit rien de tel",
            },
            {"name": "P2", "role": "porteurs", "stance": "for"},
        ]
        _, state = await _read(_payload(players), DOC_A)

        player = state["players"][0]
        assert player["basis"] == MODEL_KNOWLEDGE_BASIS
        assert player["anchor"] == ANCHOR_UNANCHORED

    def test_a_hand_built_read_cannot_smuggle_a_text_basis(self):
        """A ``text`` basis without a quote AND a locating offset does not survive."""
        read = StrategicRead(
            players=[
                {"name": "P1", "basis": TEXT_BASIS, "quote": "", "offset": 0},
                {"name": "P2", "basis": TEXT_BASIS, "quote": "x", "offset": None},
            ]
        )
        assert [p["basis"] for p in read.to_state()["players"]] == [
            MODEL_KNOWLEDGE_BASIS,
            MODEL_KNOWLEDGE_BASIS,
        ]


# ============================================================================
# Act I tells the two apart
# ============================================================================


class TestActOneTellsTheTwoApart:
    def _merged_read(self):
        """The measured misread: two opposed actors carried by ONE merged stance."""
        return {
            "players": [
                {
                    "name": "P1",
                    "role": "ministère",
                    "stance": "for",
                    "basis": MODEL_KNOWLEDGE_BASIS,
                },
                {
                    "name": "P2",
                    "role": "porteurs",
                    "stance": "for",
                    "basis": MODEL_KNOWLEDGE_BASIS,
                },
            ],
            "options": ["retrait", "maintien"],
            "reading": "Une seule option est portée par les deux acteurs.",
            "game": {"status": "insufficient_profile"},
        }

    def test_the_block_names_each_stance_provenance(self):
        read = {
            "players": [
                {
                    "name": "P1",
                    "role": "ministère",
                    "stance": "against",
                    "basis": TEXT_BASIS,
                    "quote": QUOTE_A,
                    "offset": DOC_A.find(QUOTE_A),
                },
                {"name": "P2", "role": "porteurs", "stance": "for"},
                {
                    "name": "P3",
                    "role": "assemblée",
                    "stance": "for",
                    "anchor": ANCHOR_UNANCHORED,
                },
            ]
        }
        block = _format_strategic_block(read)

        assert f"le texte dit : « {QUOTE_A} »" in block
        # #3461 — the no-quote label says UNVERIFIED, never absent.
        assert "savoir du modèle, sans citation" in block
        assert "le texte ne l'énonce pas" not in block
        assert "citation non ancrée" in block

    def test_a_merged_position_never_reaches_act_one_as_the_texts(self):
        """Born red: on the pre-fix tree the block carried no provenance at all."""
        prompt = build_act1_prompt(_evidence(self._merged_read()))

        # #3461 — same deliberate relabel on the full prompt.
        assert "savoir du modèle, sans citation" in prompt
        # Nothing here is presented as the document's words.
        assert "le texte dit :" not in prompt

    def test_the_drafting_rule_gives_each_register(self):
        prompt = build_act1_prompt(_evidence(self._merged_read()))

        assert "« le texte présente X comme … »" in prompt
        assert "« on sait par ailleurs que … »" in prompt
        assert "Aucune position n'est attribuée au texte sans sa citation." in prompt

    def test_an_anchored_stance_may_be_quoted(self):
        read = {
            "players": [
                {
                    "name": "P1",
                    "role": "assemblée",
                    "stance": "for",
                    "basis": TEXT_BASIS,
                    "quote": QUOTE_B,
                    "offset": DOC_B.find(QUOTE_B),
                }
            ]
        }
        prompt = build_act1_prompt(_evidence(read))

        assert f"le texte dit : « {QUOTE_B} »" in prompt


# ============================================================================
# Anti-pendulum — the strategist is not stripped down to quotes
# ============================================================================


class TestTheReadingKeepsItsValue:
    async def test_a_failed_quote_does_not_lose_the_player(self):
        players = [
            {
                "name": "P1",
                "role": "ministère",
                "stance": "against",
                "quote": "passage absent du document",
            },
            {"name": "P2", "role": "porteurs", "stance": "for"},
        ]
        result, state = await _read(_payload(players), DOC_A)

        assert len(state["players"]) == 2
        assert state["reading"]
        # The game is still computed from the profile the model declared.
        assert result.game["status"] in ("ok", "ok_completed", "no_condorcet_winner")
        assert "Joueurs" in _format_strategic_block(state)
        assert "Lecture :" in _format_strategic_block(state)

    def test_an_empty_read_still_says_it_is_absent(self):
        block = _format_strategic_block({})

        assert "aucune lecture stratégique" in block
