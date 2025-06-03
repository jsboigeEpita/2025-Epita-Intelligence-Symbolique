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
        Initialise un agent logique abstrait.

        :param kernel: Le kernel Semantic Kernel à utiliser pour les fonctions sémantiques.
        :type kernel: Kernel
        :param agent_name: Le nom de cet agent.
        :type agent_name: str
        """
        self._kernel = kernel
        self._agent_name = agent_name
        self._logger = logging.getLogger(f"Orchestration.{agent_name}")
        self._logger.info(f"Initialisation de l'agent {agent_name}")
    
    @property
    def name(self) -> str:
        """Retourne le nom de l'agent.

        :return: Le nom de l'agent.
        :rtype: str
        """
        return self._agent_name
    
    @property
    def kernel(self) -> Kernel:
        """Retourne le kernel Semantic Kernel associé à cet agent.

        :return: L'instance du kernel.
        :rtype: Kernel
        """
        return self._kernel
    
    @abstractmethod
    def setup_kernel(self, llm_service) -> None:
        """
        Configure le kernel Semantic Kernel avec les plugins natifs et les fonctions
        sémantiques spécifiques à cet agent logique.

        Cette méthode doit être implémentée par les classes dérivées.

        :param llm_service: L'instance du service LLM à utiliser pour configurer
                            les fonctions sémantiques.
        :type llm_service: Any
        :return: None
        :rtype: None
        """
        pass
    
    @abstractmethod
    def text_to_belief_set(self, text: str) -> Tuple[Optional[BeliefSet], str]:
        """
        Convertit un texte donné en un ensemble de croyances logiques formelles.

        Cette méthode doit être implémentée par les classes dérivées pour gérer
        la logique de conversion spécifique au type de logique de l'agent.

        :param text: Le texte en langage naturel à convertir.
        :type text: str
        :return: Un tuple contenant:
                 - L'objet `BeliefSet` créé (ou None si la conversion échoue).
                 - Un message de statut (str) décrivant le résultat de l'opération.
        :rtype: Tuple[Optional[BeliefSet], str]
        """
        pass
    
    @abstractmethod
    def generate_queries(self, text: str, belief_set: BeliefSet) -> List[str]:
        """
        Génère une liste de requêtes logiques pertinentes à partir d'un texte source
        et d'un ensemble de croyances existant.

        Cette méthode doit être implémentée par les classes dérivées.

        :param text: Le texte source original.
        :type text: str
        :param belief_set: L'ensemble de croyances dérivé du texte.
        :type belief_set: BeliefSet
        :return: Une liste de chaînes de caractères, chaque chaîne étant une requête logique.
        :rtype: List[str]
        """
        pass
    
    @abstractmethod
    def execute_query(self, belief_set: BeliefSet, query: str) -> Tuple[Optional[bool], str]:
        """
        Exécute une requête logique donnée sur un ensemble de croyances.

        Cette méthode doit être implémentée par les classes dérivées pour interagir
        avec le moteur logique spécifique.

        :param belief_set: L'ensemble de croyances sur lequel exécuter la requête.
        :type belief_set: BeliefSet
        :param query: La requête logique à exécuter.
        :type query: str
        :return: Un tuple contenant:
                 - Le résultat booléen de la requête (True, False, ou None si indéterminé).
                 - Une chaîne de caractères formatée représentant le résultat.
        :rtype: Tuple[Optional[bool], str]
        """
        pass
    
    @abstractmethod
    def interpret_results(self, text: str, belief_set: BeliefSet, 
                         queries: List[str], results: List[str]) -> str:
        """
        Interprète les résultats d'une série de requêtes logiques par rapport
        au texte source original et à l'ensemble de croyances.

        Cette méthode doit être implémentée par les classes dérivées pour fournir
        une explication en langage naturel des implications des résultats logiques.

        :param text: Le texte source original.
        :type text: str
        :param belief_set: L'ensemble de croyances utilisé.
        :type belief_set: BeliefSet
        :param queries: La liste des requêtes qui ont été exécutées.
        :type queries: List[str]
        :param results: La liste des résultats formatés correspondants aux requêtes.
        :type results: List[str]
        :return: Une chaîne de caractères fournissant une interprétation en langage naturel
                 des résultats.
        :rtype: str
        """
        pass
    
    def process_task(self, task_id: str, task_description: str, 
                    state_manager: Any) -> Dict[str, Any]:
        """
        Traite une tâche assignée à l'agent logique.

        Cette méthode implémente le flux de travail général pour traiter une tâche,
        en analysant la `task_description` pour router vers des handlers spécifiques
        comme `_handle_translation_task` ou `_handle_query_task`.

        :param task_id: L'identifiant unique de la tâche.
        :type task_id: str
        :param task_description: La description en langage naturel de la tâche à effectuer.
        :type task_description: str
        :param state_manager: L'instance du gestionnaire d'état pour lire et écrire
                              les données partagées (par exemple, `raw_text`, `belief_sets`).
        :type state_manager: Any
        :return: Un dictionnaire contenant le statut ("success" ou "error") et un message
                 résumant le résultat du traitement de la tâche.
        :rtype: Dict[str, Any]
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
        Gère une tâche spécifique de conversion de texte en un ensemble de croyances logiques.

        Extrait le texte source, le convertit en utilisant `self.text_to_belief_set`,
        enregistre le nouvel ensemble de croyances via le `state_manager`, et
        rapporte le résultat.

        :param task_id: L'identifiant de la tâche.
        :type task_id: str
        :param task_description: La description de la tâche.
        :type task_description: str
        :param state: L'état actuel (snapshot) des données partagées.
        :type state: Dict[str, Any]
        :param state_manager: Le gestionnaire d'état.
        :type state_manager: Any
        :return: Un dictionnaire de résultat avec statut, message, et ID de l'ensemble de croyances.
        :rtype: Dict[str, Any]
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
        Gère une tâche d'exécution de requêtes logiques sur un ensemble de croyances existant.

        Extrait l'ID de l'ensemble de croyances, génère des requêtes pertinentes,
        exécute ces requêtes, interprète les résultats, et enregistre les réponses
        via le `state_manager`.

        :param task_id: L'identifiant de la tâche.
        :type task_id: str
        :param task_description: La description de la tâche.
        :type task_description: str
        :param state: L'état actuel (snapshot) des données partagées.
        :type state: Dict[str, Any]
        :param state_manager: Le gestionnaire d'état.
        :type state_manager: Any
        :return: Un dictionnaire de résultat avec statut, message, requêtes, résultats, et IDs de log.
        :rtype: Dict[str, Any]
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
        Extrait le texte source pertinent pour une tâche, soit à partir de la description
        de la tâche (si elle contient "texte:"), soit à partir du champ "raw_text"
        de l'état partagé.

        :param task_description: La description de la tâche.
        :type task_description: str
        :param state: L'état actuel (snapshot) des données partagées.
        :type state: Dict[str, Any]
        :return: Le texte source extrait, ou une chaîne vide si non trouvé.
        :rtype: str
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
        Extrait un ID d'ensemble de croyances à partir de la description d'une tâche.

        Recherche un motif comme "belief_set_id: [ID]".

        :param task_description: La description de la tâche.
        :type task_description: str
        :return: L'ID de l'ensemble de croyances extrait, ou None s'il n'est pas trouvé.
        :rtype: Optional[str]
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
        Crée une instance de `BeliefSet` à partir d'un dictionnaire de données.

        Cette méthode doit être implémentée par les classes dérivées pour instancier
        le type correct de `BeliefSet` (par exemple, `PropositionalBeliefSet`).

        :param belief_set_data: Un dictionnaire contenant les données nécessaires
                                pour initialiser un `BeliefSet` (typiquement
                                "logic_type" et "content").
        :type belief_set_data: Dict[str, Any]
        :return: Une instance de `BeliefSet` (ou une sous-classe).
        :rtype: BeliefSet
        """
        pass