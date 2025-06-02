# argumentation_analysis/agents/core/logic/query_executor.py
"""
Exécuteur de requêtes logiques.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple

from .belief_set import BeliefSet
from .tweety_bridge import TweetyBridge

# Configuration du logger
logger = logging.getLogger("Orchestration.QueryExecutor")

class QueryExecutor:
    """
    Exécuteur de requêtes logiques.
    
    Cette classe fournit une interface unifiée pour exécuter des requêtes
    sur différents types d'ensembles de croyances.
    """
    
    def __init__(self):
        """
        Initialise l'exécuteur de requêtes.
        """
        self._logger = logger
        self._tweety_bridge = TweetyBridge()
    
    def execute_query(self, belief_set: BeliefSet, query: str) -> Tuple[Optional[bool], str]:
        """
        Exécute une requête logique sur un ensemble de croyances donné.

        Route l'exécution vers la méthode appropriée (`_execute_propositional_query`,
        `_execute_first_order_query`, ou `_execute_modal_query`) en fonction
        du `belief_set.logic_type`.

        :param belief_set: L'objet `BeliefSet` sur lequel exécuter la requête.
        :type belief_set: BeliefSet
        :param query: La requête logique (chaîne de caractères) à exécuter.
        :type query: str
        :return: Un tuple contenant:
                 - Le résultat booléen de la requête (True, False, ou None si indéterminé
                   ou si une erreur survient).
                 - Un message formaté (str) décrivant le résultat ou l'erreur.
        :rtype: Tuple[Optional[bool], str]
        """
        self._logger.info(f"Exécution de la requête '{query}' sur un ensemble de croyances de type '{belief_set.logic_type}'")
        
        # Vérifier si la JVM est prête
        if not self._tweety_bridge.is_jvm_ready():
            error_msg = "JVM non prête ou composants Tweety non chargés"
            self._logger.error(error_msg)
            return None, f"FUNC_ERROR: {error_msg}"
        
        # Exécuter la requête en fonction du type de logique
        if belief_set.logic_type == "propositional":
            return self._execute_propositional_query(belief_set, query)
        elif belief_set.logic_type == "first_order":
            return self._execute_first_order_query(belief_set, query)
        elif belief_set.logic_type == "modal":
            return self._execute_modal_query(belief_set, query)
        else:
            error_msg = f"Type de logique non supporté: {belief_set.logic_type}"
            self._logger.error(error_msg)
            return None, f"FUNC_ERROR: {error_msg}"
    
    def execute_queries(self, belief_set: BeliefSet, queries: List[str]) -> List[Tuple[str, Optional[bool], str]]:
        """
        Exécute une liste de requêtes logiques sur un ensemble de croyances.

        Appelle `execute_query` pour chaque requête dans la liste.

        :param belief_set: L'objet `BeliefSet` sur lequel exécuter les requêtes.
        :type belief_set: BeliefSet
        :param queries: Une liste de requêtes logiques (chaînes de caractères).
        :type queries: List[str]
        :return: Une liste de tuples. Chaque tuple contient la requête originale (str),
                 son résultat booléen (Optional[bool]), et le message formaté (str).
        :rtype: List[Tuple[str, Optional[bool], str]]
        """
        self._logger.info(f"Exécution de {len(queries)} requêtes sur un ensemble de croyances de type '{belief_set.logic_type}'")
        
        results = []
        for query in queries:
            result, message = self.execute_query(belief_set, query)
            results.append((query, result, message))
        
        return results
    
    def _execute_propositional_query(self, belief_set: BeliefSet, query: str) -> Tuple[Optional[bool], str]:
        """
        Exécute une requête de logique propositionnelle via `TweetyBridge`.

        Valide d'abord la formule, puis l'exécute et parse le résultat.

        :param belief_set: L'ensemble de croyances propositionnelles.
        :type belief_set: BeliefSet
        :param query: La requête en logique propositionnelle.
        :type query: str
        :return: Tuple (résultat booléen, message formaté).
        :rtype: Tuple[Optional[bool], str]
        """
        try:
            # Valider la requête
            is_valid, validation_msg = self._tweety_bridge.validate_formula(query)
            if not is_valid:
                self._logger.error(f"Requête propositionnelle invalide: {validation_msg}")
                return None, f"FUNC_ERROR: Requête invalide: {validation_msg}"
            
            # Exécuter la requête
            result_str = self._tweety_bridge.execute_pl_query(belief_set.content, query)
            
            # Analyser le résultat
            if "FUNC_ERROR" in result_str:
                self._logger.error(f"Erreur lors de l'exécution de la requête propositionnelle: {result_str}")
                return None, result_str
            
            if "ACCEPTED" in result_str:
                return True, result_str
            elif "REJECTED" in result_str:
                return False, result_str
            else:
                return None, result_str
        
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête propositionnelle: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            return None, f"FUNC_ERROR: {error_msg}"
    
    def _execute_first_order_query(self, belief_set: BeliefSet, query: str) -> Tuple[Optional[bool], str]:
        """
        Exécute une requête de logique du premier ordre (FOL) via `TweetyBridge`.

        Valide d'abord la formule FOL, puis l'exécute et parse le résultat.

        :param belief_set: L'ensemble de croyances en logique du premier ordre.
        :type belief_set: BeliefSet
        :param query: La requête en logique du premier ordre.
        :type query: str
        :return: Tuple (résultat booléen, message formaté).
        :rtype: Tuple[Optional[bool], str]
        """
        try:
            # Valider la requête
            is_valid, validation_msg = self._tweety_bridge.validate_fol_formula(query)
            if not is_valid:
                self._logger.error(f"Requête du premier ordre invalide: {validation_msg}")
                return None, f"FUNC_ERROR: Requête invalide: {validation_msg}"
            
            # Exécuter la requête
            result_str = self._tweety_bridge.execute_fol_query(belief_set.content, query)
            
            # Analyser le résultat
            if "FUNC_ERROR" in result_str:
                self._logger.error(f"Erreur lors de l'exécution de la requête du premier ordre: {result_str}")
                return None, result_str
            
            if "ACCEPTED" in result_str:
                return True, result_str
            elif "REJECTED" in result_str:
                return False, result_str
            else:
                return None, result_str
        
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête du premier ordre: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            return None, f"FUNC_ERROR: {error_msg}"
    
    def _execute_modal_query(self, belief_set: BeliefSet, query: str) -> Tuple[Optional[bool], str]:
        """
        Exécute une requête de logique modale via `TweetyBridge`.

        Valide d'abord la formule modale, puis l'exécute et parse le résultat.

        :param belief_set: L'ensemble de croyances en logique modale.
        :type belief_set: BeliefSet
        :param query: La requête en logique modale.
        :type query: str
        :return: Tuple (résultat booléen, message formaté).
        :rtype: Tuple[Optional[bool], str]
        """
        try:
            # Valider la requête
            is_valid, validation_msg = self._tweety_bridge.validate_modal_formula(query)
            if not is_valid:
                self._logger.error(f"Requête modale invalide: {validation_msg}")
                return None, f"FUNC_ERROR: Requête invalide: {validation_msg}"
            
            # Exécuter la requête
            result_str = self._tweety_bridge.execute_modal_query(belief_set.content, query)
            
            # Analyser le résultat
            if "FUNC_ERROR" in result_str:
                self._logger.error(f"Erreur lors de l'exécution de la requête modale: {result_str}")
                return None, result_str
            
            if "ACCEPTED" in result_str:
                return True, result_str
            elif "REJECTED" in result_str:
                return False, result_str
            else:
                return None, result_str
        
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête modale: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            return None, f"FUNC_ERROR: {error_msg}"