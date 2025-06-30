import os
import glob
import random

# --- CONFIGURATION AVEC JPYPE ---
# Ce fichier ne doit PAS démarrer la JVM. Il suppose qu'elle est déjà démarrée
# par le point d'entrée de l'application (ex: api/main.py ou une fixture de test).
import jpype
import jpype.imports
# Assurez-vous que le pont est démarré en amont (par ex. dans l'API)
import matplotlib.pyplot as plt
import networkx as nx
from jpype import JClass

# Classes pour la structure du graphe
DungTheory = JClass('org.tweetyproject.arg.dung.syntax.DungTheory')
Argument = JClass('org.tweetyproject.arg.dung.syntax.Argument')
Attack = JClass('org.tweetyproject.arg.dung.syntax.Attack')

# Classes pour le raisonnement (calcul des extensions)
SimpleGroundedReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimpleGroundedReasoner')
SimplePreferredReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimplePreferredReasoner')
SimpleStableReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimpleStableReasoner')
SimpleCompleteReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimpleCompleteReasoner')
SimpleAdmissibleReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimpleAdmissibleReasoner')
SimpleIdealReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimpleIdealReasoner')
SimpleSemiStableReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimpleSemiStableReasoner')


# --- Définition de l'Agent d'Argumentation ---

class DungAgent:
    def __init__(self):
        """
        Initialise l'agent. Les classes Java sont importées ici pour s'assurer
        que la JVM est prête au moment de l'instanciation.
        """
        if not jpype.isJVMStarted():
            raise RuntimeError(
                "La JVM doit être démarrée avant d'instancier un DungAgent. "
                "Vérifiez le point d'entrée de l'application."
            )

        # Classes pour la structure du graphe
        self.DungTheory = JClass('org.tweetyproject.arg.dung.syntax.DungTheory')
        self.Argument = JClass('org.tweetyproject.arg.dung.syntax.Argument')
        self.Attack = JClass('org.tweetyproject.arg.dung.syntax.Attack')

        # Classes pour le raisonnement (calcul des extensions)
        self.SimpleGroundedReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimpleGroundedReasoner')
        self.SimplePreferredReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimplePreferredReasoner')
        self.SimpleStableReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimpleStableReasoner')
        self.SimpleCompleteReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimpleCompleteReasoner')
        self.SimpleAdmissibleReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimpleAdmissibleReasoner')
        self.SimpleIdealReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimpleIdealReasoner')
        self.SimpleSemiStableReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimpleSemiStableReasoner')
        
        self.af = self.DungTheory()
        self._arguments = {}
        
        # Initialiser les reasoners une seule fois
        self.grounded_reasoner = self.SimpleGroundedReasoner()
        self.preferred_reasoner = self.SimplePreferredReasoner()
        self.stable_reasoner = self.SimpleStableReasoner()
        self.complete_reasoner = self.SimpleCompleteReasoner()
        self.admissible_reasoner = self.SimpleAdmissibleReasoner()
        self.ideal_reasoner = self.SimpleIdealReasoner()
        self.semi_stable_reasoner = self.SimpleSemiStableReasoner()

        # Attributs pour le cache des extensions
        self._cached_extensions = {}
        self._cache_valid = False

    def add_argument(self, name: str):
        if name not in self._arguments:
            arg = self.Argument(name)
            self.af.add(arg)
            self._arguments[name] = arg
            self._invalidate_cache()
        else:
            print(f"Avertissement : L'argument '{name}' existe déjà.")

    def add_attack(self, source_name: str, target_name: str):
        if source_name in self._arguments and target_name in self._arguments:
            self.af.add(self.Attack(self._arguments[source_name], self._arguments[target_name]))
            self._invalidate_cache()
        else:
            print(f"Erreur : Un ou plusieurs arguments ('{source_name}', '{target_name}') n'existent pas.")

    def _invalidate_cache(self):
        """Invalide le cache quand le framework est modifié."""
        self._cached_extensions = {}
        self._cache_valid = False

    def _compute_extensions_if_needed(self):
        """Calcule les extensions seulement si elles n'ont pas déjà été calculées."""
        if not self._cache_valid:
            print("(Calcul des extensions en cours...)")
            self._cached_extensions = {
                'grounded': sorted([str(arg.getName()) for arg in self.grounded_reasoner.getModel(self.af)]),
                'preferred': self._format_extensions(self.preferred_reasoner.getModels(self.af)),
                'stable': self._format_extensions(self.stable_reasoner.getModels(self.af)),
                'complete': self._format_extensions(self.complete_reasoner.getModels(self.af)),
                'admissible': self._format_extensions(self.admissible_reasoner.getModels(self.af)),
                'ideal': sorted([str(arg.getName()) for arg in self.ideal_reasoner.getModel(self.af)]),
                'semi_stable': self._format_extensions(self.semi_stable_reasoner.getModels(self.af))
            }
            self._cache_valid = True

    def reset_cache(self):
        """Vide manuellement le cache des extensions."""
        self._invalidate_cache()

    def _format_extensions(self, java_collection) -> list:
        return [sorted([str(arg.getName()) for arg in extension]) for extension in java_collection]

    def get_grounded_extension(self) -> list:
        self._compute_extensions_if_needed()
        return self._cached_extensions['grounded']

    def get_preferred_extensions(self) -> list:
        self._compute_extensions_if_needed()
        return self._cached_extensions['preferred']

    def get_stable_extensions(self) -> list:
        self._compute_extensions_if_needed()
        return self._cached_extensions['stable']
    
    def get_complete_extensions(self) -> list:
        self._compute_extensions_if_needed()
        return self._cached_extensions['complete']

    def get_admissible_sets(self) -> list:
        self._compute_extensions_if_needed()
        return self._cached_extensions['admissible']

    def get_ideal_extension(self) -> list:
        self._compute_extensions_if_needed()
        return self._cached_extensions['ideal']

    def get_semi_stable_extensions(self) -> list:
        self._compute_extensions_if_needed()
        return self._cached_extensions['semi_stable']
    
    # LA MÉTHODE SUIVANTE A ÉTÉ SUPPRIMÉE
    # def get_cf2_extensions(self) -> list:
    #     return self._format_extensions(Cf2Reasoner().getModels(self.af))
        
    def visualize_graph(self, extension_to_highlight: list = None, title_suffix: str = ""):
        import matplotlib.pyplot as plt
        import networkx as nx
        
        G = nx.DiGraph()
        nodes = [arg.getName() for arg in self.af.getNodes()]
        G.add_nodes_from(nodes)
        edges = [(a.getAttacker().getName(), a.getAttacked().getName()) for a in self.af.getAttacks()]
        G.add_edges_from(edges)

        plt.figure(figsize=(10, 8))
        pos = nx.spring_layout(G, seed=42, k=0.8)
        
        title = "Graphe d'Argumentation" + title_suffix
        node_colors = 'skyblue'
        if extension_to_highlight is not None:
            node_colors = ['lightgreen' if node in extension_to_highlight else 'lightcoral' for node in G.nodes()]
            title += f"\n(Extension surlignée : {extension_to_highlight})"

        nx.draw(G, pos, with_labels=True, node_size=2500, node_color=node_colors, 
                font_size=10, font_weight='bold', arrowsize=20, edge_color='gray')
        plt.title(title)
        plt.show()

    def get_semantics_relationships(self) -> dict:
        """Retourne l'analyse des relations sémantiques sous forme de dictionnaire."""
        self._compute_extensions_if_needed()
        
        grounded = self._cached_extensions['grounded']
        preferred = self._cached_extensions['preferred']
        complete = self._cached_extensions['complete']
        stable = self._cached_extensions['stable']
        admissible = self._cached_extensions['admissible']
        ideal = self._cached_extensions['ideal']
        
        # Vérifications théoriques
        relationships = {
            'extensions': {
                'grounded': grounded,
                'ideal': ideal,
                'preferred': preferred,
                'complete': complete,
                'stable': stable,
                'admissible': admissible
            },
            'theoretical_checks': {
                'grounded_in_complete': grounded in complete,
                'all_preferred_are_complete': all(pref in complete for pref in preferred),
                'all_stable_are_preferred': all(stable_ext in preferred for stable_ext in stable)
            }
        }
        
        return relationships

    def analyze_semantics_relationships(self):
        """Affiche l'analyse des relations sémantiques (méthode de convenance)."""
        data = self.get_semantics_relationships()
        
        print("=== ANALYSE DES RELATIONS SÉMANTIQUES ===")
        extensions = data['extensions']
        print(f"Extension Fondée: {extensions['grounded']}")
        print(f"Extension Idéale: {extensions['ideal']}")
        print(f"Extensions Préférées: {extensions['preferred']}")
        print(f"Extensions Complètes: {extensions['complete']}")
        print(f"Extensions Stables: {extensions['stable']}")
        print(f"Ensembles Admissibles: {extensions['admissible']}")
        
        print("\n--- Vérifications Théoriques ---")
        checks = data['theoretical_checks']
        if checks['grounded_in_complete']:
            print("✓ L'extension fondée est dans les extensions complètes")
        if checks['all_preferred_are_complete']:
            print("✓ Toutes les extensions préférées sont complètes")
        if checks['all_stable_are_preferred']:
            print("✓ Toutes les extensions stables sont préférées")

    def get_argument_status(self, arg_name: str) -> dict:
        """Détermine le statut d'un argument selon différentes sémantiques."""
        if arg_name not in self._arguments:
            return {'error': f"Argument '{arg_name}' n'existe pas"}
        
        self._compute_extensions_if_needed()
        
        grounded = self._cached_extensions['grounded']
        preferred = self._cached_extensions['preferred']
        stable = self._cached_extensions['stable']
        
        status = {
            'credulously_accepted': any(arg_name in ext for ext in preferred),
            'skeptically_accepted': all(arg_name in ext for ext in preferred) if preferred else False,
            'grounded_accepted': arg_name in grounded,
            'stable_accepted': any(arg_name in ext for ext in stable) if stable else False
        }
        
        return status

    def get_all_arguments_status(self) -> dict:
        """Retourne un dictionnaire avec le statut de chaque argument."""
        all_status = {}
        for arg_name in self._arguments.keys():
            all_status[arg_name] = self.get_argument_status(arg_name)
        return all_status
    
    def print_all_arguments_status(self):
        """Affiche le statut de tous les arguments (méthode de convenance)."""
        all_status = self.get_all_arguments_status()
        print("\n=== STATUT DES ARGUMENTS ===")
        for arg_name, status in all_status.items():
            if 'error' in status:
                print(f"Argument '{arg_name}': {status['error']}")
            else:
                print(f"Argument '{arg_name}':")
                print(f"  - Accepté de manière crédule: {status['credulously_accepted']}")
                print(f"  - Accepté de manière sceptique: {status['skeptically_accepted']}")
                print(f"  - Accepté dans l'extension fondée: {status['grounded_accepted']}")
                print(f"  - Accepté dans une extension stable: {status['stable_accepted']}")

    def get_framework_properties(self) -> dict:
        """Retourne les propriétés structurelles du framework."""
        nodes = list(self.af.getNodes())
        attacks = list(self.af.getAttacks())
        
        # Vérifier s'il y a des cycles
        import networkx as nx
        G = nx.DiGraph()
        G.add_nodes_from([arg.getName() for arg in nodes])
        G.add_edges_from([(a.getAttacker().getName(), a.getAttacked().getName()) for a in attacks])
        
        cycles = list(nx.simple_cycles(G))
        
        # Arguments self-attacking
        self_attacking = [a.getAttacker().getName() for a in attacks 
                         if a.getAttacker().getName() == a.getAttacked().getName()]
        
        return {
            'num_arguments': len(nodes),
            'num_attacks': len(attacks),
            'has_cycles': len(cycles) > 0,
            'cycles': cycles,
            'self_attacking': self_attacking
        }

    def analyze_framework_properties(self):
        """Affiche les propriétés structurelles du framework (méthode de convenance)."""
        properties = self.get_framework_properties()
        
        print("=== PROPRIÉTÉS STRUCTURELLES ===")
        print(f"Nombre d'arguments: {properties['num_arguments']}")
        print(f"Nombre d'attaques: {properties['num_attacks']}")
        print(f"Cycles détectés: {len(properties['cycles'])}")
        
        if properties['cycles']:
            print(f"Cycles: {properties['cycles']}")
        
        if properties['self_attacking']:
            print(f"Arguments auto-attaquants: {properties['self_attacking']}")

# --- Cas d'étude et Démonstration ---

if __name__ == "__main__":
    print("\n--- DÉMONSTRATION DE LA CLASSE DungAgent ---")
    print("NOTE: Ce bloc n'est exécuté que si le script est lancé directement.")
    print("Pour fonctionner, une JVM doit être disponible et configurée.")

    try:
        if not jpype.isJVMStarted():
            print("\n[__main__] Démarrage d'une JVM pour la démo...")
            # Chargement des libs depuis le dossier central, pas le dossier local
            project_root = Path(__file__).parent.parent
            libs_dir = project_root / 'libs' / 'tweety'
            
            if not libs_dir.exists():
                raise FileNotFoundError(f"Le répertoire des librairies Tweety est introuvable: {libs_dir}")

            jar_files = glob.glob(str(libs_dir / '*.jar'))
            if not jar_files:
                raise FileNotFoundError(f"Aucun JAR trouvé dans {libs_dir}")
            
            classpath = os.pathsep.join(jar_files)
            
            jpype.startJVM(jpype.getDefaultJVMPath(), "-ea", f"-Djava.class.path={classpath}")
            print("[__main__] JVM démarrée pour la démo.")

        # --- Le reste du code de démo ---
        print("\n--- CAS D'ÉTUDE ÉTENDU ---")
        
        agent = DungAgent()
        agent.add_argument("a")
        agent.add_argument("b")
        agent.add_argument("c")

        agent.add_attack("a", "b")
        agent.add_attack("b", "c")

        print("\n--- Analyse Sémantique Complète ---")
        agent.analyze_semantics_relationships()
        agent.print_all_arguments_status()
        
        print("\n\n--- CAS D'ÉTUDE COMPLEXE ---")
        complex_agent = DungAgent()
        
        for arg in ["a", "b", "c", "d", "e"]:
            complex_agent.add_argument(arg)
        
        complex_agent.add_attack("a", "b")
        complex_agent.add_attack("b", "c")
        complex_agent.add_attack("c", "a")
        complex_agent.add_attack("d", "c")
        complex_agent.add_attack("e", "d")
        
        print("Framework avec cycle d'arguments:")
        complex_agent.analyze_semantics_relationships()
        complex_agent.analyze_framework_properties()

    except Exception as e:
        print(f"\nERREUR lors de l'exécution de la démo : {e}")
        print("Assurez-vous que JAVA_HOME est configuré et que les JARs Tweety sont dans libs/tweety.")
