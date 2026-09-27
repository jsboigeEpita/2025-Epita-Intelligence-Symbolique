"""#2719 — a designation target taught to the LLM must be a name a live
casting produces.

The four live instruction constants taught a designation vocabulary
("ProjectManagerAgent", ...) inherited from the retired scripted PM stack.
Measured: no live path seats these agents next to a PM of that name — the
conversational chat names its PM "ProjectManager" (AGENT_CONFIG) and serves
its own instructions, while every path that serves these four constants
(conversation_orchestrator real agents, analysis_config pipeline, the
hierarchical adapters, the extract editor UI) runs the agent SOLO under its
own name, where no designation resolves at all.

The witness parses every designation target the constants teach (inline
``designate_next_agent(agent_name="...")`` calls and the "noms d'agents
valides" lists) and requires each to be a name some live casting can
produce: the AGENT_CONFIG roster — the only group chat whose selection
strategy reads designations — or the constructor default of one of the
carrier classes. No name list lives here; both sides are derived from code.
Reintroducing a dead name into any block reddens the matching case.
"""

import inspect
import re

import pytest

from argumentation_analysis.agents.concrete_agents.informal_fallacy_agent import (
    InformalFallacyAgent,
)
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.agents.core.extract.prompts import (
    EXTRACT_AGENT_INSTRUCTIONS,
)
from argumentation_analysis.agents.core.informal.informal_agent import (
    InformalAnalysisAgent,
)
from argumentation_analysis.agents.core.informal.informal_definitions import (
    INFORMAL_AGENT_INSTRUCTIONS,
)
from argumentation_analysis.agents.core.logic.propositional_logic_agent import (
    PropositionalLogicAgent,
    SYSTEM_PROMPT_PL,
)
from argumentation_analysis.agents.core.pl.pl_definitions import (
    PL_AGENT_INSTRUCTIONS,
)
from argumentation_analysis.orchestration.conversational_orchestrator import (
    AGENT_CONFIG,
)

TAUGHT_BLOCKS = {
    "extract/prompts.py:EXTRACT_AGENT_INSTRUCTIONS": EXTRACT_AGENT_INSTRUCTIONS,
    "informal_definitions.py:INFORMAL_AGENT_INSTRUCTIONS": INFORMAL_AGENT_INSTRUCTIONS,
    "propositional_logic_agent.py:SYSTEM_PROMPT_PL": SYSTEM_PROMPT_PL,
    "pl_definitions.py:PL_AGENT_INSTRUCTIONS": PL_AGENT_INSTRUCTIONS,
}

_CARRIER_CLASSES = (
    ExtractAgent,
    InformalAnalysisAgent,
    PropositionalLogicAgent,
    InformalFallacyAgent,
)

_DESIGNATION_CALL = re.compile(r'designate_next_agent\(\s*agent_name\s*=\s*"([^"]*)"')
_VALID_NAMES_LIST = re.compile(r"noms d.agents valides[^:\n]*:\s*([^\n]+)")


def _taught_targets(text: str) -> set:
    """Names a constant tells the LLM it may pass to designate_next_agent."""
    targets = set(_DESIGNATION_CALL.findall(text))
    for listed in _VALID_NAMES_LIST.findall(text):
        targets.update(re.findall(r'"([^"]+)"', listed))
    return targets


def _producible_names() -> set:
    """Names a live casting can actually seat, derived from code."""
    names = set(AGENT_CONFIG.keys())
    for cls in _CARRIER_CLASSES:
        default = inspect.signature(cls.__init__).parameters["agent_name"].default
        names.add(default)
    return names


@pytest.mark.parametrize("where", list(TAUGHT_BLOCKS))
def test_taught_designation_targets_resolve_in_a_live_casting(where: str) -> None:
    block = TAUGHT_BLOCKS[where]
    unresolvable = _taught_targets(block) - _producible_names()
    assert not unresolvable, (
        f"{where} teaches the LLM to designate {sorted(unresolvable)}, but no "
        "live casting produces that name (AGENT_CONFIG roster + carrier "
        "constructor defaults). The designation falls through to the "
        "selection fallback and leaves an unresolved-designation trace (#1751)."
    )
