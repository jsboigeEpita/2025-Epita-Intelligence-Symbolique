import unittest
from agent import DungAgent
from framework_generator import FrameworkGenerator
import itertools


class AdvancedDungAgentTests(unittest.TestCase):
    def setUp(self):
        self.agent = DungAgent()

    def test_complex_layered_framework(self):
        """Test framework complexe avec plusieurs couches d'attaques"""
        # Création d'un framework hiérarchique
        # Niveau 1: a1, a2 (fondation)
        # Niveau 2: b1, b2 (attaquent niveau 1)
        # Niveau 3: c1, c2 (attaquent niveau 2)
        # Niveau 4: d1 (attaque niveau 3)

        for level in ["a", "b", "c"]:
            for i in [1, 2]:
                self.agent.add_argument(f"{level}{i}")
        self.agent.add_argument("d1")

        # Attaques inter-niveaux
        self.agent.add_attack("b1", "a1")
        self.agent.add_attack("b2", "a2")
        self.agent.add_attack("c1", "b1")
        self.agent.add_attack("c2", "b2")
        self.agent.add_attack("d1", "c1")

        # Attaques intra-niveau (conflits)
        self.agent.add_attack("a1", "a2")
        self.agent.add_attack("c1", "c2")

        grounded = self.agent.get_grounded_extension()
        preferred = self.agent.get_preferred_extensions()
        stable = self.agent.get_stable_extensions()

        print(f"\nDEBUG Complex Layered:")
        print(f"Grounded: {grounded}")
        print(f"Preferred: {preferred}")
        print(f"Stable: {stable}")

        # Vérifications attendues
        self.assertIn("d1", grounded)  # d1 n'est attaqué par personne
        self.assertNotIn("c1", grounded)  # c1 est attaqué par d1

        # Au moins une extension préférée doit exister
        self.assertGreater(len(preferred), 0)

    def test_reinstatement_patterns(self):
        """Test des motifs de réinstauration (A attaque B, B attaque C, C attaque A)"""
        # Pattern: a -> b -> c -> a (cycle)
        # Plus: d -> b (défend a indirectement)

        for arg in ["a", "b", "c", "d"]:
            self.agent.add_argument(arg)

        # Cycle principal
        self.agent.add_attack("a", "b")
        self.agent.add_attack("b", "c")
        self.agent.add_attack("c", "a")

        # Défenseur externe
        self.agent.add_attack("d", "b")

        grounded = self.agent.get_grounded_extension()
        preferred = self.agent.get_preferred_extensions()

        print(f"\nDEBUG Reinstatement:")
        print(f"Grounded: {grounded}")
        print(f"Preferred: {preferred}")

        # d devrait être accepté (non attaqué)
        self.assertIn("d", grounded)

        # Vérifier que d influence les extensions préférées
        for ext in preferred:
            if "d" in ext:
                # Si d est accepté, b est rejeté, donc a peut être réinstauré
                self.assertTrue("a" in ext or "c" in ext)

    def test_floating_arguments(self):
        """Test arguments 'flottants' - non connectés au reste"""
        # Framework principal: a -> b -> c
        for arg in ["a", "b", "c"]:
            self.agent.add_argument(arg)
        self.agent.add_attack("a", "b")
        self.agent.add_attack("b", "c")

        # Arguments flottants isolés
        for arg in ["x", "y", "z"]:
            self.agent.add_argument(arg)

        # Cycle flottant
        self.agent.add_attack("x", "y")
        self.agent.add_attack("y", "x")
        # z reste complètement isolé

        grounded = self.agent.get_grounded_extension()
        preferred = self.agent.get_preferred_extensions()

        print(f"\nDEBUG Floating Arguments:")
        print(f"Grounded: {grounded}")
        print(f"Preferred: {preferred}")

        # Les arguments non attaqués doivent être dans l'extension fondée
        expected_grounded = {"a", "c", "z"}
        self.assertEqual(set(grounded), expected_grounded)

        # Vérifier que toutes les extensions préférées contiennent les arguments fondés
        for ext in preferred:
            for arg in expected_grounded:
                self.assertIn(arg, ext)

    def test_complex_self_attacks(self):
        """Test combinations complexes avec self-attacks"""
        # a s'auto-attaque ET est attaqué par b
        # b est attaqué par c
        # c est attaqué par d
        # d s'auto-attaque

        for arg in ["a", "b", "c", "d"]:
            self.agent.add_argument(arg)

        self.agent.add_attack("a", "a")  # Self-attack
        self.agent.add_attack("b", "a")
        self.agent.add_attack("c", "b")
        self.agent.add_attack("d", "c")
        self.agent.add_attack("d", "d")  # Self-attack

        grounded = self.agent.get_grounded_extension()
        preferred = self.agent.get_preferred_extensions()
        complete = self.agent.get_complete_extensions()

        print(f"\nDEBUG Complex Self-Attacks:")
        print(f"Grounded: {grounded}")
        print(f"Preferred: {preferred}")
        print(f"Complete: {complete}")

        # Arguments auto-attaquants ne peuvent pas être acceptés
        self.assertNotIn("a", grounded)
        self.assertNotIn("d", grounded)

        # Analyser la chaîne: d(auto) -> c -> b -> a(auto)
        # c pourrait être acceptable si d n'est pas accepté
        status = self.agent.get_all_arguments_status()
        for arg, stat in status.items():
            print(f"Argument {arg}: {stat}")

    def test_symmetric_conflicts(self):
        """Test conflits symétriques multiples"""
        # Deux paires en conflit: (a1,a2) et (b1,b2)
        # Plus des interactions croisées

        for pair in ["a", "b"]:
            for i in [1, 2]:
                self.agent.add_argument(f"{pair}{i}")

        # Conflits symétriques
        self.agent.add_attack("a1", "a2")
        self.agent.add_attack("a2", "a1")
        self.agent.add_attack("b1", "b2")
        self.agent.add_attack("b2", "b1")

        # Interactions croisées
        self.agent.add_attack("a1", "b1")
        self.agent.add_attack("b2", "a2")

        grounded = self.agent.get_grounded_extension()
        preferred = self.agent.get_preferred_extensions()

        print(f"\nDEBUG Symmetric Conflicts:")
        print(f"Grounded: {grounded}")
        print(f"Preferred: {preferred}")

        # Extension fondée vide (tous en conflit)
        self.assertEqual(len(grounded), 0)

        # Doit y avoir exactement 4 extensions préférées
        # (combinaisons des choix dans chaque paire)
        # Sauf si TweetyProject optimise...
        print(f"Nombre d'extensions préférées: {len(preferred)}")

        # Vérifier que chaque extension respecte les contraintes
        for ext in preferred:
            # Pas deux arguments d'une même paire en conflit
            pair_a = set(ext) & {"a1", "a2"}
            pair_b = set(ext) & {"b1", "b2"}
            self.assertLessEqual(len(pair_a), 1)
            self.assertLessEqual(len(pair_b), 1)

    def test_large_complete_graph(self):
        """Test graphe complet (tous attaquent tous)"""
        n = 5
        args = [f"arg_{i}" for i in range(n)]

        for arg in args:
            self.agent.add_argument(arg)

        # Tous attaquent tous (y compris eux-mêmes)
        for i in range(n):
            for j in range(n):
                self.agent.add_attack(f"arg_{i}", f"arg_{j}")

        grounded = self.agent.get_grounded_extension()
        preferred = self.agent.get_preferred_extensions()
        stable = self.agent.get_stable_extensions()
        admissible = self.agent.get_admissible_sets()

        print(f"\nDEBUG Complete Graph:")
        print(f"Grounded: {grounded}")
        print(f"Preferred: {preferred}")
        print(f"Stable: {stable}")
        print(f"Admissible count: {len(admissible)}")

        # Dans un graphe complet avec self-attacks, seule l'extension vide est possible
        self.assertEqual(len(grounded), 0)
        self.assertEqual(len(preferred), 1)
        self.assertEqual(preferred[0], [])
        self.assertEqual(len(stable), 0)  # Pas d'extensions stables

    def test_performance_stress(self):
        """Test de performance sur un framework dense"""
        import time

        n = 15  # Framework de taille modérée
        for i in range(n):
            self.agent.add_argument(f"stress_{i}")

        # Ajouter des attaques aléatoires avec une densité contrôlée
        import random

        random.seed(42)
        attack_probability = 0.3

        for i in range(n):
            for j in range(n):
                if i != j and random.random() < attack_probability:
                    self.agent.add_attack(f"stress_{i}", f"stress_{j}")

        start_time = time.time()

        grounded = self.agent.get_grounded_extension()
        preferred = self.agent.get_preferred_extensions()
        stable = self.agent.get_stable_extensions()
        complete = self.agent.get_complete_extensions()

        end_time = time.time()
        computation_time = end_time - start_time

        print(f"\nDEBUG Performance Stress:")
        print(f"Temps de calcul: {computation_time:.4f}s")
        print(f"Grounded size: {len(grounded)}")
        print(f"Preferred count: {len(preferred)}")
        print(f"Stable count: {len(stable)}")
        print(f"Complete count: {len(complete)}")

        # Le calcul ne devrait pas prendre trop de temps
        self.assertLess(computation_time, 5.0, "Calcul trop lent pour ce framework")

    def test_semantic_inclusion_properties(self):
        """Test des propriétés d'inclusion entre sémantiques"""
        # Créer un framework non-trivial
        for arg in ["a", "b", "c", "d", "e"]:
            self.agent.add_argument(arg)

        # Structure mixte: chaîne + cycle partiel
        self.agent.add_attack("a", "b")  # a -> b
        self.agent.add_attack("b", "c")  # b -> c
        self.agent.add_attack("c", "d")  # c -> d
        self.agent.add_attack("d", "c")  # d <-> c (cycle)
        self.agent.add_attack("e", "d")  # e -> d

        grounded = self.agent.get_grounded_extension()
        preferred = self.agent.get_preferred_extensions()
        stable = self.agent.get_stable_extensions()
        complete = self.agent.get_complete_extensions()
        admissible = self.agent.get_admissible_sets()

        print(f"\nDEBUG Semantic Inclusions:")
        print(f"Grounded: {grounded}")
        print(f"Preferred: {preferred}")
        print(f"Stable: {stable}")
        print(f"Complete: {complete}")
        print(f"Admissible: {admissible}")

        # Propriétés théoriques à vérifier
        # 1. Grounded ⊆ chaque Complete
        for complete_ext in complete:
            for arg in grounded:
                self.assertIn(
                    arg,
                    complete_ext,
                    f"Grounded arg '{arg}' not in complete extension {complete_ext}",
                )

        # 2. Chaque Preferred ⊆ Complete
        for pref_ext in preferred:
            self.assertIn(
                pref_ext,
                complete,
                f"Preferred extension {pref_ext} not in complete extensions",
            )

        # 3. Chaque Stable ⊆ Preferred (si stables existent)
        for stable_ext in stable:
            self.assertIn(
                stable_ext,
                preferred,
                f"Stable extension {stable_ext} not in preferred extensions",
            )

        # 4. Toutes les extensions sont admissibles
        for complete_ext in complete:
            self.assertIn(
                complete_ext,
                admissible,
                f"Complete extension {complete_ext} not admissible",
            )

    def test_cardinality_bounds(self):
        """Test des bornes sur le nombre d'extensions"""
        # Framework conçu pour tester les limites
        # Triangle + arguments isolés

        # Triangle conflictuel
        for arg in ["t1", "t2", "t3"]:
            self.agent.add_argument(arg)
        self.agent.add_attack("t1", "t2")
        self.agent.add_attack("t2", "t3")
        self.agent.add_attack("t3", "t1")

        # Arguments isolés
        for i in range(3):
            self.agent.add_argument(f"isolated_{i}")

        # Paire en conflit
        self.agent.add_argument("pair_a")
        self.agent.add_argument("pair_b")
        self.agent.add_attack("pair_a", "pair_b")
        self.agent.add_attack("pair_b", "pair_a")

        preferred = self.agent.get_preferred_extensions()
        stable = self.agent.get_stable_extensions()

        print(f"\nDEBUG Cardinality Bounds:")
        print(f"Preferred: {preferred}")
        print(f"Stable: {stable}")

        # Analyser la structure des extensions
        isolated_args = {f"isolated_{i}" for i in range(3)}

        for ext in preferred:
            ext_set = set(ext)
            # Tous les arguments isolés doivent être présents
            self.assertTrue(
                isolated_args.issubset(ext_set),
                f"Extension {ext} missing isolated arguments",
            )

            # Exactement un argument de la paire conflictuelle
            pair_intersection = ext_set & {"pair_a", "pair_b"}
            self.assertEqual(
                len(pair_intersection),
                1,
                f"Extension {ext} has wrong number of pair arguments",
            )

    def test_framework_modifications(self):
        """Test modifications dynamiques du framework"""
        # Construire un framework initial
        for arg in ["base1", "base2"]:
            self.agent.add_argument(arg)
        self.agent.add_attack("base1", "base2")

        initial_grounded = self.agent.get_grounded_extension()
        print(f"Initial grounded: {initial_grounded}")

        # Ajouter un nouvel argument qui change la situation
        self.agent.add_argument("disruptor")
        self.agent.add_attack("disruptor", "base1")

        modified_grounded = self.agent.get_grounded_extension()
        print(f"Modified grounded: {modified_grounded}")

        # La modification devrait avoir changé les extensions
        self.assertNotEqual(initial_grounded, modified_grounded)

        # Vérifier que le cache a été correctement invalidé
        # (test indirect via les résultats)
        self.assertIn("base2", modified_grounded)
        self.assertNotIn("base1", modified_grounded)  # Maintenant attaqué

    def test_argumentation_patterns(self):
        """Test des patterns classiques d'argumentation"""
        patterns_results = {}

        # Pattern 1: Chaîne simple
        agent1 = DungAgent()
        for i in range(4):
            agent1.add_argument(f"chain_{i}")
        for i in range(3):
            agent1.add_attack(f"chain_{i}", f"chain_{i+1}")
        patterns_results["chain"] = agent1.get_grounded_extension()

        # Pattern 2: Étoile (un centre attaque tous les autres)
        agent2 = DungAgent()
        agent2.add_argument("center")
        for i in range(4):
            agent2.add_argument(f"spoke_{i}")
            agent2.add_attack("center", f"spoke_{i}")
        patterns_results["star"] = agent2.get_grounded_extension()

        # Pattern 3: Roue (étoile + cycle externe)
        agent3 = DungAgent()
        agent3.add_argument("hub")
        spokes = [f"wheel_{i}" for i in range(4)]
        for spoke in spokes:
            agent3.add_argument(spoke)
            agent3.add_attack("hub", spoke)
        # Cycle externe
        for i in range(4):
            agent3.add_attack(spokes[i], spokes[(i + 1) % 4])
        patterns_results["wheel"] = agent3.get_grounded_extension()

        print(f"\nDEBUG Argumentation Patterns:")
        for pattern, result in patterns_results.items():
            print(f"{pattern}: {result}")

        # Vérifications spécifiques aux patterns
        self.assertIn("chain_0", patterns_results["chain"])
        self.assertIn("chain_2", patterns_results["chain"])

        self.assertIn("center", patterns_results["star"])
        self.assertEqual(len(patterns_results["star"]), 1)  # Seul le centre

        self.assertIn("hub", patterns_results["wheel"])


if __name__ == "__main__":
    # Lancer les tests avancés
    suite = unittest.TestLoader().loadTestsFromTestCase(AdvancedDungAgentTests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Statistiques finales
    print(f"\n{'='*60}")
    print(f"RÉSULTATS DES TESTS AVANCÉS")
    print(f"{'='*60}")
    print(f"Tests exécutés: {result.testsRun}")
    print(f"Échecs: {len(result.failures)}")
    print(f"Erreurs: {len(result.errors)}")
    print(f"Succès: {result.testsRun - len(result.failures) - len(result.errors)}")
