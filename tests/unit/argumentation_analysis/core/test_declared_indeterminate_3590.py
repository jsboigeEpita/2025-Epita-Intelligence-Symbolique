"""#3590 — a passage the document declares unsettled is not mined as determinate.

Measured on one cycle-13 panel document: the extraction pass mints a
DETERMINATE content for a line the document itself calls deliberate invented
language (a bracket note denies any settled record of the lines and names
the talk deliberate invented language). The paraphrase then feeds the
fallacy pass, the counters, the JTMS and Act II — a precision the document
never granted.

The repair has three parts:
(1) the extraction prompt NAMES the document's own declaration when one
    exists (byte-identical prompt when none does);
(2) a deterministic post-check marks a unit whose recorded position falls in
    a declared zone — ``argument_provenance[arg_id]["indeterminate"]``,
    dating-"uncertain"-style: the unit is NOT dropped;
(3) Acte II renders the document's declaration for that line, never the
    minted paraphrase.

R1170 rework — the measured exchange holds TWO turns: the invented-language
lines of one party, and another speaker's plain-language line. The opening
note ANNOUNCES the exchange as the one settled, citable portion, so the
passage between the notes is NOT a zone of unsettled transcription: a note
that announces what follows as settled opens no such zone. What remains is
the language declaration, and Act II names IT (document-level block), never
« ce passage n'est pas établi » over a line the document says is settled.

The reader lives beside the #3584 form gate and reads by CLASS (public
indeterminacy vocabulary, fr+en), never a word taken from the corpus, never
a length threshold.

Privacy: invented filler throughout (review 2: every run of 28+ collapsed
lowercase chars was checked against the recorded panel texts — zero
overlap), opaque ids, no corpus text.
Deterministic: no JVM, no network, no LLM.
"""

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState

# --- invented filler (the SHAPE of the measured class, never its words) -----

#: The pair-of-notes shape: an opener naming the invented language, then a
#: scene note, then a closer denying any settled record. The passage
#: BETWEEN the two declaration notes is the declared zone. The opener says
#: NOTHING about the transcription being settled — the genuine shape (a).
PAIR_TEXT = (
    "[Scene: a fictional assembly hall. The orator addresses the room in "
    "pseudo-Marlev speech; a scribe relays each burst.] "
    "Vlorbnex kessamil drau. "
    "[The audience murmurs approvingly] "
    "Skrell vanda torr. "
    "[Across the rest of the speech, the only quotable scraps are watchwords "
    "such as « Vandra krill », set in plain gibberish around them. There "
    "exists no verbatim record of the whole oration: the talking is wilful "
    "pseudo-Marlev and printed versions diverge.]"
)

#: The measured two-turn shape (R1170): the opener names the invented
#: language AND announces the lines that follow as the settled, citable
#: portion; one turn in the invented language, another speaker's turn in
#: plain language; the closer denies any settled record of the WHOLE
#: oration. The settled announcement kills the zone — what the document
#: declares is the invented language, never the exchange.
TWO_TURN_TEXT = (
    "[Scene: a fictional assembly hall. The orator addresses the room in "
    "pseudo-Marlev speech; a scribe relays each burst into ordinary "
    "wording. The lines below carry the speech's sole settled and citable "
    "transcription. What follows is an excerpt, not the complete oration.] "
    "ORATOR: Vlorbnex kessamil drau. "
    "[The audience murmurs approvingly] "
    "SCRIBE: The orator has just hailed the loyal fellowship of his first "
    "seasons in the cause. "
    "[Across the rest of the speech, the only quotable scraps are watchwords "
    "such as « Vandra krill », set in plain gibberish around them. There "
    "exists no verbatim record of the whole oration: the talking is wilful "
    "pseudo-Marlev and printed versions diverge.]"
)

#: The invented-language turn's unit, and the plain-language turn's unit.
ORATOR_QUOTE = "Vlorbnex kessamil drau."
SCRIBE_QUOTE = (
    "The orator has just hailed the loyal fellowship of his first seasons "
    "in the cause."
)

#: The declared unit: the invented line between the two declaration notes.
INSIDE_QUOTE = "Vlorbnex kessamil drau."

#: A unit quoting a watchword sitting INSIDE the closing declaration's own
#: span — a note is the declaration, never a declared passage.
NOTE_INTERNAL_QUOTE = "Vandra krill"

#: The single-note announcing shape: one declaration whose own sentence
#: announces what follows.
ANNOUNCE_TEXT = (
    "[Note: the following address is in deliberate invented language; no "
    "verbatim record of it exists.] Blah veshk trall. More invented noise."
)

#: Control: TWO bracket notes that declare nothing — with the marker binding
#: removed, every note would declare and the passage between them would fire.
PLAIN_TEXT = (
    "[Applause in the hall] The measure should be maintained. "
    "[The speaker points at the gallery] The budget must hold."
)

#: Control: the settled-record vocabulary WITHOUT a negation, in the
#: two-note shape — the same family of nouns, saying the opposite.
NOT_NEGATED_TEXT = (
    "[A verbatim record of the oration is held at the archive.] "
    "The measure should be maintained. "
    "[The speaker points at the gallery] The budget must hold."
)


def _spans(text):
    from argumentation_analysis.core.shared_state import declared_indeterminate_spans

    return declared_indeterminate_spans(text)


def _declarations(text):
    from argumentation_analysis.core.shared_state import (
        declared_indeterminate_declarations,
    )

    return declared_indeterminate_declarations(text)


def _write(text, arguments):
    from argumentation_analysis.orchestration.state_writers import (
        _write_fact_extraction_to_state,
    )

    state = UnifiedAnalysisState(text)
    _write_fact_extraction_to_state(
        {"arguments": arguments, "extraction_status": "ok"}, state, {}
    )
    return state


# --- the reader ---------------------------------------------------------------


class TestTheReader:
    """The declared zones, read by form — public vocabulary only."""

    def test_the_passage_between_two_declaration_notes_is_one_zone(self):
        spans = _spans(PAIR_TEXT)
        assert len(spans) == 1, f"expected one declared zone, got {spans}"
        opener_end = PAIR_TEXT.index("]") + 1
        closer_start = PAIR_TEXT.index("[Across")
        assert (spans[0].start, spans[0].end) == (opener_end, closer_start)

    def test_the_zone_is_named_by_the_strongest_declaration(self):
        """The closer NIEGATES the settled record; the opener only names the
        invented language. The negated declaration names the zone."""
        zone = _spans(PAIR_TEXT)[0]
        assert zone.quote.startswith("There exists no verbatim record")
        assert zone.offset == PAIR_TEXT.index("There exists no verbatim record")

    def test_the_quote_is_the_declaring_sentence_not_the_whole_note(self):
        zone = _spans(PAIR_TEXT)[0]
        assert "Scene: a fictional assembly hall" not in zone.quote
        assert zone.quote.endswith("printed versions diverge.")

    def test_a_note_that_announces_opens_the_zone_after_it(self):
        spans = _spans(ANNOUNCE_TEXT)
        assert len(spans) == 1
        note_end = ANNOUNCE_TEXT.index("]") + 1
        assert (spans[0].start, spans[0].end) == (note_end, len(ANNOUNCE_TEXT))

    def test_a_plain_bracket_note_declares_nothing(self):
        assert _spans(PLAIN_TEXT) == []

    def test_a_settled_record_that_is_not_negated_declares_nothing(self):
        assert _spans(NOT_NEGATED_TEXT) == []

    def test_a_note_is_never_its_own_zone(self):
        from argumentation_analysis.core.shared_state import (
            declared_indeterminate_span_at,
        )

        spans = _spans(PAIR_TEXT)
        assert declared_indeterminate_span_at(PAIR_TEXT.index("Vandra"), spans) is None
        assert declared_indeterminate_span_at(PAIR_TEXT.index("Scene"), spans) is None

    def test_an_absent_offset_is_never_in_a_zone(self):
        from argumentation_analysis.core.shared_state import (
            declared_indeterminate_span_at,
        )

        assert declared_indeterminate_span_at(None, _spans(PAIR_TEXT)) is None


class TestTheSettledExchangeOpensNoZone:
    """R1170 — an opener that announces the following exchange as the
    SETTLED, citable portion cannot open a zone of unsettled transcription:
    what the document declares is the invented language of one party's
    lines, never the passage between the notes."""

    def test_the_two_turn_exchange_declares_no_zone(self):
        assert _spans(TWO_TURN_TEXT) == []

    def test_the_declarations_survive_the_zone(self):
        """The zone dies, the declarations do not: the prompt and Acte II
        still name what the document declares about its own lines."""
        declarations = _declarations(TWO_TURN_TEXT)
        assert [d.rank for d in declarations] == [1, 2]
        assert declarations[0].quote.startswith("The orator addresses")
        assert declarations[1].quote.startswith("There exists no verbatim record")
        assert declarations[1].offset == TWO_TURN_TEXT.index(
            "There exists no verbatim record"
        )

    def test_without_the_settled_announcement_the_zone_stays(self):
        """Control: the same two-turn shape MINUS the settledness sentence —
        the between-notes zone opens (shape (a) is intact), and it covers
        both turns, which is then what the document declared."""
        variant = TWO_TURN_TEXT.replace(
            "The lines below carry the speech's sole settled and citable "
            "transcription. ",
            "",
        )
        spans = _spans(variant)
        assert len(spans) == 1
        opener_end = variant.index("]") + 1
        closer_start = variant.index("[Across")
        assert (spans[0].start, spans[0].end) == (opener_end, closer_start)
        assert opener_end < variant.index(SCRIBE_QUOTE) < closer_start

    def test_the_stability_words_without_an_announce_keep_the_zone(self):
        """The announce cue is what binds the settledness to what follows:
        the same stability words about a passage the note does NOT announce
        leave the zone intact."""
        variant = TWO_TURN_TEXT.replace("The lines below", "Those lines")
        assert len(_spans(variant)) == 1


# --- the writer post-check ----------------------------------------------------


class TestTheWriterMarksWithoutDropping:
    """Ask 2 — the unit is not dropped: the state carries the declaration."""

    def test_the_unit_in_the_declared_zone_is_marked(self):
        state = _write(
            PAIR_TEXT,
            [{"text": "A determinate paraphrase.", "source_quote": INSIDE_QUOTE}],
        )
        entry = next(iter(state.argument_provenance.values()))
        declared = entry.get("indeterminate")
        assert isinstance(declared, dict), "the declared passage was not marked"
        assert declared["status"] == "indeterminate"
        assert declared["declared_quote"].startswith("There exists no verbatim record")
        assert declared["declared_offset"] == PAIR_TEXT.index(
            "There exists no verbatim record"
        )

    def test_the_unit_stays_in_the_corpus(self):
        state = _write(
            PAIR_TEXT,
            [{"text": "A determinate paraphrase.", "source_quote": INSIDE_QUOTE}],
        )
        assert len(state.identified_arguments) == 1
        assert "A determinate paraphrase." in " ".join(
            state.identified_arguments.values()
        )

    def test_a_unit_quoting_a_declaration_note_is_not_marked(self):
        state = _write(
            PAIR_TEXT,
            [
                {
                    "text": "A paraphrase of a watchword.",
                    "source_quote": NOTE_INTERNAL_QUOTE,
                }
            ],
        )
        entry = next(iter(state.argument_provenance.values()))
        assert "indeterminate" not in entry

    def test_a_document_without_declaration_is_byte_identical(self):
        """Ask 5 — no declaration writing anywhere: the provenance entry
        carries exactly the pre-#3590 keys and nothing else."""
        state = _write(
            PLAIN_TEXT,
            [
                {
                    "text": "The measure holds.",
                    "source_quote": "The measure should be maintained.",
                }
            ],
        )
        entry = next(iter(state.argument_provenance.values()))
        assert set(entry) == {"producer", "offset", "offset_basis", "source_quote"}
        assert entry["producer"] == "llm_extract"


class TestTheWriterMarksNoSettledTurn:
    """R1170 — a unit of the settled exchange (either turn) is not marked:
    the bar is zero marks on the plain-language turn, and no zone means no
    mark on the invented-language turn either."""

    def test_no_unit_of_the_settled_exchange_is_marked(self):
        state = _write(
            TWO_TURN_TEXT,
            [
                {"text": "A pseudo-language line.", "source_quote": ORATOR_QUOTE},
                {"text": "A plain relay line.", "source_quote": SCRIBE_QUOTE},
            ],
        )
        assert len(state.argument_provenance) == 2
        for entry in state.argument_provenance.values():
            assert "indeterminate" not in entry


# --- Acte II ------------------------------------------------------------------


class TestTheAct2RendersTheDeclaration:
    """Ask 3 — the beat renders the document's own declaration."""

    def _evidence_state(self):
        return _write(
            PAIR_TEXT,
            [{"text": "A determinate paraphrase.", "source_quote": INSIDE_QUOTE}],
        )

    def test_the_evidence_carries_the_declaration(self):
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            build_act2_evidence,
        )

        evidence = build_act2_evidence(self._evidence_state())
        units = [a for mvt in evidence.movements for a in mvt.arguments]
        assert len(units) == 1
        assert isinstance(units[0].indeterminate, dict)
        assert units[0].indeterminate["status"] == "indeterminate"

    def _prompt(self, indeterminate):
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            Act2Evidence,
            ArgEvidence,
            MovementEvidence,
            build_act2_prompt,
        )

        evidence = Act2Evidence(
            movements=[
                MovementEvidence(
                    movement_id="mvt_1",
                    theme="Faux raisonnement",
                    arguments=[
                        # Passed only when set, so the control below collects on
                        # main (the field is introduced by this branch).
                        ArgEvidence(
                            arg_id="arg_1",
                            description="A DETERMINATE PARAPHRASE.",
                            **(
                                {}
                                if indeterminate is None
                                else {"indeterminate": indeterminate}
                            ),
                        )
                    ],
                )
            ],
            args_total=1,
            # The legend binds Greek letters to unit text; empty here so the
            # paraphrase can only reach the prompt through the movement beat.
            unit_texts={},
        )
        return build_act2_prompt(evidence)

    def test_the_beat_renders_the_declaration_not_the_paraphrase(self):
        prompt = self._prompt(
            {
                "status": "indeterminate",
                "declared_quote": "There exists no verbatim record.",
                "declared_offset": 12,
            }
        )
        assert "There exists no verbatim record." in prompt
        assert "A DETERMINATE PARAPHRASE." not in prompt
        # R1170 — the line NAMES the declaration; it never asserts that the
        # passage is not established (that is the document's to say, and a
        # settled passage must never read as unsettled).
        assert "n'est pas établi" not in prompt

    def test_the_control_keeps_the_description(self):
        prompt = self._prompt(None)
        assert "A DETERMINATE PARAPHRASE." in prompt


class TestTheAct2DocumentDeclarations:
    """R1170 — when the declared passage is announced settled, no unit is
    marked and no beat line fires; Act II still names the document's own
    declarations at DOCUMENT level, and never says a settled passage is
    unsettled."""

    def _two_turn_state(self):
        return _write(
            TWO_TURN_TEXT,
            [
                {"text": "A pseudo-language line.", "source_quote": ORATOR_QUOTE},
                {"text": "A plain relay line.", "source_quote": SCRIBE_QUOTE},
            ],
        )

    def test_the_evidence_carries_the_document_declarations(self):
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            build_act2_evidence,
        )

        evidence = build_act2_evidence(self._two_turn_state())
        assert "pseudo-Marlev" in evidence.document_declarations
        assert "There exists no verbatim record" in evidence.document_declarations
        assert "n'est pas établi" not in evidence.document_declarations

    def test_the_prompt_names_the_declarations_and_no_beat_line(self):
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            build_act2_evidence,
            build_act2_prompt,
        )

        prompt = build_act2_prompt(build_act2_evidence(self._two_turn_state()))
        assert "DÉCLARATIONS DU DOCUMENT" in prompt
        # No marked unit: no beat line fires, both turns read as units.
        assert "lecture INDÉTERMINÉE" not in prompt

    def test_a_document_without_declarations_has_no_block(self):
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            build_act2_evidence,
        )

        state = _write(
            PLAIN_TEXT,
            [
                {
                    "text": "The measure holds.",
                    "source_quote": "The measure should be maintained.",
                }
            ],
        )
        assert build_act2_evidence(state).document_declarations == ""


# --- the extraction prompt (ask 1 + ask 5) -------------------------------------


class TestTheExtractionPrompt:
    """Ask 1 — the prompt names the declaration; ask 5 — nothing otherwise."""

    def test_the_instruction_names_the_documents_own_words(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _indeterminate_declaration_instruction,
        )

        instruction = _indeterminate_declaration_instruction(_declarations(PAIR_TEXT))
        assert "There exists no verbatim record" in instruction
        # the anchor rides: only a line the declaration NAMES is affected
        assert "keeps its normal reading" in instruction

    def test_the_instruction_rides_the_declarations_not_the_zone(self):
        """R1170 — on the settled exchange the zone is empty; the
        instruction still names the declarations, so the model is told
        what the document declares about its own lines."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _indeterminate_declaration_instruction,
        )

        assert _spans(TWO_TURN_TEXT) == []
        instruction = _indeterminate_declaration_instruction(
            _declarations(TWO_TURN_TEXT)
        )
        assert "pseudo-Marlev" in instruction
        assert "There exists no verbatim record" in instruction
        assert "keeps its normal reading" in instruction

    def test_no_declaration_means_no_instruction(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _indeterminate_declaration_instruction,
        )

        assert _indeterminate_declaration_instruction([]) == ""

    def test_the_no_declaration_prompt_is_byte_identical(self):
        """Ask 5 — the expected string is assembled from the module's own
        constants: an instruction appended UNCONDITIONALLY breaks it."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _MOVE_AUTHOR_INSTRUCTION,
            _OPPOSING_POSITIONS_INSTRUCTION,
            _QUESTION_FORCE_INSTRUCTION,
            _fact_extraction_system_content,
        )

        expected = (
            "You are an expert argument analyst. Extract the key arguments "
            "and verifiable claims from the text. "
            "For each argument and claim, include the exact quote from the "
            "source text that supports it (verbatim, max 150 chars). "
            "Do NOT detect fallacies — that is handled by a separate specialist. "
            "Focus on: (1) identifying distinct argumentative positions, "
            "(2) extracting factual claims that can be verified, "
            "(3) noting rhetorical strategies used (without labeling them as fallacies). "
            + _OPPOSING_POSITIONS_INSTRUCTION
            + _MOVE_AUTHOR_INSTRUCTION
            + _QUESTION_FORCE_INSTRUCTION
            + ""
            + " Respond with ONLY a JSON object:\n"
            '{"arguments": [{"text": "arg description", "source_quote": "exact quote...", '
            '"move_author": "speaker|reported"}], '
            '"claims": [{"text": "claim description", "source_quote": "exact quote..."}], '
            '"summary": "brief analysis summary"}'
        )
        assert _fact_extraction_system_content("", []) == expected
