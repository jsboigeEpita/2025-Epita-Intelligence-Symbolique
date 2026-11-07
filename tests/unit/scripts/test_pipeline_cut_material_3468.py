"""#3468 — a wall-clock-cut pipeline run must leave a judge-readable text.

Measured on main (``f3157c634``, before the fix): when ``run_pipeline_mode``
hits its wall-clock bound the partial state IS recovered by reference (CB
#1528) — but the act phases sit at the DAG tail, so the recovered state has
no act strings, and ``pipeline_full_text`` (the ONE producer the fiche and
the blind judge both read, #3375 tranche 3) prints four « absent de l'état »
lines and nothing else. Everything the upstream phases established — the
extracts, the fallacies, the stakes — is paid for and lost to the reader at
the cut.

The fix renders what the recovered state honestly supports, under the #3392
rule: one clause per recorded element, absent fields omitted, never a
fabricated act. Completed states (acts present) and non-argumentative
documents are untouched.

Offline: no JVM, no network, no LLM.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.dataset.judge_panel import pipeline_text_from_state
from scripts.dataset.render_campaign_reading_folder import pipeline_full_text

#: Twelve synthetic extract units — more than the render cap, so the witness
#: also pins that a cut dump stays bounded.
_ARGUMENTS = {f"arg_{i}": f"extrait synthétique n°{i}" for i in range(1, 13)}
_FALLACIES = {
    "fallacy_1": {
        "type": "appel à l'autorité",
        "justification": "un exemple synthétique",
    },
    "fallacy_2": {
        "type": "fausse dichotomie",
        "justification": "un second exemple synthétique",
    },
}


def _cut_state(**extra):
    """The snapshot a wall-clock cut leaves behind: upstream material, no acts."""
    state = {
        "act1_framing": None,
        "act2_narrative": None,
        "act3_conclusion": None,
        "narrative_synthesis": None,
        "interpretive_question": None,
        "raw_text": "Texte synthétique pour le témoin de coupe.",
        "identified_arguments": dict(_ARGUMENTS),
        "identified_fallacies": dict(_FALLACIES),
        "stakes_and_stakeholders": {
            "stakes": [{"description": "un enjeu synthétique"}],
            "stakeholders": [],
        },
    }
    state.update(extra)
    return state


_CUT_OUTCOME = {"status": "partial", "reason": "budget"}


class TestACutRunLeavesItsMaterial:
    """The judge-readable text carries what the cut state established."""

    def test_the_judge_text_carries_the_cut_state_material(self):
        """Born red on main: the judge's arm text is four absence lines.

        ``pipeline_text_from_state`` is the judge's exact consumer — same
        producer as the fiche — so the witness runs through it.
        """
        text = pipeline_text_from_state(
            {"state": _cut_state()},
            {
                "document_classification": None,
                "opaque_id": "corpus_3468",
                "outcome": _CUT_OUTCOME,
            },
        )
        # The absent acts stay named — that honesty is not removed.
        assert "absent de l'état" in text
        # Born red: the material the run paid for reaches the reader.
        assert "extrait synthétique n°1" in text
        assert "appel à l'autorité" in text
        assert "un enjeu synthétique" in text

    def test_the_dump_is_bounded_on_a_large_cut_state(self):
        """Twelve units, a bounded render — volume is capped, not dumped."""
        text = pipeline_full_text(_cut_state(), None, "corpus_3468", _CUT_OUTCOME)
        rendered_units = [f"extrait synthétique n°{i}" for i in range(1, 13)]
        shown = sum(1 for unit in rendered_units if unit in text)
        assert 0 < shown < 12


class TestTheHonestShapesStayUntouched:
    """Completed, empty and classified states keep their current text."""

    def _completed_state(self):
        return {
            "act1_framing": "Acte I synthétique.",
            "act2_narrative": "Acte II synthétique.",
            "act3_conclusion": "Acte III synthétique.",
            "narrative_synthesis": "Synthèse synthétique.",
            "interpretive_question": None,
            "raw_text": "Texte synthétique.",
            "identified_arguments": dict(_ARGUMENTS),
        }

    def test_a_completed_state_keeps_its_acts_alone(self):
        """With acts present, no cut section appears — the text is the acts."""
        text = pipeline_full_text(
            self._completed_state(), None, "corpus_3468", {"status": "ok"}
        )
        assert "Acte I synthétique." in text
        assert "extrait synthétique" not in text

    def test_an_empty_cut_state_keeps_only_the_named_absences(self):
        """Cut before anything finished: nothing to show, nothing invented."""
        text = pipeline_full_text(
            {
                "act1_framing": None,
                "act2_narrative": None,
                "act3_conclusion": None,
                "narrative_synthesis": None,
                "interpretive_question": None,
                "raw_text": "Texte synthétique.",
                "identified_arguments": {},
                "identified_fallacies": {},
            },
            None,
            "corpus_3468",
            _CUT_OUTCOME,
        )
        assert "absent de l'état" in text
        # Nothing was fabricated to fill the cut.
        assert text.count("absent de l'état") == 4
        assert "extrait" not in text

    def test_a_non_argumentative_document_is_untouched(self):
        """The classification branch keeps its own paragraph."""
        text = pipeline_full_text(
            _cut_state(),
            "non_argumentative",
            "corpus_3468",
            {"status": "non_argumentative"},
        )
        assert "Classification terminale" in text
        assert "absent de l'état" not in text
