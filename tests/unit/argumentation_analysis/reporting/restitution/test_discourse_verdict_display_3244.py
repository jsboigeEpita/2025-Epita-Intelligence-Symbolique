"""#3244 — the pre-calculated discourse verdict prints snake_case virtue
identifiers on the reader surface.

The R1111a paid pass (issue #3244) showed Act III's verdict sentence
reading « Le discours tient sur pertinence (…) ; refutation_constructive
(…) ; redondance_faible (…). » — the internal virtue identifiers, snake_case
and unaccented, on the surface the reader sees. R1110b's Act III carried
the same class (« clarte », the identifier without its accent). Third
instance of the #3225 family: a code-written token, copied by a writer
INSTRUCTED to copy it (« VERDICT PRÉ-CALCULÉ (reprends-le tel quel) »),
invisible to the checks.

Census (this seat, 49 stored states, main ``fe9f9e4c2``):

* the sentence builder is ``discourse_virtue_sentence`` (act3:1074): the
  ``named`` join interpolates ``s.virtue`` raw — the identifier exactly as
  ``_collect_quality_strengths`` counted it from
  ``state.argument_quality_scores``, whose keys are the producer's ``VERTUES``
  (quality_evaluator:261, the 9 identifiers);
* rebuilt from every stored state's real scores, **19 of 48** verdict
  sentences carry at least one machinery identifier (``redondance_faible``
  the most common, then ``refutation_constructive``, ``clarte``) — the
  occurrence needs a virtue above the 3/4 bar, hence intermittent renders;
* on the reader surface (144 stored act bodies) this seat carries **0** —
  the 4 known hits (R1110b + R1111a, both ``act3_conclusion``) live on the
  coordinator's corpus; the population witness below turns the measurement
  into the property (every carrier flags, never passes);
* the strengths LIST at act3:2956 (``- {s.virtue} (…)``) stays on ids by
  design — the data side, the ``social_choice`` precedent (#3238): the
  verdict SENTENCE is the code-written surface the writer copies verbatim.

The fix is the sentence only (anti-pendulum): a display mapping beside the
verdict builder prints each virtue in reader French — « réfutation
constructive », « faible redondance », « clarté »… The state's identifiers
are NOT renamed (``VERTUES``, the quality plugin and every reader keyed by
them keep the ids); the 3/4 bar, the counts and « Aucune autre vertu ne se
dit du discours » stay as they are.

``pertinence`` is excluded from the check class by construction: its
display name IS the French word — flagging it would be a false positive by
definition. The class holds the 8 spellings whose display differs: the 6
snake_case compounds and the 2 accent-stripped singles (« clarte »,
« exhaustivite »), letter-bounded both sides (#3225/#3238 precedent) — the
accented display words (« clarté », « exhaustivité », measured on 59 of
the 144 bodies) never match.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path

import pytest

from argumentation_analysis.agents.core.quality.quality_evaluator import VERTUES
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    QualityStrength,
    discourse_virtue_sentence,
)
from argumentation_analysis.reporting.restitution.reader_vocabulary_check import (
    check_reader_vocabulary,
)


def _virtue_display():
    """Lazy: the mapping does not exist on unrepaired main — each test that
    needs it reddens on its own instead of failing the whole collection."""
    from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
        VIRTUE_DISPLAY_FR,
    )

    return VIRTUE_DISPLAY_FR


def _virtue_id_re():
    """Lazy — same pattern for the check's token class."""
    from argumentation_analysis.reporting.restitution.reader_vocabulary_check import (
        _VIRTUE_ID_RE,
    )

    return _VIRTUE_ID_RE


# The display mapping this PR ships — mirrored here only for the census
# asserts; the totality witness reads the real one from the module.
_DISPLAY = {
    "clarte": "clarté",
    "pertinence": "pertinence",
    "presence_sources": "présence de sources",
    "refutation_constructive": "réfutation constructive",
    "structure_logique": "structure logique",
    "analogie_pertinente": "analogie pertinente",
    "fiabilite_sources": "fiabilité des sources",
    "exhaustivite": "exhaustivité",
    "redondance_faible": "faible redondance",
}

# The 8 machinery spellings the check class holds (``pertinence`` excluded).
_MACHINERY = tuple(v for v in _DISPLAY if v != "pertinence")

# The R1111a Act III verdict sentence as the issue quotes it — the stored
# body lives on the coordinator's seat; the quoted sentence is the witness
# (the #3238 precedent). Writer-produced French, no corpus text.
_R1111A_SENTENCE = (
    "Le discours tient sur pertinence (6/8 arguments évalués, 90 unités) ; "
    "refutation_constructive (7/8 arguments évalués, 90 unités) ; "
    "redondance_faible (6/8 arguments évalués, 90 unités)."
)

# The R1110b form: the identifier without its accent.
_R1110B_SENTENCE = "Le discours tient sur clarte (7/8 arguments évalués, 12 unités)."


def _strength(
    virtue: str, at_top: int = 6, evaluated: int = 8, units: int = 90
) -> QualityStrength:
    return QualityStrength(
        virtue=virtue,
        score=1.0,
        args_at_top=at_top,
        args_evaluated=evaluated,
        units_total=units,
    )


class TestTheVerdictSentenceSpeaksTheReadersFrench:
    def test_every_machinery_identifier_gets_its_display_name(self) -> None:
        """Born red on main: the named join interpolates ``s.virtue`` raw,
        so all 8 machinery identifiers print as themselves."""
        for virtue in _MACHINERY:
            sentence = discourse_virtue_sentence([_strength(virtue)])
            assert _DISPLAY[virtue] in sentence, virtue
            assert virtue not in sentence, virtue

    def test_pertinence_stays_the_french_word(self) -> None:
        """The one identifier whose display IS the French word — unchanged
        (control, green on main; a fix that renames it would be a drift)."""
        sentence = discourse_virtue_sentence([_strength("pertinence")])
        assert "pertinence" in sentence

    def test_the_r1111a_sentence_carries_the_display_names(self) -> None:
        """DoD box 1: rebuilt from R1111a-shaped strengths (the issue's
        sentence, 2 identifiers at base), the verdict carries display names
        and no snake_case identifier."""
        strengths = [
            _strength("pertinence", at_top=6, evaluated=8),
            _strength("refutation_constructive", at_top=7, evaluated=8),
            _strength("redondance_faible", at_top=6, evaluated=8),
        ]
        sentence = discourse_virtue_sentence(strengths)
        assert "réfutation constructive" in sentence
        assert "faible redondance" in sentence
        assert not _virtue_id_re().search(sentence)

    def test_the_bar_the_counts_and_the_exclusivity_clause_stay(self) -> None:
        """Anti-pendulum: the display change softens nothing — the
        pre-calculated verdict keeps its instruction, its measured base and
        its exclusivity clause verbatim."""
        sentence = discourse_virtue_sentence(
            [_strength("redondance_faible", at_top=6, evaluated=7, units=35)]
        )
        # #3319: the directive still demands verbatim, and now names the
        # delimiters it must not copy.
        assert "VERDICT PRÉ-CALCULÉ (reprends-le tel quel, sans guillemets)" in sentence
        assert "(6/7 arguments évalués, 35 unités)" in sentence
        assert "Aucune autre vertu ne se dit du discours." in sentence

    def test_the_mapping_is_total_over_the_canonical_virtues(self) -> None:
        """The mapping reads the producer's own ``VERTUES`` list: a tenth
        virtue arriving without a display name reddens HERE, not in a
        render. (Born red on main: the mapping does not exist.)"""
        assert set(_virtue_display()) == set(VERTUES)

    def test_reinserted_identifier_reddens_the_sentence_witness(self) -> None:
        """Mutation (DoD 3): putting an identifier back in the fixed
        sentence — the exact pre-fix defect — reddens this and the class
        tests above."""
        fixed = discourse_virtue_sentence([_strength("refutation_constructive")])
        reverted = fixed.replace("réfutation constructive", "refutation_constructive")
        assert "refutation_constructive" in reverted, "the mutation did not take"
        assert _virtue_id_re().search(reverted)


class TestTheCheckKnowsTheTokenClass:
    def test_the_r1111a_rendered_sentence_flags(self) -> None:
        """DoD box 2: the stored R1111a Act III (quoted verbatim) FAILs —
        on main the check passes it with no reasons."""
        verdict = check_reader_vocabulary(_R1111A_SENTENCE)
        assert verdict.band == "FAIL"
        assert any("refutation_constructive" in r for r in verdict.reasons)

    def test_the_r1110b_unaccented_form_flags(self) -> None:
        assert check_reader_vocabulary(_R1110B_SENTENCE).band == "FAIL"

    @pytest.mark.parametrize("virtue", _MACHINERY)
    def test_each_machinery_identifier_flags_alone(self, virtue: str) -> None:
        verdict = check_reader_vocabulary(
            f"Le discours tient sur {virtue} (6/8 arguments évalués, 90 unités)."
        )
        assert verdict.band == "FAIL", virtue

    def test_the_fixed_sentence_passes(self) -> None:
        """The repaired surface reads clean — the verdict keeps speaking,
        in the reader's French."""
        verdict = check_reader_vocabulary(
            "Le discours tient sur pertinence (6/8 arguments évalués, 90 "
            "unités) ; réfutation constructive (7/8 arguments évalués, 90 "
            "unités) ; faible redondance (6/8 arguments évalués, 90 unités)."
        )
        assert verdict.band == "PASS"

    def test_the_french_display_words_do_not_flag(self) -> None:
        """False-positive control: every display phrase, woven in prose —
        measured on 59 of the 144 stored bodies for « clarté »/«
        exhaustivité » alone."""
        verdict = check_reader_vocabulary(
            "La clarté du propos tient à une structure logique sûre, à une "
            "analogie pertinente et à la présence de sources dont la "
            "fiabilité des citations donne l'exhaustivité ; c'est une "
            "réfutation constructive, sans bavardage."
        )
        assert verdict.band == "PASS"

    def test_pertinence_the_word_does_not_flag(self) -> None:
        """Excluded by construction — its display IS the French word."""
        verdict = check_reader_vocabulary(
            "Le discours tient sur pertinence (6/8 arguments évalués, 90 unités)."
        )
        assert verdict.band == "PASS"

    def test_internal_key_shapes_do_not_flag(self) -> None:
        """The issue's boundary clause: ``argument_quality_scores`` and the
        scores mapping keys are internal shapes, not prose tokens — the
        letter boundaries keep them out (body-only scope, #1914)."""
        assert not _virtue_id_re().search("argument_quality_scores")
        assert not _virtue_id_re().search("scores_par_vertu")


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


@pytest.mark.skipif(not _STORED_STATES, reason="no stored states on this seat")
class TestTheStoredActBodies:
    def test_every_carrier_is_flagged(self) -> None:
        """Population form of the no-false-positive measurement: a stored
        act body carrying a machinery identifier MUST be flagged, never
        passed. On this seat's 144 bodies the carrier count is 0 (the 4
        known hits live on the coordinator's corpus, R1110b + R1111a) — a
        carrier that appears later is a real defect and this witness must
        hold."""
        carriers = 0
        for _name, body in _stored_act_bodies():
            if _virtue_id_re().search(body):
                carriers += 1
                assert check_reader_vocabulary(body).band == "FAIL", _name
        # The measurement this test encodes (2026-10-25, 49 states):
        assert carriers == 0
