import pytest
from agent import DungAgent
from enhanced_agent import EnhancedDungAgent


def test_self_attacking_argument(initialize_jvm):
    """
    Teste le comportement des agents face à un argument qui s'auto-attaque.
    Ce test est encapsulé dans une fonction pour s'assurer que la JVM est
    initialisée par la fixture `initialize_jvm` avant l'instanciation des agents.
    """
    # Cas problématique : self-attack
    standard_agent = DungAgent()
    enhanced_agent = EnhancedDungAgent()

    print("--- Test avec un argument qui s'auto-attaque ---")

    for agent in [standard_agent, enhanced_agent]:
        agent.add_argument("a")
        agent.add_argument("b")
        agent.add_attack("a", "a")  # Self-attack
        agent.add_attack("a", "b")

    grounded_standard = standard_agent.get_grounded_extension()
    grounded_enhanced = enhanced_agent.get_grounded_extension()

    print("Agent Standard  (Grounded):", grounded_standard)
    print("Agent Amélioré (Grounded):", grounded_enhanced)

    # On pourrait ajouter des assertions ici pour en faire un vrai test
    assert "b" in grounded_standard
    assert "a" not in grounded_standard
    assert "b" in grounded_enhanced
    assert "a" not in grounded_enhanced

    print("Agent Standard  (Grounded):", standard_agent.get_grounded_extension())
    print("Agent Amélioré (Grounded):", enhanced_agent.get_grounded_extension())
