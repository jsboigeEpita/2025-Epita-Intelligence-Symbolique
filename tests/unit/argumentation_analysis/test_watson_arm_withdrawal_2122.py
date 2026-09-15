"""Born-red guard for the watson_jtms dead-arm withdrawal (#2122, decision A4).

The dead arm (measured 2026-09-15, issuecomment-5681982173): the
communication hub + the watson shim + the whole ``watson_jtms/`` package —
0 production importer, transitively closed. **Excluded because they are
alive**: ``sherlock_jtms_agent.py`` (factory:472 + sherlock_watson scripts)
and ``jtms_agent_base.py`` (imported by sherlock).
"""

import importlib.util

WITHDRAWN_MODULES = [
    "argumentation_analysis.agents.jtms_communication_hub",
    "argumentation_analysis.agents.watson_jtms_agent",
    "argumentation_analysis.agents.watson_jtms",
    "argumentation_analysis.agents.watson_jtms.agent",
    "argumentation_analysis.agents.watson_jtms.consistency",
    "argumentation_analysis.agents.watson_jtms.critique",
    "argumentation_analysis.agents.watson_jtms.models",
    "argumentation_analysis.agents.watson_jtms.synthesis",
    "argumentation_analysis.agents.watson_jtms.utils",
    "argumentation_analysis.agents.watson_jtms.validation",
]

EXCLUDED_ALIVE_MODULES = [
    "argumentation_analysis.agents.sherlock_jtms_agent",
    "argumentation_analysis.agents.jtms_agent_base",
]


def _spec_or_none(name):
    # find_spec raises ModuleNotFoundError for a submodule whose parent
    # package is gone — that state IS "gone".
    try:
        return importlib.util.find_spec(name)
    except ModuleNotFoundError:
        return None


def test_dead_arm_modules_are_gone():
    gone = [name for name in WITHDRAWN_MODULES if _spec_or_none(name) is not None]
    assert gone == [], f"modules of the withdrawn watson arm still resolvable: {gone}"


def test_excluded_survivors_are_alive():
    """The withdrawal must not take the alive sherlock arm with it."""
    alive = [
        name
        for name in EXCLUDED_ALIVE_MODULES
        if importlib.util.find_spec(name) is None
    ]
    assert alive == [], f"excluded-but-alive modules missing: {alive}"
