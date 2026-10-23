# -*- coding: utf-8 -*-
"""#3164 — four per-unit rows are not one four-method coincidence.

Deep synthesis said the most exposed nodes are those where *fallacy, counter-
argument, quality score and retraction coincide*, citing four rows. No unit
carried all four: two rows were retracted with no quality score, the other two
were scored but not retracted. The writer took the **union** of four per-unit
sets and wrote it as an **intersection** on each of the four nodes — every
citation pointed at a row that refutes the sentence it supports.

The rows themselves were right, so the fix is not to merge them (anti-pendulum:
the per-unit evidence stays per-unit). The briefing gains a deterministic
census of the combinations actually observed, and says when the union is
carried by no unit; the reading rules forbid the generalisation.

* witness — two disjoint 3-method sets: the block says no unit carries the
  union, and names the two combinations.
* control — one row carrying the union: no such warning.
* mutation — dropping the census makes the witness red.

Synthetic ids and method labels only (privacy HARD).
"""

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.agents.core.synthesis.deep_synthesis_models import (
    ConvergentVerdict,
    DeepSynthesisReport,
)

_A = ("sophisme", "contre-argument", "JTMS retracte")
_B = ("sophisme", "qualite faible", "contre-argument")


def _report(*method_sets):
    return DeepSynthesisReport(
        convergent_verdicts=[
            ConvergentVerdict(
                arg_id=f"arg_{i}", score=0.9, methods=list(methods), statement=""
            )
            for i, methods in enumerate(method_sets, start=1)
        ]
    )


def _briefing(report):
    return DeepSynthesisAgent.build_artifact_briefing(state=object(), report=report)


class TestTheUnionIsNotTheIntersection:
    def test_no_unit_carries_the_union_and_the_block_says_so(self):
        """Born red on main: the briefing handed the rows and nothing else, so
        the four-method sentence was writable with no signal against it."""
        text = _briefing(_report(_A, _A, _B, _B))
        assert "NO unit carries the 4 methods cited above" in text
        assert "UNION as an INTERSECTION" in text

    def test_the_block_names_the_combinations_that_occur(self):
        """The census is what lets the writer say something true instead of
        the false coincidence — without it the warning alone is unactionable."""
        text = _briefing(_report(_A, _A, _B, _B))
        # methods are sorted inside a combination, so the census is stable
        # across runs whatever order the signals were computed in
        assert "{JTMS retracte, contre-argument, sophisme} x 2" in text
        assert "{contre-argument, qualite faible, sophisme} x 2" in text

    def test_one_unit_actually_carrying_the_union_earns_no_warning(self):
        """Control — when a cited unit really carries the four methods, the
        sentence is licensed and nothing is said against it. Two rows, so the
        census runs: the carrier must silence the warning, not the row count."""
        text = _briefing(
            _report(
                ("sophisme", "contre-argument", "JTMS retracte", "qualite faible"),
                ("sophisme",),
            )
        )
        assert "NO unit carries" not in text

    def test_a_single_row_gets_no_census(self):
        """Control — one row cannot be generalised over: no block at all."""
        text = _briefing(_report(_A))
        assert "CONVERGENCE READING" not in text

    def test_the_reading_rule_forbids_the_generalisation(self):
        """The rule the census supports — it must be in the briefing the
        writer receives, not only in this test."""
        text = _briefing(_report(_A, _B))
        assert "convergent_verdicts rows are PER UNIT" in text
