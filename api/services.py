# Ce fichier contiendra la logique métier pour les services de l'API.
# Par exemple, le service d'analyse de texte.

from .models import AnalysisResponse, Fallacy

import jpype
import jpype.imports
import time
from typing import Dict

class AnalysisService:
    def __init__(self):
        """
        Initialise le service d'analyse. Assure que la JVM est démarrée.
        """
        if not jpype.isJVMStarted():
            raise RuntimeError("La JVM n'est pas démarrée. Veuillez l'initialiser au point d'entrée de l'application.")
        
        # Import des classes Java nécessaires
        try:
            from org.tweetyproject.arg.text import ArgumentParser
            from org.tweetyproject.arg.structures import PropositionalFormula
            self.ArgumentParser = ArgumentParser
            print("INFO: AnalysisService initialisé avec succès et classes Tweety importées.")
        except Exception as e:
            print(f"ERREUR: Impossible d'importer les classes Tweety. Vérifiez le classpath. Erreur: {e}")
            raise ImportError("Les classes Tweety n'ont pu être importées.") from e

    async def analyze_text(self, text: str) -> Dict:
        """
        Effectue une analyse de reconstruction d'argument en utilisant Tweety.
        """
        start_time = time.time()
        
        try:
            # 1. Utilisation du parseur d'arguments de Tweety
            parser = self.ArgumentParser()
            kb = parser.parse(text)
            
            # 2. Extraction des prémisses et de la conclusion
            # La base de connaissance (kb) contient des formules.
            # La dernière formule est généralement la conclusion.
            formulas = kb.getFormulas()
            
            premises = []
            conclusion = None

            if formulas:
                if len(formulas) > 1:
                    for i in range(len(formulas) - 1):
                        premises.append(str(formulas.get(i)))
                conclusion = str(formulas.get(len(formulas) - 1))

            argument_structure = {
                "premises": [{"id": f"p{i+1}", "text": premise} for i, premise in enumerate(premises)],
                "conclusion": {"id": "c1", "text": conclusion} if conclusion else None
            }
            summary = "La reconstruction de l'argument a été effectuée avec succès."
            service_result = {
                "argument_structure": argument_structure,
                "fallacies": [], # L'analyse de sophisme n'est pas implémentée ici
                "suggestions": ["Vérifiez la validité logique de la structure."],
                "summary": summary
            }

        except Exception as e:
            print(f"ERREUR lors de l'analyse du texte avec Tweety: {e}")
            service_result = {
                "argument_structure": None,
                "fallacies": [],
                "suggestions": ["Une erreur est survenue pendant l'analyse."],
                "summary": f"Erreur du service d'analyse: {e}",
            }

        duration = time.time() - start_time
        service_result["duration"] = duration
        service_result["components_used"] = ["TweetyArgumentReconstructor"]
        
        return service_result

# Exemple d'autres services qui pourraient être ajoutés :
# class UserService:
#     def get_user(self, user_id: int): ...
#
# class FallacyDefinitionService:
#     def get_fallacy_definition(self, fallacy_type: str): ...


# --- Service d'analyse d'argumentation de Dung ---
import os
import glob
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
        from enhanced_agent import EnhancedDungAgent
        self.agent_class = EnhancedDungAgent
        print("Service d'analyse Dung initialisé, utilisant EnhancedDungAgent.")


    def analyze_framework(self, arguments: list[str], attacks: list[tuple[str, str]], options: dict = None) -> dict:
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
            'argument_status': {}, # Sera rempli plus bas
            'graph_properties': self._get_framework_properties(agent)
        }

        # 2. Calculer les extensions et le statut des arguments si demandé
        if options.get('compute_extensions', False):
            grounded_ext = agent.get_grounded_extension()
            preferred_ext = agent.get_preferred_extensions()
            stable_ext = agent.get_stable_extensions()
            complete_ext = agent.get_complete_extensions()
            admissible_sets = agent.get_admissible_sets()

            # Remplir le statut des arguments
            results['argument_status'] = self._get_all_arguments_status(arguments, preferred_ext, grounded_ext, stable_ext)
            
            # Renommer la clé 'semantics' en 'extensions' pour correspondre au test
            results['extensions'] = {
                'grounded': sorted([str(arg) for arg in grounded_ext]),
                'preferred': sorted([[str(arg) for arg in ext] for ext in preferred_ext]),
                'stable': sorted([[str(arg) for arg in ext] for ext in stable_ext]),
                'complete': sorted([[str(arg) for arg in ext] for ext in complete_ext]),
                'admissible': sorted([[str(arg) for arg in ext] for ext in admissible_sets]),
                'ideal': [],
                'semi_stable': []
            }
        
        return results

    def _get_all_arguments_status(self, arg_names: list[str], preferred_ext: list, grounded_ext: list, stable_ext: list) -> dict:
        # NOTE: Assurer la présence des statuts grounded et stable.
        all_status = {}
        for name in arg_names:
            all_status[name] = {
                'credulously_accepted': any(name in ext for ext in preferred_ext),
                'skeptically_accepted': all(name in ext for ext in preferred_ext) if preferred_ext else False,
                'grounded_accepted': name in grounded_ext,
                'stable_accepted': all(name in ext for ext in stable_ext) if stable_ext else False,
            }
        return all_status
    
    def _get_framework_properties(self, agent: "EnhancedDungAgent") -> dict:
        """Extrait les propriétés du graphe directement depuis l'agent ou son framework Java."""
        # L'agent de l'étudiant ne stocke pas directement le graphe networkx
        # Nous le reconstruisons ici pour l'analyse des propriétés
        nodes = [str(arg.getName()) for arg in agent.af.getNodes()]
        attacks = [(str(a.getAttacker().getName()), str(a.getAttacked().getName())) for a in agent.af.getAttacks()]
        
        G = nx.DiGraph()
        G.add_nodes_from(nodes)
        G.add_edges_from(attacks)
        
        cycles = [list(map(str, c)) for c in nx.simple_cycles(G)]
        self_attacking = [str(a.getAttacker().getName()) for a in agent.af.getAttacks() if a.getAttacker() == a.getAttacked()]

        return {
            'num_arguments': len(nodes),
            'num_attacks': len(attacks),
            'has_cycles': len(cycles) > 0,
            'cycles': cycles,
            'self_attacking_nodes': list(set(self_attacking))
        }
