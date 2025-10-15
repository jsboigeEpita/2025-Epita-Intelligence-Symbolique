import pytest
from abs_arg_dung.agent import DungAgent
from abs_arg_dung.enhanced_agent import EnhancedDungAgent


def test_self_attacking_argument():
    """
    Teste le comportement des agents avec un argument qui s'auto-attaque.
    """
    standard_agent = DungAgent()
    enhanced_agent = EnhancedDungAgent()

    for agent in [standard_agent, enhanced_agent]:
        agent.add_argument("a")
        agent.add_argument("b")
        agent.add_attack("a", "a")  # Self-attack
        agent.add_attack("a", "b")

    assert standard_agent.get_grounded_extension() == []
    assert enhanced_agent.get_grounded_extension() == []
