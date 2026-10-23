"""#3155 — a capped artifact field states its population, and its maximum is the field's.

The R1107 render (doc_B, Sonnet, main ``044af5147``, run ``0b1a82fc``) said « the
highest-scoring counter-argument, at 0.565 ». The state holds 40 counter-arguments:
the maximum is **0.59**, held by ``ca_22`` and ``ca_38``, and six items tie at
0.565. The briefing passed ``counter_arguments[:15]`` with no denominator, so the
writer's "highest" was the maximum of a **prefix**.

The repair is the denominator plus the field's true rank, not a prompt rule: one
``POPULATIONS`` line per TRUNCATED field, with the maximum over the whole
population and the ids that hold it where the field carries a rankable quantity.
A field whose population fits the cap says nothing (the DoD's control: a state
with 10 counter-arguments leaves the briefing unchanged).

``identified_arguments`` and ``identified_fallacies`` already state theirs through
``analysis_coverage`` (``synthesis_args`` / ``synthesis_fallacies``) — the census
in the PR body names every capped site and its status.

Deterministic — no JVM, no LLM, no network.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)


def _state(**fields) -> SimpleNamespace:
    base = dict(
        identified_arguments={},
        identified_fallacies={},
        counter_arguments=[],
        argument_quality_scores={},
        propositional_analysis_results=[],
        fol_analysis_results=[],
        modal_analysis_results=[],
        dung_frameworks={},
        jtms_retraction_chain=[],
        belief_revision_results=[],
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _briefing(state, report=None) -> str:
    return DeepSynthesisAgent.build_artifact_briefing(state, report)


#: The R1107 shape: ca_1..ca_15 stop at 0.565, the true maximum (0.59) sits at
#: ca_22 and ca_38 — beyond the cap.
def _forty_counters() -> list:
    counters = [
        {
            "id": f"ca_{i}",
            "strategy": "direct_refutation",
            "score": 0.4,
            "counter_content": f"contre-argument {i}",
        }
        for i in range(1, 41)
    ]
    for i in range(6):  # six items tie at 0.565 inside the prefix
        counters[i]["score"] = 0.565
    counters[21]["score"] = 0.59  # ca_22
    counters[37]["score"] = 0.59  # ca_38
    return counters


# ============================================================================
# The measured defect
# ============================================================================


class TestTheCappedFieldStatesItsPopulation:
    def test_the_true_maximum_and_the_denominator_are_stated(self):
        briefing = _briefing(_state(counter_arguments=_forty_counters()))

        assert "POPULATIONS" in briefing
        assert "counter_arguments: 15 of 40 shown" in briefing
        assert "max score over all = 0.59 (ca_22, ca_38)" in briefing

    def test_the_cap_still_applies(self):
        """The repair is the denominator, not showing everything."""
        briefing = _briefing(_state(counter_arguments=_forty_counters()))

        assert "[artifact:counter_arguments.ca_22]" not in briefing
        assert "[artifact:counter_arguments.ca_1]" in briefing

    def test_a_population_within_the_cap_is_unchanged(self):
        """Control (DoD): 10 counter-arguments — nothing to declare."""
        counters = _forty_counters()[:10]
        briefing = _briefing(_state(counter_arguments=counters))

        assert "POPULATIONS" not in briefing
        assert "counter_arguments:" not in briefing
        assert "[artifact:counter_arguments.ca_10]" in briefing

    def test_a_field_exactly_at_the_cap_is_silent(self):
        """Boundary: 15 of 15 shown hides nothing — no line."""
        briefing = _briefing(_state(counter_arguments=_forty_counters()[:15]))

        assert "POPULATIONS" not in briefing

    def test_the_quality_top_is_over_the_population(self):
        """#3159's sibling: a ranking of a capped field ranks the field."""
        quality = {f"arg_{i}": {"overall": 3.0} for i in range(40)}
        quality["arg_39"] = {"overall": 5.0}  # beyond the cap
        briefing = _briefing(_state(argument_quality_scores=quality))

        assert "argument_quality_scores: 15 of 40 shown" in briefing
        assert "max overall over all = 5.0 (arg_39)" in briefing

    def test_every_other_capped_field_states_its_population(self):
        entries = [{"whatever": i} for i in range(16)]
        briefing = _briefing(
            _state(
                propositional_analysis_results=list(entries),
                fol_analysis_results=list(entries),
                modal_analysis_results=list(entries),
                jtms_retraction_chain=list(entries),
                belief_revision_results=list(entries),
                dung_frameworks={
                    f"dung_{i}": {"arguments": ["a"], "attacks": []} for i in range(16)
                },
            )
        )

        for field in (
            "propositional_analysis_results",
            "fol_analysis_results",
            "modal_analysis_results",
            "jtms_retraction_chain",
            "belief_revision_results",
            "dung_frameworks",
        ):
            assert f"- {field}: 15 of 16 shown" in briefing, field

    def test_convergent_verdicts_state_their_population(self):
        verdicts = [
            SimpleNamespace(arg_id=f"arg_{i}", score=1.0 + i / 100, methods=["a", "b"])
            for i in range(20)
        ]
        report = SimpleNamespace(convergent_verdicts=verdicts)
        briefing = _briefing(_state(), report=report)

        assert "convergent_verdicts: 15 of 20 shown" in briefing
        assert "max score over all = 1.19 (arg_19)" in briefing

    def test_no_capped_field_means_no_block(self):
        """Control: nothing truncated → the block never appears."""
        briefing = _briefing(_state())

        assert "POPULATIONS" not in briefing
        assert "shown (cap" not in briefing
