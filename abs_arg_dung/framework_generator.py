import random
from agent import DungAgent


class FrameworkGenerator:
    @staticmethod
    def generate_random_framework(
        num_args: int, attack_probability: float = 0.3, seed: int = None
    ) -> DungAgent:
        """Génère un framework d'argumentation aléatoire"""
        if seed:
            random.seed(seed)

        agent = DungAgent()

        # Ajouter les arguments
        for i in range(num_args):
            agent.add_argument(f"arg_{i}")

        # Ajouter des attaques aléatoires
        args = list(agent._arguments.keys())
        for source in args:
            for target in args:
                if random.random() < attack_probability:
                    agent.add_attack(source, target)

        return agent

    @staticmethod
    def generate_classic_examples() -> dict:
        """Génère des exemples classiques d'argumentation"""
        examples = {}

        # Triangle
        triangle = DungAgent()
        for arg in ["a", "b", "c"]:
            triangle.add_argument(arg)
        triangle.add_attack("a", "b")
        triangle.add_attack("b", "c")
        triangle.add_attack("c", "a")
        examples["triangle"] = triangle

        # Self-defending argument
        self_def = DungAgent()
        for arg in ["a", "b"]:
            self_def.add_argument(arg)
        self_def.add_attack("a", "b")
        self_def.add_attack("b", "a")
        examples["self_defending"] = self_def

        # Nixon Diamond
        nixon = DungAgent()
        for arg in ["quaker", "republican", "pacifist", "hawk"]:
            nixon.add_argument(arg)
        nixon.add_attack("quaker", "republican")
        nixon.add_attack("republican", "pacifist")
        nixon.add_attack("quaker", "pacifist")
        nixon.add_attack("republican", "hawk")
        examples["nixon_diamond"] = nixon

        return examples


# Test du générateur
if __name__ == "__main__":
    # Framework aléatoire
    random_agent = FrameworkGenerator.generate_random_framework(5, 0.4, seed=42)
    print("Framework aléatoire généré:")
    random_agent.analyze_framework_properties()
    random_agent.analyze_semantics_relationships()

    # Exemples classiques
    examples = FrameworkGenerator.generate_classic_examples()
    for name, agent in examples.items():
        print(f"\n=== {name.upper()} ===")
        agent.analyze_semantics_relationships()
