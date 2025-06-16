#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Service pour les opérations logiques.

Ce service gère les opérations liées aux agents logiques, notamment:
- Conversion de texte en ensemble de croyances
- Exécution de requêtes logiques
- Génération de requêtes pertinentes
- Interprétation des résultats
"""

import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from semantic_kernel import Kernel # Déjà présent, pas de changement nécessaire

from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory
from argumentation_analysis.agents.core.abc.agent_bases import BaseLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import BeliefSet
from argumentation_analysis.agents.core.logic.query_executor import QueryExecutor
from argumentation_analysis.core.llm_service import create_llm_service

from ..models.request_models import (
    LogicBeliefSetRequest, LogicQueryRequest, LogicGenerateQueriesRequest, LogicOptions
)
from ..models.response_models import (
    LogicBeliefSet, LogicBeliefSetResponse, LogicQueryResult, LogicQueryResponse,
    LogicGenerateQueriesResponse, LogicInterpretationResponse
)


class LogicService:
    """Service pour les opérations logiques."""
    
    def __init__(self):
        """Initialisation du service."""
        self.logger = logging.getLogger("WebAPI.LogicService")
        self.logger.info("Initialisation du service LogicService")
        
        # Initialisation du kernel et du service LLM
        self.kernel = Kernel()
        try:
            llm_service = create_llm_service(service_id="default_logic_llm")
            self.kernel.add_service(llm_service)
            self.logger.info("Service LLM 'default_logic_llm' créé et ajouté au kernel pour LogicService.")
        except Exception as e:
            self.logger.error(f"Erreur lors de la création du service LLM pour LogicService: {e}")
        
        # Initialisation de l'exécuteur de requêtes
        self.query_executor = QueryExecutor()
        
        # Stockage des ensembles de croyances (en mémoire pour l'exemple)
        # Dans une application réelle, on utiliserait une base de données
        self.belief_sets: Dict[str, Dict[str, Any]] = {}
    
    def is_healthy(self) -> bool:
        """Vérifie si le service est opérationnel."""
        try:
            # Vérifier que le kernel est initialisé
            if not self.kernel:
                return False
            
            # Vérifier que l'exécuteur de requêtes est initialisé
            if not self.query_executor:
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors du health check: {str(e)}")
            return False
    
    async def text_to_belief_set(self, request: LogicBeliefSetRequest) -> LogicBeliefSetResponse:
        """
        Convertit un texte en ensemble de croyances logiques.
        
        Args:
            request: La requête contenant le texte à convertir
            
        Returns:
            Une réponse contenant l'ensemble de croyances créé
        """
        self.logger.info(f"Conversion de texte en ensemble de croyances de type '{request.logic_type}'")
        start_time = time.time()
        
        try:
            # Créer l'agent logique approprié
            agent = LogicAgentFactory.create_agent(request.logic_type, self.kernel)
            if not agent:
                raise ValueError(f"Impossible de créer un agent pour le type de logique '{request.logic_type}'")
            
            # Configurer l'agent
            agent.setup_agent_components(llm_service_id="default_logic_llm")
            
            # Convertir le texte en ensemble de croyances
            belief_set, message = await agent.text_to_belief_set(request.text)
            if not belief_set:
                raise ValueError(f"Échec de la conversion: {message}")
            
            # Générer un ID unique pour l'ensemble de croyances
            belief_set_id = str(uuid.uuid4())
            
            # Stocker l'ensemble de croyances
            self.belief_sets[belief_set_id] = {
                "id": belief_set_id,
                "logic_type": request.logic_type,
                "content": belief_set.content,
                "source_text": request.text,
                "creation_timestamp": datetime.now()
            }
            
            # Créer la réponse
            response = LogicBeliefSetResponse(
                success=True,
                belief_set=LogicBeliefSet(
                    id=belief_set_id,
                    logic_type=request.logic_type,
                    content=belief_set.content,
                    source_text=request.text,
                    creation_timestamp=datetime.now()
                ),
                processing_time=time.time() - start_time,
                conversion_options=request.options if request.options else {}
            )
            
            return response
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la conversion: {str(e)}", exc_info=True)
            import traceback
            tb_str = traceback.format_exc()
            raise ValueError(f"Erreur lors de la conversion: {str(e)}\nTRACEBACK:\n{tb_str}")
        
        finally:
            processing_time = time.time() - start_time
            self.logger.info(f"Conversion terminée en {processing_time:.2f} secondes")
    
    async def execute_query(self, request: LogicQueryRequest) -> LogicQueryResponse:
        """
        Exécute une requête logique sur un ensemble de croyances.
        
        Args:
            request: La requête contenant l'ID de l'ensemble de croyances et la requête à exécuter
            
        Returns:
            Une réponse contenant le résultat de la requête
        """
        self.logger.info(f"Exécution de la requête '{request.query}' sur l'ensemble de croyances '{request.belief_set_id}'")
        start_time = time.time()
        
        try:
            # Récupérer l'ensemble de croyances
            belief_set_data = self._get_belief_set(request.belief_set_id)
            if not belief_set_data:
                raise ValueError(f"Ensemble de croyances non trouvé: {request.belief_set_id}")
            
            # Vérifier que le type de logique correspond
            if belief_set_data["logic_type"] != request.logic_type:
                raise ValueError(f"Type de logique incompatible: attendu '{belief_set_data['logic_type']}', reçu '{request.logic_type}'")
            
            # Créer l'agent logique approprié
            agent = LogicAgentFactory.create_agent(request.logic_type, self.kernel)
            if not agent:
                raise ValueError(f"Impossible de créer un agent pour le type de logique '{request.logic_type}'")
            
            # Créer l'objet BeliefSet approprié
            belief_set = self._create_belief_set_from_data(belief_set_data)
            
            # Exécuter la requête
            result, formatted_result = await agent.execute_query(belief_set, request.query)
            
            # Créer la réponse
            response = LogicQueryResponse(
                success=True,
                belief_set_id=request.belief_set_id,
                logic_type=request.logic_type,
                result=LogicQueryResult(
                    query=request.query,
                    result=result,
                    formatted_result=formatted_result,
                    explanation=self._generate_explanation(belief_set, request.query, result, formatted_result) if request.options and request.options.include_explanation else None
                ),
                processing_time=time.time() - start_time,
                query_options=request.options.dict() if request.options else {}
            )
            
            return response
        
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution de la requête: {str(e)}", exc_info=True)
            raise ValueError(f"Erreur lors de l'exécution de la requête: {str(e)}")
        
        finally:
            processing_time = time.time() - start_time
            self.logger.info(f"Exécution terminée en {processing_time:.2f} secondes")
    
    async def generate_queries(self, request: LogicGenerateQueriesRequest) -> LogicGenerateQueriesResponse:
        """
        Génère des requêtes logiques pertinentes.
        
        Args:
            request: La requête contenant l'ID de l'ensemble de croyances et le texte source
            
        Returns:
            Une réponse contenant les requêtes générées
        """
        self.logger.info(f"Génération de requêtes pour l'ensemble de croyances '{request.belief_set_id}'")
        start_time = time.time()
        
        try:
            # Récupérer l'ensemble de croyances
            belief_set_data = self._get_belief_set(request.belief_set_id)
            if not belief_set_data:
                raise ValueError(f"Ensemble de croyances non trouvé: {request.belief_set_id}")
            
            # Vérifier que le type de logique correspond
            if belief_set_data["logic_type"] != request.logic_type:
                raise ValueError(f"Type de logique incompatible: attendu '{belief_set_data['logic_type']}', reçu '{request.logic_type}'")
            
            # Créer l'agent logique approprié
            agent = LogicAgentFactory.create_agent(request.logic_type, self.kernel)
            if not agent:
                raise ValueError(f"Impossible de créer un agent pour le type de logique '{request.logic_type}'")
            
            # Créer l'objet BeliefSet approprié
            belief_set = self._create_belief_set_from_data(belief_set_data)
            
            # Générer les requêtes
            queries = await agent.generate_queries(request.text, belief_set)
            
            # Limiter le nombre de requêtes si nécessaire
            max_queries = request.options.max_queries if request.options else 5
            queries = queries[:max_queries]
            
            # Créer la réponse
            response = LogicGenerateQueriesResponse(
                success=True,
                belief_set_id=request.belief_set_id,
                logic_type=request.logic_type,
                queries=queries,
                processing_time=time.time() - start_time,
                generation_options=request.options.dict() if request.options else {}
            )
            
            return response
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération de requêtes: {str(e)}", exc_info=True)
            raise ValueError(f"Erreur lors de la génération de requêtes: {str(e)}")
        
        finally:
            processing_time = time.time() - start_time
            self.logger.info(f"Génération terminée en {processing_time:.2f} secondes")
    
    async def interpret_results(self, belief_set_id: str, logic_type: str, text: str,
                                 queries: List[str], results: List[LogicQueryResult],
                                 options: Optional[LogicOptions] = None) -> LogicInterpretationResponse:
        """
        Interprète les résultats de requêtes logiques.
        
        Args:
            belief_set_id: L'ID de l'ensemble de croyances
            logic_type: Le type de logique
            text: Le texte source
            queries: Les requêtes exécutées
            results: Les résultats des requêtes
            options: Les options d'interprétation
            
        Returns:
            Une réponse contenant l'interprétation des résultats
        """
        self.logger.info(f"Interprétation des résultats pour l'ensemble de croyances '{belief_set_id}'")
        start_time = time.time()
        
        try:
            # Récupérer l'ensemble de croyances
            belief_set_data = self._get_belief_set(belief_set_id)
            if not belief_set_data:
                raise ValueError(f"Ensemble de croyances non trouvé: {belief_set_id}")
            
            # Vérifier que le type de logique correspond
            if belief_set_data["logic_type"] != logic_type:
                raise ValueError(f"Type de logique incompatible: attendu '{belief_set_data['logic_type']}', reçu '{logic_type}'")
            
            # Créer l'agent logique approprié
            agent = LogicAgentFactory.create_agent(logic_type, self.kernel)
            if not agent:
                raise ValueError(f"Impossible de créer un agent pour le type de logique '{logic_type}'")
            
            # Créer l'objet BeliefSet approprié
            belief_set = self._create_belief_set_from_data(belief_set_data)
            
            # Extraire les résultats formatés
            formatted_results = [result.formatted_result for result in results]
            
            # Interpréter les résultats
            interpretation = await agent.interpret_results(text, belief_set, queries, formatted_results)
            
            # Créer la réponse
            response = LogicInterpretationResponse(
                success=True,
                belief_set_id=belief_set_id,
                logic_type=logic_type,
                queries=queries,
                results=results,
                interpretation=interpretation,
                processing_time=time.time() - start_time,
                interpretation_options=options.dict() if options else {}
            )
            
            return response
        
        except Exception as e:
            self.logger.error(f"Erreur lors de l'interprétation des résultats: {str(e)}", exc_info=True)
            raise ValueError(f"Erreur lors de l'interprétation des résultats: {str(e)}")
        
        finally:
            processing_time = time.time() - start_time
            self.logger.info(f"Interprétation terminée en {processing_time:.2f} secondes")
    
    def _get_belief_set(self, belief_set_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un ensemble de croyances par son ID.
        
        Args:
            belief_set_id: L'ID de l'ensemble de croyances
            
        Returns:
            Les données de l'ensemble de croyances ou None s'il n'existe pas
        """
        return self.belief_sets.get(belief_set_id)
    
    def _create_belief_set_from_data(self, belief_set_data: Dict[str, Any]) -> BeliefSet:
        """
        Crée un objet BeliefSet à partir des données stockées.
        
        Args:
            belief_set_data: Les données de l'ensemble de croyances
            
        Returns:
            Un objet BeliefSet
        """
        return BeliefSet.from_dict({
            "logic_type": belief_set_data["logic_type"],
            "content": belief_set_data["content"]
        })
    
    def _generate_explanation(self, belief_set: BeliefSet, query: str, 
                             result: Optional[bool], formatted_result: str) -> str:
        """
        Génère une explication pour le résultat d'une requête.
        
        Args:
            belief_set: L'ensemble de croyances
            query: La requête exécutée
            result: Le résultat de la requête
            formatted_result: Le résultat formaté
            
        Returns:
            Une explication du résultat
        """
        # Dans une application réelle, on utiliserait un LLM pour générer une explication
        # plus détaillée et personnalisée
        
        if result is None:
            return "Le résultat de la requête est indéterminé. Cela peut être dû à une limitation du raisonneur ou à une ambiguïté dans l'ensemble de croyances."
        
        if result:
            return f"La requête '{query}' est acceptée par l'ensemble de croyances. Cela signifie que la formule est une conséquence logique des axiomes définis dans l'ensemble de croyances."
        else:
            return f"La requête '{query}' est rejetée par l'ensemble de croyances. Cela signifie que la formule n'est pas une conséquence logique des axiomes définis dans l'ensemble de croyances."