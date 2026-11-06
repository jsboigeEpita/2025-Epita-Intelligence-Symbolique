"""#3461 — a provenance label never says what the text lacks.

Panel cycle 3b (#3374, 6-pass consensus) kept ONE severe item: an M2 on
the central thesis of one panel document, voted 4 of 6 passes. Act I had
written a player's stance as « savoir du modèle : le texte ne l'énonce
pas » — while the document states that stance in so many words. The
zero-shot read it correctly; the judge found the passage; the verdict on
that document went ZEROSHOT_WINS on this item alone.

The defect is the NEGATION, not the provenance (#3457 was right to keep
the text and the model's knowledge apart — the anti-pendulum). "No quote
was supplied" is not "the text does not state it": ``quote_occurs_in``
can prove a passage IS in the text; nothing in the pipeline ever searched
the document for an unquoted stance. The historical block's header has the
same shape (« jamais le contenu du texte »): the historian's reading
carries no quote either, so nothing stands behind the absence either.

The repair says WHERE a claim comes from, never what the text lacks:

* a no-quote player is model knowledge the text was NOT CHECKED for;
* both headers and the drafting rule say the same;
* the one negation that may be written is a check the pipeline actually
  RAN — the unanchored case, where ``quote_occurs_in`` failed on a
  supplied quote; that label keeps its exact wording (companion);
* an anchored stance still reads « le texte dit : « … » » (companion).

Born red on ``6690030ee``: the no-quote label, the strategic header and
the historical header all carry the unverified negation this file scans
for; companions are green pre-fix.

Synthetic opaque documents only. No LLM, no network.
"""

from __future__ import annotations

from argumentation_analysis.agents.core.context import (
    MODEL_KNOWLEDGE_BASIS,
    TEXT_BASIS,
)
from argumentation_analysis.agents.core.reading import ANCHOR_UNANCHORED
from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    Act1Evidence,
    _format_strategic_block,
    build_act1_prompt,
)

#: The synthetic document states, in so many words, the stance a no-quote
#: player then carries — the panel's measured shape, opaque vocabulary.
DOC = (
    "La commission a rendu son avis au début du mois. "
    "Notre ministère combat ce texte et ne siègera pas à la table de ceux "
    "qui le portent. "
    "Nous demandons son retrait avant la prochaine séance."
)
QUOTE = "combat ce texte et ne siègera pas à la table"

#: The unverified negation #3461 removes from the player label.
_OLD_LABEL = "le texte ne l'énonce pas"


def _no_quote_player_read():
    """One player, model knowledge, no quote — whose stance the DOC states."""
    return {
        "players": [
            {
                "name": "P1",
                "role": "ministère",
                "stance": "réservoir de mobilisation de la réforme",
                "basis": MODEL_KNOWLEDGE_BASIS,
            }
        ],
        "options": ["retrait", "maintien"],
        "reading": "Un acteur seul, porté par son appareil.",
        "game": {"status": "insufficient_profile"},
    }


class TestAProvenanceLabelNeverSaysWhatTheTextLacks:
    """Born red on ``6690030ee``: the negation the judge disproved."""

    def test_a_no_quote_player_never_reads_as_absent_from_the_text(self):
        """The DOC states the stance in so many words; nothing checked it.
        The label may say WHERE the stance comes from — never that the
        text does not state it."""
        block = _format_strategic_block(_no_quote_player_read())

        assert (
            "savoir du modèle" in block
        ), "anti-pendulum: the provenance itself stays — #3457 was right"
        assert _OLD_LABEL not in block, (
            "« le texte ne l'énonce pas » asserts an absence NO control "
            "established — the panel's one severe item (#3461)"
        )

    def test_the_strategic_header_defines_model_knowledge_as_unchecked(self):
        """The block header defined « savoir du modèle » by the same
        unverified negation — the writer relayed it to the reader."""
        prompt = build_act1_prompt(Act1Evidence(strategic_read=_no_quote_player_read()))

        assert _OLD_LABEL not in prompt, (
            "the whole Act-I prompt (headers included) must not carry the "
            "unverified negation"
        )

    def test_the_historical_header_says_unverified_never_absent(self):
        """The historical block's header read « jamais le contenu du
        texte » — the likely source of the minority M2 on the second
        panel document. The historian's readings carry no quote either:
        nothing stands behind the absence."""
        prompt = build_act1_prompt(Act1Evidence(strategic_read=_no_quote_player_read()))

        assert (
            "jamais le contenu du texte" not in prompt
        ), "an absence nothing checked must not head the historical block"


class TestTheCompanionsKeepTheirLabels:
    """Green BEFORE and AFTER the repair: the two controlled cases keep
    their exact labels — the anchored stance, and the one negation a
    control actually established (the unanchored stance)."""

    def test_an_anchored_stance_still_reads_le_texte_dit(self):
        read = {
            "players": [
                {
                    "name": "P1",
                    "role": "ministère",
                    "stance": "against",
                    "basis": TEXT_BASIS,
                    "quote": QUOTE,
                    "offset": DOC.find(QUOTE),
                }
            ]
        }
        block = _format_strategic_block(read)

        assert f"le texte dit : « {QUOTE} »" in block

    def test_the_unanchored_label_keeps_its_exact_negation(self):
        """The ONE negation a control establishes: ``quote_occurs_in``
        failed on a supplied quote. Its wording is unchanged."""
        read = {
            "players": [
                {
                    "name": "P3",
                    "role": "assemblée",
                    "stance": "for",
                    "anchor": ANCHOR_UNANCHORED,
                }
            ]
        }
        block = _format_strategic_block(read)

        assert "citation non ancrée" in block
        assert "le texte ne porte pas ce passage" in block
        assert "ne le cite PAS entre guillemets" in block
