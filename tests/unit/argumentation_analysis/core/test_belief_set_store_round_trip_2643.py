"""#2643 — a stored belief set rebuilds, whichever writer stored it.

Writers and readers of ``state.belief_sets`` did not share one vocabulary:
the state wrappers stored ``"FOL"``, which ``BeliefSet.from_dict`` did not
know; they refused ``"modal"`` outright; and no store kept a propositional
belief set's ``propositions``, without which the propositional agent generates
no query. The web service's store had the same gap.
"""

import re

import pytest

from argumentation_analysis.agents.core.logic.belief_set import (
    BeliefSet,
    FirstOrderBeliefSet,
    ModalBeliefSet,
    PropositionalBeliefSet,
)
from argumentation_analysis.core.logic_types import LOGIC_TYPE_ALIASES
from argumentation_analysis.core.phase_scoped_state import FormalPhaseState
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.evaluation.sanitize_state import sanitize_state
from argumentation_analysis.evaluation.state_export_scrub import (
    _scrub_state_for_export,
)
from argumentation_analysis.services.web_api.models.request_models import (
    LogicBeliefSetRequest,
)
from argumentation_analysis.services.web_api.services import logic_service as ls

CLASS_OF = {
    "propositional": PropositionalBeliefSet,
    "first_order": FirstOrderBeliefSet,
    "modal": ModalBeliefSet,
}
WRAPPERS = [StateManagerPlugin, FormalPhaseState]
ATOMS = ["pluie", "mouille"]


def _stored(state, bs_id):
    assert bs_id in state.belief_sets, f"not stored, the writer returned {bs_id!r}"
    return state.belief_sets[bs_id]


@pytest.mark.parametrize("wrapper", WRAPPERS, ids=lambda w: w.__name__)
@pytest.mark.parametrize("spelling", sorted(LOGIC_TYPE_ALIASES))
def test_every_spelling_a_wrapper_accepts_rebuilds(wrapper, spelling):
    state = RhetoricalAnalysisState("t")

    bs_id = wrapper(state).add_belief_set(spelling, "a")

    rebuilt = BeliefSet.from_dict(_stored(state, bs_id))
    assert isinstance(rebuilt, CLASS_OF[LOGIC_TYPE_ALIASES[spelling]])
    assert rebuilt.content == "a"


# The pipeline's state writers call the state itself, with their own spelling.
@pytest.mark.parametrize("spelling", ["fol", "propositional", "FOL", "Propositional"])
def test_the_state_writers_spellings_rebuild(spelling):
    state = RhetoricalAnalysisState("t")

    bs_id = state.add_belief_set(spelling, "a")

    assert BeliefSet.from_dict(_stored(state, bs_id)) is not None


@pytest.mark.parametrize("wrapper", WRAPPERS, ids=lambda w: w.__name__)
def test_an_unknown_type_is_refused_not_stored(wrapper):
    state = RhetoricalAnalysisState("t")

    result = wrapper(state).add_belief_set("tarot", "a")

    assert result.startswith("FUNC_ERROR")
    assert state.belief_sets == {}


@pytest.mark.parametrize(
    "write",
    [
        lambda st: st.add_belief_set("propositional", "a", propositions=ATOMS),
        lambda st: StateManagerPlugin(st).add_belief_set(
            "propositional", "a", propositions=ATOMS
        ),
        lambda st: FormalPhaseState(st).add_belief_set("pl", "a", propositions=ATOMS),
    ],
    ids=["state", "StateManagerPlugin", "FormalPhaseState"],
)
def test_propositions_survive_the_state_store(write):
    state = RhetoricalAnalysisState("t")

    rebuilt = BeliefSet.from_dict(_stored(state, write(state)))

    assert rebuilt.propositions == ATOMS


def test_a_store_without_propositions_does_not_invent_the_key():
    state = RhetoricalAnalysisState("t")

    bs_id = state.add_belief_set("fol", "a")

    assert "propositions" not in state.belief_sets[bs_id]


class _PLAgent:
    def setup_agent_components(self, llm_service_id):
        pass

    async def text_to_belief_set(self, text, context=None):
        return PropositionalBeliefSet("pluie => mouille", propositions=ATOMS), "ok"


async def test_propositions_survive_the_web_service_store(monkeypatch):
    monkeypatch.setattr(
        ls.LogicAgentFactory, "create_agent", lambda logic_type, kernel: _PLAgent()
    )
    service = ls.LogicService(llm_service=None)

    response = await service.text_to_belief_set(
        LogicBeliefSetRequest(text="Il pleut.", logic_type="propositional")
    )

    stored = service.belief_sets[response.belief_set.id]
    rebuilt = service._create_belief_set_from_data(stored)
    assert rebuilt.propositions == ATOMS


def _exported_state():
    # Built by hand, so that the scrub is measured apart from the store.
    return {
        "belief_sets": {
            "propositional_bs_1": {
                "logic_type": "Propositional",
                "content": "a",
                "propositions": list(ATOMS),
            }
        }
    }


# Each scrubber runs keyless here: sanitize_state with a test salt, the export
# scrub with an instance vocabulary that matches nothing. Propositions must be
# opacified by the field policy, not by the corpus vocabulary.
@pytest.mark.parametrize(
    "scrub",
    [
        sanitize_state,
        lambda s: _scrub_state_for_export(s, instance_re=re.compile("(?!)")),
    ],
    ids=["sanitize_state", "_scrub_state_for_export"],
)
def test_the_export_scrubs_opacify_propositions(scrub, monkeypatch):
    monkeypatch.setenv("OPAQUE_ID_SALT", "test-salt-2643")
    exported = scrub(_exported_state())

    (entry,) = exported["belief_sets"].values()
    assert len(entry["propositions"]) == len(ATOMS)
    assert not set(entry["propositions"]) & set(ATOMS)


class _TranslatingAgent:
    """The collaborators ``_handle_translation_task`` reads on ``self``."""

    name = "agent_2643"

    def __init__(self, belief_set):
        import logging

        self.logger = logging.getLogger("test_2643")
        self._belief_set = belief_set

    def _extract_source_text(self, task_description, state):
        return "Il pleut, donc la route est mouillée."

    async def text_to_belief_set(self, text, context=None):
        return self._belief_set, "ok"


async def _translate(belief_set, state):
    from argumentation_analysis.agents.core.abc.agent_bases import BaseLogicAgent

    return await BaseLogicAgent._handle_translation_task(
        _TranslatingAgent(belief_set), "t1", "Traduire", {}, StateManagerPlugin(state)
    )


async def test_the_translation_task_stores_the_propositions():
    state = RhetoricalAnalysisState("t")

    result = await _translate(PropositionalBeliefSet("a", propositions=ATOMS), state)

    assert result["status"] == "success", result
    rebuilt = BeliefSet.from_dict(state.belief_sets[result["belief_set_id"]])
    assert rebuilt.propositions == ATOMS


async def test_the_translation_task_stores_a_modal_belief_set():
    state = RhetoricalAnalysisState("t")

    result = await _translate(ModalBeliefSet("type(p)\n\np"), state)

    assert result["status"] == "success", result
    rebuilt = BeliefSet.from_dict(state.belief_sets[result["belief_set_id"]])
    assert isinstance(rebuilt, ModalBeliefSet)


class _UnknownBeliefSet(BeliefSet):
    @property
    def logic_type(self):
        return "tarot"


async def test_a_refused_store_is_not_reported_as_an_id():
    state = RhetoricalAnalysisState("t")

    result = await _translate(_UnknownBeliefSet("a"), state)

    assert result["status"] == "error"
    assert "belief_set_id" not in result
    assert state.belief_sets == {}
