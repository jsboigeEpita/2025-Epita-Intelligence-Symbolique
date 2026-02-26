# Services de l'API d'analyse argumentative.

# --- Service d'analyse d'argumentation de Dung ---
import networkx as nx
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from enhanced_agent import EnhancedDungAgent

# L'agent est maintenant importable car le PYTHONPATH est géré dans api/main.py
# from enhanced_agent import EnhancedDungAgent # Déplacé pour éviter conflit JVM


class DungAnalysisService:
    """
    Service pour analyser les frameworks d'argumentation de Dung.
    Utilise l'implémentation de l'étudiant (`EnhancedDungAgent`) comme moteur principal.
    """

    def __init__(self):
        import jpype
        import jpype.imports

        if not jpype.isJVMStarted():
            raise RuntimeError(
                "La JVM n'est pas démarrée. "
                "Veuillez l'initialiser au point d'entrée de l'application."
            )
        # Importer l'agent ici pour s'assurer que la JVM est prête
        from abs_arg_dung.enhanced_agent import EnhancedDungAgent

        self.agent_class = EnhancedDungAgent

        # Exposer les classes Java nécessaires pour que le test worker puisse passer
        self.DungTheory = JClass("org.tweetyproject.arg.dung.syntax.DungTheory")
        self.Argument = JClass("org.tweetyproject.arg.dung.syntax.Argument")
        self.Attack = JClass("org.tweetyproject.arg.dung.syntax.Attack")

        print("Service d'analyse Dung initialisé, utilisant EnhancedDungAgent.")

    def analyze_framework(
        self, arguments: list[str], attacks: list[tuple[str, str]], options: dict = None
    ) -> dict:
        """
        Analyse complète d'un framework d'argumentation en utilisant EnhancedDungAgent.
        """
        if options is None:
            options = {}

        # 1. Créer et peupler l'agent de l'étudiant
        agent = self.agent_class()
        for arg_name in arguments:
            agent.add_argument(arg_name)
        for source, target in attacks:
            agent.add_attack(source, target)

        # 3. Formater les résultats dans la structure attendue
        results = {
            "argument_status": {},  # Sera rempli plus bas
            "graph_properties": self._get_framework_properties(agent),
        }

        # 2. Calculer les extensions et le statut des arguments si demandé
        if options.get("compute_extensions", False):
            grounded_ext = agent.get_grounded_extension()
            preferred_ext = agent.get_preferred_extensions()
            stable_ext = agent.get_stable_extensions()
            complete_ext = agent.get_complete_extensions()
            admissible_sets = agent.get_admissible_sets()

            # Remplir le statut des arguments
            results["argument_status"] = self._get_all_arguments_status(
                arguments, preferred_ext, grounded_ext, stable_ext
            )

            # Renommer la clé 'semantics' en 'extensions' pour correspondre au test
            results["extensions"] = {
                "grounded": sorted([str(arg) for arg in grounded_ext]),
                "preferred": sorted(
                    [[str(arg) for arg in ext] for ext in preferred_ext]
                ),
                "stable": sorted([[str(arg) for arg in ext] for ext in stable_ext]),
                "complete": sorted([[str(arg) for arg in ext] for ext in complete_ext]),
                "admissible": sorted(
                    [[str(arg) for arg in ext] for ext in admissible_sets]
                ),
                "ideal": [],
                "semi_stable": [],
            }

        return results

    def _get_all_arguments_status(
        self,
        arg_names: list[str],
        preferred_ext: list,
        grounded_ext: list,
        stable_ext: list,
    ) -> dict:
        # NOTE: Assurer la présence des statuts grounded et stable.
        all_status = {}
        # Convertir les extensions en listes de chaînes une seule fois pour l'efficacité
        preferred_ext_str = [[str(arg) for arg in ext] for ext in preferred_ext]
        grounded_ext_str = [str(arg) for arg in grounded_ext]
        stable_ext_str = [[str(arg) for arg in ext] for ext in stable_ext]

        for name in arg_names:
            all_status[name] = {
                "credulously_accepted": any(name in ext for ext in preferred_ext_str),
                "skeptically_accepted": (
                    all(name in ext for ext in preferred_ext_str)
                    if preferred_ext_str
                    else False
                ),
                "grounded_accepted": name in grounded_ext_str,
                "stable_accepted": (
                    all(name in ext for ext in stable_ext_str)
                    if stable_ext_str
                    else False
                ),
            }
        return all_status

    def _get_framework_properties(self, agent: "EnhancedDungAgent") -> dict:
        """Extrait les propriétés du graphe directement depuis l'agent ou son framework Java."""
        # L'agent de l'étudiant ne stocke pas directement le graphe networkx
        # Nous le reconstruisons ici pour l'analyse des propriétés
        nodes = [str(arg.getName()) for arg in agent.af.getNodes()]
        attacks = [
            (str(a.getAttacker().getName()), str(a.getAttacked().getName()))
            for a in agent.af.getAttacks()
        ]

        G = nx.DiGraph()
        G.add_nodes_from(nodes)
        G.add_edges_from(attacks)

        # Les cycles retournés par simple_cycles sont déjà des listes de nœuds (str), pas besoin de map
        cycles = [c for c in nx.simple_cycles(G)]
        self_attacking = [
            str(a.getAttacker().getName())
            for a in agent.af.getAttacks()
            if a.getAttacker() == a.getAttacked()
        ]

        return {
            "num_arguments": len(nodes),
            "num_attacks": len(attacks),
            "has_cycles": len(cycles) > 0,
            "cycles": cycles,
            "self_attacking_nodes": list(set(self_attacking)),
        }
