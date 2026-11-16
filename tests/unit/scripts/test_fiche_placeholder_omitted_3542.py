"""#3542 — a field with no value is left out of the reader's paragraph.

The panel's non-argumentative document is described to the reader by ONE
paragraph, built from what the extract and the corpus recorded. On that
document the registry holds placeholder values (« unknown »), and the
paragraph printed them as « non renseigné » — three clauses that carry no
information and read, on a document that states its own date, as the
opposite of what the document says.

The decision (#3542, coordinator's state after cycle 11): a placeholder
carries no information and the reader paragraph is not the place to print
it. A missing field is also not something to infer — the date must come
from the document, with its quote, or not at all. So a field with no value
is LEFT OUT; a field with a value renders exactly as before.

Synthetic content throughout (invented neutral words): no corpus document,
no document id, no date of any corpus document.

Offline: no JVM, no network, no LLM, no corpus.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.dataset.render_campaign_reading_folder import (
    render_non_argumentative_reader_paragraph,
    render_fiche,
)

#: The document's own words, synthetic: they carry the recorded values, so
#: the paragraph quotes them (#3389's rule).
_TEXT = (
    "Note de service de l'Institution X. Audience de la commission "
    "synthetique, deux rapporteurs fictifs. Rapport sur un sujet invente."
)

#: The fields that hold a value.
_VALUES = {
    "discourse_type": "note de service",
    "venue": "Institution X",
    "event": "audience de la commission synthetique",
    "participants": "deux rapporteurs fictifs",
    "report_title": "Rapport sur un sujet invente",
}

#: The registry fields that hold a placeholder — the measured shape.
_PLACEHOLDERS = {
    "era": "unknown",
    "regime_type": "unknown",
    "year_bucket": "unknown",
}

#: The paragraph's material sentence when no field holds a placeholder —
#: byte-identical to what the code printed before the fix (the control).
_CONTROL_SENTENCE = (
    "Le matériel enregistré le décrit ainsi — type de discours : « note de "
    "service » ; lieu : « Institution X » ; événement : « audience de la "
    "commission synthetique » ; participants : « deux rapporteurs fictifs » ; "
    "titre du rapport : « Rapport sur un sujet invente »."
)


def _state(metadata):
    return {
        "act1_framing": None,
        "act2_narrative": None,
        "act3_conclusion": None,
        "narrative_synthesis": None,
        "interpretive_question": None,
        "raw_text": _TEXT,
        "source_metadata": dict(metadata),
    }


def _paragraph(metadata) -> str:
    return render_non_argumentative_reader_paragraph(_state(metadata), 320)


class TestAFieldWithNoValueIsLeftOut:
    def test_the_paragraph_prints_no_placeholder(self):
        """RED on the unmodified code: three « non renseigné » clauses."""
        out = _paragraph({**_VALUES, **_PLACEHOLDERS})
        assert "non renseigné" not in out

    def test_the_field_is_neither_renamed_nor_inferred(self):
        """A missing field is left out, not replaced by a guess: no label,
        no value borrowed from elsewhere."""
        out = _paragraph({**_VALUES, **_PLACEHOLDERS})
        assert "époque" not in out
        assert "régime" not in out
        assert "tranche d'années" not in out
        # The raw placeholder never reaches the reader either.
        assert "unknown" not in out

    def test_the_reader_surface_of_the_fiche_is_the_same_paragraph(self):
        """The fiche of a non-argumentative document prints this paragraph
        and no act — the reader's whole product for that document."""
        facts = {
            "title": "Note de service",
            "speaker": "secretariat",
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
        out = render_fiche(
            facts,
            _state({**_VALUES, **_PLACEHOLDERS}),
            None,
            "abc1234",
            "gpt-x",
            "run",
        )
        assert "non renseigné" not in out
        assert "type de discours : « note de service »" in out


class TestAFieldWithAValueStillRenders:
    def test_every_recorded_value_is_still_described(self):
        out = _paragraph({**_VALUES, **_PLACEHOLDERS})
        assert "type de discours : « note de service »" in out
        assert "lieu : « Institution X »" in out
        assert "événement : « audience de la commission synthetique »" in out
        assert "participants : « deux rapporteurs fictifs »" in out
        assert "titre du rapport : « Rapport sur un sujet invente »" in out

    def test_the_paragraph_still_explains_the_absence_of_analysis(self):
        out = _paragraph({**_VALUES, **_PLACEHOLDERS})
        assert "n'a pas été lu comme une argumentation" in out
        assert "Le matériel enregistré le décrit ainsi" in out
        assert "ce n'est pas un échec" in out


class TestTheControlRenderStaysByteIdentical:
    def test_a_metadata_without_placeholder_keeps_its_exact_bytes(self):
        """No placeholder, no registry field: the paragraph is the one the
        code already printed, byte for byte."""
        out = _paragraph(_VALUES)
        assert _CONTROL_SENTENCE in out
        assert "non renseigné" not in out

    def test_a_metadata_with_no_field_at_all_keeps_its_absence(self):
        out = _paragraph({})
        assert "Le matériel enregistré" not in out
        assert "n'a pas été lu comme une argumentation" in out
