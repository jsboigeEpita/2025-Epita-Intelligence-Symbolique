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
valides" lists). Per serving path (review 04:49Z): the only live chat that
reads designations is the AGENT_CONFIG chat, and it serves each entry's own
instructions — a constant served by it (its text embedded in an entry's
instructions) may teach targets from the roster plus the carrier classes'
constructor defaults. A constant NOT served by it runs solo on every
measured path, where no designation target resolves at all — its taught set
must be empty. No name list lives here; both sides are derived from code.
Reintroducing a designation teaching into any block reddens the matching
case.
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


def _served_by_the_designation_reader(block: str) -> bool:
    """Whether the conversational chat serves this very block.

    The only live chat that reads designations builds one
    ``ChatCompletionAgent`` per ``AGENT_CONFIG`` key and serves that entry's
    own instructions. A constant is served by it only if the entry's
    instructions embed the constant's text.
    """
    return any(
        block[:80] in (config.get("instructions") or "")
        for config in AGENT_CONFIG.values()
    )


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
    if _served_by_the_designation_reader(block):
        unresolvable = _taught_targets(block) - _producible_names()
    else:
        # Per serving path (review 04:49Z): every measured path that serves
        # these constants runs the agent SOLO — no other agent sits beside
        # the reader, so NO designation target can resolve. A name that
        # merely exists as some class's constructor default somewhere else
        # is not designatable from here.
        unresolvable = _taught_targets(block)
    assert not unresolvable, (
        f"{where} teaches the LLM to designate {sorted(unresolvable)}, but the "
        "paths serving this block run the agent solo — the only chat that "
        "reads designations (AGENT_CONFIG) serves its own instructions, so no "
        "taught target can resolve. A name that exists as a constructor "
        "default elsewhere is not designatable from here (review 04:49Z)."
    )
