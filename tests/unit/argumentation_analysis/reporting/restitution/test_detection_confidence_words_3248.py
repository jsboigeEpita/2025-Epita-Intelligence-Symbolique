"""#3248 — the detector's raw decimal confidence is evidence vocabulary,
not reader prose.

The R1113a paid pass (issue #3248) showed the Act III narrative saying
« avec une confiance de détection de 0,6 à 0,7 » — twice on one sentence
pair — while the same render said the standing in words three pages
earlier (« sa lecture reste provisoire », « le détecteur le juge
fermement »). Both vocabularies live in one render and the reader cannot
weigh a « 0,6 ». The copy source is the evidence side: every fallacy line
in both acts' prompts prints « confiance du détecteur : 0,x »
(``fallacy_attribution.detector_confidence_note``, #3231) — correct AS
EVIDENCE — and the #3234 contract already gives the acts their standing
in words. The consignes did not pin the choice, so the decimal riding the
writer's copy is the #3225/#3244 class: evidence vocabulary on the reader
surface.

Three gestures, one per side:

* ``DETECTION_STANDING_RULE`` lives in ``fallacy_attribution``, beside the
  note that prints the decimal — the ONE reader-facing ladder in words
  (provisoire / moyenne / ferme) and the ban on the figure — grafted into
  BOTH acts' consignes (one constant, one father, the #3237 gesture);
* ``check_reader_vocabulary`` learns the class: a line carrying
  « confiance »/« confidence » AND a 0,x decimal FAILs. BOTH tokens must
  sit on the same line — the ladder words alone never match;
* the pre-calculated evidence keeps its decimals (the evidence side is
  unchanged — anti-pendulum).

Measured on this seat before narrowing (measure_3248_before, scratchpad,
2026-10-25): 57 stored campaign renders, 0 line carries the pair, while
the ladder words appear throughout (provisoire ×5, ferme ×16 — none
flagged). The six tunnel renders (R1108→R1113a) live on the coordinator's
seat; the replay box stays there (#3243 precedent) — this witness proves
the same property on this seat's population.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)
from argumentation_analysis.reporting.restitution.reader_vocabulary_check import (
    check_reader_vocabulary,
)


def _standing_rule():
    """Lazy: the constant does not exist on unrepaired main — each test that
    needs it reddens on its own instead of failing the whole collection."""
    from argumentation_analysis.core.fallacy_attribution import (
        DETECTION_STANDING_RULE,
    )

    return DETECTION_STANDING_RULE


# The R1113a sentence pair, quoted in the issue — writer-produced French
# standing on a detection, no corpus text carried.
_R1113A_LINE = (
    "Le trait d'esprit relève de la dérision, avec une confiance de "
    "détection de 0,6 à 0,7 ; le texte attaque l'interlocuteur sans "
    "répondre sur le fond (confiance de 0,6 à 0,7)."
)
# The same render, three pages earlier — the #3234 ladder doing its job.
_LADDER_SENTENCES = (
    "Sa lecture reste provisoire : le détecteur le juge fermement, et le "
    "degré de confiance du verdict suit la convergence des méthodes."
)

_STORED_STATES = sorted(
    glob.glob(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "..",
            "argumentation_analysis",
            "evaluation",
            "results",
            "campaign_2841_lecture",
            "04_annexes",
            "states",
            "state_full_*.json",
        )
    )
)

_ACT_KEYS = ("act1_framing", "act2_narrative", "act3_conclusion")


def _stored_act_bodies() -> list[tuple[str, str]]:
    """The stored act bodies (file stem, body) — skipped cleanly on CI."""
    import json

    bodies: list[tuple[str, str]] = []
    for path in _STORED_STATES:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for key in _ACT_KEYS:
            value = data.get(key)
            if isinstance(value, str) and value:
                bodies.append((f"{os.path.basename(path)}:{key}", value))
    return bodies


def _carries_the_class(body: str) -> bool:
    """The class, spelled independently of the check's own regexes — a
    witness must not merely re-run the code it guards (anti-theatre)."""
    import re

    return any(
        re.search(r"confiance|confidence", line, re.IGNORECASE)
        and re.search(r"\b0[.,]\d", line)
        for line in body.splitlines()
    )


class TestTheCheckKnowsTheConfidenceDecimalClass:
    def test_the_r1113a_sentence_pair_flags(self) -> None:
        """Born red: check_reader_vocabulary passes the line on main."""
        verdict = check_reader_vocabulary(_R1113A_LINE)
        assert verdict.band == "FAIL"
        assert any("#3248" in r for r in verdict.reasons)

    def test_the_english_spelling_flags_too(self) -> None:
        verdict = check_reader_vocabulary(
            "the detector holds this one with a confidence of 0.7, says prose"
        )
        assert verdict.band == "FAIL"

    def test_the_ladder_words_alone_pass(self) -> None:
        """The #3234 words never carry a figure — they must not flag."""
        assert check_reader_vocabulary(_LADDER_SENTENCES).band == "PASS"

    def test_a_confidence_word_without_any_number_passes(self) -> None:
        verdict = check_reader_vocabulary(
            "la convergence des méthodes donne au lecteur une confiance élevée"
        )
        assert verdict.band == "PASS"

    def test_a_bare_decimal_without_the_word_passes(self) -> None:
        """A decimal alone belongs to other families — the class needs the
        word AND the figure on the same line."""
        verdict = check_reader_vocabulary(
            "la densité du graphe Dung calculée est de 0,33"
        )
        assert verdict.band == "PASS"


class TestBothActsConsignesNameTheLadder:
    """The prompt side that removes the temptation (the #3225 gesture):
    the consigne pins the ONE ladder in words and bans the figure."""

    def test_the_rule_names_the_ladder_and_bans_the_figure(self) -> None:
        rule = _standing_rule()
        for word in ("provisoire", "moyenne", "ferme"):
            assert word in rule, f"the ladder word {word!r} is missing"
        assert (
            "la confiance chiffrée du détecteur ne paraît jamais dans le "
            "récit" in rule
        ), "the ban sentence the issue words is missing"

    def test_the_act2_consigne_carries_the_rule(self) -> None:
        state = UnifiedAnalysisState("texte synthétique sans valeur de corpus")
        prompt = build_act2_prompt(build_act2_evidence(state))
        assert _standing_rule() in prompt

    def test_the_act3_consigne_carries_the_rule(self) -> None:
        state = UnifiedAnalysisState("texte synthétique sans valeur de corpus")
        prompt = build_act3_prompt(build_act3_evidence(state))
        assert _standing_rule() in prompt

    def test_the_evidence_keeps_its_decimals(self) -> None:
        """Anti-pendulum: the ban is on the READER surface only — the
        pre-calculated evidence lines keep printing the detector's figure
        (correct AS EVIDENCE, the issue's own boundary)."""
        state = SimpleNamespace(
            identified_arguments={"arg_1": "these A"},
            identified_fallacies={
                "f_1": {
                    "target_argument_id": "arg_1",
                    "type": "ad_hominem",
                    "justification": "la ligne attaque l'auteur au lieu du propos",
                    "confidence": 0.6,
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
        act2_prompt = build_act2_prompt(build_act2_evidence(state))
        assert "confiance du détecteur : 0,6" in act2_prompt
        act3_prompt = build_act3_prompt(build_act3_evidence(state))
        assert "confiance du détecteur : 0,6" in act3_prompt


@pytest.mark.skipif(not _STORED_STATES, reason="no stored states on this seat")
class TestTheStoredActBodies:
    def test_every_carrier_is_flagged(self) -> None:
        """Population form of the no-false-positive measurement: a stored
        act body carrying the class MUST be flagged, never passed. On this
        seat's campaign renders the carrier count is 0 (the one known hit
        — R1113a — lives on the coordinator's corpus); a carrier that
        appears later is a real defect and this witness must hold."""
        carriers = 0
        for _name, body in _stored_act_bodies():
            if _carries_the_class(body):
                carriers += 1
                assert check_reader_vocabulary(body).band == "FAIL", _name
        # The measurement this test encodes (2026-10-25, 49 states):
        assert carriers == 0
