"""The agent and its adapter categorise a fallacy type the same way (#2345, item ``categorize_fallacies`` ×2).

``InformalAnalysisAgent.categorize_fallacies`` and the adapter's ``_categorize_fallacies``
each carried their own type → category mapping. The two had drifted: each sent the other's
four extra types to ``AUTRES``, so the adapter never filled ``AMBIGUITE``. Both sides must
now read one mapping, and one normalisation of the LLM's free-text ``fallacy_type``.
"""

import pytest
import semantic_kernel as sk
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)

from argumentation_analysis.agents.core.informal.informal_agent import (
    InformalAnalysisAgent,
)
from argumentation_analysis.agents.core.informal.informal_agent_adapter import (
    InformalAgent,
)

# The union of the two former mappings: no key mapped to two categories.
KNOWN_TYPES = {
    "ad_hominem": "RELEVANCE",
    "appel_autorite": "RELEVANCE",
    "argument_d_autorite": "RELEVANCE",
    "appel_emotion": "RELEVANCE",
    "appel_popularite": "INDUCTION",
    "generalisation_hative": "INDUCTION",
    "anecdote_personnelle": "INDUCTION",
    "pente_glissante": "CAUSALITE",
    "fausse_cause": "CAUSALITE",
    "equivoque": "AMBIGUITE",
    "amphibologie": "AMBIGUITE",
    "petitio_principii": "PRESUPPOSITION",
    "fausse_dichotomie": "PRESUPPOSITION",
    "faux_dilemme": "PRESUPPOSITION",
}
CATEGORIES = {
    "RELEVANCE",
    "INDUCTION",
    "CAUSALITE",
    "AMBIGUITE",
    "PRESUPPOSITION",
    "AUTRES",
}


class _NoCallChatCompletion(ChatCompletionClientBase):
    """A real SK service that fails if called: categorising never reaches the LLM."""

    async def _inner_get_chat_message_contents(self, chat_history, settings):
        raise AssertionError("categorisation must not call the LLM")


@pytest.fixture(scope="module")
def categorizers():
    kernel = sk.Kernel()
    kernel.add_service(
        _NoCallChatCompletion(ai_model_id="no-call-2345", service_id="default")
    )
    agent = InformalAnalysisAgent(kernel=kernel)
    adapter = InformalAgent()
    return {
        "agent": agent.categorize_fallacies,
        "adapter": adapter._categorize_fallacies,
    }


def _category_of(categorize, fallacy_type):
    result = categorize([{"fallacy_type": fallacy_type}])
    return [c for c, types in result.items() if types]


@pytest.mark.parametrize("side", ["agent", "adapter"])
@pytest.mark.parametrize("fallacy_type, expected", sorted(KNOWN_TYPES.items()))
def test_every_known_type_reaches_its_category(
    categorizers, side, fallacy_type, expected
):
    assert _category_of(categorizers[side], fallacy_type) == [expected]


@pytest.mark.parametrize("side", ["agent", "adapter"])
@pytest.mark.parametrize(
    "written, expected",
    [
        ("Généralisation hâtive", "INDUCTION"),
        ("Argument d'autorité", "RELEVANCE"),
        ("Faux dilemme", "PRESUPPOSITION"),
        ("Équivoque", "AMBIGUITE"),
        ("  Pente   glissante ", "CAUSALITE"),
    ],
)
def test_names_as_an_llm_writes_them_reach_their_category(
    categorizers, side, written, expected
):
    assert _category_of(categorizers[side], written) == [expected]


@pytest.mark.parametrize("side", ["agent", "adapter"])
def test_spellings_of_one_type_collapse_to_one_entry(categorizers, side):
    result = categorizers[side](
        [
            {"fallacy_type": "generalisation_hative"},
            {"fallacy_type": "Généralisation hâtive"},
        ]
    )
    assert result["INDUCTION"] == ["generalisation_hative"]
    assert not result["AUTRES"]


@pytest.mark.parametrize("side", ["agent", "adapter"])
def test_negative_control_unknown_type_goes_to_autres(categorizers, side):
    result = categorizers[side]([{"fallacy_type": "unknown_type"}])
    assert set(result) == CATEGORIES
    assert result["AUTRES"] == ["unknown_type"]
    assert all(not v for c, v in result.items() if c != "AUTRES")
