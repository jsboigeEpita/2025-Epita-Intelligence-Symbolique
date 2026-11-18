"""#3559 — Act III's claim lines carry the turn's speaker tag (synthetic).

On c7 the conclusion gave one party the words the document gives to
another: the claims block named no party per line, and the descent's own
tag rule mis-read a turn whose tag a stage direction precedes. This
witness pins, with invented texts only:

* ``own_sentence_speaker_tag`` reads the tag of the unit's OWN sentence —
  including when leading bracketed stage directions precede it — and
  never scans backward into an earlier turn;
* the descent's frame (#3557) reads that stage-direction-led tag too;
* the assembled Act III prompt marks a speaker's own claim line, never a
  reported move's line, and carries the TOUR MARQUÉ rule only when a
  marker rides (#3416 byte-for-byte otherwise);
* the post-weave attribution check flags a sentence that quotes a marked
  claim's words while naming another marked party, and stands when the
  quote stays with its own party.

Privacy: invented parties, invented text, no corpus sentence.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.agents.core.reading.first_reading import (
    document_frame_for_unit,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

# Born-red at the ASSERTIONS, not at collection: on main the two reader
# symbols and the check module do not exist yet — their import fails here
# and every assertion below then fails on behaviour, never on ImportError.
try:
    from argumentation_analysis.agents.core.reading.first_reading import (
        own_sentence_speaker_tag,
    )
except ImportError:  # main: the symbol does not exist yet

    def own_sentence_speaker_tag(state, offset):  # type: ignore[no-redef]
        return ""


try:
    from argumentation_analysis.reporting.restitution.speaker_attribution_check import (
        attribution_flagged_sentences,
        tag_party_name,
    )
except ImportError:  # main: the module does not exist yet

    def tag_party_name(tag):  # type: ignore[no-redef]
        return ""

    def attribution_flagged_sentences(narrative, unit_texts, claim_speakers):  # type: ignore[no-redef]
        return []


DOC = (
    "[Setting note, invented. The moderator opens with a stage direction.] "
    "\n\n"
    "PREMIER ORATEUR: La citerne déborde dès la première averse. "
    "[Il se tourne vers la table]\n\n"
    "SECOND ORATEUR: Le premier prétend que la citerne déborde. "
    "\n\n"
    "[Annexe descriptive : on y lit les slogans inventés « Rassemblement "
    "d'abord » et « Justice partout », sans retranscription des tours.] "
)


def _state(**fields) -> SimpleNamespace:
    base = dict(
        identified_arguments={},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks={},
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        narrative_synthesis="",
        governance_decisions=[],
        debate_transcripts=[],
        raw_text="",
        argument_provenance={},
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _two_party_state() -> SimpleNamespace:
    """arg_1 = first voice's own reply; arg_2 = reported move (second
    voice's rendering, tag preceded by a stage direction); arg_3 = a
    slogan sitting inside the bracketed annex (its own sentence carries
    no tag)."""
    off_reply = DOC.index("PREMIER ORATEUR:") + len("PREMIER ORATEUR: ")
    off_reported = DOC.index("Le premier prétend")
    off_slogan = DOC.index("Rassemblement")
    return _state(
        raw_text=DOC,
        identified_arguments={
            "arg_1": "La citerne déborde dès la première averse.",
            "arg_2": "Le premier orateur présente la citerne comme débordante.",
            "arg_3": "Le slogan « Rassemblement d'abord » est invoqué.",
        },
        argument_provenance={
            "arg_1": {
                "offset": off_reply,
                "source_quote": "La citerne déborde dès la première averse.",
                "move_author": "speaker",
            },
            "arg_2": {
                "offset": off_reported,
                "source_quote": "Le premier prétend que la citerne déborde.",
                "move_author": "reported",
            },
            "arg_3": {
                "offset": off_slogan,
                "source_quote": "Rassemblement d'abord",
                "move_author": "speaker",
            },
        },
    )


class TestTheOwnSentenceTag:
    def test_tag_opening_the_units_own_sentence(self):
        st = _two_party_state()
        off = st.argument_provenance["arg_1"]["offset"]
        assert own_sentence_speaker_tag(st, off) == "PREMIER ORATEUR:"

    def test_tag_a_stage_direction_precedes_reads(self):
        st = _two_party_state()
        off = st.argument_provenance["arg_2"]["offset"]
        assert own_sentence_speaker_tag(st, off) == "SECOND ORATEUR:"

    def test_no_backward_scan_into_an_earlier_turn(self):
        """A slogan inside the bracketed annex inherits NO turn's tag."""
        st = _two_party_state()
        off = st.argument_provenance["arg_3"]["offset"]
        assert own_sentence_speaker_tag(st, off) == ""

    def test_missing_offset_or_raw_text_reads_nothing(self):
        assert own_sentence_speaker_tag(_state(raw_text=""), 0) == ""
        assert own_sentence_speaker_tag(_two_party_state(), None) == ""


class TestTheDescentFrameReadsTheStageDirectionLedTag:
    def test_frame_speaker_after_directions(self):
        st = _two_party_state()
        p = st.argument_provenance["arg_2"]
        frame = document_frame_for_unit(
            st,
            unit_text=st.identified_arguments["arg_2"],
            offset=p["offset"],
            source_quote=p["source_quote"],
        )
        assert frame.get("speaker") == "SECOND ORATEUR:"

    def test_frame_without_directions_unchanged(self):
        st = _two_party_state()
        p = st.argument_provenance["arg_1"]
        frame = document_frame_for_unit(
            st,
            unit_text=st.identified_arguments["arg_1"],
            offset=p["offset"],
            source_quote=p["source_quote"],
        )
        assert frame.get("speaker") == "PREMIER ORATEUR:"


class TestTheAct3PromptCarriesTheMarker:
    def test_speakers_own_claim_line_is_marked(self):
        ev = build_act3_evidence(_two_party_state())
        assert ev.claim_speakers.get("arg_1") == "PREMIER ORATEUR:"
        prompt = build_act3_prompt(ev)
        assert "[tour : PREMIER ORATEUR:]" in prompt
        assert "TOUR MARQUÉ" in prompt

    def test_reported_move_line_is_never_marked(self):
        ev = build_act3_evidence(_two_party_state())
        assert "arg_2" not in ev.claim_speakers

    def test_slogan_inside_directions_is_never_marked(self):
        ev = build_act3_evidence(_two_party_state())
        assert "arg_3" not in ev.claim_speakers

    def test_no_tag_document_keeps_prompt_byte_for_byte(self):
        """#3416: a document no tag rule fires on assembles unchanged."""
        st = _state(
            raw_text="Une seule voix tient un propos suivi, sans étiquette. "
            "Elle avance une raison puis une autre.",
            identified_arguments={
                "arg_1": "La voix avance une raison puis une autre.",
            },
            argument_provenance={
                "arg_1": {"offset": 0, "move_author": "speaker"},
            },
        )
        ev = build_act3_evidence(st)
        assert ev.claim_speakers == {}
        prompt = build_act3_prompt(ev)
        assert "[tour :" not in prompt
        assert "TOUR MARQUÉ" not in prompt


class TestThePostWeaveAttributionCheck:
    UNIT_TEXTS = {
        "arg_1": "La citerne déborde dès la première averse.",
        "arg_2": "Le second orateur affirme que la grange est solide.",
    }
    SPEAKERS = {"arg_1": "PREMIER ORATEUR:", "arg_2": "SECOND ORATEUR:"}

    def test_tag_party_name_resolves_both_forms(self):
        assert tag_party_name("PREMIER ORATEUR:") == "PREMIER ORATEUR"
        assert tag_party_name("SECOND ORATEUR.") == "SECOND ORATEUR"
        assert tag_party_name("") == ""

    def test_quoting_another_partys_words_flags(self):
        bad = (
            "Le SECOND ORATEUR affirme que « la citerne déborde dès la "
            "première averse » et en tire son verdict."
        )
        flagged = attribution_flagged_sentences(bad, self.UNIT_TEXTS, self.SPEAKERS)
        assert len(flagged) == 1

    def test_quote_staying_with_its_own_party_stands(self):
        good = (
            "Le PREMIER ORATEUR soutient que « la citerne déborde dès la "
            "première averse » ; le SECOND ORATEUR répond sur la grange."
        )
        assert attribution_flagged_sentences(good, self.UNIT_TEXTS, self.SPEAKERS) == []

    def test_unmarked_document_never_flags(self):
        text = "Une voix dit « la citerne déborde dès la première averse »."
        assert attribution_flagged_sentences(text, self.UNIT_TEXTS, {}) == []
