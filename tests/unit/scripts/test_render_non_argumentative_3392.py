"""#3392 — a non-argumentative document gets an explained refusal in French.

The v1 panel's one non-argumentative document (cycle 0) was classified
right and rendered as an English batch line carrying an internal issue
number — the batch's LOG line, on the reader's surface. The zero-shot
named what the document was and why no argument could be analysed; the
render taught the reader less. That was the panel's only ZEROSHOT_WINS.

The fix is a reader paragraph built ONLY from what the extract and the
corpus record put on the state (the metadata, through the same reader
labels the acts use) — no LLM call, nothing invented, and the batch log
line stays in the log.

Offline: no JVM, no network, no LLM.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.dataset.render_campaign_reading_folder import render_fiche
from scripts.dataset.run_corpus_batch import render_non_argumentative_restitution

#: 320 characters, a header listing a kind of document, an institution,
#: an event and a title — the panel's measured shape, synthetic words.
_FACTS = {
    "title": "Ordre du jour",
    "speaker": "secrétariat",
    "year": "2026",
    "opaque_id": "doc_A",
    "workflow": "spectacular",
    "status": "non_argumentative",
    "chars": 320,
    "args": 0,
    "fallacies": 0,
    "fol": 0,
    "pl": 0,
    "modal": 0,
    "wall_s": 3.5,
    "calls": 1,
    "cost": 0.0002,
    "reading_window_status": None,
    "restitution_acts_degraded": None,
    "classification": "non_argumentative",
    "outcome": {"status": "non_argumentative", "phase": "extraction"},
}

_STATE = {
    "act1_framing": None,
    "act2_narrative": None,
    "act3_conclusion": None,
    "narrative_synthesis": None,
    "interpretive_question": None,
    "source_metadata": {
        "discourse_type": "note de service",
        "title": "Ordre du jour",
        "venue": "Institution X",
        "date_or_year": "2026",
    },
}


def _fiche(facts=None, state=None) -> str:
    return render_fiche(
        dict(facts or _FACTS), dict(state or _STATE), None, "abc1234", "gpt-x", "run"
    )


class TestTheReaderGetsAFrenchParagraph:
    def test_the_paragraph_explains_the_absence_of_analysis(self):
        """On main the fiche carried the batch's English line instead."""
        out = _fiche()
        assert "n'a pas été lu comme une argumentation" in out
        assert "aucun argument" in out
        assert "aucune thèse à examiner" in out
        assert "ce n'est pas un échec" in out

    def test_the_paragraph_cites_the_recorded_metadata_under_reader_labels(self):
        out = _fiche()
        assert "Le matériel enregistré le décrit ainsi" in out
        # The recorded kind and venue, under the SAME reader labels the
        # acts use (#3311) — never the raw state keys.
        assert "type de discours : « note de service »" in out
        assert "lieu : « Institution X »" in out
        assert "discourse_type" not in out
        assert "venue :" not in out

    def test_no_english_and_no_issue_number_reachable_from_github(self):
        out = _fiche()
        assert "classified non-argumentative" not in out
        assert "#1909" not in out
        # Not even the raw classification id: the surface says it in French.
        assert "non_argumentative" not in out

    def test_the_classification_and_the_skipped_phases_stay_unchanged(self):
        out = _fiche()
        assert "**Classification terminale : document non-argumentatif.**" in out
        # No acts are produced — and none is faked as "absent".
        assert "### Acte I" not in out
        assert "*(absent de l'état" not in out


class TestTheGapIsNamedNotInvented:
    def test_without_recorded_metadata_no_material_line_is_invented(self):
        """#3392 ask 2: an element the extract did not record is the gap —
        the paragraph says the absence, it does not write a description."""
        state = dict(_STATE)
        state["source_metadata"] = {}
        out = _fiche(state=state)
        assert "n'a pas été lu comme une argumentation" in out
        assert "Le matériel enregistré" not in out
        assert "ce n'est pas un échec" in out

    def test_the_inputs_are_not_mutated(self):
        facts = dict(_FACTS)
        state = dict(_STATE)
        _fiche(facts, state)
        assert facts == _FACTS and state == _STATE


class TestTheBatchLogKeepsItsLine:
    def test_the_english_line_stays_where_it_belongs(self):
        """The log line is not removed — only taken out of the reader's
        text. This control must stay green on both trees."""
        line = render_non_argumentative_restitution(
            "doc_A", {"status": "non_argumentative", "phase": "extraction"}
        )
        assert "classified non-argumentative" in line
        assert "#1909" in line


class TestTheHeaderSElementsAreRecordedAndRead:
    """#3392 ask 2 — the extract records what its own header lists.

    The coordinator's ask: the gap closes by the EXTRACT recording the
    event, the participants and the report's title — not by an LLM call in
    the paragraph. Two producers carry it: ``expand_corpus`` reads
    extract-level metadata (dead before — a source-9-shaped extract carried
    fields nothing read), and the paragraph names the recorded elements
    under reader labels. Synthetic words throughout.
    """

    _HEADER_META = {
        "discourse_type": "compte rendu",
        "event": "audition de la commission synthétique",
        "participants": "deux rapporteures fictives",
        "report_title": "Rapport sur un sujet inventé",
    }

    def test_the_paragraph_names_the_three_elements(self):
        state = dict(_STATE)
        state["source_metadata"] = dict(self._HEADER_META)
        out = _fiche(state=state)
        assert "événement : « audition de la commission synthétique »" in out
        assert "participants : « deux rapporteures fictives »" in out
        assert "titre du rapport : « Rapport sur un sujet inventé »" in out
        # raw keys never reach the reader
        assert "report_title" not in out
        assert "event :" not in out

    def test_expand_corpus_reads_extract_level_metadata(self):
        """Born red on main: the per-document record carried only the
        source-level classification — an extract recording its own event
        handed the reader nothing."""
        from scripts.dataset.run_corpus_batch import expand_corpus

        defs = [
            {
                "source_name": "Source synthétique",
                "extracts": [
                    {
                        "extract_id": "hdr",
                        "extract_name": "En-tête",
                        "extract_text": "Un en-tête synthétique sans argument.",
                        "metadata": {
                            "event": "audition de la commission synthétique",
                            "participants": "deux rapporteures fictives",
                            "report_title": "Rapport sur un sujet inventé",
                        },
                    }
                ],
            }
        ]
        docs, _omitted, _skipped = expand_corpus(defs)
        assert len(docs) == 1
        meta = docs[0]["metadata"]
        assert meta["event"] == "audition de la commission synthétique"
        assert meta["participants"] == "deux rapporteures fictives"
        assert meta["report_title"] == "Rapport sur un sujet inventé"

    def test_extract_metadata_does_not_erase_source_classification(self):
        """#1906 precedence, extract layer: an explicit value wins, but the
        source-level fields the extract does not mention survive."""
        from scripts.dataset.run_corpus_batch import expand_corpus

        defs = [
            {
                "source_name": "Discourspolitiquefr",
                "metadata": {"era": "2020-2029"},
                "extracts": [
                    {
                        "extract_text": "Un extrait synthétique.",
                        "metadata": {"event": "un événement enregistré"},
                    }
                ],
            }
        ]
        docs, _omitted, _skipped = expand_corpus(defs)
        meta = docs[0]["metadata"]
        assert meta["event"] == "un événement enregistré"
        assert meta["era"] == "2020-2029"
