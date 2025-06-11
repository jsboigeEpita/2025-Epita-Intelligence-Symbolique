# argumentation_analysis/orchestration/plugins/logique_complexe_plugin.py

import logging
from typing import Dict, Any, List
from semantic_kernel.functions import kernel_function

from argumentation_analysis.core.logique_complexe_states import EinsteinsRiddleState

class LogiqueComplexePlugin:
    """
    Plugin pour gérer les énigmes logiques complexes nécessitant 
    une formalisation obligatoire avec TweetyProject.
    """
    
    def __init__(self, state_instance: EinsteinsRiddleState):
        self._state = state_instance
        self._logger = logging.getLogger(f"SK.{self.__class__.__name__}")
        self._logger.info(f"LogiqueComplexePlugin initialisé avec l'instance d'état (id: {id(state_instance)}, type: {type(state_instance).__name__}).")

    @kernel_function(name="get_enigme_description", description="Récupère la description complète de l'énigme d'Einstein.")
    def get_enigme_description(self) -> str:
        self._logger.info("Récupération de la description de l'énigme d'Einstein.")
        
        description = {
            "titre": "L'Énigme d'Einstein Complexe",
            "contexte": "5 maisons en ligne, chacune avec 5 caractéristiques distinctes",
            "domaines": {
                "positions": self._state.positions,
                "couleurs": self._state.couleurs, 
                "nationalités": self._state.nationalites,
                "animaux": self._state.animaux,
                "boissons": self._state.boissons,
                "métiers": self._state.metiers
            },
            "objectif": "Déterminer qui possède le poisson (et toutes les autres correspondances)",
            "complexité": "15 contraintes interdépendantes nécessitant une logique formelle"
        }
        
        return f"Énigme: {description}"

    @kernel_function(name="get_contraintes_logiques", description="Récupère les contraintes complexes de l'énigme.")
    def get_contraintes_logiques(self) -> str:
        self._logger.info("Récupération des contraintes logiques.")
        
        contraintes = self._state.get_contraintes_complexes()
        contraintes_dict = {
            "contraintes": contraintes,
            "nombre_total": len(contraintes),
            "difficulté": "Nécessite formalisation logique obligatoire",
            "conseil": "Chaque contrainte doit être traduite en clause logique TweetyProject"
        }
        
        return f"Contraintes: {contraintes_dict}"

    @kernel_function(name="formuler_clause_logique", description="Permet à Watson de formuler une clause logique en syntaxe TweetyProject.")
    def formuler_clause_logique(self, clause: str, justification: str = "") -> str:
        self._logger.info(f"Formulation d'une clause logique: {clause}")
        
        if len(clause.strip()) < 10:
            return f"Erreur: Clause trop courte. Une clause TweetyProject doit être détaillée (minimum 10 caractères)."
        
        ajoutee = self._state.ajouter_clause_logique(clause, "Watson")
        
        if ajoutee:
            progression = self._state.verifier_progression_logique()
            return f"Clause ajoutée avec succès. Progression: {progression['clauses_formulees']}/10 clauses minimales. Justification: {justification}"
        else:
            return f"Clause déjà existante ou invalide: {clause}"

    @kernel_function(name="executer_requete_tweety", description="Exécute une requête logique avec TweetyProject pour déduire des informations.")
    def executer_requete_tweety(self, requete: str, type_requete: str = "satisfiabilite") -> str:
        self._logger.info(f"Exécution d'une requête TweetyProject: {requete}")
        
        if len(self._state.clauses_logiques) < 3:
            return f"Erreur: Impossible d'exécuter une requête sans au moins 3 clauses logiques formulées. Actuellement: {len(self._state.clauses_logiques)} clauses."
        
        resultat = self._state.executer_requete_logique(requete)
        
        progression = self._state.verifier_progression_logique()
        
        return f"Requête exécutée: {resultat}. Progression requêtes: {progression['requetes_executees']}/5 minimales."

    @kernel_function(name="verifier_deduction_partielle", description="Vérifie une déduction partielle pour une maison spécifique.")
    def verifier_deduction_partielle(self, position: int, caracteristiques: Dict[str, str]) -> str:
        self._logger.info(f"Vérification déduction partielle pour position {position}: {caracteristiques}")
        
        if position not in self._state.positions:
            return f"Erreur: Position {position} invalide. Positions valides: {self._state.positions}"
        
        # Vérification contre la solution secrète
        solution_position = self._state.solution_secrete.get(position, {})
        correspondances = 0
        total_propositions = len(caracteristiques)
        
        for attribut, valeur in caracteristiques.items():
            if solution_position.get(attribut) == valeur:
                correspondances += 1
        
        if correspondances == total_propositions:
            self._state.solution_partielle[position] = caracteristiques
            return f"Déduction correcte pour la position {position}! {correspondances}/{total_propositions} attributs corrects."
        else:
            return f"Déduction incorrecte: {correspondances}/{total_propositions} attributs corrects pour la position {position}."

    @kernel_function(name="proposer_solution_complete", description="Propose une solution complète à l'énigme d'Einstein.")
    def proposer_solution_complete(self, solution: Dict[int, Dict[str, str]]) -> str:
        self._logger.info(f"Proposition de solution complète: {solution}")
        
        resultat = self._state.proposer_solution_complexe(solution)
        
        if resultat["acceptee"]:
            return f"Solution acceptée! {resultat['message']} Score logique: {resultat['score_logique']}"
        else:
            progression = self._state.verifier_progression_logique()
            if not progression["force_logique_formelle"]:
                return f"Solution rejetée: {resultat['raison']}. État actuel: {progression['clauses_formulees']} clauses, {progression['requetes_executees']} requêtes."
            else:
                return f"Solution incorrecte: {resultat['raison']}"

    @kernel_function(name="obtenir_progression_logique", description="Obtient l'état de progression de l'utilisation de la logique formelle.")
    def obtenir_progression_logique(self) -> str:
        self._logger.info("Récupération de la progression logique.")
        
        progression = self._state.obtenir_etat_progression()
        
        return f"État progression: {progression}"

    @kernel_function(name="generer_indice_complexe", description="Génère un indice nécessitant une formalisation logique.")
    def generer_indice_complexe(self) -> str:
        self._logger.info("Génération d'un indice complexe.")
        
        indices_complexes = [
            "Constraint: ∀x (Maison(x) ∧ Couleur(x,Rouge) → Nationalité(x,Anglais))",
            "Constraint: ∃!x (Position(x,3) ∧ Boisson(x,Lait))",
            "Constraint: ∀x (Couleur(x,Verte) → ∃y (Position(y,Position(x)+1) ∧ Couleur(y,Blanche)))",
            "Constraint: Adjacent(x,y) ↔ |Position(x) - Position(y)| = 1",
            "Constraint: ∀x (Métier(x,Avocat) → ∃y (Adjacent(x,y) ∧ Animal(y,Chat)))"
        ]
        
        import random
        indice_choisi = random.choice(indices_complexes)
        
        return f"Indice complexe (à formaliser en TweetyProject): {indice_choisi}"

    @kernel_function(name="valider_syntaxe_tweety", description="Valide la syntaxe d'une clause TweetyProject.")
    def valider_syntaxe_tweety(self, clause_proposee: str) -> str:
        self._logger.info(f"Validation syntaxe TweetyProject: {clause_proposee}")
        
        # Vérifications syntaxiques basiques
        erreurs = []
        
        if not any(op in clause_proposee for op in ["∀", "∃", "→", "∧", "∨", "¬"]):
            erreurs.append("Clause manque d'opérateurs logiques (∀, ∃, →, ∧, ∨, ¬)")
            
        if not any(pred in clause_proposee for pred in ["Maison", "Position", "Couleur", "Nationalité", "Animal", "Boisson", "Métier"]):
            erreurs.append("Clause manque de prédicats de domaine")
            
        if len(clause_proposee.strip()) < 15:
            erreurs.append("Clause trop simple pour une formalisation complète")
        
        if erreurs:
            return f"Syntaxe invalide: {'; '.join(erreurs)}. Exemple valide: ∀x (Maison(x) ∧ Couleur(x,Rouge) → Nationalité(x,Anglais))"
        else:
            return f"Syntaxe TweetyProject valide: {clause_proposee}"