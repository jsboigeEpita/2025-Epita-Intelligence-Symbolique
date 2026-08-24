"""#1874 (DoD): a non-vacuity control — the JVM boots with real Tweety classes.

``initialize_jvm`` returning True is NOT enough: with the #1874 Piège 2 preemption
bug the JVM "boots" while its classpath holds only a 0-class thin aggregator. This
test loads the PL parser, parses a formula and builds a belief set with a computed
size — if the classpath is empty or aggregator-only, the class load fails loudly
(NoClassDefFoundError) instead of a green-but-meaningless JVM boot.

Synthetic atoms only (a, b, c); the jpype/tweety markers mirror
test_native_sat_decides_1798 so the gate still runs this when jars are present.
"""

import jpype
import pytest

from argumentation_analysis.core.jvm_setup import initialize_jvm

pytestmark = [pytest.mark.jpype, pytest.mark.tweety]


@pytest.fixture(scope="module", autouse=True)
def _jvm():
    """Idempotent: the session conftest normally started it already."""
    initialize_jvm()


def test_pl_parser_parses_and_belief_set_has_size():
    PlBeliefSet = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet")
    PlParser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")
    parser = PlParser()
    kb = PlBeliefSet()
    kb.add(parser.parseFormula("a && (b || !c)"))
    kb.add(parser.parseFormula("a"))
    assert kb.size() == 2, (
        f"belief set must hold 2 formulas, got {kb.size()} — "
        "the classpath likely has no real Tweety classes (#1874)"
    )
