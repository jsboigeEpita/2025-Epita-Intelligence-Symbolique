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
  marker rides — on a document no tag fires on, the assembled bytes
  EQUAL the base implementation's actual output (#3416), pinned by the
  digest measured at the fixed base SHA below.

Enforcement is marker + conditional instruction alone: the review of the
first cut showed a quotation/rebuttal trigger cannot discriminate a
legitimate contestation from a faulty attribution without a verb list,
so no post-weave check rides (marker-only, per the issue's own answer).

Privacy: invented parties, invented text, no corpus sentence.
"""

from __future__ import annotations

import hashlib
from types import SimpleNamespace

from argumentation_analysis.agents.core.reading.first_reading import (
    document_frame_for_unit,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

# Born-red at the ASSERTIONS, not at collection: on main the reader symbol
# does not exist yet — its import fails here and every assertion below
# then fails on behaviour, never on ImportError.
try:
    from argumentation_analysis.agents.core.reading.first_reading import (
        own_sentence_speaker_tag,
    )
except ImportError:  # main: the symbol does not exist yet

    def own_sentence_speaker_tag(state, offset):  # type: ignore[no-redef]
        return ""


# #3416 — the byte-for-byte proof compares the HEAD's actual assembled
# prompt against the BASE implementation's actual output for the SAME
# no-tag synthetic state. The base digest below was measured at the FIXED
# base SHA (the branch point), never ``origin/main`` (which moves):
# worktree at that commit, editable finder bypassed, module path proven.
_BASE_SHA = "2c4b82fd5"
_BASE_NO_TAG_PROMPT_SHA256 = (
    "6c535abd3170395195b85de350cfc0582eb17335627b283ca90d683dc7d914f1"
)
_BASE_NO_TAG_PROMPT_LEN = 16851


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
        """#3416: on a document no tag fires on, the head's assembled
        prompt EQUALS the base implementation's actual output — same
        synthetic state, base pinned at the fixed SHA (not origin/main)."""
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
        assert len(prompt) == _BASE_NO_TAG_PROMPT_LEN
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        assert digest == _BASE_NO_TAG_PROMPT_SHA256, (
            "the no-tag prompt drifted from the pinned base output "
            f"(base {_BASE_SHA}): the marker path must be additive only"
        )
        # Secondary, the same claim read directly.
        assert "[tour :" not in prompt
        assert "TOUR MARQUÉ" not in prompt
