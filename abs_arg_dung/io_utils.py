import json
from agent import DungAgent


class FrameworkIO:
    @staticmethod
    def export_to_json(agent: DungAgent, filename: str):
        """Exporte un framework vers un fichier JSON"""
        nodes = [str(arg.getName()) for arg in agent.af.getNodes()]
        edges = [
            (str(a.getAttacker().getName()), str(a.getAttacked().getName()))
            for a in agent.af.getAttacks()
        ]

        data = {
            "arguments": nodes,
            "attacks": edges,
            "metadata": {
                "num_arguments": len(nodes),
                "num_attacks": len(edges),
                "creation_time": None,  # Peut être ajouté plus tard
            },
        }

        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

        print(f"Framework exporté vers {filename}")

    @staticmethod
    def import_from_json(filename: str) -> DungAgent:
        """Importe un framework depuis un fichier JSON"""
        with open(filename, "r") as f:
            data = json.load(f)

        agent = DungAgent()

        # Ajouter les arguments
        for arg in data["arguments"]:
            agent.add_argument(arg)

        # Ajouter les attaques
        for source, target in data["attacks"]:
            agent.add_attack(source, target)

        print(f"Framework importé depuis {filename}")
        return agent

    @staticmethod
    def export_to_tgf(agent: DungAgent, filename: str):
        """Exporte vers le format TGF (Trivial Graph Format)"""
        with open(filename, "w") as f:
            # Nodes
            for i, arg in enumerate(agent._arguments.keys()):
                f.write(f"{i+1} {str(arg)}\n")

            f.write("#\n")  # Separator

            # Edges
            arg_to_id = {
                str(arg): i + 1 for i, arg in enumerate(agent._arguments.keys())
            }
            for attack in agent.af.getAttacks():
                source_id = arg_to_id[str(attack.getAttacker().getName())]
                target_id = arg_to_id[str(attack.getAttacked().getName())]
                f.write(f"{source_id} {target_id}\n")

        print(f"Framework exporté vers {filename} (format TGF)")

    @staticmethod
    def export_to_dot(agent: DungAgent, filename: str):
        """Exporte vers le format DOT (GraphViz)"""
        with open(filename, "w") as f:
            f.write("digraph argumentation {\n")
            f.write("  rankdir=LR;\n")
            f.write("  node [shape=circle];\n")

            # Nodes
            for arg in agent._arguments.keys():
                f.write(f'  "{str(arg)}";\n')

            # Edges
            for attack in agent.af.getAttacks():
                source = str(attack.getAttacker().getName())
                target = str(attack.getAttacked().getName())
                f.write(f'  "{source}" -> "{target}";\n')

            f.write("}\n")

        print(f"Framework exporté vers {filename} (format DOT)")

    @staticmethod
    def export_analysis_report(agent: DungAgent, filename: str):
        """Exporte un rapport d'analyse complet"""
        # Calculer toutes les informations
        properties = agent.get_framework_properties()
        semantics = agent.get_semantics_relationships()
        all_status = agent.get_all_arguments_status()

        report = {
            "framework_properties": properties,
            "semantics_analysis": semantics,
            "arguments_status": all_status,
            "summary": {
                "total_arguments": properties["num_arguments"],
                "total_attacks": properties["num_attacks"],
                "has_cycles": properties["has_cycles"],
                "grounded_extension_size": len(semantics["extensions"]["grounded"]),
                "num_preferred_extensions": len(semantics["extensions"]["preferred"]),
                "num_stable_extensions": len(semantics["extensions"]["stable"]),
            },
        }

        with open(filename, "w") as f:
            json.dump(report, f, indent=2)

        print(f"Rapport d'analyse exporté vers {filename}")


# Test des utilitaires I/O
if __name__ == "__main__":
    # Créer un framework de test
    agent = DungAgent()
    agent.add_argument("a")
    agent.add_argument("b")
    agent.add_argument("c")
    agent.add_attack("a", "b")
    agent.add_attack("b", "c")

    # Tests d'export
    FrameworkIO.export_to_json(agent, "test_framework.json")
    FrameworkIO.export_to_tgf(agent, "test_framework.tgf")
    FrameworkIO.export_to_dot(agent, "test_framework.dot")
    FrameworkIO.export_analysis_report(agent, "test_analysis.json")

    # Test d'import
    imported_agent = FrameworkIO.import_from_json("test_framework.json")
    print("Framework importé avec succès!")
    imported_agent.analyze_semantics_relationships()
