"""#3556 — the player's basis is checked against the document, both ways.

Cycle 7 measured two severe M2 items that trace to ``anchor_player`` deciding
a player's basis from the REPLY alone:

* a player the document names, whose reply carried no quote, was labelled
  plain ``model_knowledge`` — and Act I wrote the position « au registre de
  l'historien », as knowledge from OUTSIDE the text, for an actor the text
  itself carries;
* a player anchored on a quote the document does carry, but whose passage is
  addressed to another party, got ``basis: text`` by the quote's presence
  alone — and Act I could quote that passage as the player's position.

The repair adds two document-side checks, both run by the PRODUCER on the
text it already holds (the reply's omission must not decide what the text
says):

* no quote + the text names the player → ``named_offset``, where the text
  carries the name; the unquoted stance itself stays a reading (#3461);
* quote located + the sentence that carries it names ANOTHER player of the
  same read (whole name or role, as the reply gives them) and not this one
  → ``anchor="unrelated"``: the passage is kept as the record of what was
  offered, but never renders as this player's position. A passage nobody's
  vocabulary claims keeps #3430's anchor — unproven is not disproven, and
  the speaker's own declarations, whose name the excerpt never carries,
  must not be stripped by a rule that cannot see speech attribution.

Anti-pendulum, the two kept lines: #3430's unquoted players stay (dropping
them was the refused pendulum), and #3461's rule holds — the no-quote label
says UNVERIFIED, never absent. ``test_strategist_anchor_3430.py`` is the
positive control and must pass on both sides.

The two documents below are synthetic and opaque. No LLM, no JVM, no
network: the fakes are plain async callables.
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

try:  # Born-red granularity: on main the constant does not exist yet.
    from argumentation_analysis.agents.core.reading import ANCHOR_UNRELATED
except ImportError:  # pragma: no cover — main only, until #3556 lands
    ANCHOR_UNRELATED = "unrelated"

from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    Act1Evidence,
    _format_strategic_block,
    build_act1_prompt,
)

#: The first line names both parties; only one of them comes back with a
#: name the text carries.
DOC_NAMED = (
    "La commission et le conseil se sont saisis du texte ce matin. "
    "La commission en demande le retrait avant la fin du mois. "
    "Le conseil attend l'avis de l'assemblée avant de trancher."
)

#: A sentence about one party, offered as another party's position: the
#: quote itself is verbatim in the document (the #3430 check passes).
DOC_MIS = (
    "L'association a rendu son rapport public ce matin. "
    "Le syndicat, lui, demandait encore hier que le texte soit retiré. "
    "Personne n'a cédé."
)
QUOTE_MIS = "demandait encore hier que le texte soit retiré"


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
    preferences = {}
    for index, player in enumerate(players):
        preferences[player["name"]] = (
            list(options) if index % 2 == 0 else list(reversed(options))
        )
    return {
        "players": players,
        "options": list(options),
        "preferences": preferences,
        "reading": "Deux parties se partagent la décision.",
    }


async def _read(payload, raw_text):
    result = await build_strategic_read(_state(raw_text), _llm(payload))
    return result, result.to_state()


def _evidence(players_state):
    return Act1Evidence(strategic_read=players_state)


# ============================================================================
# The name check — a player the document names is not outside knowledge
# ============================================================================


class TestTheDocumentNamesThePlayer:
    async def test_a_named_player_without_a_quote_records_where(self):
        """Born red on main: the no-quote branch never looked at the text."""
        players = [
            {"name": "la commission", "role": "rapporteuse", "stance": "against"},
            {"name": "la fédération", "role": "observatrice", "stance": "ambivalent"},
        ]
        _, state = await _read(_payload(players), DOC_NAMED)

        named, unnamed = state["players"]
        # The stance itself stays an unverified reading (#3461 kept).
        assert named["basis"] == MODEL_KNOWLEDGE_BASIS
        assert "quote" not in named
        assert "anchor" not in named
        # But the text CARRIES the name, and the record says where.
        assert isinstance(named["named_offset"], int)
        assert (
            DOC_NAMED[
                named["named_offset"] : named["named_offset"] + len("la commission")
            ].lower()
            == "la commission"
        )
        # The other player's name is nowhere in the text: byte-identical
        # pre-#3556 shape (no key gained).
        assert unnamed["basis"] == MODEL_KNOWLEDGE_BASIS
        assert "named_offset" not in unnamed
        assert "quote" not in unnamed
        assert "anchor" not in unnamed

    async def test_the_model_cannot_smuggle_a_named_offset(self):
        """``named_offset`` is computed from the text, never relayed."""
        players = [
            {
                "name": "la commission",
                "role": "rapporteuse",
                "stance": "against",
                "named_offset": 9999,
            }
        ]
        _, state = await _read(_payload(players), DOC_NAMED)

        assert state["players"][0]["named_offset"] == 0

    def test_the_name_check_is_a_whole_word(self):
        """#2012, on names: a word boundary would hide inside a longer word."""
        from argumentation_analysis.agents.core.context.strategist import (
            _name_in_text,
        )

        assert _name_in_text("commission", "La Commission siège") == 3
        assert _name_in_text("commission", "la commissionnelle siège") is None
        assert _name_in_text("commission", "") is None


# ============================================================================
# The concern check — a located passage is not every player's
# ============================================================================


class TestThePassageMustConcernThePlayer:
    async def test_an_anchor_on_a_passage_addressed_to_another_party(self):
        """Born red on main: quote-occurs alone set ``basis: text``.

        The addressee is a player of the SAME read (the measured doc had six
        players, the passage's addressee among them) — the reply's own
        vocabulary is what lets the producer recognise the passage as
        another party's.
        """
        players = [
            {
                "name": "l'association",
                "role": "groupe de pression",
                "stance": "against",
                "quote": QUOTE_MIS,
            },
            {"name": "le syndicat", "role": "salariés", "stance": "against"},
        ]
        _, state = await _read(_payload(players), DOC_MIS)

        player = state["players"][0]
        # The passage is kept as the record of what was offered…
        assert player["quote"] == QUOTE_MIS
        assert isinstance(player["offset"], int)
        assert (
            DOC_MIS[player["offset"] : player["offset"] + len(QUOTE_MIS)] == QUOTE_MIS
        )
        # …but it is NOT this player's text basis.
        assert player["basis"] == MODEL_KNOWLEDGE_BASIS
        assert player["anchor"] == ANCHOR_UNRELATED

    async def test_a_speaker_no_one_names_keeps_their_own_declaration(self):
        """The refused pendulum: #3430's never-named anchors must stand.

        The document never carries this player's name or role; the quote is
        their own declaration (the speaker's shape — whole cycle panels are
        full of them). Unproven is not disproven: the anchor stands.
        """
        players = [
            {
                "name": "l'orateur jamais nommé",
                "role": "celui qui parle et tranche",
                "stance": "for",
                "quote": QUOTE_MIS,
            },
        ]
        _, state = await _read(_payload(players), DOC_MIS)

        player = state["players"][0]
        assert player["basis"] == TEXT_BASIS
        assert player["quote"] == QUOTE_MIS
        assert "anchor" not in player

    async def test_the_same_passage_keeps_anchoring_the_player_it_concerns(self):
        """Ask 3: a correct anchor is unchanged (control, green on main too)."""
        players = [
            {
                "name": "le syndicat",
                "role": "salariés",
                "stance": "against",
                "quote": QUOTE_MIS,
            },
        ]
        _, state = await _read(_payload(players), DOC_MIS)

        player = state["players"][0]
        assert player["basis"] == TEXT_BASIS
        assert player["quote"] == QUOTE_MIS
        assert "anchor" not in player

    async def test_a_short_form_of_the_player_keeps_the_anchor(self):
        """A peer named in the passage does not refuse what the passage also
        carries of THIS player, even under a short form of the name — the
        recorded panels anchor ``Judge Douglas`` on sentences that say
        ``Douglas``. Control: green on main too.
        """
        players = [
            {
                "name": "la commission nationale",
                "role": "autorité de contrôle",
                "stance": "for",
                "quote": "La commission et le conseil se sont saisis du texte",
            },
            {"name": "le conseil", "role": "second organe", "stance": "for"},
        ]
        _, state = await _read(_payload(players), DOC_NAMED)

        player = state["players"][0]
        assert player["basis"] == TEXT_BASIS
        assert player["quote"] == "La commission et le conseil se sont saisis du texte"
        assert "anchor" not in player

    def test_an_unrelated_anchor_cannot_smuggle_a_text_basis(self):
        """A hand-built read cannot re-arm what the producer refused."""
        read = StrategicRead(
            players=[
                {
                    "name": "l'association",
                    "basis": TEXT_BASIS,
                    "quote": QUOTE_MIS,
                    "offset": DOC_MIS.find(QUOTE_MIS),
                    "anchor": ANCHOR_UNRELATED,
                }
            ]
        )
        assert read.to_state()["players"][0]["basis"] == MODEL_KNOWLEDGE_BASIS

    async def test_an_absent_quote_stays_unanchored_not_unrelated(self):
        """The pre-existing outcome keeps its own marker (control)."""
        players = [
            {
                "name": "l'association",
                "role": "groupe de pression",
                "stance": "against",
                "quote": "une phrase que le document ne porte pas",
            }
        ]
        _, state = await _read(_payload(players), DOC_MIS)

        player = state["players"][0]
        assert player["basis"] == MODEL_KNOWLEDGE_BASIS
        assert player["anchor"] == ANCHOR_UNANCHORED


# ============================================================================
# Act I — the two new labels, and the register they command
# ============================================================================


class TestActOneTellsTheTwoApart:
    async def test_the_block_labels_the_unrelated_anchor(self):
        players = [
            {
                "name": "l'association",
                "role": "groupe de pression",
                "stance": "against",
                "quote": QUOTE_MIS,
            },
            {
                "name": "le syndicat",
                "role": "salariés",
                "stance": "against",
                "quote": QUOTE_MIS,
            },
        ]
        _, state = await _read(_payload(players), DOC_MIS)
        block = _format_strategic_block(state)

        # The player the passage concerns keeps its quotation…
        assert f"le texte dit : « {QUOTE_MIS} »" in block
        # …and the other NEVER has it presented as their position.
        assert "l'association (groupe de pression, against) — le texte dit" not in block
        assert "citation sans rapport" in block

    async def test_the_block_says_the_text_names_the_player(self):
        players = [
            {"name": "la commission", "role": "rapporteuse", "stance": "against"},
            {"name": "la fédération", "role": "observatrice", "stance": "ambivalent"},
        ]
        _, state = await _read(_payload(players), DOC_NAMED)
        block = _format_strategic_block(state)

        # The stance stays an unverified reading — #3461's wording kept…
        assert "savoir du modèle, sans citation" in block
        # …but exactly the player the text names is not read as outside it.
        assert block.count("le texte nomme ce joueur") == 1
        assert "la commission (rapporteuse, against)" in block
        assert "la fédération (observatrice, ambivalent)" in block

    async def test_the_register_rule_separates_named_from_outside(self):
        players = [
            {"name": "la commission", "role": "rapporteuse", "stance": "against"},
            {
                "name": "l'association",
                "role": "groupe de pression",
                "stance": "against",
                "quote": QUOTE_MIS,
            },
        ]
        _, state = await _read(_payload(players), DOC_MIS)
        prompt = build_act1_prompt(_evidence(state))

        # A named actor is a reading OF the text, never outside knowledge.
        assert "un acteur que le document nomme s'écrit comme" in prompt
        # An unrelated citation is never the player's position.
        assert "n'est JAMAIS la position de ce joueur" in prompt
        # #3430's registers and #3461's rule are kept as they were.
        assert "« on sait par ailleurs que … »" in prompt
        assert "Aucune position n'est attribuée au texte sans sa citation." in prompt
        assert "le texte ne l'énonce pas" not in prompt
