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
        Exécute une requête sur un ensemble de croyances.
        
        Args:
            belief_set: L'ensemble de croyances
            query: La requête à exécuter
            
        Returns:
            Un tuple contenant le résultat de la requête (True, False ou None si indéterminé)
            et un message formaté
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
        Exécute une liste de requêtes sur un ensemble de croyances.
        
        Args:
            belief_set: L'ensemble de croyances
            queries: La liste des requêtes à exécuter
            
        Returns:
            Une liste de tuples (requête, résultat, message formaté)
        """
        self._logger.info(f"Exécution de {len(queries)} requêtes sur un ensemble de croyances de type '{belief_set.logic_type}'")
        
        results = []
        for query in queries:
            result, message = self.execute_query(belief_set, query)
            results.append((query, result, message))
        
        return results
    
    def _execute_propositional_query(self, belief_set: BeliefSet, query: str) -> Tuple[Optional[bool], str]:
        """
        Exécute une requête de logique propositionnelle.
        
        Args:
            belief_set: L'ensemble de croyances
            query: La requête à exécuter
            
        Returns:
            Un tuple contenant le résultat de la requête (True, False ou None si indéterminé)
            et un message formaté
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
        Exécute une requête de logique du premier ordre.
        
        Args:
            belief_set: L'ensemble de croyances
            query: La requête à exécuter
            
        Returns:
            Un tuple contenant le résultat de la requête (True, False ou None si indéterminé)
            et un message formaté
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
        Exécute une requête de logique modale.
        
        Args:
            belief_set: L'ensemble de croyances
            query: La requête à exécuter
            
        Returns:
            Un tuple contenant le résultat de la requête (True, False ou None si indéterminé)
            et un message formaté
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