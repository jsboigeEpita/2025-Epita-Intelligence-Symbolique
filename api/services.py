# Ce fichier contiendra la logique métier pour les services de l'API.
# Par exemple, le service d'analyse de texte.

from .models import AnalysisResponse, Fallacy

class AnalysisService:
    def __init__(self):
        # Initialisation du service, par exemple chargement de modèles, connexion à une base de données, etc.
        # Pour l'instant, nous n'avons pas de dépendances complexes.
        pass

    def analyze_text(self, text: str) -> AnalysisResponse:
        """
        Effectue l'analyse du texte pour détecter les sophismes.
        Cette implémentation est un mock et devra être remplacée par la logique réelle.
        """
        # Logique de mock similaire à celle dans endpoints.py pour la cohérence,
        # mais idéalement, cette logique ne devrait exister qu'ici.
        if not text or not text.strip():
            # Gérer le cas d'un texte vide ou ne contenant que des espaces.
            # Bien que la validation Pydantic puisse déjà le faire, une double vérification est possible.
            return AnalysisResponse(original_text=text, fallacies_detected=[])

        if "example fallacy" in text.lower():
            fallacies = [
                Fallacy(type="Ad Hominem (Service)", description="Attacking the person instead of the argument."),
                Fallacy(type="Straw Man (Service)", description="Misrepresenting the opponent's argument.")
            ]
        elif "no fallacy" in text.lower():
            fallacies = []
        else:
            fallacies = [
                Fallacy(type="Hasty Generalization (Service)", description="Drawing a conclusion based on a small sample size.")
            ]
        
        return AnalysisResponse(original_text=text, fallacies_detected=fallacies)

# Exemple d'autres services qui pourraient être ajoutés :
# class UserService:
#     def get_user(self, user_id: int): ...
#
# class FallacyDefinitionService:
#     def get_fallacy_definition(self, fallacy_type: str): ...


# --- Service d'analyse d'argumentation de Dung ---
import os
import glob
import jpype
import jpype.imports
import networkx as nx
# Remarque: L'initialisation de la JVM est maintenant gérée de manière centralisée
# au démarrage de l'application (dans main.py) ou via conftest.py pour les tests.

class DungAnalysisService:
    """
    Service pour analyser les frameworks d'argumentation de Dung.
    Suppose que la JVM a déjà été démarrée.
    """

    def __init__(self):
        if not jpype.isJVMStarted():
            raise RuntimeError(
                "La JVM n'est pas démarrée. "
                "Veuillez l'initialiser au point d'entrée de l'application."
            )
        self._import_java_classes()

    def _import_java_classes(self):
        """Importe les classes Java nécessaires une fois la JVM démarrée."""
        from jpype import JClass
        # Syntaxe
        self.DungTheory = JClass('org.tweetyproject.arg.dung.syntax.DungTheory')
        self.Argument = JClass('org.tweetyproject.arg.dung.syntax.Argument')
        self.Attack = JClass('org.tweetyproject.arg.dung.syntax.Attack')
        # Raisonneurs
        self.SimpleGroundedReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimpleGroundedReasoner')
        self.SimplePreferredReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimplePreferredReasoner')
        self.SimpleStableReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimpleStableReasoner')
        self.SimpleCompleteReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimpleCompleteReasoner')
        self.SimpleAdmissibleReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimpleAdmissibleReasoner')
        self.SimpleIdealReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimpleIdealReasoner')
        self.SimpleSemiStableReasoner = JClass('org.tweetyproject.arg.dung.reasoner.SimpleSemiStableReasoner')
        print("Classes Java de TweetyProject liées au service.")


    def analyze_framework(self, arguments: list[str], attacks: list[tuple[str, str]]) -> dict:
        """
        Analyse complète d'un framework d'argumentation.
        Prend une liste de noms d'arguments et une liste de tuples pour les attaques.
        """
        af = self.DungTheory()
        arg_map = {name: self.Argument(name) for name in arguments}
        
        for arg_obj in arg_map.values():
            af.add(arg_obj)
            
        for source, target in attacks:
            if source in arg_map and target in arg_map:
                af.add(self.Attack(arg_map[source], arg_map[target]))
        
        # Calcul des sémantiques
        preferred_ext = self._format_extensions(self.SimplePreferredReasoner().getModels(af))
        
        # Analyse et résultats
        results = {
            'semantics': {
                'grounded': sorted([str(arg.getName()) for arg in self.SimpleGroundedReasoner().getModel(af)]),
                'preferred': preferred_ext,
                'stable': self._format_extensions(self.SimpleStableReasoner().getModels(af)),
                'complete': self._format_extensions(self.SimpleCompleteReasoner().getModels(af)),
                'admissible': self._format_extensions(self.SimpleAdmissibleReasoner().getModels(af)),
                'ideal': sorted([str(arg.getName()) for arg in self.SimpleIdealReasoner().getModel(af)]),
                'semi_stable': self._format_extensions(self.SimpleSemiStableReasoner().getModels(af))
            },
            'argument_status': self._get_all_arguments_status(arg_map.keys(), af),
            'graph_properties': self._get_framework_properties(af)
        }
        
        return results

    def _format_extensions(self, java_collection) -> list:
        return [sorted([str(arg.getName()) for arg in extension]) for extension in java_collection]

    def _get_argument_status(self, arg_name: str, af, preferred_ext, grounded_ext, stable_ext) -> dict:
        status = {
            'credulously_accepted': any(arg_name in ext for ext in preferred_ext),
            'skeptically_accepted': all(arg_name in ext for ext in preferred_ext) if preferred_ext else False,
            'grounded_accepted': arg_name in grounded_ext,
            'stable_accepted': any(arg_name in ext for ext in stable_ext) if stable_ext else False
        }
        return status

    def _get_all_arguments_status(self, arg_names: list[str], af) -> dict:
        # Calculer les extensions une seule fois
        preferred = self._format_extensions(self.SimplePreferredReasoner().getModels(af))
        grounded = sorted([str(arg.getName()) for arg in self.SimpleGroundedReasoner().getModel(af)])
        stable = self._format_extensions(self.SimpleStableReasoner().getModels(af))
        
        all_status = {}
        for name in arg_names:
            all_status[name] = self._get_argument_status(name, af, preferred, grounded, stable)
        return all_status
    
    def _get_framework_properties(self, af) -> dict:
        nodes = list(af.getNodes())
        attacks = list(af.getAttacks())
        
        G = nx.DiGraph()
        G.add_nodes_from([arg.getName() for arg in nodes])
        G.add_edges_from([(a.getAttacker().getName(), a.getAttacked().getName()) for a in attacks])
        
        cycles = [list(c) for c in nx.simple_cycles(G)]
        self_attacking = [a.getAttacker().getName() for a in attacks if a.getAttacker() == a.getAttacked()]

        return {
            'num_arguments': len(nodes),
            'num_attacks': len(attacks),
            'has_cycles': len(cycles) > 0,
            'cycles': cycles,
            'self_attacking_nodes': list(set(self_attacking))
        }
