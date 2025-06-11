from agent import DungAgent
from enhanced_agent import EnhancedDungAgent

# Cas problématique : self-attack
standard_agent = DungAgent()
enhanced_agent = EnhancedDungAgent()

print("--- Test avec un argument qui s'auto-attaque ---")

for agent in [standard_agent, enhanced_agent]:
    agent.add_argument("a")
    agent.add_argument("b")
    agent.add_attack("a", "a")  # Self-attack
    agent.add_attack("a", "b")

print("Agent Standard  (Grounded):", standard_agent.get_grounded_extension())
print("Agent Amélioré (Grounded):", enhanced_agent.get_grounded_extension())

