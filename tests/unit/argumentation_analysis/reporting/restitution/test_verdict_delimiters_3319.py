"""#3319 — the pre-calculated Act III verdict is handed to the writer
between « », and the writer copies the delimiters into the render.

The dispatch R1129 census: 2 of the coordinator's 6 saved renders print
the discourse verdict inside « » — quotes the producer itself
interpolated (``discourse_virtue_sentence`` used to return
``« Le discours tient sur … . »`` under an instruction that only said
« reprends-le tel quel »). A model line handed over quoted comes back
quoted: the delimiters read as part of the sentence to copy.

This seat's census (1016 stored reader texts, zero LLM calls): **0**
carriers — the verdict-carrying renders live on the coordinator's
corpus, so the check class below is justified by the population witness
(the #3244 precedent): every carrier flags, never passes, and the shape
is pinned to the builder's own lead plus its machine figures — a corpus
sentence cannot carry them, so nothing a speaker said can match.

The fix is the quoting only (anti-pendulum): the verdict stays
pre-composed, verbatim-demanded, display-named (#3244), figure-based
(#3159) and exclusive. Only the « » go, and the instruction says so in
words.
"""

from __future__ import annotations

from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    QualityStrength,
    discourse_virtue_sentence,
)
from argumentation_analysis.reporting.restitution.reader_vocabulary_check import (
    check_reader_vocabulary,
)


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


def _quoted_verdict_re():
    """Lazy — the class does not exist on unrepaired main; each check-class
    test reddens on its own instead of failing the whole collection."""
    from argumentation_analysis.reporting.restitution.reader_vocabulary_check import (
        _QUOTED_VERDICT_RE,
    )

    return _QUOTED_VERDICT_RE


# The defect's exact shape, as the dispatch quotes it: the builder's lead,
# display names (#3244), machine figures (#3159) — inside « ». Writer-
# produced French, no corpus text.
_R1129_QUOTED = (
    "Le verdict tombe : « Le discours tient sur faible redondance "
    "(6/7 arguments évalués, 35 unités). »"
)

_R1129_BARE = (
    "Le verdict tombe : Le discours tient sur faible redondance "
    "(6/7 arguments évalués, 35 unités)."
)


class TestTheVerdictPrintsBare:
    """Born red on main: the builder interpolates « » (2 of the coordinator's
    6 saved renders carried them into the reader surface)."""

    def test_the_verdict_carries_no_guillemets(self) -> None:
        sentence = discourse_virtue_sentence(
            [_strength("redondance_faible", at_top=6, evaluated=7, units=35)]
        )
        assert "«" not in sentence, sentence
        assert "»" not in sentence, sentence

    def test_the_instruction_names_the_delimiters(self) -> None:
        """« tel quel » alone was read as « delimiters included » — the
        instruction now excludes them in words."""
        sentence = discourse_virtue_sentence(
            [_strength("redondance_faible", at_top=6, evaluated=7, units=35)]
        )
        assert "sans guillemets" in sentence

    def test_the_multi_virtue_verdict_is_bare_too(self) -> None:
        sentence = discourse_virtue_sentence(
            [
                _strength("pertinence", at_top=6, evaluated=8, units=90),
                _strength("refutation_constructive", at_top=7, evaluated=8, units=90),
            ]
        )
        assert "«" not in sentence and "»" not in sentence, sentence


class TestTheVerdictSubstanceIsUntouched:
    """Anti-pendulum: the quoting change softens nothing — the verdict
    keeps its instruction, its measured base, its display names and its
    exclusivity clause (all green on both sides)."""

    def test_verbatim_still_demanded(self) -> None:
        sentence = discourse_virtue_sentence(
            [_strength("redondance_faible", at_top=6, evaluated=7, units=35)]
        )
        assert "reprends-le tel quel" in sentence

    def test_the_lead_the_figures_and_the_exclusivity_stay(self) -> None:
        sentence = discourse_virtue_sentence(
            [_strength("redondance_faible", at_top=6, evaluated=7, units=35)]
        )
        assert "Le discours tient sur" in sentence
        assert "(6/7 arguments évalués, 35 unités)" in sentence
        assert "Aucune autre vertu ne se dit du discours." in sentence

    def test_the_display_name_not_the_identifier(self) -> None:
        sentence = discourse_virtue_sentence(
            [_strength("refutation_constructive", at_top=7, evaluated=8)]
        )
        assert "réfutation constructive" in sentence
        assert "refutation_constructive" not in sentence

    def test_the_no_virtue_branch_never_had_them(self) -> None:
        """The honest-absence branch was already bare and stays so."""
        sentence = discourse_virtue_sentence(
            [_strength("clarte", at_top=2, evaluated=8)]
        )
        assert "aucune vertu n'atteint 3/4" in sentence
        assert "«" not in sentence and "»" not in sentence


class TestTheCheckKnowsTheQuotedVerdict:
    """The population witness: every quoted carrier flags, never passes
    (born red on main — the class does not exist there)."""

    def test_the_r1129_quoted_shape_flags(self) -> None:
        verdict = check_reader_vocabulary(_R1129_QUOTED)
        assert verdict.band == "FAIL", verdict.reasons
        assert any("#3319" in r for r in verdict.reasons)

    def test_the_bare_verdict_does_not_flag(self) -> None:
        """The same sentence, delimiters dropped — the fix's own output —
        passes: the class holds the quoting, not the verdict."""
        verdict = check_reader_vocabulary(_R1129_BARE)
        assert verdict.band == "PASS", verdict.reasons

    def test_a_quoted_corpus_line_does_not_flag(self) -> None:
        """Guillemets are legitimate French punctuation for a quoted line;
        without the builder's lead and figures there is no verdict shape."""
        body = "L'orateur concède un point : « Le discours est dense et vif. »"
        verdict = check_reader_vocabulary(body)
        assert verdict.band == "PASS", verdict.reasons

    def test_the_regex_is_pinned_to_the_builder_shape(self) -> None:
        """The lead without the figures (a paraphrase) and the figures
        without the lead (a bare enumeration) both stay out — the shape is
        the pair, and the pair is code-written."""
        lead_only = "« Le discours tient sur la faible redondance. »"
        figures_only = "« Forte (6/7 arguments évalués, 35 unités). »"
        assert _quoted_verdict_re().search(lead_only) is None
        assert _quoted_verdict_re().search(figures_only) is None
