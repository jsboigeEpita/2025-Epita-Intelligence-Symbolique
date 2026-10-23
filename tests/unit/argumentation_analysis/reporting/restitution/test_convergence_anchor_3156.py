"""#3156 — the Act III convergence line carries its unit's anchor.

The R1107 render said « two other passages » combine low quality, a
counter-argument and an influence device, and described **arg_30**'s passage.
The two converging units were **arg_66** and **arg_79**; arg_30 is neither of
them and has no quality score at all. In the rebuilt prompt the convergence
lines carried **bare ids** — arg_66 and arg_79 appeared nowhere else with
text — so the writer bound them to the one nearby passage it could describe.

Same defect as #3151 on the Act III axis, and the same remedy as #2965: the
referent travels on the line that asks for it.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

_CONVERGENT = ("arg_66", "arg_79")
_DISTRACTOR = "arg_30"


def _state() -> SimpleNamespace:
    """Two convergent units, one distractor whose text is described elsewhere.

    arg_66 and arg_79 are weak (unpenalised quality fraction under the bar),
    each targeted by a fallacy and by a counter-argument; arg_1 spans the weak
    bar so the quality population is not uniformly weak (#1942); the counter
    sample shows the axis discriminates (#3145) because arg_1 is sampled and
    got no counter.

    The distractors carry a fallacy **justification** — the one kind of unit
    text the prompt prints — while the convergent units carry none. That is
    exactly the R1107 asymmetry: the writer could describe arg_30 and only
    name the other two.
    """
    return SimpleNamespace(
        identified_arguments={
            "arg_1": "hypothese de travail sereine",
            "arg_66": "passage faible sur la premiere question",
            "arg_79": "passage faible sur la seconde question",
            _DISTRACTOR: "passage sans note de qualite, sur un autre sujet",
        },
        identified_fallacies={
            "f66": {"target_argument_id": "arg_66", "type": "ad_hominem"},
            "f79": {"target_argument_id": "arg_79", "type": "ad_verecundiam"},
            "f30": {
                "target_argument_id": _DISTRACTOR,
                "type": "faux_dilemme",
                "justification": "la justification visible du seul passage decrit",
            },
        },
        argument_quality_scores={
            "arg_66": {"scores": {"clarte": 0.3, "coherence": 0.3}, "overall": 0.6},
            "arg_79": {"scores": {"clarte": 0.2, "coherence": 0.4}, "overall": 0.6},
            "arg_1": {"scores": {"clarte": 0.9, "coherence": 0.9}, "overall": 1.8},
        },
        counter_arguments=[
            {"target_arg_id": "arg_66", "counter_content": "c1"},
            {"target_arg_id": "arg_79", "counter_content": "c2"},
        ],
        analysis_coverage={
            "counter": {
                "k": 3,
                "N": 3,
                "bands_covered": 3,
                "bands_total": 3,
                "unit_ids": ["arg_1", "arg_66", "arg_79"],
            }
        },
        jtms_beliefs={},
        dung_frameworks={},
        workflow_results={},
    )


def _convergence_lines(prompt: str) -> list:
    return [
        line
        for line in prompt.splitlines()
        if line.strip().startswith("- [convergence]")
    ]


class TestTheConvergenceLineCarriesItsAnchor:
    def test_both_convergent_units_carry_their_excerpt(self):
        prompt = build_act3_prompt(build_act3_evidence(_state()))
        lines = _convergence_lines(prompt)
        assert lines, "the two convergent units must produce convergence lines"
        joined = "\n".join(lines)
        for unit_id in _CONVERGENT:
            assert f"{unit_id} — «" in joined, joined
        assert "passage faible sur la premiere question" in joined
        assert "passage faible sur la seconde question" in joined

    def test_the_line_does_not_lend_them_the_distractor(self):
        prompt = build_act3_prompt(build_act3_evidence(_state()))
        joined = "\n".join(_convergence_lines(prompt))
        assert _DISTRACTOR not in joined, (
            "arg_30 is neither convergent unit; naming it on their line is the "
            "R1107 miss-binding"
        )

    def test_a_unit_already_excerpted_says_so(self):
        evidence = build_act3_evidence(_state())
        prompt = build_act3_prompt(evidence)
        listed = {unit_id for unit_id, _ in evidence.claim_excerpts}
        assert listed & set(
            _CONVERGENT
        ), "the convergent units are cited, so the claims list should hold them"
        joined = "\n".join(_convergence_lines(prompt))
        assert "déjà listé parmi les revendications" in joined, joined


class TestTheEvidenceCarriesTheAnchors:
    def test_anchor_excerpts_hold_the_cited_units_only(self):
        evidence = build_act3_evidence(_state())
        assert set(_CONVERGENT) <= set(evidence.anchor_excerpts)
        assert _DISTRACTOR not in evidence.anchor_excerpts

    def test_the_mutation_target_is_the_map_itself(self):
        """Dropping the map is what turns the first witness red — the prompt
        then falls back to the bare ids it printed on R1107."""
        evidence = build_act3_evidence(_state())
        evidence.anchor_excerpts = {}
        joined = "\n".join(_convergence_lines(build_act3_prompt(evidence)))
        for unit_id in _CONVERGENT:
            assert f"{unit_id} — «" not in joined
