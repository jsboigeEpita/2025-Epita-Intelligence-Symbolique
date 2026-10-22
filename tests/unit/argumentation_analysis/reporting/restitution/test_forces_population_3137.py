"""#3137 — a strength reaches the writer with its population, never as a
property of the discourse.

Measured on the paid pass R1105c (doc_A, Opus 5.5): ``argument_quality_scores``
covers 8 arguments of 91 units, and `_collect_quality_strengths` keeps a
virtue when ONE argument hits the top band, printing it as ``meilleur score
du discours : 1.0`` with no count. The writer then turns 3/8 into "le
discours est clair, bien structuré…" — the #1622 shape on the quality axis,
and the #1907 residue the threshold only half closed (it stops weak sets
being praised, not a single strong argument being generalised).

The fix: each strength carries `k` arguments at the top band, of `m`
evaluated (whose scores carry the virtue), of `N` units; the line says
"sur k des m arguments évalués", never "du discours"; and a writer rule —
proposed threshold 3/4 of the evaluated arguments, the line that admits
7/8 (refutation, R1105c) as discourse-level while excluding the 5/8, 3/8
and 3/8 the same render's Act II contradicts — tells the conductor when a
virtu may be generalised.

Fixtures are synthetic with opaque ids; the state shape mirrors the #1907
witnesses (``SimpleNamespace``, ``build_act3_evidence``/``build_act3_prompt``).
Born red on main: the population fields do not exist there and the line
reads ``meilleur score du discours``.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

# 8 evaluated arguments of a 15-unit discourse (the R1105c shape, shrunk):
# structure_logique reaches 1.0 on ONE argument, pertinence on 6 of 8.
_QUALITY_1_OF_8 = {
    f"arg_{i}": {
        "scores": {
            "structure_logique": 1.0 if i == 1 else 0.5,
            "pertinence": 1.0 if i <= 6 else 0.5,
        }
    }
    for i in range(1, 9)
}
_ARGS_15_UNITS = {
    f"arg_{i}": f"Une revendication synthetique numero {i}." for i in range(1, 16)
}
_QUALITY_8_OF_8 = {f"arg_{i}": {"scores": {"pertinence": 1.0}} for i in range(1, 9)}


def _state(quality: dict, args: dict) -> SimpleNamespace:
    return SimpleNamespace(
        identified_arguments=args,
        identified_fallacies={},
        argument_quality_scores=quality,
        counter_arguments=[],
    )


def _forces_slot(prompt: str) -> str:
    start = prompt.find("[CE QUI TIENT — forces (qualité)]")
    assert start != -1, "forces slot missing from the Act III prompt"
    end = prompt.find("[", start + 1)
    return prompt[start : end if end != -1 else len(prompt)]


class TestStrengthsCarryTheirPopulation:
    """Main prints ``meilleur score du discours : 1.0`` with no count — the
    writer cannot see that structure_logique holds on 1 argument of 8, of
    15 units; the fix carries k/m/N to the very line."""

    def test_the_collector_counts_k_of_m_of_n(self):
        ev = build_act3_evidence(_state(_QUALITY_1_OF_8, _ARGS_15_UNITS))
        by_virtue = {s.virtue: s for s in ev.quality_strengths}
        struct = by_virtue["structure_logique"]
        assert (struct.args_at_top, struct.args_evaluated, struct.units_total) == (
            1,
            8,
            15,
        ), (
            "a strength must carry its population: k arguments at the top "
            "band, of m evaluated, of N units (#3137)"
        )
        pert = by_virtue["pertinence"]
        assert (pert.args_at_top, pert.args_evaluated, pert.units_total) == (6, 8, 15)

    def test_the_line_names_the_population_never_the_discourse(self):
        prompt = build_act3_prompt(
            build_act3_evidence(_state(_QUALITY_1_OF_8, _ARGS_15_UNITS))
        )
        slot = _forces_slot(prompt)
        assert "meilleur score du discours" not in slot, (
            "the label reads as a score OF the discourse — one top-band "
            "argument of 8 became 'le discours est bien structuré' (#3137)"
        )
        assert "structure_logique (1.0 sur 1 des 8 arguments évalués" in slot
        assert "15 unités" in slot

    def test_positive_control_a_virtue_on_all_evaluated_still_stands(self):
        ev = build_act3_evidence(_state(_QUALITY_8_OF_8, _ARGS_15_UNITS))
        (strength,) = ev.quality_strengths
        assert strength.virtue == "pertinence"
        assert (strength.args_at_top, strength.args_evaluated) == (8, 8)
        prompt = build_act3_prompt(
            build_act3_evidence(_state(_QUALITY_8_OF_8, _ARGS_15_UNITS))
        )
        assert "pertinence (1.0 sur 8 des 8 arguments évalués" in _forces_slot(prompt)


class TestGeneralizationRule:
    """Whether a virtue may be said OF the discourse is the writer's rule,
    read from the counts — main gives the writer no counts and no rule."""

    def test_the_prompt_carries_the_three_quarter_rule_with_its_basis(self):
        prompt = build_act3_prompt(
            build_act3_evidence(_state(_QUALITY_1_OF_8, _ARGS_15_UNITS))
        )
        slot = _forces_slot(prompt)
        assert "3/4" in slot and "DU DISCOURS" in slot, (
            "the conductor must be told when a virtue may be generalised to "
            "the discourse — proposed threshold: 3/4 of the evaluated "
            "arguments (#3137)"
        )

    def test_no_rule_without_strengths(self):
        # Scope guard: the rule rides the forces slot; with no strength the
        # slot keeps the pre-existing honest-absence wording (#1907), unruled.
        weak = {
            "arg_1": {"scores": {"pertinence": 0.5}},
            "arg_2": {"scores": {"pertinence": 0.2}},
        }
        prompt = build_act3_prompt(
            build_act3_evidence(_state(weak, {"arg_1": "x", "arg_2": "y"}))
        )
        assert "non concluable" in _forces_slot(prompt)
        assert "3/4" not in _forces_slot(prompt)
