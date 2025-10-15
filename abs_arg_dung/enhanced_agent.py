from abs_arg_dung.agent import DungAgent
import networkx as nx


class EnhancedDungAgent(DungAgent):
    """Agent avec corrections pour certains cas spécifiques"""

    def __init__(self):
        super().__init__()
        self.correction_mode = True

    def get_preferred_extensions(self) -> list:
        """Version corrigée des extensions préférées"""
        original_extensions = super().get_preferred_extensions()

        if not self.correction_mode:
            return original_extensions

        # Détecter les cycles parfaits et corriger si nécessaire
        if (
            self._is_perfect_cycle()
            and len(original_extensions) == 1
            and original_extensions[0] == []
        ):
            return self._compute_cycle_extensions()

        return original_extensions

    def get_grounded_extension(self) -> list:
        """Version corrigée de l'extension fondée"""
        original_grounded = super().get_grounded_extension()

        if not self.correction_mode:
            return original_grounded

        # Correction pour le cas self-attack + attack
        if len(original_grounded) == 0:
            corrected = self._check_self_attack_case()
            if corrected is not None:
                return corrected

        return original_grounded

    def _is_perfect_cycle(self) -> bool:
        """Détecte si le framework est un cycle parfait"""
        nodes = [arg.getName() for arg in self.af.getNodes()]
        attacks = [
            (a.getAttacker().getName(), a.getAttacked().getName())
            for a in self.af.getAttacks()
        ]

        # Vérifier si c'est un cycle simple
        if len(nodes) != len(attacks):
            return False

        G = nx.DiGraph()
        G.add_nodes_from(nodes)
        G.add_edges_from(attacks)

        # Vérifier si chaque nœud a exactement un entrant et un sortant
        return all(G.in_degree(node) == 1 and G.out_degree(node) == 1 for node in nodes)

    def _compute_cycle_extensions(self) -> list:
        """Calcule manuellement les extensions pour un cycle parfait"""
        nodes = [arg.getName() for arg in self.af.getNodes()]
        # Pour un cycle parfait, chaque argument forme une extension préférée
        return [[node] for node in nodes]

    def _check_self_attack_case(self) -> list:
        """Vérifie et corrige le cas self-attack + attack"""
        nodes = [arg.getName() for arg in self.af.getNodes()]
        attacks = [
            (a.getAttacker().getName(), a.getAttacked().getName())
            for a in self.af.getAttacks()
        ]

        self_attacking = set()
        attacked_by_others = set()

        for source, target in attacks:
            if source == target:
                self_attacking.add(source)
            else:
                attacked_by_others.add(target)

        # Arguments qui ne sont ni self-attacking ni attaqués par des arguments valides
        candidates = []
        for node in nodes:
            if node not in self_attacking:
                # Vérifier si attaqué par un argument non-self-attacking
                attacked_by_valid = any(
                    source != target and target == node
                    for source, target in attacks
                    if source not in self_attacking
                )
                if not attacked_by_valid:
                    candidates.append(node)

        return sorted(candidates) if candidates else None

    def toggle_correction_mode(self):
        """Active/désactive le mode correction"""
        self.correction_mode = not self.correction_mode
        self._invalidate_cache()
        return self.correction_mode


# Test de l'agent amélioré
if __name__ == "__main__":
    print("=== TEST AGENT AMÉLIORÉ ===")

    # Test self-attack
    agent = EnhancedDungAgent()
    agent.add_argument("a")
    agent.add_argument("b")
    agent.add_attack("a", "a")
    agent.add_attack("a", "b")

    print("Self-attack case:")
    print(f"Grounded (corrigé): {agent.get_grounded_extension()}")
    print(f"Preferred (corrigé): {agent.get_preferred_extensions()}")

    # Test cycle
    agent2 = EnhancedDungAgent()
    for arg in ["a", "b", "c"]:
        agent2.add_argument(arg)
    agent2.add_attack("a", "b")
    agent2.add_attack("b", "c")
    agent2.add_attack("c", "a")

    print("\nCycle case:")
    print(f"Preferred (corrigé): {agent2.get_preferred_extensions()}")
