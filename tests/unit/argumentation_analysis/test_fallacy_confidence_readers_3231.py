# -*- coding: utf-8 -*-
"""#3231 — the shared readers of a detection's confidence and its cut.

``confidence_of`` carries #3029's guard out of the synthesis into the one
father every act reads: a measurement is a number the producer wrote; a bool,
a string or an absent field is UNMEASURED — never a default value.
``detector_confidence_note`` renders the standing the evidence lines print,
``truncate_head_and_tail`` keeps the producer's final sentence past the head
cap — the coordinator measured, on the stored R1110 states, that every speaker
justification runs longer than 200 characters and a detector states its hedge
at the END of its reasoning, so a 200-character head cut dropped the qualifier
of exactly the detections the acts then presented as established faults.

Synthetic values only; deterministic — no JVM, no LLM, no network.
"""

from __future__ import annotations

from argumentation_analysis.core.fallacy_attribution import (
    confidence_of,
    detector_confidence_note,
)
from argumentation_analysis.reporting.restitution.cited_units import (
    truncate_head_and_tail,
)


class TestConfidenceOf:
    def test_a_number_the_producer_wrote_is_the_measurement(self):
        assert confidence_of({"confidence": 0.4}) == 0.4
        assert confidence_of({"confidence": 1}) == 1.0

    def test_an_absent_field_is_unmeasured_never_a_default(self):
        assert confidence_of({}) is None
        assert confidence_of({"confidence": None}) is None

    def test_a_string_is_not_a_measurement(self):
        assert confidence_of({"confidence": "high"}) is None

    def test_a_bool_is_a_flag_not_a_measure(self):
        """#3029's guard: True would coerce to 1.0 and print a confidence the
        producer never stated."""
        assert confidence_of({"confidence": True}) is None
        assert confidence_of({"confidence": False}) is None

    def test_reads_attribute_records_like_the_dict_record(self):
        from types import SimpleNamespace

        assert confidence_of(SimpleNamespace(confidence=0.55)) == 0.55
        assert confidence_of(SimpleNamespace()) is None


class TestDetectorConfidenceNote:
    def test_a_measured_confidence_prints_as_itself(self):
        assert detector_confidence_note(0.4) == "confiance du détecteur : 0,4"
        assert detector_confidence_note(0.35) == "confiance du détecteur : 0,35"
        assert detector_confidence_note(0.9) == "confiance du détecteur : 0,9"
        assert detector_confidence_note(1.0) == "confiance du détecteur : 1"

    def test_an_unmeasured_confidence_prints_as_unmeasured(self):
        assert detector_confidence_note(None) == (
            "confiance du détecteur : non mesurée"
        )


_HEDGE = "The analogy itself is not shown in the excerpt, so this match is tentative."


def _long_justification(head_sentences: int = 3) -> str:
    setup = (
        "The unit draws a parallel between two situations that differ in scale. "
        "The reasoning leans on the similarity of one feature. "
        "The comparison carries the weight of the claim. "
    ) * head_sentences
    return setup + _HEDGE


class TestTruncateHeadAndTail:
    def test_a_short_justification_is_returned_untouched(self):
        short = "La corrélation est lue comme un lien de cause à effet."
        assert truncate_head_and_tail(short, 200, 200) == short

    def test_the_final_sentence_survives_the_head_cap(self):
        """#3231's witness shape: the hedge lies ONLY past the cut."""
        out = truncate_head_and_tail(_long_justification(), 200, 200)
        assert _HEDGE in out
        assert "[…]" in out  # the head's cut stays visible (#2967)

    def test_the_head_keeps_the_setups_beginning(self):
        out = truncate_head_and_tail(_long_justification(), 200, 200)
        assert out.startswith("The unit draws a parallel")

    def test_a_final_sentence_longer_than_the_tail_cap_is_itself_capped(self):
        run_on_hedge = " ".join(["word" for _ in range(120)]) + " tentative end."
        text = _long_justification() + " " + run_on_hedge
        out = truncate_head_and_tail(text, 200, 200)
        assert len(out) < len(text)
        assert out.count("[…]") >= 2  # the head's cut and the tail's own cap

    def test_one_boundary_less_sentence_keeps_the_texts_end_not_the_heads_start(self):
        """A single sentence with no delimiter: the qualifier lives at the
        END — the tail is the end, never a repetition of the head."""
        blob = (
            "reasoning " * 60
        ) + "and the match stays tentative for lack of a shown basis."
        out = truncate_head_and_tail(blob, 200, 200)
        assert "tentative for lack of a shown basis." in out
        # no duplicated run: head shows chars 0..199, tail shows the END
        assert out.count("reasoning") < blob.count("reasoning")

    def test_a_decimal_point_never_splits_the_tail(self):
        text = (
            "The detector scores its match. "
            "A rate held at 0.4 across the excerpt because the analogy "
            "itself is not shown, so this match is tentative."
        )
        out = truncate_head_and_tail(text, 60, 200)
        assert "so this match is tentative." in out
        assert not out.split("[…]")[-1].lstrip().startswith("4")
