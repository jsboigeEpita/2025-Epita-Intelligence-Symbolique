# -*- coding: utf-8 -*-
"""#3369 — the ladder has one scale: the same record, the same word.

#3248 gave both acts the SAME ladder words (« provisoire, moyenne, ferme »)
and banned the figure from prose — but never wrote the line between the
words. Each act re-derived its own bands, and on the R1136a render the same
detections read « fermes » in Act II and « confiance moyenne » in Act III
(fallacy_4/5/6 at 0.70-0.72). The reader meets one passage twice and cannot
tell which word to believe.

The repair is one father, ``detection_standing_word(confidence)`` in
``fallacy_attribution``, grafted where the words already lived: the evidence
line prints the word BESIDE the decimal it already prints (#3231 — the
figure stays in evidence), and the consigne says « reprends le mot de la
ligne » instead of letting each writer trace its own scale. A written
reserve in the justification can only lower the word (#3231) — the writer's
judgement stays, the scale does not.

Born red on main: the note prints « confiance du détecteur : 0,72 » and no
word anywhere, so both acts' briefings carry no standing word at all.
"""

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from argumentation_analysis.core import fallacy_attribution as _fa
from argumentation_analysis.core.fallacy_attribution import (
    DETECTION_STANDING_RULE,
    detector_confidence_note,
)
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)


def detection_standing_word(confidence):
    """Lazy reach for the #3369 father — the witness stays COLLECTABLE on
    the pre-repair tree, so the born-red partition reads as failures, not
    as one import error hiding the count."""
    word = getattr(_fa, "detection_standing_word", None)
    assert word is not None, "the #3369 father must exist in fallacy_attribution"
    return word(confidence)


#: The R1136a measured pair — the numbers that read two different ways.
_FERME_CONFIDENCE = 0.72
_PROVISOIRE_CONFIDENCE = 0.40

#: The one real state on this seat that carries measured fallacy
#: confidences (17 values, 0.35-0.70) — the offline replay surface.
_REAL_STATE = (
    Path("argumentation_analysis/evaluation/results/real_analysis")
    / "real_A_pipeline_state.json"
)


def _state(confidence):
    """One unit, one detection — the smallest state both acts can read."""
    return SimpleNamespace(
        identified_arguments={"arg_1": "un mouvement défendu par une comparaison"},
        identified_fallacies={
            "f_1": {
                "target_argument_id": "arg_1",
                "type": "ad_hominem",
                "justification": "la ligne attaque l'auteur au lieu du propos",
                "confidence": confidence,
            }
        },
        argument_quality_scores={},
        counter_arguments=[],
        jtms_beliefs={},
        dung_frameworks={},
        propositional_analysis_results=[],
        fol_analysis_results=[],
        modal_analysis_results=[],
        workflow_results={},
    )


def _both_prompts(state):
    return (
        build_act2_prompt(build_act2_evidence(state)),
        build_act3_prompt(build_act3_evidence(state)),
    )


class TestTheScaleItself:
    """The father: three words, two boundaries, one place."""

    @pytest.mark.parametrize(
        "value,word",
        [
            (0.72, "lecture ferme"),
            (0.70, "lecture ferme"),
            (0.69, "lecture moyenne"),
            (0.65, "lecture moyenne"),
            (0.50, "lecture moyenne"),
            (0.49, "lecture provisoire"),
            (0.40, "lecture provisoire"),
        ],
    )
    def test_a_number_gives_one_word(self, value, word):
        assert detection_standing_word(value) == word

    def test_an_unmeasured_confidence_has_no_word(self):
        """#3029 — nothing is filled in: the scale needs a number, and the
        note says « non mesurée » alone."""
        assert detection_standing_word(None) == ""
        assert detector_confidence_note(None) == (
            "confiance du détecteur : non mesurée"
        )

    def test_the_note_prints_the_word_beside_the_decimal(self):
        """#3231 stays — the decimal keeps its place in evidence; the word
        stands next to it, so the writer copies instead of re-deriving."""
        assert detector_confidence_note(0.72) == (
            "confiance du détecteur : 0,72 — lecture ferme"
        )
        assert detector_confidence_note(0.4) == (
            "confiance du détecteur : 0,4 — lecture provisoire"
        )


class TestBothActsPrintTheSameWord:
    """The R1136a defect, as a witness: one detection, two briefings."""

    def test_the_same_detection_is_ferme_in_both_acts(self):
        act2, act3 = _both_prompts(_state(_FERME_CONFIDENCE))
        expected = "confiance du détecteur : 0,72 — lecture ferme"
        assert expected in act2, "Act II must print the ladder word"
        assert expected in act3, "Act III must print the SAME ladder word"

    def test_a_low_confidence_is_provisoire_in_both_acts(self):
        act2, act3 = _both_prompts(_state(_PROVISOIRE_CONFIDENCE))
        expected = "confiance du détecteur : 0,4 — lecture provisoire"
        assert expected in act2
        assert expected in act3

    def test_the_consigne_says_take_the_printed_word(self):
        """The rule the writers receive: the word is printed beside the
        measure — reprends CE mot, and a written reserve only lowers."""
        act2, act3 = _both_prompts(_state(_FERME_CONFIDENCE))
        for prompt in (act2, act3):
            assert "reprends CE mot" in prompt
            assert "jamais l'élever" in prompt


class TestTheCalibrationIsHonest:
    """The bands are a choice on a measured distribution — pin the choice
    where the census can be re-read (the PR body carries the census)."""

    def test_the_rule_no_longer_leaves_the_scale_to_the_writer(self):
        assert "provisoire" in DETECTION_STANDING_RULE
        assert "moyenne" in DETECTION_STANDING_RULE
        assert "ferme" in DETECTION_STANDING_RULE
        # the pre-#3369 rule said the words and the ban only — the scale
        # sentence is what this repair adds.
        assert "ne trace pas ta propre échelle" in DETECTION_STANDING_RULE


@pytest.mark.skipif(
    not _REAL_STATE.exists(), reason="no stored real state on this seat"
)
class TestTheOfflineReplayOnTheRealState:
    """DoD replay — the most recent real state this seat holds (named in
    the PR body): every confidence the acts print carries the word the
    father gives that number, in BOTH acts."""

    _NOTE_RE = re.compile(r"confiance du détecteur : (\d,\d+) — (lecture \w+)")

    def _notes(self, prompt):
        found = {}
        for match in self._NOTE_RE.finditer(prompt):
            value = float(match.group(1).replace(",", "."))
            word = match.group(2)
            if value in found:
                assert found[value] == word, (value, word)
            found[value] = word
        return found

    def test_every_printed_note_carries_its_fathers_word(self):
        with _REAL_STATE.open(encoding="utf-8") as handle:
            # The evidence builders read the state through attributes
            # (``getattr``), so the stored mapping becomes a namespace —
            # the same bridge every stored-state witness here uses.
            state = SimpleNamespace(**json.load(handle))
        act2, act3 = _both_prompts(state)
        notes2, notes3 = self._notes(act2), self._notes(act3)
        assert notes2 and notes3, "the real state must reach both acts"
        for value, word in {**notes2, **notes3}.items():
            assert word == detection_standing_word(value), (value, word)
