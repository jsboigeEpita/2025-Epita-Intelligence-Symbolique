"""#2966 — Acte II distinguishes « examinée, propre » from « jamais examinée ».

Act II used to hand its writer a movement « les soutiens qui tiennent (aucun
sophisme localisé) » listing every unit that simply had no fallacy entry — on
the 06/10 paid pass, 84 of 94 units, while the per-argument detector had
EXAMINED 10. The word « tiennent » was never a verdict: it was the absence of
an entry, over a population nobody had looked at (family #1019).

The father is coverage: ``record_analysis_coverage`` recorded __how many__
units a phase sampled, never __which__ (#2850/#2896). This file pins the three
states that replace the old two, the ids the writer now carries, and the honest
degradation of a state written before the field.

Privacy: synthetic opaque ids (``arg_N``) and invented French filler only — no
corpus sentence, no source name. Deterministic: no JVM, no LLM, no network.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)

_SOUTIENS = "soutiens"
_NON_EXAMINE = "non examinés"
_SANS_ECHANTILLON = "échantillon non enregistré"

_FILLER = (
    "Une revendication soutenue par un raisonnement explicite, développée sur "
    "plusieurs phrases afin que le mouvement ait de la matière à tisser."
)


def _coverage(
    sampled: List[str], phase: str = "fallacy_per_argument"
) -> Dict[str, Any]:
    """A coverage entry shaped exactly as ``record_analysis_coverage`` writes
    it — including the #2966 ``unit_ids`` the phases now pass."""
    return {
        phase: {
            "k": len(sampled),
            "N": 6,
            "bands_covered": 1,
            "bands_total": 3,
            "unit_ids": list(sampled),
        }
    }


def _state(
    n_units: int = 6, coverage: Dict[str, Any] | None = None, **fields: Any
) -> SimpleNamespace:
    args = {f"arg_{i}": f"{_FILLER} (unité {i})" for i in range(1, n_units + 1)}
    base: Dict[str, Any] = dict(
        identified_arguments=args,
        identified_fallacies={
            "fl_1": {
                "target_argument_id": "arg_1",
                "family": "ad hominem",
                "type": "ad hominem circonstanciel",
                "justification": "L'attaque porte sur la personne, pas sur la thèse.",
            }
        },
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks={},
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        governance_decisions=[],
        debate_transcripts=[],
    )
    if coverage is not None:
        base["analysis_coverage"] = coverage
    base.update(fields)
    return SimpleNamespace(**base)


def _themes(ev: Any) -> List[str]:
    return [m.theme for m in ev.movements]


def _args_of(ev: Any, theme: str) -> List[str]:
    for m in ev.movements:
        if m.theme == theme:
            return [a.arg_id for a in m.arguments]
    return []


class TestCoverageCarriesTheSampledIds:
    """Expected 1 — one field at the writer, read by every consumer."""

    def test_record_analysis_coverage_keeps_the_ids(self) -> None:
        st = UnifiedAnalysisState("2966 probe")
        st.record_analysis_coverage(
            "fallacy_per_argument",
            2,
            6,
            1,
            3,
            span=(0.0, 0.4),
            unit_ids=["arg_1", "arg_2"],
        )
        entry = st.analysis_coverage["fallacy_per_argument"]
        assert entry["unit_ids"] == ["arg_1", "arg_2"]
        # the #2850/#2896 figures are untouched — this is ONE added field
        assert (entry["k"], entry["N"]) == (2, 6)
        assert entry["span_start"] == 0.0

    def test_absent_ids_stay_absent_not_empty(self) -> None:
        """``None`` (not recorded) and ``[]`` (recorded, saw nothing) are two
        different facts and must not collapse: Act II reads the difference."""
        st = UnifiedAnalysisState("2966 probe")
        st.record_analysis_coverage("quality", 0, 6, 0, 3)
        assert "unit_ids" not in st.analysis_coverage["quality"]

        st.record_analysis_coverage("quality", 0, 6, 0, 3, unit_ids=[])
        assert st.analysis_coverage["quality"]["unit_ids"] == []

    def test_ids_are_coerced_to_str(self) -> None:
        st = UnifiedAnalysisState("2966 probe")
        st.record_analysis_coverage("x", 1, 1, 1, 1, unit_ids=[1, "arg_2"])  # type: ignore[list-item]
        assert st.analysis_coverage["x"]["unit_ids"] == ["1", "arg_2"]


class TestAct2ThreeStates:
    """Expected 2 — attacked / examined-and-clean / never examined."""

    def test_only_the_examined_clean_unit_is_called_holding(self) -> None:
        """The issue's witness: N=6, sample {arg_1, arg_2}, a fallacy on arg_1.

        Before the fix arg_2…arg_6 were all 'soutiens qui tiennent'. Now arg_2
        alone holds — it was read and came back clean — and arg_3…arg_6 are
        named as never submitted."""
        ev = build_act2_evidence(_state(coverage=_coverage(["arg_1", "arg_2"])))
        assert _args_of(ev, "ad hominem") == ["arg_1"]
        assert _args_of(ev, _SOUTIENS) == ["arg_2"]
        assert _args_of(ev, _NON_EXAMINE) == ["arg_3", "arg_4", "arg_5", "arg_6"]

    def test_positive_control_full_sample_keeps_every_clean_unit_holding(self) -> None:
        """POSITIVE CONTROL (the issue's own): with the sample covering ALL six
        units, the five clean ones are holding — before AND after the fix.
        Without it, a 'fix' that stops calling anything holding passes."""
        ev = build_act2_evidence(
            _state(coverage=_coverage([f"arg_{i}" for i in range(1, 7)]))
        )
        assert _args_of(ev, _SOUTIENS) == [
            "arg_2",
            "arg_3",
            "arg_4",
            "arg_5",
            "arg_6",
        ]
        assert _NON_EXAMINE not in _themes(ev)
        assert ev.fallacy_sample_recorded is True
        assert ev.fallacy_sample_size == 6

    def test_unrecorded_sample_degrades_honestly(self) -> None:
        """Back-compat (Expected 4): a counts-only state — the shape written
        before #2966 — says the examined set was not recorded, and never
        'holding'. The degradation is loud, not silent."""
        ev = build_act2_evidence(_state())
        assert _themes(ev) == ["ad hominem", _SANS_ECHANTILLON]
        assert _args_of(ev, _SOUTIENS) == []
        assert ev.fallacy_sample_recorded is False
        assert all(a.fallacy_examined is None for a in ev.movements[-1].arguments)

    def test_recorded_but_empty_sample_is_not_the_same_as_unrecorded(self) -> None:
        """A coverage that recorded ZERO examined units is an information:
        every unit is 'never examined', which is not the same sentence as
        'the examined set was not recorded'."""
        ev = build_act2_evidence(_state(coverage=_coverage([])))
        assert _themes(ev) == ["ad hominem", _NON_EXAMINE]
        assert ev.fallacy_sample_recorded is True
        assert ev.fallacy_sample_size == 0
        assert all(a.fallacy_examined is False for a in ev.movements[-1].arguments)

    def test_examined_flag_reports_the_sample_and_a_fallacy_outranks_it(self) -> None:
        """``fallacy_examined`` reports membership of the RECORDED sample, and
        nothing else. A unit can sit outside that sample and still carry a
        located fallacy — another phase may have found it — so the flag stays
        ``False`` there while the MOVEMENT still follows the fallacy: a located
        device is its own proof that something read the unit, and it must not
        be demoted to 'never examined'."""
        ev = build_act2_evidence(_state(coverage=_coverage(["arg_2"])))
        by_id = {
            a.arg_id: a.fallacy_examined for m in ev.movements for a in m.arguments
        }
        assert by_id["arg_1"] is False  # outside the recorded sample…
        assert _args_of(ev, "ad hominem") == ["arg_1"]  # …yet attacked
        assert by_id["arg_2"] is True  # submitted, clean
        assert by_id["arg_3"] is False  # never submitted
        assert _args_of(ev, _NON_EXAMINE) == [
            "arg_3",
            "arg_4",
            "arg_5",
            "arg_6",
        ]


class TestQualityLineNamesItsScope:
    """Expected 3 — the quality line stops imputing a unit's absence to the run."""

    def _state_with_quality(self, scored: List[str], **fields: Any) -> SimpleNamespace:
        quality = {
            f"arg_{i}": {"overall": 7.0 + i, "scores": {"clarte": 7.0}} for i in (1, 2)
        }
        for k in scored:
            quality.setdefault(k, {"overall": 6.0, "scores": {"clarte": 6.0}})
        cov = _coverage(["arg_1", "arg_2"])
        cov["quality"] = {
            "k": len(scored),
            "N": 6,
            "bands_covered": 1,
            "bands_total": 3,
            "unit_ids": list(scored),
        }
        return _state(coverage=cov, argument_quality_scores=quality, **fields)

    def test_unit_outside_the_sample_is_named_as_such(self) -> None:
        prompt = build_act2_prompt(
            build_act2_evidence(self._state_with_quality(["arg_1", "arg_2"]))
        )
        assert "hors des 2 unités évaluées" in prompt

    def test_run_level_wording_is_reserved_for_an_empty_axis(self) -> None:
        """'indisponible sur ce run' must survive ONLY where the run really
        produced no usable score — that is the sentence's honest home."""
        prompt = build_act2_prompt(
            build_act2_evidence(
                _state(coverage=_coverage(["arg_1"]), argument_quality_scores={})
            )
        )
        assert "indisponible sur ce run" in prompt
        assert "hors des" not in prompt

    def test_in_sample_without_a_score_says_so(self) -> None:
        state = self._state_with_quality(["arg_1", "arg_2"])
        state.argument_quality_scores.pop("arg_2", None)
        prompt = build_act2_prompt(build_act2_evidence(state))
        assert "soumise à l'évaluation, aucun score rendu" in prompt

    def test_unrecorded_quality_sample_degrades_honestly(self) -> None:
        state = _state(
            argument_quality_scores={
                "arg_1": {"overall": 7.0, "scores": {"clarte": 7.0}}
            }
        )
        prompt = build_act2_prompt(build_act2_evidence(state))
        assert "l'ensemble des unités évaluées n'a pas été enregistré" in prompt


class TestPromptStatesTheCoverageFact:
    """Expected 2 — the third state is reported as a COVERAGE FACT."""

    def test_prompt_counts_the_units_nothing_was_asked_about(self) -> None:
        prompt = build_act2_prompt(
            build_act2_evidence(_state(coverage=_coverage(["arg_1", "arg_2"])))
        )
        assert "4 unités n'ont PAS été soumises à la détection de sophismes" in prompt
        assert "2 unités examinées" in prompt

    def test_unexamined_movement_is_never_presented_as_holding(self) -> None:
        prompt = build_act2_prompt(
            build_act2_evidence(_state(coverage=_coverage(["arg_1", "arg_2"])))
        )
        # the never-examined units are NOT in the soutiens block
        soutiens_start = prompt.index("MOUVEMENT « soutiens »")
        non_examine_start = prompt.index(f"MOUVEMENT « {_NON_EXAMINE} »")
        south = prompt[soutiens_start:non_examine_start]
        assert "arg_3" not in south
        assert "arg_4" not in south

    def test_prompt_says_why_no_unit_can_hold_on_an_unrecorded_run(self) -> None:
        prompt = build_act2_prompt(build_act2_evidence(_state()))
        assert "aucune unité ne peut être présentée comme tenant" in prompt
