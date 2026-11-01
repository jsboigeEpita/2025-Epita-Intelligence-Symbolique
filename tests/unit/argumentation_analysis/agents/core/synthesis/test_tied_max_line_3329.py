"""#3329 — the max line SAYS the tie, and the reading rule says what a
superlative may do with it.

Paid pass R1130a (`doc_A`, main ``762d034c5``) called one counter-argument
« le contre-argument le mieux noté du lot affiché (0,565) » and anchored a
single id, while two counter-arguments held 0.565. #3155 had already printed
the true maximum with its holders — ``max score over all = 0.565 (ca_14,
ca_29)`` — so the briefing **did** name both. What it never said is that two
holders make a tie: a writer reading a parenthesised list can keep one id and
still be describing the line it read.

The repair sits upstream, where the writer reads (#3123: the licence records,
it never rewrites, and no retry loop was added):

- the line says ``tied:`` when at least two items hold the maximum, and names
  every holder (or how many more there are beyond the shown four);
- one READING RULE says a superlative may not single one out.

Deterministic — no JVM, no LLM, no network. Born red on ``198d7dd9a``.
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


def _briefing(state: SimpleNamespace) -> str:
    return DeepSynthesisAgent.build_artifact_briefing(state)


def _forty(tied: bool) -> list:
    """40 counter-arguments, so the POPULATIONS line is emitted (cap 15).

    ``ca_14`` holds the maximum; ``tied`` adds ``ca_29`` at the same score,
    which is the R1130a shape.
    """
    counters = [
        {
            "id": f"ca_{i}",
            "strategy": "direct_refutation",
            "score": 0.4,
            "counter_content": f"contre-argument {i}",
        }
        for i in range(1, 41)
    ]
    counters[13]["score"] = 0.59 if not tied else 0.565  # ca_14
    if tied:
        counters[28]["score"] = 0.565  # ca_29
    return counters


class TestTheLineSaysTheTie:
    """DoD box 1 — the line the writer reads distinguishes a shared maximum
    from a unique one."""

    def test_a_tied_maximum_is_named_as_a_tie(self):
        """Born red: on the pre-fix module the line is
        ``max score over all = 0.565 (ca_14, ca_29)`` — both ids, no tie."""
        line = DeepSynthesisAgent._max_over_population(
            [("ca_14", 0.565), ("ca_29", 0.565), ("ca_7", 0.4)], "score"
        )
        assert "tied: ca_14, ca_29" in line
        assert "à égalité" in line

    def test_a_unique_maximum_leaves_the_line_unchanged(self):
        """DoD control — one holder: the #3155 shape, byte for byte."""
        line = DeepSynthesisAgent._max_over_population(
            [("ca_1", 0.9), ("ca_2", 0.4)], "score"
        )
        assert line == "max score over all = 0.9 (ca_1)"

    def test_a_wide_tie_says_how_many_holders_are_not_shown(self):
        """The four-id cap stays, but it stops being silent: a tie of six
        ids shows four and counts the rest."""
        pairs = [(f"ca_{i}", 0.5) for i in range(1, 7)]
        line = DeepSynthesisAgent._max_over_population(pairs, "score")
        assert "tied: ca_1, ca_2, ca_3, ca_4, and 2 more" in line

    def test_the_briefing_carries_the_tie_for_a_tied_state(self):
        """End to end: the briefing of a state whose top is shared says so."""
        briefing = _briefing(_state(counter_arguments=_forty(tied=True)))
        assert "tied: ca_14, ca_29" in briefing

    def test_the_briefing_of_a_unique_maximum_keeps_the_old_shape(self):
        """Control: the same state with a unique top reads exactly as
        before, and no tie is claimed for it."""
        briefing = _briefing(_state(counter_arguments=_forty(tied=False)))
        assert "max score over all = 0.59 (ca_14)" in briefing
        assert "tied: ca_14" not in briefing


class TestTheReadingRuleIsStated:
    """DoD box 1, second half — the grounded prompt carries the matching
    reading rule, so the licence is not the only place that knows."""

    def test_the_rule_forbids_singling_out_one_holder(self):
        briefing = _briefing(_state(counter_arguments=_forty(tied=True)))
        assert "no superlative may single one out" in briefing

    def test_the_rule_is_present_on_a_unique_maximum_too(self):
        """Control: the rule is a property of reading the line, not of the
        state — it does not appear and vanish with the data."""
        briefing = _briefing(_state(counter_arguments=_forty(tied=False)))
        assert "no superlative may single one out" in briefing
