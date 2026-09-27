"""#2699: the scripted ProjectManagerAgent stack stays retired.

``ProjectManagerAgent`` (``pm_agent.py``) was the scripted five-step PM of the
pre-Lego conversational stack: ``prompt_define_tasks_v15`` walked a fixed
"Séquence d'Analyse Idéale" and ``prompt_write_conclusion_v7`` wrote the
conclusion. Its only production consumer, the enhanced PM analysis runner, was
retired in #2638/#2704 — a repo-wide census then measured zero production
importers. The PM that holds the role today is the inline conversational PM
(``conversational_orchestrator.py``, RA-6 #1051: "Aucune sequence n'est
imposee"), and the factory's generic ``create_project_manager_agent()`` builds
a plain ``ChatCompletionAgent`` — neither imports this class.

Its conclusion prompt carried one live intent — refusing to conclude on an
incomplete state — which #1605's conclusion gate generalizes; that issue owns
the recycling, not this tombstone.

Removed with the class, same census: ``pm_definitions.py`` (plugin + setup,
read only by the class and the tests that left with it), ``prompts.py`` (read
only by the class), the participation-balancing simulation script and
``BalancedParticipationStrategy`` (the script was the strategy's only
constructor; the runner that "built then discarded" it is the one #2704
retired).

This tombstone reddens if a merge or conflict resolution brings any of the
four modules back: a deletion lost to a concurrent branch must surface as a
review decision, not slip in silently.
"""

import importlib.util

import pytest

RETIRED_MODULES = [
    "argumentation_analysis.agents.core.pm.pm_agent",
    "argumentation_analysis.agents.core.pm.pm_definitions",
    "argumentation_analysis.agents.core.pm.prompts",
    "argumentation_analysis.scripts.simulate_balanced_participation",
]


@pytest.mark.parametrize("module_name", RETIRED_MODULES)
def test_the_module_is_gone(module_name):
    spec = importlib.util.find_spec(module_name)
    assert spec is None, (
        f"{module_name.rsplit('.', 1)[-1]} est de retour : la pile PM scriptée "
        "a été retirée (#2699, zéro consommateur production mesuré après "
        "#2704) — une résurrection doit passer par une décision review, pas "
        "par une résolution de conflit silencieuse"
    )


def test_no_test_still_certifies_the_retired_class():
    """Les témoins de la classe retirée partent avec elle : aucun test ne
    revient la certifier."""
    from pathlib import Path

    repo = Path(__file__).resolve().parents[6]
    retired_witnesses = [
        repo / "tests" / "unit" / "argumentation_analysis" / "test_pm_agent.py",
        repo
        / "tests"
        / "unit"
        / "argumentation_analysis"
        / "agents"
        / "core"
        / "pm"
        / "test_pm_agent.py",
        repo
        / "tests"
        / "unit"
        / "argumentation_analysis"
        / "test_agent_interaction.py",
        repo
        / "tests"
        / "unit"
        / "argumentation_analysis"
        / "test_integration_balanced_strategy.py",
    ]
    for witness in retired_witnesses:
        message = (
            f"le témoin {witness.name} teste la pile PM scriptée retirée — "
            "il doit partir avec elle"
        )
        assert not witness.exists(), message
