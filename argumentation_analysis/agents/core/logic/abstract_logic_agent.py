# argumentation_analysis/agents/core/logic/abstract_logic_agent.py
"""
Classe abstraite de base pour tous les agents logiques.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple

from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function

from .belief_set import BeliefSet

# Configuration du logger
logger = logging.getLogger("Orchestration.AbstractLogicAgent")

class AbstractLogicAgent(ABC):
    """
    Classe abstraite de base pour tous les agents logiques.
    
    Cette classe définit l'interface commune que tous les agents logiques
    doivent implémenter, indépendamment du type de logique utilisé.
    """
    
    def __init__(self, kernel: Kernel, agent_name: str):
        """
        Initialise un agent logique.
        
        Args:
            kernel: Le kernel Semantic Kernel à utiliser pour les fonctions sémantiques
            agent_name: Le nom de l'agent
        """
        self._kernel = kernel
        self._agent_name = agent_name
        self._logger = logging.getLogger(f"Orchestration.{agent_name}")
        self._logger.info(f"Initialisation de l'agent {agent_name}")
    
    @property
    def name(self) -> str:
        """Retourne le nom de l'agent."""
        return self._agent_name
    
    @property
    def kernel(self) -> Kernel:
        """Retourne le kernel associé à l'agent."""
        return self._kernel
    
    @abstractmethod
    def setup_kernel(self, llm_service) -> None:
        """
        Configure le kernel avec les plugins et fonctions nécessaires.
        
        Args:
            llm_service: Le service LLM à utiliser
        """
        pass
    
    @abstractmethod
    def text_to_belief_set(self, text: str) -> Tuple[Optional[BeliefSet], str]:
        """
        Convertit un texte en ensemble de croyances.
        
        Args:
            text: Le texte à convertir
            
        Returns:
            Un tuple contenant l'ensemble de croyances créé (ou None en cas d'erreur)
            et un message de statut
        """
        pass
    
    @abstractmethod
    def generate_queries(self, text: str, belief_set: BeliefSet) -> List[str]:
        """
        Génère des requêtes logiques pertinentes basées sur le texte et l'ensemble de croyances.
        
        Args:
            text: Le texte source
            belief_set: L'ensemble de croyances
            
        Returns:
            Une liste de requêtes logiques
        """
        pass
    
    @abstractmethod
    def execute_query(self, belief_set: BeliefSet, query: str) -> Tuple[Optional[bool], str]:
        """
        Exécute une requête logique sur un ensemble de croyances.
        
        Args:
            belief_set: L'ensemble de croyances
            query: La requête à exécuter
            
        Returns:
            Un tuple contenant le résultat de la requête (True, False ou None si indéterminé)
            et un message formaté
        """
        pass
    
    @abstractmethod
    def interpret_results(self, text: str, belief_set: BeliefSet, 
                         queries: List[str], results: List[str]) -> str:
        """
        Interprète les résultats des requêtes logiques.
        
        Args:
            text: Le texte source
            belief_set: L'ensemble de croyances
            queries: Les requêtes exécutées
            results: Les résultats des requêtes
            
        Returns:
            Une interprétation textuelle des résultats
        """
        pass
    
    def process_task(self, task_id: str, task_description: str, 
                    state_manager: Any) -> Dict[str, Any]:
        """
        Traite une tâche assignée à l'agent.
        
        Cette méthode implémente le flux de travail général pour traiter une tâche,
        en déléguant les opérations spécifiques aux méthodes abstraites.
        
        Args:
            task_id: L'identifiant de la tâche
            task_description: La description de la tâche
            state_manager: Le gestionnaire d'état pour accéder aux données partagées
            
        Returns:
            Un dictionnaire contenant les résultats du traitement
        """
        self._logger.info(f"Traitement de la tâche {task_id}: {task_description}")
        
        # Récupérer l'état actuel
        state = state_manager.get_current_state_snapshot(summarize=False)
        
        # Analyser la description de la tâche pour déterminer l'action à effectuer
        if "Traduire" in task_description and "Belief Set" in task_description:
            return self._handle_translation_task(task_id, task_description, state, state_manager)
        elif "Exécuter" in task_description and "Requêtes" in task_description:
            return self._handle_query_task(task_id, task_description, state, state_manager)
        else:
            error_msg = f"Type de tâche non reconnu: {task_description}"
            self._logger.error(error_msg)
            state_manager.add_answer(
                task_id=task_id,
                author_agent=self.name,
                answer_text=error_msg,
                source_ids=[]
            )
            return {"status": "error", "message": error_msg}
    
    def _handle_translation_task(self, task_id: str, task_description: str, 
                               state: Dict[str, Any], state_manager: Any) -> Dict[str, Any]:
        """
        Gère une tâche de traduction de texte en ensemble de croyances.
        
        Args:
            task_id: L'identifiant de la tâche
            task_description: La description de la tâche
            state: L'état actuel
            state_manager: Le gestionnaire d'état
            
        Returns:
            Un dictionnaire contenant les résultats du traitement
        """
        # Extraire le texte source depuis l'état ou la description
        raw_text = self._extract_source_text(task_description, state)
        if not raw_text:
            error_msg = "Impossible de trouver le texte source pour la traduction"
            self._logger.error(error_msg)
            state_manager.add_answer(
                task_id=task_id,
                author_agent=self.name,
                answer_text=error_msg,
                source_ids=[]
            )
            return {"status": "error", "message": error_msg}
        
        # Convertir le texte en ensemble de croyances
        belief_set, status_msg = self.text_to_belief_set(raw_text)
        if not belief_set:
            error_msg = f"Échec de la conversion en ensemble de croyances: {status_msg}"
            self._logger.error(error_msg)
            state_manager.add_answer(
                task_id=task_id,
                author_agent=self.name,
                answer_text=error_msg,
                source_ids=[]
            )
            return {"status": "error", "message": error_msg}
        
        # Ajouter l'ensemble de croyances à l'état
        bs_id = state_manager.add_belief_set(
            logic_type=belief_set.logic_type,
            content=belief_set.content
        )
        
        # Préparer et ajouter la réponse
        answer_text = f"Ensemble de croyances créé avec succès (ID: {bs_id}).\n\n{status_msg}"
        state_manager.add_answer(
            task_id=task_id,
            author_agent=self.name,
            answer_text=answer_text,
            source_ids=[bs_id]
        )
        
        return {
            "status": "success",
            "message": answer_text,
            "belief_set_id": bs_id
        }
    
    def _handle_query_task(self, task_id: str, task_description: str, 
                         state: Dict[str, Any], state_manager: Any) -> Dict[str, Any]:
        """
        Gère une tâche d'exécution de requêtes sur un ensemble de croyances.
        
        Args:
            task_id: L'identifiant de la tâche
            task_description: La description de la tâche
            state: L'état actuel
            state_manager: Le gestionnaire d'état
            
        Returns:
            Un dictionnaire contenant les résultats du traitement
        """
        # Extraire l'ID de l'ensemble de croyances depuis la description
        belief_set_id = self._extract_belief_set_id(task_description)
        if not belief_set_id:
            error_msg = "Impossible de trouver l'ID de l'ensemble de croyances dans la description de la tâche"
            self._logger.error(error_msg)
            state_manager.add_answer(
                task_id=task_id,
                author_agent=self.name,
                answer_text=error_msg,
                source_ids=[]
            )
            return {"status": "error", "message": error_msg}
        
        # Récupérer l'ensemble de croyances
        belief_sets = state.get("belief_sets", {})
        if belief_set_id not in belief_sets:
            error_msg = f"Ensemble de croyances non trouvé: {belief_set_id}"
            self._logger.error(error_msg)
            state_manager.add_answer(
                task_id=task_id,
                author_agent=self.name,
                answer_text=error_msg,
                source_ids=[]
            )
            return {"status": "error", "message": error_msg}
        
        # Créer l'objet BeliefSet approprié
        belief_set_data = belief_sets[belief_set_id]
        belief_set = self._create_belief_set_from_data(belief_set_data)
        
        # Récupérer le texte source
        raw_text = self._extract_source_text(task_description, state)
        
        # Générer les requêtes
        queries = self.generate_queries(raw_text, belief_set)
        if not queries:
            error_msg = "Aucune requête n'a pu être générée"
            self._logger.error(error_msg)
            state_manager.add_answer(
                task_id=task_id,
                author_agent=self.name,
                answer_text=error_msg,
                source_ids=[belief_set_id]
            )
            return {"status": "error", "message": error_msg}
        
        # Exécuter les requêtes
        formatted_results = []
        log_ids = []
        
        for query in queries:
            result, result_str = self.execute_query(belief_set, query)
            formatted_results.append(result_str)
            
            # Enregistrer le résultat
            log_id = state_manager.log_query_result(
                belief_set_id=belief_set_id,
                query=query,
                raw_result=result_str
            )
            log_ids.append(log_id)
        
        # Interpréter les résultats
        interpretation = self.interpret_results(
            raw_text, belief_set, queries, formatted_results
        )
        
        # Ajouter la réponse
        state_manager.add_answer(
            task_id=task_id,
            author_agent=self.name,
            answer_text=interpretation,
            source_ids=[belief_set_id] + log_ids
        )
        
        return {
            "status": "success",
            "message": interpretation,
            "queries": queries,
            "results": formatted_results,
            "log_ids": log_ids
        }
    
    def _extract_source_text(self, task_description: str, state: Dict[str, Any]) -> str:
        """
        Extrait le texte source depuis la description de la tâche ou l'état.
        
        Args:
            task_description: La description de la tâche
            state: L'état actuel
            
        Returns:
            Le texte source
        """
        # Implémentation par défaut - à surcharger si nécessaire
        # Essayer d'extraire depuis l'état
        raw_text = state.get("raw_text", "")
        
        # Si pas trouvé, essayer d'extraire depuis la description
        if not raw_text and "texte:" in task_description.lower():
            parts = task_description.split("texte:", 1)
            if len(parts) > 1:
                raw_text = parts[1].strip()
        
        return raw_text
    
    def _extract_belief_set_id(self, task_description: str) -> Optional[str]:
        """
        Extrait l'ID de l'ensemble de croyances depuis la description de la tâche.
        
        Args:
            task_description: La description de la tâche
            
        Returns:
            L'ID de l'ensemble de croyances ou None si non trouvé
        """
        # Implémentation par défaut - à surcharger si nécessaire
        if "belief_set_id:" in task_description.lower():
            parts = task_description.split("belief_set_id:", 1)
            if len(parts) > 1:
                bs_id_part = parts[1].strip()
                # Extraire l'ID (supposé être le premier mot)
                bs_id = bs_id_part.split()[0].strip()
                return bs_id
        return None
    
    @abstractmethod
    def _create_belief_set_from_data(self, belief_set_data: Dict[str, Any]) -> BeliefSet:
        """
        Crée un objet BeliefSet à partir des données de l'état.
        
        Args:
            belief_set_data: Les données de l'ensemble de croyances
            
        Returns:
            Un objet BeliefSet
        """
        pass