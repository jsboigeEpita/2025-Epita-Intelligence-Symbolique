# -*- coding: utf-8 -*-
"""#3054 — the appendix renders confidence provenance, carried from every lane.

#3029 made an unmeasured confidence honest (None + note) and the note travels
into the descent JSON — measured (issue #3054 census): no production reader
past the model, the state writers read explicit fields only. #1914 criterion 6
names the missing consumer: "confidence provenance here" (appendix.py:539-542).
This module pins the two halves of the wire (coordinator decision R1092):

- **Carry**: the fallacy entry in the state receives ``confidence_note`` beside
  ``confidence`` on every lane that applies ``fallacy_measured_fields`` — the
  hierarchical writer, the camembert writer, the conversational parent-harness
  loop. A lane that writes None without the note is the defect the issue names.
- **Render**: the appendix counts measured vs not, by reason class, and stays
  silent when everything is measured. No fabricated number — None is never
  turned into 0, in the state or in the render (#1019).

Synthetic state only — no corpus content, no LLM call.
"""

from __future__ import annotations

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_camembert_to_state,
    _write_hierarchical_fallacy_to_state,
)
from argumentation_analysis.reporting.restitution.appendix import render_appendix
from argumentation_analysis.reporting.restitution.state_adapter import (
    state_to_appendix_mapping,
)

# The two note shapes #3034's ``_confidence_score`` produces
# (exploration_plugin.py:42-58): the omitted argument and the unreadable
# input. The classifier keys on these exact prefixes — the reason classes the
# dispatch names (omitted / unreadable).
NOTE_OMITTED = "confidence absente (argument omis par le modèle)"
NOTE_UNREADABLE = "unreadable confidence 'x !', not measured"


def _state_with_both_kinds() -> UnifiedAnalysisState:
    """One measured detection, one None-with-note — the #3054 witness state."""
    state = UnifiedAnalysisState(initial_text="texte synthetique")
    state.add_fallacy(
        fallacy_type="type_A",
        justification="justification synthetique A",
        confidence=0.8,
    )
    state.add_fallacy(
        fallacy_type="type_B",
        justification="justification synthetique B",
        confidence=None,
        confidence_note=NOTE_OMITTED,
    )
    return state


class TestReasonClassification3054:
    def test_the_two_contract_note_shapes_classify(self):
        from argumentation_analysis.plugins.identification_models import (
            confidence_note_reason,
        )

        assert confidence_note_reason(NOTE_OMITTED) == "omise"
        assert confidence_note_reason(NOTE_UNREADABLE) == "illisible"

    def test_an_empty_note_is_not_a_reason_invented(self):
        from argumentation_analysis.plugins.identification_models import (
            confidence_note_reason,
        )

        # A note-free unmeasured detection (e.g. a producer that emits no
        # note) is counted as such — the class is never guessed (#1019).
        assert confidence_note_reason("") == "raison non fournie"

    def test_the_classifier_reads_the_real_producers_notes(self):
        """R1093 follow-up (#3056 review): the classes pin through
        ``_confidence_score`` itself, not through copied literals — if the
        producer rewords a note, this reddens instead of silently counting
        the reworded notes as ``autre`` in the appendix."""
        from argumentation_analysis.plugins.exploration_plugin import (
            _confidence_score,
        )
        from argumentation_analysis.plugins.identification_models import (
            confidence_note_reason,
        )

        for raw, expected in (
            ("", "omise"),  # the model omitted the argument
            (None, "illisible"),  # absent raw lands in the unreadable branch
            ("x !", "illisible"),  # unparseable raw
        ):
            score, note = _confidence_score(raw)
            assert score is None, raw  # every shape here is unmeasured
            assert confidence_note_reason(note) == expected, (raw, note)


class TestCarry3054:
    def test_add_fallacy_stores_the_note_beside_confidence(self):
        state = _state_with_both_kinds()
        entries = list(state.identified_fallacies.values())
        measured = [e for e in entries if "confidence" in e]
        unmeasured = [e for e in entries if "confidence" not in e]
        assert len(measured) == 1 and measured[0]["confidence"] == 0.8
        # A faithful read needs no note (#3029) — no empty-string key either.
        assert "confidence_note" not in measured[0]
        assert len(unmeasured) == 1
        assert unmeasured[0]["confidence_note"] == NOTE_OMITTED

    def test_hierarchical_writer_carries_the_note(self):
        """The lane that applies ``fallacy_measured_fields`` (state_writers.py)
        must pass the note through — writing None without it is the defect."""
        state = UnifiedAnalysisState(initial_text="texte synthetique")
        output = {
            "fallacies": [
                {
                    "type": "type_C",
                    "explanation": "explication synthetique",
                    "confidence": None,
                    "confidence_note": NOTE_UNREADABLE,
                }
            ]
        }
        _write_hierarchical_fallacy_to_state(output, state, {})
        (entry,) = state.identified_fallacies.values()
        assert "confidence" not in entry  # None stays absent, not 0 (#1019)
        assert entry["confidence_note"] == NOTE_UNREADABLE

    def test_camembert_writer_carries_the_note_when_produced(self):
        state = UnifiedAnalysisState(initial_text="texte synthetique")
        output = {
            "detected_fallacies": {
                "type_D": {
                    "source": "synthetic",
                    "confidence": None,
                    "confidence_note": NOTE_OMITTED,
                },
            }
        }
        _write_camembert_to_state(output, state, {})
        (entry,) = state.neural_fallacy_scores
        assert entry["confidence"] is None
        assert entry["confidence_note"] == NOTE_OMITTED

    def test_camembert_writer_invents_no_note(self):
        """Anti-fabrication: a producer that emits no note stays note-free."""
        state = UnifiedAnalysisState(initial_text="texte synthetique")
        output = {
            "detected_fallacies": {
                "type_E": {"source": "synthetic", "confidence": None}
            }
        }
        _write_camembert_to_state(output, state, {})
        (entry,) = state.neural_fallacy_scores
        assert "confidence_note" not in entry


class TestRender3054:
    def test_appendix_counts_measured_vs_not_by_reason(self):
        """Born-red witness (#3054 DoD): one measured, one None+note — on main
        the subsection is absent; here it must name the counts and the class."""
        state = _state_with_both_kinds()
        rendered = render_appendix(state_to_appendix_mapping(state))
        assert "Confiances des sophismes localisés" in rendered
        assert "mesurées : 1/2" in rendered
        assert "omise : 1" in rendered

    def test_no_subsection_when_every_confidence_is_measured(self):
        """The subsection exists only when there is a provenance to report."""
        state = UnifiedAnalysisState(initial_text="texte synthetique")
        state.add_fallacy(fallacy_type="type_F", justification="j", confidence=0.9)
        state.add_fallacy(fallacy_type="type_G", justification="j", confidence=0.4)
        rendered = render_appendix(state_to_appendix_mapping(state))
        assert "Confiances des sophismes localisés" not in rendered

    def test_no_number_is_fabricated_in_the_render(self):
        """A None-with-note detection must not surface as 0 or 'faible'."""
        rendered = render_appendix(state_to_appendix_mapping(_state_with_both_kinds()))
        assert "mesurées : 0/2" not in rendered
