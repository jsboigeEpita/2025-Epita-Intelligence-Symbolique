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

#: The player is named under an elided determiner at its first mention, then
#: called by ANOTHER determiner in the passage it is offered — while a peer's
#: whole name sits in that same sentence. Synthetic (#3556 elision blocker).
DOC_ELIDED = (
    "L'association a rendu son rapport public ce matin. "
    "Le syndicat a suivi cette association dans sa demande de retrait. "
    "Personne n'a cédé."
)
QUOTE_ELIDED = "a suivi cette association dans sa demande de retrait"

#: The text names the commission and states its demand; the offered quote
#: differs from what the text carries by ONE inserted word — the #3430
#: verbatim check fails, the name check must not (#3556, c12).
DOC_NEAR_MISS = (
    "La commission et le conseil se sont saisis du texte ce matin. "
    "La commission exige le retrait du texte avant la fin du mois. "
    "Le conseil attend l'avis de l'assemblée avant de trancher."
)
QUOTE_NEAR_MISS = "exige le retrait intégral du texte avant la fin du mois"


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
        recorded panels anchor ``Mayor Ferrand`` on sentences that say
        ``Ferrand``. Control: green on main too.
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

    def test_the_distinctive_words_read_through_a_french_elision(self):
        """The elided determiner is not part of the name (#3556 blocker).

        ``l'association`` yields ``association`` — the promise the comment
        above ``_NAME_STOP_WORDS`` makes — and ``d'une`` yields nothing at
        all, which also closes the ``d'une`` minor of the review.
        """
        from argumentation_analysis.agents.core.context.strategist import (
            _distinctive_words,
        )

        assert "association" in _distinctive_words("l'association")
        assert "état" in _distinctive_words("l'État")
        # ``d'une`` is the elided article plus a function word: nothing is left.
        assert _distinctive_words("d'une") == []
        # A long head is not an elision; the token stays whole.
        assert _distinctive_words("lorsqu'association") == ["lorsqu'association"]

    async def test_a_french_elision_does_not_refuse_the_players_own_passage(self):
        """Born red on ``228bd276e``: ``l'association`` stayed one opaque token.

        The passage calls the player by another determiner (« cette
        association ») and carries a peer's whole name in the same sentence,
        so a concern check that cannot read through the elision falls to the
        peer loop and refuses the player its OWN passage as ``unrelated``.
        The base ``d664ed7cf`` anchored it correctly: this restores that.
        """
        players = [
            {
                "name": "l'association",
                "role": "groupe de pression",
                "stance": "against",
                "quote": QUOTE_ELIDED,
            },
            {"name": "le syndicat", "role": "salariés", "stance": "against"},
        ]
        _, state = await _read(_payload(players), DOC_ELIDED)

        player = state["players"][0]
        assert player["basis"] == TEXT_BASIS
        assert player["quote"] == QUOTE_ELIDED
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
# The unanchored branch — a failed quote is not a failed name check
# ============================================================================


class TestTheUnanchoredQuoteStillSeesTheText:
    """#3556 (c12) — the unanchored branch never looked at the document.

    A player whose offered quote the text does not carry verbatim, but whose
    name the text DOES carry, rendered exactly like outside knowledge — the
    same omission the no-quote branch repaired. And the control that ran is
    ``quote_occurs_in`` on the OFFERED string: it establishes that this
    citation was not found, never that the text lacks the passage.
    """

    async def test_an_unanchored_player_the_text_names_records_where(self):
        """Born red on main: the unanchored branch returned early."""
        players = [
            {
                "name": "la commission",
                "role": "rapporteuse",
                "stance": "against",
                "quote": QUOTE_NEAR_MISS,
            }
        ]
        _, state = await _read(_payload(players), DOC_NEAR_MISS)

        player = state["players"][0]
        # The offered quote is kept out of the record, as before…
        assert player["basis"] == MODEL_KNOWLEDGE_BASIS
        assert player["anchor"] == ANCHOR_UNANCHORED
        assert "quote" not in player
        # …but the text CARRIES the player's name, and the record says where.
        assert isinstance(player["named_offset"], int)
        assert (
            DOC_NEAR_MISS[
                player["named_offset"] : player["named_offset"] + len("la commission")
            ].lower()
            == "la commission"
        )

    async def test_the_model_cannot_smuggle_an_unanchored_named_offset(self):
        """``named_offset`` is computed from the text, never relayed."""
        players = [
            {
                "name": "la commission",
                "role": "rapporteuse",
                "stance": "against",
                "quote": QUOTE_NEAR_MISS,
                "named_offset": 9999,
            }
        ]
        _, state = await _read(_payload(players), DOC_NEAR_MISS)

        assert state["players"][0]["named_offset"] == 0

    async def test_an_unanchored_player_the_text_does_not_name_gains_nothing(self):
        """Control: the unnamed unanchored player keeps its exact shape."""
        players = [
            {
                "name": "la fédération",
                "role": "observatrice",
                "stance": "ambivalent",
                "quote": QUOTE_NEAR_MISS,
            }
        ]
        _, state = await _read(_payload(players), DOC_NEAR_MISS)

        player = state["players"][0]
        assert player["basis"] == MODEL_KNOWLEDGE_BASIS
        assert player["anchor"] == ANCHOR_UNANCHORED
        assert "named_offset" not in player
        assert "quote" not in player


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

    async def test_the_block_states_the_control_that_ran_on_an_unanchored_quote(self):
        """Born red on main: the label wrote « le texte ne porte pas ce
        passage » — a claim about the TEXT, when the only control that ran
        (quote_occurs_in on the OFFERED string) established that this
        citation was not found verbatim (#3556, c12).
        """
        players = [
            {
                "name": "la commission",
                "role": "rapporteuse",
                "stance": "against",
                "quote": QUOTE_NEAR_MISS,
            },
            {
                "name": "la fédération",
                "role": "observatrice",
                "stance": "ambivalent",
                "quote": QUOTE_NEAR_MISS,
            },
        ]
        _, state = await _read(_payload(players), DOC_NEAR_MISS)
        block = _format_strategic_block(state)

        # The label names the control: the proposed QUOTE was not found…
        assert (
            "citation non ancrée : la citation proposée n'a pas été "
            "retrouvée" in block
        )
        # …never what the text lacks.
        assert "le texte ne porte pas ce passage" not in block
        # Exactly the player the text names gets the naming line.
        assert block.count("le texte nomme ce joueur") == 1

    async def test_the_register_rule_names_the_control_that_ran(self):
        """The prompt's unanchored exception states the same measured fact."""
        players = [
            {
                "name": "la commission",
                "role": "rapporteuse",
                "stance": "against",
                "quote": QUOTE_NEAR_MISS,
            }
        ]
        _, state = await _read(_payload(players), DOC_NEAR_MISS)
        prompt = build_act1_prompt(_evidence(state))

        assert "la citation proposée n'a pas été retrouvée telle quelle" in prompt
        assert "le passage fourni n'a pas été retrouvé dans le document" not in prompt
        # The register rule still routes a named player to a reading OF the
        # text — the unanchored label now carries the naming line.
        assert "un acteur que le document nomme s'écrit comme" in prompt


#: #3556 (c13) — the naming sentence itself carries the reply's
#: role/interests vocabulary: the SECOND occurrence's sentence says what
#: the reply files under the role, the first occurrence's says nothing of
#: it. The check must read every naming sentence, not only the recorded
#: offset's.
DOC_NAMING_SENTENCE = (
    "Le bureau a publié son avis ce matin. "
    "La mission régionale a répondu la semaine suivante. "
    "Puis la mission régionale a signé la charte de la coopération."
)
NAMING_SENTENCE_HIT = "Puis la mission régionale a signé la charte de la coopération."

#: #3556 (c13) — the naming sentence carries the role's morphological
#: FAMILY, noun in the text against adjective in the reply, never the word
#: itself: an exact-word rule scores zero on it.
DOC_NAMING_FAMILY = (
    "Le préau s'est vidé à midi. "
    "La fédération a repris l'institution de la province."
)

#: #3556 (c13) control — the naming sentence carries none of the role's
#: vocabulary, family included: the exact pre-c13 shape, unchanged.
DOC_NAMING_QUIET = (
    "Le secrétariat a diffusé la note. " "La province a répondu par courrier."
)

#: #3556 (c14) — the compound the text carries by its conjunction: every
#: conjunct INSIDE ONE sentence, the full string never contiguous.
DOC_COMPOUND = (
    "Le préau s'est vidé à midi. "
    "Les archivistes et les greffiers municipaux ont signé "
    "le registre d'accueil."
)

#: #3556 (c14) control — the text carries the first conjunct and a
#: REWORDED second (« experts des comptes » against « experts
#: comptables »): the player stays unnamed, byte-identically.
DOC_COMPOUND_MISS = (
    "Le comité a statué sans débat. "
    "Les archivistes et les experts des comptes publics ont validé "
    "le relevé."
)

#: #3556 (c14) control — the two conjuncts sit in DIFFERENT sentences:
#: the document never conjoins the parties, so the player stays unnamed.
DOC_COMPOUND_SPLIT = (
    "Les archivistes se sont réunis lundi. " "Les greffiers municipaux ont signé mardi."
)

#: #3556 (c14) control — the first conjunct occurs ALONE before the whole
#: name: the plain whole-name check runs first, so the offset is the whole
#: name's, not the lone conjunct's earlier one.
DOC_COMPOUND_WHOLE_FIRST = (
    "Les archivistes se sont réunis lundi. "
    "Puis les archivistes et greffiers municipaux ont signé le registre."
)


class TestTheNamingSentenceCarriesTheRole:
    """#3556 (c13) — the producer already records WHERE the text names the
    player (c12). When the naming sentence also carries the reply's own
    role/interests vocabulary, it records the sentence itself — computed
    from the text, never relayed from the reply. Born red on ``e4eb7e74d``:
    no ``naming_span``/``naming_sentence`` key exists there."""

    async def test_the_span_is_the_sentence_that_carries_the_vocabulary(self):
        """The vocabulary sits in the SECOND occurrence's sentence — the
        check reads every naming sentence, and records the span of the one
        that hits."""
        players = [
            {
                "name": "la mission régionale",
                "role": "coordinateur de la coopération",
                "stance": "for",
                "interests": "défendre la charte commune",
            }
        ]
        _, state = await _read(_payload(players), DOC_NAMING_SENTENCE)
        player = state["players"][0]

        assert "named_offset" in player
        span = player["naming_span"]  # born red: KeyError on main
        lo, hi = span
        assert DOC_NAMING_SENTENCE[lo:hi].strip() == NAMING_SENTENCE_HIT
        assert player["naming_sentence"] == NAMING_SENTENCE_HIT

    async def test_the_family_shape_hits_where_the_exact_word_cannot(self):
        """The recorded family shape: the text's « institution » against the
        reply's « institutionnel » — same word family, never the same word.
        An exact-word check stays silent; the family rule fires."""
        players = [
            {
                "name": "la province",
                "role": "gardien du cadre institutionnel",
                "stance": "against",
            }
        ]
        _, state = await _read(_payload(players), DOC_NAMING_FAMILY)
        player = state["players"][0]

        assert "naming_span" in player, (
            "« institution » must ride « institutionnel » — the recorded "
            "family shape, where the exact-word rule scores zero"
        )
        assert "institution" in player["naming_sentence"]

    async def test_a_naming_sentence_without_the_vocabulary_changes_nothing(self):
        """The c13 control: no role word in the naming sentence (family
        included) → no span recorded, the exact pre-c13 shape."""
        players = [
            {
                "name": "la province",
                "role": "gardien de la concurrence",
                "stance": "against",
            }
        ]
        _, state = await _read(_payload(players), DOC_NAMING_QUIET)
        player = state["players"][0]

        assert "named_offset" in player
        assert "naming_span" not in player
        assert "naming_sentence" not in player

    async def test_the_unanchored_branch_gets_the_same_sentence(self):
        """The naming check runs wherever ``named_offset`` is set — the
        unanchored branch too, not only the no-quote one."""
        players = [
            {
                "name": "la mission régionale",
                "role": "coordinateur de la coopération",
                "stance": "for",
                "quote": "a signé la charte de la coopération élargie",
            }
        ]
        _, state = await _read(_payload(players), DOC_NAMING_SENTENCE)
        player = state["players"][0]

        assert player["anchor"] == ANCHOR_UNANCHORED
        assert player["naming_sentence"] == NAMING_SENTENCE_HIT

    async def test_a_text_basis_player_gets_no_naming_sentence(self):
        """The check is for players the text NAMES but does not quote: an
        anchored player keeps the c7 shape — the stance quote is the only
        quote."""
        players = [
            {
                "name": "la commission",
                "role": "rapporteuse",
                "stance": "against",
                "quote": "en demande le retrait avant la fin du mois",
            }
        ]
        _, state = await _read(_payload(players), DOC_NAMED)
        player = state["players"][0]

        assert player["basis"] == TEXT_BASIS
        assert "naming_span" not in player


class TestActOneQuotesTheNamingSentence:
    """#3556 (c13) — on such a hit the label quotes the naming sentence
    verbatim and truncated, as what the text says WHERE it names the
    player. The stance basis is unchanged: the naming quote is never the
    position (#3461, #3389). Born red on ``e4eb7e74d``."""

    async def test_the_label_quotes_what_the_text_says_where_it_names(self):
        players = [
            {
                "name": "la mission régionale",
                "role": "coordinateur de la coopération",
                "stance": "for",
            }
        ]
        _, state = await _read(_payload(players), DOC_NAMING_SENTENCE)
        block = _format_strategic_block(state)

        assert "en le nommant, le texte dit" in block
        assert f"« {NAMING_SENTENCE_HIT} »" in block
        # The stance basis is unchanged — a naming quote is not a stance quote.
        assert "le texte n'a pas été vérifié pour cette position" in block

    async def test_without_the_sentence_the_label_keeps_its_exact_shape(self):
        players = [
            {
                "name": "la province",
                "role": "gardien de la concurrence",
                "stance": "against",
            }
        ]
        _, state = await _read(_payload(players), DOC_NAMING_QUIET)
        block = _format_strategic_block(state)

        assert "en le nommant" not in block
        assert "le texte nomme ce joueur" in block

    async def test_the_register_rule_keeps_the_naming_quote_off_the_stance(self):
        """The drafting rule says what the naming quote may and may not
        stand for: the text's own words at the naming place — never the
        player's position."""
        players = [
            {
                "name": "la mission régionale",
                "role": "coordinateur de la coopération",
                "stance": "for",
            }
        ]
        _, state = await _read(_payload(players), DOC_NAMING_SENTENCE)
        prompt = build_act1_prompt(_evidence(state))

        assert "en le nommant, le texte dit" in prompt
        assert "jamais la position du joueur elle-même" in prompt
        # The c12 rules are kept as they were.
        assert "un acteur que le document nomme s'écrit comme" in prompt


class TestACompoundNameNamesThePlayer:
    """#3556 (c14) — a compound name on its conjunction names the player
    when EVERY conjunct occurs contiguously INSIDE ONE sentence: the
    text's own conjunction of the parties, never a word-bag of parts
    scattered through the document. The plain whole-name check runs first.
    A single missing or reworded conjunct leaves the player unnamed,
    byte-identically. Born red on ``e4eb7e74d``: the whole-string check
    alone refuses the recorded c14 player the text does carry."""

    async def test_every_conjunct_contiguous_names_the_player(self):
        players = [
            {
                "name": "Archivistes et greffiers municipaux",
                "role": "corps de greffe",
                "stance": "ambivalent",
            }
        ]
        _, state = await _read(_payload(players), DOC_COMPOUND)
        player = state["players"][0]

        # named_offset is the FIRST conjunct's offset, in that sentence.
        assert player["named_offset"] == DOC_COMPOUND.find("archivistes")

    async def test_conjuncts_in_two_sentences_leave_the_player_unnamed(self):
        """The tightener: each conjunct present, but never conjoined by
        the text — two different sentences name the two parties."""
        players = [
            {
                "name": "Archivistes et greffiers municipaux",
                "role": "corps de greffe",
                "stance": "ambivalent",
            }
        ]
        _, state = await _read(_payload(players), DOC_COMPOUND_SPLIT)
        player = state["players"][0]

        assert "named_offset" not in player

    async def test_the_whole_name_wins_over_a_lone_first_conjunct(self):
        """The plain check runs FIRST: where the whole name is contiguous,
        its offset stands even though the first conjunct occurs alone
        earlier in the text."""
        players = [
            {
                "name": "Archivistes et greffiers municipaux",
                "role": "corps de greffe",
                "stance": "ambivalent",
            }
        ]
        _, state = await _read(_payload(players), DOC_COMPOUND_WHOLE_FIRST)
        player = state["players"][0]

        whole = DOC_COMPOUND_WHOLE_FIRST.find("archivistes et greffiers")
        assert player["named_offset"] == whole
        assert player["named_offset"] != DOC_COMPOUND_WHOLE_FIRST.find("archivistes")

    async def test_one_reworded_conjunct_leaves_the_player_unnamed(self):
        players = [
            {
                "name": "Archivistes et experts comptables",
                "role": "corps de contrôle",
                "stance": "uncommitted",
            }
        ]
        _, state = await _read(_payload(players), DOC_COMPOUND_MISS)
        player = state["players"][0]

        assert "named_offset" not in player
        block = _format_strategic_block(state)
        assert "le texte nomme ce joueur" not in block
        # The unnamed path is byte-identical to the pre-c14 shape.
        assert "savoir du modèle, sans citation" in block

    async def test_a_contiguous_compound_keeps_its_whole_name_offset(self):
        """A compound the text carries whole keeps the plain check's offset
        — the first conjunct's IS the whole name's start. The lone-conjunct
        ordering case is its own control above."""
        doc = (
            "Le comité a statué. "
            "La fédération et confédération du bâtiment a suivi l'accord."
        )
        players = [
            {
                "name": "Fédération et confédération du bâtiment",
                "role": "chambre syndicale",
                "stance": "for",
            }
        ]
        _, state = await _read(_payload(players), doc)
        player = state["players"][0]

        assert player["named_offset"] == doc.find("fédération")


#: #3556 (c16) — the reply's name carries a leading article the text does
#: not repeat: the document names the player once, without any determiner.
#: The recorded c16 shape (a player kept severe by both judge families
#: because Act I filed a position the text states under outside knowledge).
#: Synthetic and opaque.
DOC_ARTICLE = (
    "L'assemblée a voté le budget sans débat. "
    "Alliance boréale livrera l'appui industriel promis dès l'automne. "
    "Le vote a été enregistré au procès-verbal."
)

#: #3556 (c16) control — the text carries the whole name WITH its article:
#: the plain whole-name check runs first, so the offset is the whole
#: name's, not the articleless form's later occurrence.
DOC_ARTICLE_WHOLE_FIRST = (
    "L'Alliance boréale a signé la charte dès le printemps. "
    "Alliance boréale livrera l'appui industriel promis dès l'automne."
)


class TestALeadingArticleIsTheReplysGrammar:
    """#3556 (c16) — a leading article in the REPLY's name is the reply's
    own grammar, not the document's: the text may name the player without
    it. The whole-name check keeps priority wherever the text carries the
    full string; only when it does not is ONE leading article stripped —
    a closed set, the name minus its determiner, never a word-bag. Born
    red on ``main``: the recorded c16 player stayed plain model knowledge
    with no ``named_offset``, because « Les … » never occurs where the
    text names « … » alone."""

    async def test_the_text_names_the_player_without_the_replys_article(self):
        players = [
            {
                "name": "L'Alliance boréale",
                "role": "partenaire industriel de l'effort",
                "stance": "ambivalent",
            }
        ]
        _, state = await _read(_payload(players), DOC_ARTICLE)
        player = state["players"][0]

        # The stance itself stays an unverified reading (#3461 kept).
        assert player["basis"] == MODEL_KNOWLEDGE_BASIS
        assert "quote" not in player
        assert "anchor" not in player
        # The text CARRIES the name without the article, and the record
        # says where — born red on main: no key exists there.
        offset = player["named_offset"]
        assert isinstance(offset, int)
        assert DOC_ARTICLE[offset : offset + len("Alliance boréale")].lower() == (
            "alliance boréale"
        )
        # The naming sentence fires on the same occurrence: it carries the
        # reply's own role vocabulary (« industriel »).
        assert player["naming_sentence"] == (
            "Alliance boréale livrera l'appui industriel promis dès l'automne."
        )

    async def test_the_whole_name_keeps_priority_over_the_articleless_form(self):
        """Control, green on main too: where the whole name occurs, its
        offset stands even though the articleless form occurs later."""
        players = [
            {
                "name": "L'Alliance boréale",
                "role": "partenaire industriel de l'effort",
                "stance": "ambivalent",
            }
        ]
        _, state = await _read(_payload(players), DOC_ARTICLE_WHOLE_FIRST)
        player = state["players"][0]

        whole = DOC_ARTICLE_WHOLE_FIRST.find("L'Alliance boréale")
        assert player["named_offset"] == whole
        assert player["named_offset"] != DOC_ARTICLE_WHOLE_FIRST.rfind("Alliance")

    async def test_no_article_to_strip_changes_nothing(self):
        """Control, green on main too: a name the text does not carry,
        with or without an article, keeps its exact pre-c16 shape."""
        players = [
            {
                "name": "Le comité des sages",
                "role": "arbitre bénévole",
                "stance": "for",
            }
        ]
        _, state = await _read(_payload(players), DOC_ARTICLE)
        player = state["players"][0]

        assert "named_offset" not in player
        assert "naming_span" not in player
        assert "naming_sentence" not in player

    def test_one_article_one_time_and_only_an_article(self):
        """The strip is ONE leading article from a closed set — never a
        bare preposition, never two, never the whole name."""
        from argumentation_analysis.agents.core.context.strategist import (
            _name_without_leading_article,
        )

        assert _name_without_leading_article("Les Ateliers réunis") == "Ateliers réunis"
        assert _name_without_leading_article("la commission") == "commission"
        assert _name_without_leading_article("L'Alliance boréale") == "Alliance boréale"
        assert _name_without_leading_article("des archivistes") == "archivistes"
        assert _name_without_leading_article("du bureau") == "bureau"
        assert _name_without_leading_article("The board") == "board"
        assert _name_without_leading_article("An alliance") == "alliance"
        # A bare preposition is not an article (a family name must survive).
        assert _name_without_leading_article("De Valmont") is None
        # Nothing left to name after the strip, or no article at all.
        assert _name_without_leading_article("Les") is None
        assert _name_without_leading_article("A") is None
        assert _name_without_leading_article("Alliance boréale") is None
        assert _name_without_leading_article("") is None


class TestActOneQuotesTheArticlelessNaming:
    """#3556 (c16) — the render path is the c13 one, unchanged: on an
    articleless hit the label quotes the naming sentence as what the text
    says where it names the player. Born red on ``main``."""

    async def test_the_label_quotes_the_sentence_the_text_carries(self):
        players = [
            {
                "name": "L'Alliance boréale",
                "role": "partenaire industriel de l'effort",
                "stance": "ambivalent",
            }
        ]
        _, state = await _read(_payload(players), DOC_ARTICLE)
        block = _format_strategic_block(state)
        prompt = build_act1_prompt(_evidence(state))

        sentence = "Alliance boréale livrera l'appui industriel promis dès l'automne."
        assert f"« {sentence} »" in block
        assert "en le nommant, le texte dit" in block
        assert "en le nommant, le texte dit" in prompt
        # The stance basis is unchanged — the naming quote is never the
        # position (#3461, #3389).
        assert "le texte n'a pas été vérifié pour cette position" in block
