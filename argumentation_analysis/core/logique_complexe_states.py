import uuid
import random
from typing import List, Dict, Any, Optional, Set, Tuple
from .enquete_states import BaseWorkflowState

class EinsteinsRiddleState(BaseWorkflowState):
    """
    État pour l'énigme d'Einstein complexe nécessitant une logique formelle.
    
    Cette énigme implique 5 maisons avec 5 propriétaires ayant chacun:
    - Une couleur de maison
    - Une nationalité  
    - Un animal de compagnie
    - Une boisson favorite
    - Un métier
    
    Les contraintes sont suffisamment complexes pour nécessiter 
    une formalisation logique obligatoire.
    """
    
    def __init__(self, initial_context: dict = None, workflow_id: str = None):
        super().__init__(initial_context or {}, workflow_id)
        
        # Définition des domaines
        self.positions = [1, 2, 3, 4, 5]  # Position des maisons
        self.couleurs = ["Rouge", "Bleue", "Verte", "Jaune", "Blanche"]
        self.nationalites = ["Anglais", "Suédois", "Danois", "Norvégien", "Allemand"]
        self.animaux = ["Chien", "Chat", "Oiseau", "Poisson", "Cheval"]
        self.boissons = ["Thé", "Café", "Lait", "Bière", "Eau"]
        self.metiers = ["Médecin", "Avocat", "Ingénieur", "Professeur", "Artiste"]
        
        # Génération de la solution secrète
        self._generer_solution_secrete()
        
        # État du raisonnement
        self.clauses_logiques: List[str] = []
        self.deductions_watson: List[Dict] = []
        self.contraintes_formulees: Set[str] = set()
        self.requetes_executees: List[Dict] = []
        self.solution_partielle: Dict[int, Dict[str, str]] = {}
        
        # Compteurs de progression
        self.etapes_raisonnement = 0
        self.contraintes_obligatoires_restantes = 15  # Minimum requis
        
    def _generer_solution_secrete(self):
        """Génère une solution valide respectant toutes les contraintes."""
        # Solution prédéfinie pour cohérence
        self.solution_secrete = {
            1: {"couleur": "Jaune", "nationalite": "Norvégien", "animal": "Chat", "boisson": "Eau", "metier": "Médecin"},
            2: {"couleur": "Bleue", "nationalite": "Danois", "animal": "Cheval", "boisson": "Thé", "metier": "Avocat"},
            3: {"couleur": "Rouge", "nationalite": "Anglais", "animal": "Oiseau", "boisson": "Lait", "metier": "Ingénieur"},
            4: {"couleur": "Verte", "nationalite": "Allemand", "animal": "Poisson", "boisson": "Café", "metier": "Professeur"},
            5: {"couleur": "Blanche", "nationalite": "Suédois", "animal": "Chien", "boisson": "Bière", "metier": "Artiste"}
        }
        
    def get_contraintes_complexes(self) -> List[str]:
        """Retourne la liste des contraintes complexes de l'énigme."""
        return [
            "L'Anglais vit dans la maison rouge",
            "Le Suédois a un chien",
            "Le Danois boit du thé", 
            "La maison verte est immédiatement à gauche de la maison blanche",
            "Le propriétaire de la maison verte boit du café",
            "La personne qui fume des Pall Mall élève des oiseaux",
            "Le propriétaire de la maison jaune est médecin",
            "L'homme qui vit dans la maison du centre boit du lait",
            "Le Norvégien vit dans la première maison",
            "L'homme qui est avocat vit à côté de celui qui a des chats",
            "L'homme qui a un cheval vit à côté de celui qui est médecin",
            "L'homme qui est artiste boit de la bière",
            "L'Allemand est professeur",
            "Le Norvégien vit à côté de la maison bleue",
            "L'avocat vit à côté de celui qui boit de l'eau"
        ]
    
    def ajouter_clause_logique(self, clause: str, source: str = "Watson") -> bool:
        """
        Ajoute une clause logique formulée par Watson.
        Retourne True si la clause est valide et nouvelle.
        """
        if clause not in self.clauses_logiques:
            self.clauses_logiques.append(clause)
            self.deductions_watson.append({
                "etape": len(self.deductions_watson) + 1,
                "clause": clause,
                "source": source,
                "timestamp": uuid.uuid4().hex[:8]
            })
            return True
        return False
    
    def executer_requete_logique(self, requete: str) -> Dict[str, Any]:
        """
        Simule l'exécution d'une requête logique par TweetyProject.
        """
        self.requetes_executees.append({
            "requete": requete,
            "etape": len(self.requetes_executees) + 1
        })
        
        # Simulation de résultats selon la requête
        if "existe(" in requete.lower():
            return {"type": "existence", "resultat": True, "bindings": ["X=1", "X=3"]}
        elif "forall(" in requete.lower():
            return {"type": "universel", "resultat": False, "contre_exemple": "Position 2"}
        else:
            return {"type": "satisfiabilite", "resultat": True, "modele": "Modèle trouvé"}
    
    def verifier_progression_logique(self) -> Dict[str, Any]:
        """
        Vérifie si Watson utilise suffisamment la logique formelle.
        """
        progression = {
            "clauses_formulees": len(self.clauses_logiques),
            "requetes_executees": len(self.requetes_executees),
            "contraintes_traitees": len(self.contraintes_formulees),
            "force_logique_formelle": len(self.clauses_logiques) >= 10 and len(self.requetes_executees) >= 5
        }
        return progression
    
    def proposer_solution_complexe(self, solution: Dict[int, Dict[str, str]]) -> Dict[str, Any]:
        """
        Valide une solution complexe proposée.
        Nécessite que Watson ait utilisé la logique formelle de manière suffisante.
        """
        progression = self.verifier_progression_logique()
        
        if not progression["force_logique_formelle"]:
            return {
                "acceptee": False,
                "raison": "Solution rejetée: Watson doit utiliser au minimum 10 clauses logiques et 5 requêtes TweetyProject",
                "progression": progression
            }
        
        # Vérification de la validité
        correspondances = 0
        for pos in self.positions:
            if pos in solution and pos in self.solution_secrete:
                if solution[pos] == self.solution_secrete[pos]:
                    correspondances += 1
        
        if correspondances == 5:
            return {
                "acceptee": True,
                "message": "Solution parfaite! Énigme résolue avec méthode logique formelle.",
                "score_logique": progression
            }
        else:
            return {
                "acceptee": False,
                "raison": f"Solution incorrecte: {correspondances}/5 maisons correctes",
                "indices_supplementaires": self._generer_indices_complexes()
            }
    
    def _generer_indices_complexes(self) -> List[str]:
        """Génère des indices nécessitant une formalisation logique."""
        return [
            "Il existe exactement une maison où (couleur=Rouge AND nationalité=Anglais)",
            "Pour toute maison i, si (couleur=Verte), alors la maison i+1 a (couleur=Blanche)",
            "Il existe une unique position j telle que (position=j AND boisson=Lait AND j=3)",
            "L'adjacence est définie par |position_i - position_j| = 1"
        ]
    
    def obtenir_etat_progression(self) -> Dict[str, Any]:
        """Retourne l'état complet de progression de l'énigme."""
        return {
            "contraintes_disponibles": self.get_contraintes_complexes(),
            "clauses_watson": self.clauses_logiques,
            "requetes_executees": self.requetes_executees,
            "solution_partielle": self.solution_partielle,
            "progression_logique": self.verifier_progression_logique(),
            "etapes_restantes": max(0, 15 - len(self.clauses_logiques))
        }


class LogiqueBridgeState(BaseWorkflowState):
    """
    État pour les problèmes de traversée complexes (style Cannibales/Missionnaires)
    nécessitant une exploration d'états avec logique formelle.
    """
    
    def __init__(self, initial_context: dict = None, workflow_id: str = None):
        super().__init__(initial_context or {}, workflow_id)
        
        # Problème: 5 Cannibales et 5 Missionnaires, bateau pour 3 personnes
        self.cannibales_gauche = 5
        self.missionnaires_gauche = 5  
        self.cannibales_droite = 0
        self.missionnaires_droite = 0
        self.bateau_position = "gauche"  # "gauche" ou "droite"
        self.capacite_bateau = 3
        
        # État de recherche
        self.etats_explores = []
        self.chemin_solution = []
        self.contraintes_logiques = []
        
    def etat_valide(self, c_g: int, m_g: int, c_d: int, m_d: int) -> bool:
        """Vérifie si un état est valide (pas de débordement cannibale)."""
        if c_g < 0 or m_g < 0 or c_d < 0 or m_d < 0:
            return False
        if c_g > m_g and m_g > 0:  # Cannibales > Missionnaires côté gauche
            return False
        if c_d > m_d and m_d > 0:  # Cannibales > Missionnaires côté droit  
            return False
        return True
    
    def etat_objectif(self) -> bool:
        """Vérifie si l'état objectif est atteint."""
        return (self.cannibales_gauche == 0 and self.missionnaires_gauche == 0 and 
                self.cannibales_droite == 5 and self.missionnaires_droite == 5)
    
    def generer_actions_possibles(self) -> List[Tuple[int, int]]:
        """Génère les actions possibles selon la position du bateau."""
        actions = []
        for c in range(self.capacite_bateau + 1):
            for m in range(self.capacite_bateau + 1 - c):
                if 1 <= c + m <= self.capacite_bateau:  # Au moins 1 personne dans le bateau
                    actions.append((c, m))
        return actions