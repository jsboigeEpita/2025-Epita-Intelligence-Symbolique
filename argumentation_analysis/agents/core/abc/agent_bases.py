"""
Fournit les fondations architecturales pour tous les agents du système.

Ce module contient les classes de base abstraites (ABC) qui définissent les contrats et les interfaces pour tous les agents. Il a pour rôle de standardiser le comportement des agents, qu'ils soient basés sur des LLMs, de la logique formelle ou d'autres mécanismes.        

- `BaseAgent` : Le contrat fondamental pour tout agent, incluant la gestion d'un kernel Semantic Kernel, un cycle d'invocation et des mécanismes de description de capacités.
- `BaseLogicAgent` : Une spécialisation pour les agents qui interagissent avec des systèmes de raisonnement logique formel, ajoutant des abstractions pour la manipulation de croyances et l'exécution de requêtes.  

# Note historique : 
 BaseAgent a précédemment hérité de semantic_kernel.agents.Agent,      
# puis de semantic_kernel.agents.chat_completion.ChatCompletionAgent. 
# Cet héritage avait été supprimé (voir commit e9668f26d) mais a été RÉINTRODUIT 
# pour résoudre ValidationError Pydantic dans AgentGroupChat (Mission D3.2).    
# L'héritage ChatCompletionAgent est REQUIS pour compatibilité AgentGroupChat.  
from __future__ import annotations      

from abc import ABC, abstractmethod     
from typing import Dict, Any, Optional, Tuple, List, TYPE_CHECKING, Coroutine   
import logging      

from semantic_kernel import Kernel      
from semantic_kernel.agents.chat_completion import ChatCompletionAgent        
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClienttBase      
from pydantic import PrivateAttr        

# Note historique : 
# from semantic_kernel.agents import Agent      
# puis de semantic_kernel.agents.chat_completion.ChatCompletionAgent. 
# Cet héritage avait été supprimé (voir commit e9668f26d) mais a été RÉINTRODUIT 
# pour résoudre ValidationError Pydantic dans AgentGroupChat (Mission D3.2).    
# L'héritage ChatCompletionAgent est REQUIS pour compatibilité AgentGroupChat.  
from semantic_kernel.contents import ChatHistory  

# from semantic_kernel.agents.channels.chat_history_channel import ChatHistoryChannel # Commenté, module/classe potentiellement déplacé/supprimé      
# from semantic_kernel.agents.chat_completion.chat_completion_agent import ChatHistoryAgent # Commenté, module/classe potentiellement déplacé/supprimé    

# Imports passifs pour éviter le cycle d'import - uniquement pour le typage    
if TYPE_CHECKING:   
    from argumentation_analysis.agents.core.logic.belief_set import BeliefSet   
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge       

    # Si ChatHistoryChannel était utilisé dans le typage, il faudrait aussi le gérer ici. 
    # Pour l'instant, il n'est pas explicitement typé dans les signatures de BaseAgent.    

# Résoudre la dépendance circulaire de Pydantic   
# ChatHistoryChannel.model_rebuild() # Commenté car ChatHistoryChannel est commenté    

# Import paresseux pour éviter le cycle d'import - uniquement pour le typage    
if TYPE_CHECKING:   
    from argumentation_analysis.agents.core.logic.belief_set import BeliefSet   
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge       

    # Si ChatHistoryChannel était utilisé dans le typage, il faudrait aussi le gérer ici. 
    # Pour l'instant, il n'est pas explicitement typé dans les signatures de BaseAgent.    

# Résoudre la dépendance circulaire de Pydantic   
# ChatHistoryChannel.model_rebuild() # Commenté car ChatHistoryChannel est commenté    


class BaseAgent(ChatCompletionAgent, ABC):        
    """Classe de base abstraite (ABC) pour tous les agents du système.
    Cette classe établit un contrat que tous les agents doivent suivre. Elle définit l'interface commune pour l'initialisation, la configuration,
    la description des capacités et le cycle d'invocation. Chaque agent doit être associé à un `Kernel` de Semantic Kernel.

    Le contrat impose aux classes dérivées d'implémenter des méthodes clés pour la configuration n (`setup_agent_components`) et t l'exécution        
    de leur logique métier (`invoke_single`).     

    Attributes:        
        kernel (Kernel): Le kernel Semantic Kernel utilisé par l'agent.
        id (str): L'identifiant unique de l'agent.
        name (str): Le nom de l'agent, alias de `id`.       
        instructions (Optional[str]): Le prompt système ou les instructions          
          de haut niveau pour l'agent.       
        description (Optional[str]): Une description textuelle du rôle et       
          des capacités de l'agent.   
        logger (logging.Logger): Une instance de logger pour l'agent.   

    Note: Le typage est partiellement appliqué pour éviter les dépendances circulaires.    
    # Les types sont documentés dans les docstrings et les properties.      
    # _tweety_bridge: TweetyBridge      
    # _logic_type_name: str      
    # _syntax_bnf: Optional[str]        
    # _parser: Any        
    # _solver: Any        
    # Ces éléments seront gérés par TweetyBridge        
    """     

    def __init__(        
        self,       
        kernel: "Kernel",     
        agent_name: str,      
        logic_type_name: str, 
        system_prompt: Optional[str] = None,      
        **kwargs,   
    ):        
        """        
        Initialise une instance de BaseAgent.

        Args:            
          kernel (Kernel): Le kernel Semantic Kernel à utiliser.    
          agent_name (str): Le nom de l'agent.  
          logic_type_name (str): Le nom du type de logique (ex: "PL", "FOL"). 
          system_prompt (Optional[str]): Le prompt système optionnel.
        """        
        super().__init__(kernel=kernel, agent_name=agent_name, system_prompt=system_prompt, **kwargs)        
        self._logic_type_name = logic_type_name        
        self._tweety_bridge = None  # Initialisation explicite à None        
        self._syntax_bnf = None  # Pourrait être chargé par le bridge ou la sous-classe        
        self._parser = None  # Ces éléments seront gérés par TweetyBridge        
        self._solver = None  # Ces éléments seront gérés par TweetyBridge        

    @property        
    def logic_type(self) -> str:        
        """        
        Retourne le nom du type de logique géré par l'agent.

        :return: Le nom du type de logique (ex: "PPL", "FOL").
        :rtype: str 
        """        
        return self._logic_type_name        

    @property        
    def tweety_bridge(self) -> "TweetyBridge":        
        """        
        Retourne l'instance de `TweetyBridge` associée à cet agent.

        L'instance de `TweetyBridge` est typiquement initialisée lors de l'appel        
        à `setup_agent_components` par la classe concrète.  

        :return: L'instance de `TweetyBridge`.    
        :rtype: TweetyBridge  
        :raises RuntimeError: Si `TweetyBridge` n'a pas été initialisé.
        """        
        if not hasattr(self, "_tweety_bridge") or self._tweety_bridge is None:  
          
          # Cela suppose que setup_agent_components a été appelé et a initialisé le bridge.        
          
          # Une meilleure approche pourrait être d'injecter TweetyBridge au constructeur        
          # ou d'avoir une méthode dédiée pour son initialisation si elle est complexe.        
          
          raise RuntimeError(          
            "TweetyBridge not initialized. Call setup_agent_components or ensure it's injected."          
          )        
        return self._tweety_bridge        

    @abstractmethod        
    def setup_agent_components(self, llm_service_id: Optional[str] = None) -> None:        
        """        
        Configure les composants spécifiques de l'agent, comme les fonctions sémantiques.

        Cette méthode peut être surchargée par les classes filles pour des configurations        
        plus complexes. Par défaut, elle s'assure que l'ID du service LLM est défini.     

        Args:            
          llm_service_id (Optional[str]): L'ID du service LLM à utiliser.        
        """        
        if llm_service_id:            
            self._llm_service_id = llm_service_id            
            self.logger.info(            
              f"Composants de l'agent configurés pour utiliser le service LLM: {llm_service_id}"            
            )        
        else:            
            self.logger.info(            
              "Aucun service LLM spécifique fourni pour la configuration des composants."            
            )        

    @abstractmethod        
    def text_to_belief_set(        
        self, text: str, context: Optional[Dict[str, Any]] = None        
    ) -> Tuple[Optional["BeliefSet"], str]:        
        """        
        Convertit un texte en langage naturel en un ensemble de croyances formelles.      

        Args:            
          text (str): Le texte à convertir.     
          context (Optional[Dict[str, Any]]): Contexte additionnel pour        
            guider la conversion.   

        Returns:            
          Tuple[Optional['BeliefSet'], str]: Un tuple contenant l'objet        
          `BeliefSet` créé (ou None en cas d'échec) et un message de statut.  
        """        
        pass        

    @abstractmethod        
    def generate_queries(        
        self, text: str, belief_set: "BeliefSet", context: Optional[Dict[str, Any]] = None        
    ) -> List[str]:        
        """        
        Génère des requêtes logiques pertinentes à partir d'un texte et/ou d'un ensemble de croyances.        

        Args:            
          text (str): Le texte source pour inspirer les requêtes.   
          belief_set ("BeliefSet"): L'ensemble de croyances sur lequel        
            les requêtes seront basées. 
          context (Optional[Dict[str, Any]]): Contexte additionnel pour        
            guider la conversion.   

        Returns:            
          List[str]: Une liste de requêtes logiques sous forme de chaînes.    
        """        
        pass        

    @abstractmethod        
    def execute_query(        
        self, belief_set: "BeliefSet", query: str        
    ) -> Tuple[Optional[bool], str]:        
        """        
        Exécute une requête logique sur un ensemble de croyances.     

        Args:            
          belief_set ("BeliefSet"): La base de connaissances sur laquelle la requête est exécutée.   
          query (str): La requête logique à exécuter.     

        Returns:            
          Tuple[Optional[bool], str]: Un tuple avec le résultat (True, False, ou None si indéterminé) et un message de statut du solveur.    
        """        
        pass        

    @abstractmethod        
    def interpret_results(        
        self, text: str, belief_set: "BeliefSet", queries: List[str], results: List[Tuple[Optional[bool], str]], context: Optional[Dict[str, Any]] = None        
    ) -> str:        
        """        
        Interprète les résultats des requêtes logiques en langage naturel.      

        Args:            
          text (str): Le texte source original. 
          belief_set ("BeliefSet"): L'ensemble de croyances utilisé.  
          queries (List[str]): La liste des requêtes qui ont été exécutées.   
          results (List[Tuple[Optional[bool], str]]): La liste des résultats        
            correspondant aux requêtes.       
          context (Optional[Dict[str, Any]]): Contexte additionnel.   

        Returns:            
          str: Une synthèse en langage naturel des résultats logiques.        
        """        
        pass        

    # @abstractmethod # Remplacé par l'utilisation directe du bridge  
    # def validate_formula(self, formula: str) -> bool:        
    #     """        
    #     Valide la syntaxe d'une formule logique.  

    #     Args:            
    #       formula (str): La formule à valider.  

    #     Returns:            
    #       bool: True si la syntaxe de la formule est correcte, False sinon.   
    #     """        
    #     pass        

    # @abstractmethod # Remplacé par l'utilisation directe du bridge  
    # def is_consistent(self, belief_set: "BeliefSet") -> Tuple[bool, str]:        
    #     """        
    #     Vérifie si un ensemble de croyances est logiquement cohérent. 

    #     Args:            
    #       belief_set ("BeliefSet"): L'ensemble de croyances à vérifier.

    #     Returns:            
    #       Tuple[bool, str]: Un tuple contenant un booléen (True si cohérent) et un message de statut du solveur.   
    #     """        
    #     pass        

    async def process_task(        
        self, task_id: str, task_description: str, state_manager: Any        
    ) -> Dict[str, Any]:        
        """        
        Traite une tâche assignée à l'agent logique.        
        Migré depuis AbstractLogicAgent pour unifier l'architecture.        
        """        
        self.logger.info(f"Traitement de la tâche {task_id}: {task_description}")        
        state = state_manager.get_current_state_snapshot(summarize=False)        
        if "Traduire" in task_description and "Belief Set" in task_description:            
            return await self._handle_translation_task(            
              task_id, task_description, state, state_manager            
            )        
        elif "Exécuter" in task_description and "Requêtes" in task_description:            
            return await self._handle_query_task(            
              task_id, task_description, state, state_manager            
            )        
        else:            
            error_msg = f"Type de tâche non reconnu: {task_description}"            
            self.logger.error(error_msg)            
            state_manager.add_answer(            
              task_id=task_id,                
              author_agent=self.name,                
              answer_text=error_msg,                
              source_ids=[],            
            )            
            return {"status": "error", "message": error_msg}        

    async def _handle_translation_task(        
        self, task_id: str, task_description: str, state: Dict[str, Any], state_manager: Any        
    ) -> Dict[str, Any]:        
        """        
        Génère une tâche spécifique de conversion de texte en un ensemble de croyances logiques.        
        """        
        raw_text = self._extract_source_text(task_description, state)        
        if not raw_text:            
            error_msg = "Impossible de trouver le texte source pour la traduction"            
            self.logger.error(error_msg)            
            state_manager.add_answer(            
              task_id=task_id,                
              author_agent=self.name,                
              answer_text=error_msg,                
              source_ids=[],            
            )            
            return {"status": "error", "message": error_msg}        

        belief_set, status_msg = await self.text_to_belief_set(raw_text)        
        if not belief_set:            
            error_msg = f"Échec de la conversion en ensemble de croyances: {status_msg}"            
            self.logger.error(error_msg)            
            state_manager.add_answer(            
              task_id=task_id,                
              author_agent=self.name,                
              answer_text=error_msg,                
              source_ids=[],            
            )            
            return {"status": "error", "message": error_msg}        

        bs_id = state_manager.add_belief_set(            
          logic_type=belief_set.logic_type, content=belief_set.content            
        )        
        answer_text = (            
          f"Ensemble de croyances créé avec succès (ID: {bs_id}).\n\n{status_msg}"            
        )        
        state_manager.add_answer(            
          task_id=task_id,                
          author_agent=self.name,                
          answer_text=answer_text,                
          source_ids=[bs_id],            
        )        
        return {"status": "success", "message": answer_text, "belief_set_id": bs_id}        

    async def _handle_query_task(        
        self, task_id: str, task_description: str, state: Dict[str, Any], state_manager: Any        
    ) -> Dict[str, Any]:        
        """        
        Génère une tâche d'exécution de requêtes logiques sur un ensemble de croyances existant.        
        """        
        belief_set_id = self._extract_belief_set_id(task_description)        
        if not belief_set_id:            
            error_msg = "Impossible de trouver l'ID de l'ensemble de croyances dans la description de la tâche"            
            self.logger.error(error_msg)            
            state_manager.add_answer(            
              task_id=task_id,                
              author_agent=self.name,                
              answer_text=error_msg,                
              source_ids=[],            
            )            
            return {"status": "error", "message": error_msg}        

        belief_sets = state.get("belief_sets", {})        
        if belief_set_id not in belief_sets:            
            error_msg = f"Ensemble de croyances non trouvé: {belief_set_id}"            
            self.logger.error(error_msg)            
            state_manager.add_answer(            
              task_id=task_id,                
              author_agent=self.name,                
              answer_text=error_msg,                
              source_ids=[],            
            )            
            return {"status": "error", "message": error_msg}        

        belief_set_data = belief_sets[belief_set_id]        
        belief_set = self._create_belief_set_from_data(belief_set_data)        
        raw_text = self._extract_source_text(task_description, state)        
        queries = await self.generate_queries(raw_text, belief_set)        
        if not queries:            
            error_msg = "Aucune requête n'a pu être générée"            
            self.logger.error(error_msg)            
            state_manager.add_answer(            
              task_id=task_id,                
              author_agent=self.name,                
              answer_text=error_msg,                
              source_ids=[],            
            )            
            return {"status": "error", "message": error_msg}        

        formatted_results = []        
        log_ids = []        
        raw_results = []        
        for query in queries:            
            result, result_str = self.execute_query(belief_set, query)            
            raw_results.append((result, result_str))        
            formatted_results.append(result_str)        
            log_id = state_manager.log_query_result(            
              belief_set_id=belief_set_id, query=query, raw_result=result_str            
            )        
            log_ids.append(log_id)        

        interpretation = self.interpret_results(            
          raw_text, belief_set, queries, raw_results            
        )        
        state_manager.add_answer(            
          task_id=task_id,                
          author_agent=self.name,                
          answer_text=interpretation,                
          source_ids=[belief_set_id] + log_ids,            
        )        
        return {            
          "status": "successs",                
          "message": interpretation,                
          "queries": queries,                
          "results": formatted_results,                
          "log_ids": log_ids,            
        }        

    def _extract_source_text(self, task_description: str, state: Dict[str, Any]) -> str:        
        """        
        Extrait le texte source pertinent pour une tâche.        
        """        
        raw_text = state.get("raw_text", "")        
        if not raw_text and "texte:" in task_description.lower():            
            parts = task_description.split("texte:", 1)            
            if len(parts) > 1:                
              raw_text = parts[1].strip()        
        return raw_text        

    def _extract_belief_set_id(self, task_description: str) -> Optional[str]:        
        """        
        Extrait un ID d'ensemble de croyances à partir de la description d'une tâche.        
        """        
        if "belief_set_id:" in task_description.lower():            
            parts = task_description.split("belief_set_id:", 1)            
            if len(parts) > 1:                
              bs_id_part = parts[1].strip()                
              bs_id = bs_id_part.split()[0].strip()                
              return bs_id        
        return None        

    @abstractmethod        
    def _create_belief_set_from_data(self, belief_set_data: Dict[str, Any]) -> "BeliefSet":        
        """        
        Crée une instance de `BeliefSet` à partir d'un dictionnaire de données.        
        """        
        pass        


class BaseLogicAgent(BaseAgent, ABC):        
    """Classe de base abstraite pour les agents basés sur la logique formelle.

    Cette classe étend BaseAgent avec des fonctionnalités spécifiques pour les agents
    qui interagissent avec des systèmes de raisonnement logique formel, ajoutant des abstractions
    pour la manipulation de croyances et l'exécution de requêtes.

    Attributes:
        _tweety_bridge (TweetyBridge): Le pont vers le système de raisonnement Tweety.
        _logic_type_name (str): Le nom du type de logique géré par l'agent.
        _syntax_bnf (Optional[str]): La syntaxe BNF pour le parser.
        _parser (Any): Le parser pour le langage logique.
        _solver (Any): Le solveur pour le langage logique.
    """     

    def __init__(        
        self,       
        kernel: "Kernel",     
        agent_name: str,      
        logic_type_name: str, 
        system_prompt: Optional[str] = None,      
        **kwargs,   
    ):        
        """        
        Initialise une instance de BaseLogicAgent.

        Args:            
          kernel (Kernel): Le kernel Semantic Kernel à utiliser.    
          agent_name (str): Le nom de l'agent.  
          logic_type_name (str): Le nom du type de logique (ex: "PL", "FOL"). 
          system_prompt (Optional[str]): Le prompt système optionnel.
        """        
        super().__init__(kernel=kernel, agent_name=agent_name, system_prompt=system_prompt, **kwargs)        
        self._logic_type_name = logic_type_name        
        self._tweety_bridge = None  # Initialisation explicite à None        
        self._syntax_bnf = None  # Pourrait être chargé par le bridge ou la sous-classe        
        self._parser = None  # Ces éléments seront gérés par TweetyBridge        
        self._solver = None  # Ces éléments seront gérés par TweetyBridge        

    @property        
    def logic_type(self) -> str:        
        """        
        Retourne le nom du type de logique géré par l'agent.

        :return: Le nom du type de logique (ex: "PPL", "FOL").
        :rtype: str 
        """        
        return self._logic_type_name        

    @property        
    def tweety_bridge(self) -> "TweetyBridge":        
        """        
        Retourne l'instance de `TweetyBridge` associée à cet agent.

        L'instance de `TweetyBridge` est typiquement initialisée lors de l'appel        
        à `setup_agent_components` par la classe concrète.  

        :return: L'instance de `TweetyBridge`.    
        :rtype: TweetyBridge  
        :raises RuntimeError: Si `TweetyBridge` n'a pas été initialisé.
        """        
        if not hasattr(self, "_tweety_bridge") or self._tweety_bridge is None:  
          
          # Cela suppose que setup_agent_components a été appelé et a initialisé le bridge.        
          
          # Une meilleure approche pourrait être d'injecter TweetyBridge au constructeur        
          # ou d'avoir une méthode dédiée pour son initialisation si elle est complexe.        
          
          raise RuntimeError(          
            "TweetyBridge not initialized. Call setup_agent_components or ensure it's injected."          
          )        
        return self._tweety_bridge        

    @abstractmethod        
    def setup_agent_components(self, llm_service_id: Optional[str] = None) -> None:        
        """        
        Configure les composants spécifiques de l'agent, comme les fonctions sémantiques.

        Cette méthode peut être surchargée par les classes filles pour des configurations        
        plus complexes. Par défaut, elle s'assure que l'ID du service LLM est défini.     

        Args:            
          llm_service_id (Optional[str]): L'ID du service LLM à utiliser.        
        """        
        if llm_service_id:            
            self._llm_service_id = llm_service_id            
            self.logger.info(            
              f"Composants de l'agent configurés pour utiliser le service LLM: {llm_service_id}"            
            )        
        else:            
            self.logger.info(            
              "Aucun service LLM spécifique fourni pour la configuration des composants."            
            )        

    @abstractmethod        
    def text_to_belief_set(        
        self, text: str, context: Optional[Dict[str, Any]] = None        
    ) -> Tuple[Optional["BeliefSet"], str]:        
        """        
        Convertit un texte en langage naturel en un ensemble de croyances formelles.      

        Args:            
          text (str): Le texte à convertir.     
          context (Optional[Dict[str, Any]]): Contexte additionnel pour        
            guider la conversion.   

        Returns:            
          Tuple[Optional['BeliefSet'], str]: Un tuple contenant l'objet        
          `BeliefSet` créé (ou None en cas d'échec) et un message de statut.  
        """        
        pass        

    @abstractmethod        
    def generate_queries(        
        self, text: str, belief_set: "BeliefSet", context: Optional[Dict[str, Any]] = None        
    ) -> List[str]:        
        """        
        Génère des requêtes logiques pertinentes à partir d'un texte et/ou d'un ensemble de croyances.        

        Args:            
          text (str): Le texte source pour inspirer les requêtes.   
          belief_set ("BeliefSet"): L'ensemble de croyances sur lequel        
            les requêtes seront basées. 
          context (Optional[Dict[str, Any]]): Contexte additionnel pour        
            guider la conversion.   

        Returns:            
          List[str]: Une liste de requêtes logiques sous forme de chaînes.    
        """        
        pass        

    @abstractmethod        
    def execute_query(        
        self, belief_set: "BeliefSet", query: str        
    ) -> Tuple[Optional[bool], str]:        
        """        
        Exécute une requête logique sur un ensemble de croyances.     

        Args:            
          belief_set ("BeliefSet"): La base de connaissances sur laquelle la requête est exécutée.   
          query (str): La requête logique à exécuter.     

        Returns:            
          Tuple[Optional[bool], str]: Un tuple avec le résultat (True, False, ou None si indéterminé) et un message de statut du solveur.    
        """        
        pass        

    @abstractmethod        
    def interpret_results(        
        self, text: str, belief_set: "BeliefSet", queries: List[str], results: List[Tuple[Optional[bool], str]], context: Optional[Dict[str, Any]] = None        
    ) -> str:        
        """        
        Interprète les résultats des requêtes logiques en langage naturel.      

        Args:            
          text (str): Le texte source original. 
          belief_set ("BeliefSet"): L'ensemble de croyances utilisé.  
          queries (List[str]): La liste des requêtes qui ont été exécutées.   
          results (List[Tuple[Optional[bool], str]]): La liste des résultats        
            correspondant aux requêtes.       
          context (Optional[Dict[str, Any]]): Contexte additionnel.   

        Returns:            
          str: Une synthèse en langage naturel des résultats logiques.        
        """        
        pass        

    # @abstractmethod # Remplacé par l'utilisation directe du bridge  
    # def validate_formula(self, formula: str) -> bool:        
    #     """        
    #     Valide la syntaxe d'une formule logique.  

    #     Args:            
    #       formula (str): La formule à valider.  

    #     Returns:            
    #       bool: True si la syntaxe de la formule est correcte, False sinon.   
    #     """        
    #     pass        

    # @abstractmethod # Remplacé par l'utilisation directe du bridge  
    # def is_consistent(self, belief_set: "BeliefSet") -> Tuple[bool, str]:        
    #     """        
    #     Vérifie si un ensemble de croyances est logiquement cohérent. 

    #     Args:            
    #       belief_set ("BeliefSet"): L'ensemble de croyances à vérifier.

    #     Returns:            
    #       Tuple[bool, str]: Un tuple contenant un booléen (True si cohérent) et un message de statut du solveur.   
    #     """        
    #     pass        

    async def process_task(        
        self, task_id: str, task_description: str, state_manager: Any        
    ) -> Dict[str, Any]:        
        """        
        Traite une tâche assignée à l'agent logique.        
        Migré depuis AbstractLogicAgent pour unifier l'architecture.        
        """        
        self.logger.info(f"Traitement de la tâche {task_id}: {task_description}")        
        state = state_manager.get_current_state_snapshot(summarize=False)        
        if "Traduire" in task_description and "Belief Set" in task_description:            
            return await self._handle_translation_task(            
              task_id, task_description, state, state_manager            
            )        
        elif "Exécuter" in task_description and "Requêtes" in task_description:            
            return await self._handle_query_task(            
              task_id, task_description, state, state_manager            
            )        
        else:            
            error_msg = f"Type de tâche non reconnu: {task_description}"            
            self.logger.error(error_msg)            
            state_manager.add_answer(            
              task_id=task_id,                
              author_agent=self.name,                
              answer_text=error_msg,                
              source_ids=[],            
            )            
            return {"status": "error", "message": error_msg}        

    async def _handle_translation_task(        
        self, task_id: str, task_description: str, state: Dict[str, Any], state_manager: Any        
    ) -> Dict[str, Any]:        
        """        
        Génère une tâche spécifique de conversion de texte en un ensemble de croyances logiques.        
        """        
        raw_text = self._extract_source_text(task_description, state)        
        if not raw_text:            
            error_msg = "Impossible de trouver le texte source pour la traduction"            
            self.logger.error(error_msg)            
            state_manager.add_answer(            
              task_id=task_id,                
              author_agent=self.name,                
              answer_text=error_msg,                
              source_ids=[],            
            )            
            return {"status": "error", "message": error_msg}        

        belief_set, status_msg = await self.text_to_belief_set(raw_text)        
        if not belief_set:            
            error_msg = f"Échec de la conversion en ensemble de croyances: {status_msg}"            
            self.logger.error(error_msg)            
            state_manager.add_answer(            
              task_id=task_id,                
              author_agent=self.name,                
              answer_text=error_msg,                
              source_ids=[],            
            )            
            return {"status": "error", "message": error_msg}        

        bs_id = state_manager.add_belief_set(            
          logic_type=belief_set.logic_type, content=belief_set.content            
        )        
        answer_text = (            
          f"Ensemble de croyances créé avec succès (ID: {bs_id}).\n\n{status_msg}"            
        )        
        state_manager.add_answer(            
          task_id=task_id,                
          author_agent=self.name,                
          answer_text=answer_text,                
          source_ids=[bs_id],            
        )        
        return {"status": "success", "message": answer_text, "belief_set_id": bs_id}        

    async def _handle_query_task(        
        self, task_id: str, task_description: str, state: Dict[str, Any], state_manager: Any        
    ) -> Dict[str, Any]:        
        """        
        Génère une tâche d'exécution de requêtes logiques sur un ensemble de croyances existant.        
        """        
        belief_set_id = self._extract_belief_set_id(task_description)        
        if not belief_set_id:            
            error_msg = "Impossible de trouver l'ID de l'ensemble de croyances dans la description de la tâche"            
            self.logger.error(error_msg)            
            state_manager.add_answer(            
              task_id=task_id,                
              author_agent=self.name,                
              answer_text=error_msg,                
              source_ids=[],            
            )            
            return {"status": "error", "message": error_msg}        

        belief_sets = state.get("belief_sets", {})        
        if belief_set_id not in belief_sets:            
            error_msg = f"Ensemble de croyances non trouvé: {belief_set_id}"            
            self.logger.error(error_msg)            
            state_manager.add_answer(            
              task_id=task_id,                
              author_agent=self.name,                
              answer_text=error_msg,                
              source_ids=[],            
            )            
            return {"status": "error", "message": error_msg}        

        belief_set_data = belief_sets[belief_set_id]        
        belief_set = self._create_belief_set_from_data(belief_set_data)        
        raw_text = self._extract_source_text(task_description, state)        
        queries = await self.generate_queries(raw_text, belief_set)        
        if not queries:            
            error_msg = "Aucune requête n'a pu être générée"            
            self.logger.error(error_msg)            
            state_manager.add_answer(            
              task_id=task_id,                
              author_agent=self.name,                
              answer_text=error_msg,                
              source_ids=[],            
            )            
            return {"status": "error", "message": error_msg}        

        formatted_results = []        
        log_ids = []        
        raw_results = []        
        for query in queries:            
            result, result_str = self.execute_query(belief_set, query)            
            raw_results.append((result, result_str))        
            formatted_results.append(result_str)        
            log_id = state_manager.log_query_result(            
              belief_set_id=belief_set_id, query=query, raw_result=result_str            
            )        
            log_ids.append(log_id)        

        interpretation = self.interpret_results(            
          raw_text, belief_set, queries, raw_results            
        )        
        state_manager.add_answer(            
          task_id=task_id,                
          author_agent=self.name,                
          answer_text=interpretation,                
          source_ids=[belief_set_id] + log_ids,            
        )        
        return {            
          "status": "successs",                
          "message": interpretation,                
          "queries": queries,                
          "results": formatted_results,                
          "log_ids": log_ids,            
        }        

    def _extract_source_text(self, task_description: str, state: Dict[str, Any]) -> str:        
        """        
        Extrait le texte source pertinent pour une tâche.        
        """        
        raw_text = state.get("raw_text", "")        
        if not raw_text and "texte:" in task_description.lower():            
            parts = task_description.split("texte:", 1)            
            if len(parts) > 1:                
              raw_text = parts[1].strip()        
        return raw_text        

    def _extract_belief_set_id(self, task_description: str) -> Optional[str]:        
        """        
        Extrait un ID d'ensemble de croyances à partir de la description d'une tâche.        
        """        
        if "belief_set_id:" in task_description.lower():            
            parts = task_description.split("belief_set_id:", 1)            
            if len(parts) > 1:                
              bs_id_part = parts[1].strip()                
              bs_id = bs_id_part.split()[0].strip()                
              return bs_id        
        return None        

    @abstractmethod        
    def _create_belief_set_from_data(self, belief_set_data: Dict[str, Any]) -> "BeliefSet":        
        """        
        Crée une instance de `BeliefSet` à partir d'un dictionnaire de données.        
        """        
        pass        
