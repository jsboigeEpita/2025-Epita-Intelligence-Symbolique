"""#3200 — the coverage range is computed from the FINAL map, at assembly.

R1109 rendered « Couverture : de 6 à 10 unités selon les modules » while the
final state's ``analysis_coverage`` held ``synthesis_args`` 15/91 and
``synthesis_fallacies`` 15/31 (range 6..15). The writer was not the cause: the
run logged zero woven-range removals, and the grafted passage is the
pipeline's own sentence (#3182). The cause is phase order — ``act1_framing``
sits at DAG level 5 of ``build_spectacular_workflow`` while ``debate`` runs at
6 and ``deep_synthesis`` / ``governance`` at 7, so Act I reads the coverage map
as it stood then, and the sentence says « selon les modules » about the whole
analysis.

The repair is a placement (issue shape (a)): the passage is re-derived at the
single assembly point (``build_restitution_acts``), where the finished state
and the act string are both in hand. Not a writer rule, not an Act I
dependency on ``deep_synthesis``.

Deterministic — no JVM, no LLM, no network.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    COVERAGE_HEADING,
    build_act1_framing,
    record_stakes_count,
    refresh_coverage_passage,
)
from argumentation_analysis.reporting.restitution.pipeline_adapter import (
    build_restitution_acts,
    render_spectacular_restitution,
)

#: What Act I can see when it runs: the phases that recorded coverage BEFORE
#: DAG level 5 (``nl_to_logic`` 2, ``fol``/``pl``/``quality`` 3, ``atms``/
#: ``counter`` 4) plus the stakes axis. Range 6..10 — the R1109 render.
_PRE_ACT1_COVERAGE = {
    "nl_to_logic": {"k": 6, "N": 90},
    "fol": {"k": 10, "N": 90},
    "pl": {"k": 10, "N": 90},
    "quality": {"k": 8, "N": 90},
    "counter": {"k": 10, "N": 90},
    "stakes": {"k": 30, "N": 90},
}

#: What ``deep_synthesis`` (DAG level 7) adds AFTER Act I has run.
_SYNTHESIS_COVERAGE = {
    "synthesis_args": {
        "k": 15,
        "N": 91,
        "bands_covered": 3,
        "bands_total": 3,
    },
    "synthesis_fallacies": {
        "k": 15,
        "N": 31,
        "bands_covered": 3,
        "bands_total": 3,
    },
}

#: A woven Acte I with no range restatement — the R1109 shape (0 removals).
_WOVEN = (
    "### Le texte\n\n"
    "Le propos vient d'un locuteur en autorité devant une assemblée.\n\n"
    "### Les enjeux\n\n"
    "Ce qui se joue est l'adhésion d'une audience hésitante.\n\n"
    "QUESTION INTERPRÉTATIVE : Ce propos gagne-t-il l'adhésion par l'autorité ?"
)

_ACT2 = (
    "### Le mouvement ad hominem\n\n"
    "Le premier mouvement disqualifie l'adversaire plutôt que sa position ; le "
    "solveur confirme l'inconsistance de l'inférence sous-jacente. C'est un "
    "dérapage de la famille ad hominem."
)
_ACT3 = (
    "### Synthèse honnête\n\n"
    "L'analyse localise un dérapage et le solveur confirme l'inconsistance "
    "d'une inférence. La caractérisation peut donc être assurée sans "
    "sur-claim, sur la base réellement examinée."
)


def _six_stakes() -> list:
    return [
        {"stake_type": "décision", "description": f"point de décision {i}"}
        for i in range(6)
    ]


def _state(**fields) -> SimpleNamespace:
    base = dict(
        act1_framing="",
        act2_narrative=_ACT2,
        act3_conclusion=_ACT3,
        source_metadata={"genre": "discours politique"},
        stakes_and_stakeholders={
            "stakes": _six_stakes(),
            "stakeholders": [],
            "rhetorical_register": "délibératif",
            "discursive_arena": "politique",
        },
        identified_arguments={"arg_a": "thèse", "arg_b": "support"},
        identified_fallacies={},
        analysis_coverage=dict(_PRE_ACT1_COVERAGE),
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _stub_llm(return_value: str):
    async def _call(_prompt: str) -> str:
        return return_value

    return _call


def _framing(state, woven: str):
    return asyncio.run(build_act1_framing(state, llm_callable=_stub_llm(woven)))


def _last_line(text: str) -> str:
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def _run_order_state(**fields) -> SimpleNamespace:
    """Simulate the spectacular run order: Act I first, ``deep_synthesis`` after.

    Act I is woven on the state as it stands at DAG level 5, persisted onto the
    state exactly as the state writer does, and only then do the synthesis
    entries land — what ``deep_synthesis`` writes at level 7.
    """
    state = _state(**fields)
    result = _framing(state, _WOVEN)
    assert result.status == "woven"
    state.act1_framing = result.narrative
    state.analysis_coverage.update(_SYNTHESIS_COVERAGE)
    return state


# ============================================================================
# 1. The witness — the ASSEMBLED report carries the final map's figures
# ============================================================================


class TestTheAssembledReportCarriesTheFinalRange:
    def test_act1_itself_saw_the_partial_map(self):
        """The defect's premise: Act I's own passage is the 6..10 range.

        On unmodified ``origin/main`` this is also the ASSEMBLED figure —
        ``build_restitution_acts`` copies the act string verbatim — so the
        test below is born red there.
        """
        state = _state()
        result = _framing(state, _WOVEN)

        assert "de 6 à 10 unités selon les modules" in result.narrative
        assert "de 6 à 15" not in result.narrative

    def test_the_assembled_report_says_the_final_range(self):
        """R1109: 6..10 rendered over a record at 6..15."""
        state = _run_order_state()

        assembled = render_spectacular_restitution(state).markdown

        assert "de 6 à 15 unités selon les modules" in assembled
        assert "de 6 à 10 unités" not in assembled, (
            "the assembled report still carries Act I's partial range — the "
            "reader reads a range the final coverage map contradicts"
        )
        assert COVERAGE_HEADING in assembled

    def test_the_refreshed_passage_keeps_the_stakes_figure_and_its_count(self):
        """The re-derived sentence is the producer's, stakes record included."""
        state = _run_order_state()

        acts = build_restitution_acts(state)

        assert "l'extracteur d'enjeux a lu 30 unités" in acts.act1_framing
        assert "le registre en nomme 6 enjeux" in acts.act1_framing

    def test_the_closing_question_stays_last_after_the_refresh(self):
        """Act III binds its response beat to the closing question line."""
        assembled = render_spectacular_restitution(_run_order_state()).markdown
        act1_block = assembled.split("\n## ", 2)[1]

        assert _last_line(act1_block).startswith("QUESTION INTERPRÉTATIVE")


# ============================================================================
# 2. Control — an unchanged map leaves the output byte-equal
# ============================================================================


class TestAnUnchangedMapLeavesTheOutputByteEqual:
    def test_the_assembled_act_equals_the_woven_act(self):
        """Every entry present before Act I: assembly changes nothing.

        ``origin/main``'s ``build_restitution_acts`` returns the state's act
        string verbatim, so equality here IS byte-equality with main on the
        same state.
        """
        state = _state(analysis_coverage={**_PRE_ACT1_COVERAGE, **_SYNTHESIS_COVERAGE})
        result = _framing(state, _WOVEN)
        state.act1_framing = result.narrative

        assert build_restitution_acts(state).act1_framing == result.narrative
        assert refresh_coverage_passage(result.narrative, state) == result.narrative

    def test_no_coverage_map_leaves_the_act_untouched(self):
        """No record figure → no passage, and no fabricated one at assembly."""
        state = _state(analysis_coverage={})
        state.act1_framing = (
            "### Le texte\n\nUn propos politique.\n\n"
            "QUESTION INTERPRÉTATIVE : Que défend-il ?"
        )

        assert build_restitution_acts(state).act1_framing == state.act1_framing

    def test_an_empty_act_stays_empty(self):
        """Assembly never invents an act to carry a passage."""
        state = _state(analysis_coverage=dict(_SYNTHESIS_COVERAGE))
        assert build_restitution_acts(state).act1_framing == ""


# ============================================================================
# 3. The passage survives — replaced, never dropped
# ============================================================================


class TestThePassageSurvives:
    def test_an_act_without_a_passage_gets_the_producers_figures(self):
        """A pre-#3159 act (no heading) is completed, not left bare."""
        state = _state(analysis_coverage=dict(_SYNTHESIS_COVERAGE))
        state.act1_framing = (
            "### Le texte\n\nUn propos politique.\n\n"
            "QUESTION INTERPRÉTATIVE : Que défend-il ?"
        )

        refreshed = build_restitution_acts(state).act1_framing

        assert COVERAGE_HEADING in refreshed
        assert "Couverture : 15 unités dans chaque module" in refreshed
        assert _last_line(refreshed).startswith("QUESTION INTERPRÉTATIVE")

    def test_the_refresh_is_idempotent(self):
        state = _run_order_state()
        once = refresh_coverage_passage(state.act1_framing, state)
        assert refresh_coverage_passage(once, state) == once

    def test_reading_the_act1_time_map_again_is_the_failing_shape(self):
        """The mutation: feed the refresh Act I's own map (#3200 DoD).

        Applied to the assembly call (its only caller), the assembled report
        carries « de 6 à 10 » again — the witness reddens. This pins the shape
        the mutation takes; the mutation itself is measured on the assembly
        call, not here.
        """
        state = _run_order_state()
        act1_time_state = _state()  # the same state Act I read at level 5

        mutated = refresh_coverage_passage(state.act1_framing, act1_time_state)

        assert "de 6 à 10 unités selon les modules" in mutated
        assert "de 6 à 15" not in mutated


# ============================================================================
# 4. The stakes count has one reader
# ============================================================================


class TestTheStakesCountHasOneReader:
    def test_the_record_list_is_counted_once(self):
        state = _state()
        assert record_stakes_count(state) == 6
        assert record_stakes_count({"stakes_and_stakeholders": {"stakes": []}}) == 0
        assert record_stakes_count(SimpleNamespace()) == 0
