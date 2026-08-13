"""#1668 conclusion-side — `strategy` is free text, the conclusion stops categorising.

Coordinator decision (R800 dispatch): ``strategy`` is free text emitted by the
``collaborative_debate`` producer. 91 counter-arguments measured, 100% distinct
values, 0 from the closed vocabulary ``("UNDERCUT","REBUT","REBUTTAL")``. The
conclusion-side consumers must present the field honestly as an observed
rhetorical move, never as a closed category; an absence must render as an
absence, not as a named label.

Armed canaries (RED on main, GREEN after fix) + no-regression on the honest
counter-argument count. Anti-#1019: the writer always stores the key
(``shared_state.add_counter_argument`` l.760), so the canaries drive the
absent-key shape and the free-text-verbatim shape directly through the reader.
"""

from types import SimpleNamespace

import pytest

from argumentation_analysis.plugins.narrative_synthesis_plugin import build_narrative


# ---------------------------------------------------------------------------
# narrative_synthesis — the "general" default + the categorical set()/join()
# ---------------------------------------------------------------------------

_FREE_TEXT_STRATEGY = (
    "The speaker conflates correlation with causation to inflate the claim"
)


def _state_with_counters(counters):
    """Minimal state carrying a counter_arguments list (reader-level fixture)."""
    return SimpleNamespace(counter_arguments=counters)


class TestNarrativeStopsCategorisingStrategy:
    """Pass: narrative_synthesis must not enumerate free-text strategies as labels
    nor fabricate the ``"general"`` label for an absent key.

    Pre-fix l.93-101 collected ``ca.get("strategy", "general")`` into a ``set()``
    and joined them into ``"via {strat_text}"`` — presenting free-text moves as a
    list of named strategies, and fabricating ``"general"`` when the key was
    absent (#1019: an absence rendered as a named label).
    """

    def test_free_text_strategy_not_enumerated_verbatim_in_prose(self):
        """The rich free-text strategy must not surface verbatim in the narrative
        joined as a pseudo-label. Pre-fix: ``set()`` + ``join()`` rendered it."""
        state = _state_with_counters(
            [{"id": "ca_1", "counter_content": "a counter point", "strategy": _FREE_TEXT_STRATEGY}]
        )
        result = build_narrative(state)
        assert _FREE_TEXT_STRATEGY not in result, (
            "Free-text strategy rendered verbatim in the narrative — the set()/join() "
            "presented a rich rhetorical move as a named label (#1668)."
        )
        assert "via " not in result, (
            "The categorical 'via {labels}' enumeration survived — strategies are free "
            "text, not a closed vocabulary to enumerate."
        )

    def test_absent_strategy_key_not_fabricated_as_general(self):
        """A counter-argument with no ``strategy`` key must not surface as the
        fabricated label ``"general"``. #1019: absence rendered as a named label."""
        state = _state_with_counters(
            [{"id": "ca_1", "counter_content": "a counter point"}]  # no strategy key
        )
        result = build_narrative(state)
        assert "general" not in result.lower(), (
            "An absent strategy key was fabricated into the named label 'general' "
            "(#1019 — an absence must render as an absence)."
        )

    def test_empty_strategy_string_not_a_label(self):
        """A counter-argument whose ``strategy`` is the empty string must not
        surface as a fabricated label either."""
        state = _state_with_counters(
            [{"id": "ca_1", "counter_content": "a counter point", "strategy": ""}]
        )
        result = build_narrative(state)
        # No 'via ,' dangling enumeration, no fabricated label
        assert "via " not in result
        assert "general" not in result.lower()

    def test_counter_argument_count_still_reported(self):
        """No-regression: the honest count of contestation points survives the
        removal of the categorical enumeration."""
        state = _state_with_counters(
            [
                {"id": "ca_1", "counter_content": "point one", "strategy": _FREE_TEXT_STRATEGY},
                {"id": "ca_2", "counter_content": "point two", "strategy": "another move"},
            ]
        )
        result = build_narrative(state)
        assert "2" in result
        assert "contestat" in result.lower() or "contre-argument" in result.lower()


# ---------------------------------------------------------------------------
# act3 conclusion — empty strategy must not render as empty parens
# ---------------------------------------------------------------------------

class TestAct3EmptyStrategyNoEmptyParens:
    """Pass: when a CounterStrategy carries an empty ``strategy`` (absence), the
    conclusion line must not render dangling empty parentheses ``()`` — an
    absence renders as an absence, not as a labelled-but-empty slot.

    Drives the prompt renderer (``build_act3_prompt``) with a minimal
    ``Act3Evidence`` whose counter carries an empty strategy. The reader-level
    fixture is legitimate here: this is a presentation test, not a writer test.
    """

    def test_no_empty_parens_in_counter_line(self):
        """The rendered counter-argument line must not carry ``()`` for an empty
        strategy. Pre-fix: ``f'({cs.strategy})'`` rendered the empty string as
        dangling parentheses."""
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            Act3Evidence,
            CounterStrategy,
            build_act3_prompt,
        )

        evidence = Act3Evidence(
            counters_total=1,
            counter_strategies=[
                CounterStrategy(
                    strategy="",  # absent / empty — honest absence, not a category
                    target_arg_id="arg_1",
                    snippet="The data does not support the inference drawn",
                )
            ],
        )
        prompt = build_act3_prompt(evidence)
        assert "()" not in prompt, (
            "Empty strategy rendered as dangling empty parentheses '()' — an absent "
            "strategy must not produce an empty labelled slot (#1668 conclusion-side)."
        )

    def test_nonempty_strategy_kept_as_observed_move(self):
        """No-regression: a non-empty free-text strategy stays in the line (as an
        observed rhetorical move), only the empty-parens slot disappears."""
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            Act3Evidence,
            CounterStrategy,
            build_act3_prompt,
        )

        move = "The speaker conflates correlation with causation"
        evidence = Act3Evidence(
            counters_total=1,
            counter_strategies=[
                CounterStrategy(strategy=move, target_arg_id="arg_1", snippet="a counter")
            ],
        )
        prompt = build_act3_prompt(evidence)
        assert move in prompt  # the observed move is still surfaced, honestly
