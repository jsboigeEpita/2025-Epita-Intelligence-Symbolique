"""#2637 — every query label the FOL agent emits is one its executor computes.

``FOLLogicAgent.generate_queries`` emitted ``universal_instances`` on "tous"
and ``existential_witnesses`` on "il existe". ``execute_query`` has no branch
for either, so each fell into the formula branch and reached the Tweety parser
as a formula. Measured on the unified pipeline's formal mode (real JVM): the
query came back ``Unknown``, with ``Predicate 'universal_instances' has not been
declared``.

The double exposes only methods of the real ``TweetyBridge`` / ``FOLHandler``,
and records every query that reaches the formula branch.
"""

from argumentation_analysis.agents.core.logic.belief_set import FirstOrderBeliefSet
from argumentation_analysis.agents.core.logic.fol_handler import FOLHandler
from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

_BELIEF_SET = FirstOrderBeliefSet(content="forall X: (P(X) => Q(X))\nP(a)")
# Every trigger generate_queries has ever reacted to, in one text.
_TEXT = (
    "Tous les hommes sont mortels, alors Socrate est mortel. "
    "Il existe un philosophe, donc quelqu'un pense. ∀ ∃ forall exists"
)


class _RecordingFolHandler:
    def __init__(self):
        self.parsed: list[str] = []

    def execute_fol_query(self, belief_set, query):
        self.parsed.append(query)
        return True, "entailed"


class _Bridge:
    def __init__(self):
        self.fol_handler = _RecordingFolHandler()

    def check_consistency(self, belief_set, logic_type):
        return True, "consistent"


def test_the_double_is_no_richer_than_the_real_bridge():
    assert {"check_consistency", "fol_handler"} <= set(dir(TweetyBridge))
    assert "execute_fol_query" in dir(FOLHandler)


async def test_no_emitted_label_reaches_the_formula_parser(mock_kernel_with_llm):
    bridge = _Bridge()
    agent = FOLLogicAgent(kernel=mock_kernel_with_llm, tweety_bridge=bridge)

    queries = await agent.generate_queries(_TEXT, _BELIEF_SET)
    assert "consistency_check" in queries
    for query in queries:
        await agent.execute_query(_BELIEF_SET, query)

    assert (
        bridge.fol_handler.parsed == []
    ), f"labels parsed as formulas: {bridge.fol_handler.parsed}"


async def test_a_formula_query_still_reaches_the_parser(mock_kernel_with_llm):
    # Control: the recorder sees the formula branch when it is taken.
    bridge = _Bridge()
    agent = FOLLogicAgent(kernel=mock_kernel_with_llm, tweety_bridge=bridge)

    verdict, _ = await agent.execute_query(_BELIEF_SET, "Q(a)")

    assert verdict is True
    assert bridge.fol_handler.parsed == ["Q(a)"]
