"""#3159 (R1108) — the coverage range is rendered by the pipeline, never by the prose.

#3175 made the producer write the range sentence and told the writer to copy it
verbatim. The first render after that (R1108, doc_A, Sonnet 5.5, union tree
``58aa468c0``) said « de **6 à 10** unités selon les modules » over a record at
6..15, and its stakes section opened on « L'extracteur dégage **trente
enjeux** » — the 30 is the number of UNITS the stakes extractor read; the
record holds 6 stakes. Two moves close it, measured here with no LLM:

1. **The range survives by construction.** A woven range restatement is removed
   and the pipeline's sentence is grafted after the prose — the #3134/#1605
   enforcement shape (the record's line replaces the woven one, the event is
   logged, never a reader note). The graft sits above the closing
   « QUESTION INTERPRÉTATIVE » line, which stays last (Act III binds to it).
2. **The stakes figure carries its unit**, and the stake count comes from the
   record's own list when it holds one.

Deterministic — no JVM, no LLM, no network.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    COVERAGE_HEADING,
    build_act1_evidence,
    build_act1_framing,
    build_act1_prompt,
    coverage_range_sentence,
    format_coverage_passage,
    restated_coverage_range_sentences,
)

# --- the doc_B shape: phases at 6..15, stakes read 30, record holds 6 --------


def _doc_b_coverage() -> dict:
    return {
        "debate": {"k": 6, "N": 90},
        "governance": {"k": 6, "N": 90},
        "nl_to_logic": {"k": 6, "N": 90},
        "quality": {"k": 8, "N": 90},
        "atms": {"k": 8, "N": 90},
        "counter": {"k": 10, "N": 90},
        "fallacy": {"k": 10, "N": 90},
        "fol": {"k": 10, "N": 90},
        "pl": {"k": 10, "N": 90},
        "jtms": {"k": 10, "N": 90},
        "synthesis": {"k": 15, "N": 90},
        "stakes": {"k": 30, "N": 90},
    }


def _six_stakes() -> list:
    return [
        {"stake_type": "décision", "description": f"point de décision {i}"}
        for i in range(6)
    ]


def _state(**fields) -> SimpleNamespace:
    base = dict(
        source_metadata={"genre": "discours politique"},
        stakes_and_stakeholders={
            "stakes": _six_stakes(),
            "stakeholders": [],
            "rhetorical_register": "délibératif",
            "discursive_arena": "politique",
        },
        identified_arguments={"arg_1": "thèse", "arg_2": "support"},
        analysis_coverage=_doc_b_coverage(),
    )
    base.update(fields)
    return SimpleNamespace(**base)


#: A woven Acte I that carries the R1108 rewrite — the writer's own range,
#: wrong by construction (6..15 in the record), and its closing question.
_WOVEN_WITH_WRONG_RANGE = (
    "### Le texte\n\n"
    "Le discours analysé est un propos politique d'un locuteur en autorité.\n\n"
    "### La couverture\n\n"
    "L'analyse a porté sur de 6 à 10 unités selon les modules.\n\n"
    "### Le spectre attendu\n\n"
    "Un auditeur averti doit guetter l'appel à l'autorité pour ce genre.\n\n"
    "QUESTION INTERPRÉTATIVE : Ce discours gagne-t-il l'adhésion par l'autorité ?"
)

#: The same act with no range restatement — the removal must leave it alone.
_WOVEN_WITHOUT_RANGE = (
    "### Le texte\n\n"
    "Le discours analysé est un propos politique d'un locuteur en autorité.\n\n"
    "### Le spectre attendu\n\n"
    "Un auditeur averti doit guetter l'appel à l'autorité pour ce genre.\n\n"
    "QUESTION INTERPRÉTATIVE : Ce discours gagne-t-il l'adhésion par l'autorité ?"
)


def _stub_llm(return_value: str):
    async def _call(_prompt: str) -> str:
        return return_value

    return _call


def _framing(state, woven: str):
    return asyncio.run(build_act1_framing(state, llm_callable=_stub_llm(woven)))


def _last_line(text: str) -> str:
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    return lines[-1] if lines else ""


# ============================================================================
# 1. The range survives the render by construction
# ============================================================================


class TestTheRangeSurvivesTheRender:
    def test_the_woven_range_is_replaced_by_the_pipeline_sentence(self):
        """R1108: the prose said 6 à 10 over a record at 6..15."""
        result = _framing(_state(), _WOVEN_WITH_WRONG_RANGE)

        assert result.status == "woven"
        assert "de 6 à 10 unités" not in result.narrative, (
            "the writer's range survived the render — the reader would read a "
            "range the record contradicts"
        )
        assert "de 6 à 15 unités selon les modules" in result.narrative
        assert COVERAGE_HEADING in result.narrative

    def test_the_closing_question_stays_last(self):
        """Act III binds its response beat to the question; the graft goes above."""
        result = _framing(_state(), _WOVEN_WITH_WRONG_RANGE)

        assert _last_line(result.narrative).startswith("QUESTION INTERPRÉTATIVE")
        assert result.interpretive_question

    def test_prose_without_a_range_is_left_intact(self):
        """Control: only a range restatement is removed — the prose survives."""
        result = _framing(_state(), _WOVEN_WITHOUT_RANGE)

        assert (
            "Un auditeur averti doit guetter l'appel à l'autorité" in result.narrative
        )
        assert "de 6 à 15 unités selon les modules" in result.narrative

    def test_no_coverage_map_means_no_graft(self):
        """Control: no record figure → no passage, never a fabricated range."""
        result = _framing(_state(analysis_coverage={}), _WOVEN_WITHOUT_RANGE)

        assert COVERAGE_HEADING not in result.narrative
        assert "Couverture :" not in result.narrative

    def test_a_single_figure_needs_no_range(self):
        uniform = {p: {"k": 10, "N": 90} for p in ("debate", "quality", "pl")}
        sentence = coverage_range_sentence(uniform)
        assert "10 unités dans chaque module" in sentence
        assert "de 10 à 10" not in sentence


# ============================================================================
# 2. The stakes figure carries its unit and the record's own count
# ============================================================================


class TestTheStakesFigureCarriesItsUnit:
    def test_the_prompt_says_units_read_and_the_records_count(self):
        evidence = build_act1_evidence(_state())
        assert evidence.stakes_count == 6
        sentence = coverage_range_sentence(evidence.analysis_coverage, 6)

        assert "l'extracteur d'enjeux a lu 30 unités" in sentence
        assert "le registre en nomme 6 enjeux" in sentence
        assert "comptés à part : 30" not in sentence

    def test_a_record_with_no_stakes_says_no_count(self):
        """Control: no stakes list → the count is not said (never « 0 enjeu »)."""
        state = _state(
            stakes_and_stakeholders={"stakes": [], "stakeholders": []},
        )
        evidence = build_act1_evidence(state)
        assert evidence.stakes_count == 0
        sentence = coverage_range_sentence(evidence.analysis_coverage, 0)

        assert "l'extracteur d'enjeux a lu 30 unités" in sentence
        assert "nomme" not in sentence

    def test_the_prompt_renders_both_figures(self):
        prompt = build_act1_prompt(build_act1_evidence(_state()))

        assert "l'extracteur d'enjeux a lu 30 unités" in prompt
        assert "le registre en nomme 6 enjeux" in prompt
        # The copy-it-verbatim instruction is gone: the passage carries it.
        assert "reprends-les tels quels" not in prompt
        assert COVERAGE_HEADING in prompt


# ============================================================================
# 3. The restatement detector — narrow shapes only
# ============================================================================


class TestTheRangeDetector:
    def test_the_r1108_rewrite_is_caught(self):
        assert restated_coverage_range_sentences(_WOVEN_WITH_WRONG_RANGE) == [
            "L'analyse a porté sur de 6 à 10 unités selon les modules."
        ]

    def test_the_other_french_range_shapes_are_caught(self):
        for text in (
            "Les modules ont lu entre 6 et 15 unités.",
            "La couverture va de 6 à 15 unités.",
        ):
            assert restated_coverage_range_sentences(text), text

    def test_a_single_phase_figure_is_not_a_range(self):
        """Control: a per-phase count is a record figure — never removed."""
        for text in (
            "La détection de sophismes a lu 10 unités.",
            "La synthèse a porté sur 15 unités.",
            "L'ancrage localise 84 unités localisées.",
        ):
            assert restated_coverage_range_sentences(text) == [], text

    def test_the_passage_is_empty_without_a_sentence(self):
        assert format_coverage_passage("") == ""
        assert format_coverage_passage("   ") == ""
