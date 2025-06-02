"""
Module d'adaptation de l'agent d'extraction pour l'architecture hiérarchique.

Ce module fournit un adaptateur qui permet à l'agent d'extraction existant
de fonctionner comme un agent opérationnel dans l'architecture hiérarchique.
"""

import os
import re
import json
import logging
from unittest.mock import Mock, MagicMock
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import time
import uuid # Ajout de l'import uuid

from argumentation_analysis.orchestration.hierarchical.operational.agent_interface import OperationalAgent
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState
from argumentation_analysis.core.communication import MessageMiddleware 

from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent # Removed setup_extract_agent
from argumentation_analysis.agents.core.extract.extract_definitions import ExtractResult


class ExtractAgentAdapter(OperationalAgent):
    """
    Adaptateur pour l'agent d'extraction.
    
    Cet adaptateur permet à l'agent d'extraction existant de fonctionner
    comme un agent opérationnel dans l'architecture hiérarchique.
    """
    
    def __init__(self, name: str = "ExtractAgent", 
                 operational_state: Optional[OperationalState] = None,
                 middleware: Optional[MessageMiddleware] = None): 
        """
        Initialise un nouvel adaptateur pour l'agent d'extraction.
        
        Args:
            name: Nom de l'agent
            operational_state: État opérationnel à utiliser. Si None, un nouvel état est créé.
            middleware: Le middleware de communication à utiliser.
        """
        super().__init__(name, operational_state, middleware=middleware)
        self.agent = None # Changed from self.extract_agent
        self.kernel = None # Will be passed during initialize
        self.llm_service_id = None # Will be passed during initialize
        self.initialized = False
        self.logger = logging.getLogger(f"ExtractAgentAdapter.{name}")
    
    async def initialize(self, kernel: Any, llm_service_id: str): # Added kernel and llm_service_id
        """
        Initialise l'agent d'extraction.

        Args:
            kernel: Le kernel Semantic Kernel à utiliser.
            llm_service_id: L'ID du service LLM à utiliser.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        if self.initialized:
            return True
        
        self.kernel = kernel
        self.llm_service_id = llm_service_id

        try:
            self.logger.info("Initialisation de l'agent d'extraction...")
            # Instancier l'agent refactoré
            self.agent = ExtractAgent(kernel=self.kernel, agent_name=f"{self.name}_ExtractAgent")
            # Configurer les composants de l'agent
            await self.agent.setup_agent_components(llm_service_id=self.llm_service_id)
            
            if self.agent is None: # Check self.agent
                self.logger.error("Échec de l'initialisation de l'agent d'extraction.")
                return False
            
            self.initialized = True
            self.logger.info("Agent d'extraction initialisé avec succès.")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation de l'agent d'extraction: {e}")
            return False
    
    def get_capabilities(self) -> List[str]:
        """
        Retourne les capacités de l'agent d'extraction.
        
        Returns:
            Liste des capacités de l'agent
        """
        return [
            "text_extraction",
            "preprocessing",
            "extract_validation"
        ]
    
    def can_process_task(self, task: Dict[str, Any]) -> bool:
        """
        Vérifie si l'agent peut traiter une tâche donnée.
        
        Args:
            task: La tâche à vérifier
            
        Returns:
            True si l'agent peut traiter la tâche, False sinon
        """
        if not self.initialized:
            return False
        
        required_capabilities = task.get("required_capabilities", [])
        agent_capabilities = self.get_capabilities()
        
        return any(cap in agent_capabilities for cap in required_capabilities)
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite une tâche opérationnelle.
        
        Args:
            task: La tâche opérationnelle à traiter
            
        Returns:
            Le résultat du traitement de la tâche
        """
        task_original_id = task.get("id", f"unknown_task_{uuid.uuid4().hex[:8]}")

        if not self.initialized:
            # L'initialisation doit maintenant être appelée avec kernel et llm_service_id
            # Ceci devrait être géré par le OperationalManager avant d'appeler process_task
            # ou alors, ces informations doivent être disponibles pour l'adaptateur.
            # Pour l'instant, on suppose qu'elles sont disponibles via self.kernel et self.llm_service_id
            # qui auraient été définies lors d'un appel explicite à initialize.
            if self.kernel is None or self.llm_service_id is None:
                self.logger.error("Kernel ou llm_service_id non configuré avant process_task.")
                return {
                    "id": f"result-{task_original_id}",
                    "task_id": task_original_id,
                    "tactical_task_id": task.get("tactical_task_id"),
                    "status": "failed",
                    "outputs": {},
                    "metrics": {},
                    "issues": [{
                        "type": "configuration_error",
                        "description": "Kernel ou llm_service_id non configuré pour l'agent d'extraction",
                        "severity": "high"
                    }]
                }
            
            success = await self.initialize(self.kernel, self.llm_service_id)
            if not success:
                return {
                    "id": f"result-{task_original_id}",
                    "task_id": task_original_id,
                    "tactical_task_id": task.get("tactical_task_id"),
                    "status": "failed",
                    "outputs": {},
                    "metrics": {},
                    "issues": [{
                        "type": "initialization_error",
                        "description": "Échec de l'initialisation de l'agent d'extraction",
                        "severity": "high"
                    }]
                }
        
        task_id_registered = self.register_task(task) 
        
        self.update_task_status(task_id_registered, "in_progress", {
            "message": "Traitement de la tâche en cours",
            "agent": self.name
        })
        
        start_time = time.time()
        
        try:
            techniques = task.get("techniques", [])
            text_extracts = task.get("text_extracts", [])
            
            if not text_extracts:
                raise ValueError("Aucun extrait de texte fourni dans la tâche.")
            
            results = []
            issues = []
            
            for technique in techniques:
                technique_name = technique.get("name", "")
                technique_params = technique.get("parameters", {})
                
                if technique_name == "relevant_segment_extraction":
                    for extract in text_extracts:
                        extract_result = await self._process_extract(extract, technique_params)
                        
                        if extract_result.status == "valid":
                            results.append({
                                "type": "extracted_segments",
                                "extract_id": extract.get("id"),
                                "source": extract.get("source"),
                                "start_marker": extract_result.start_marker,
                                "end_marker": extract_result.end_marker,
                                "template_start": extract_result.template_start,
                                "extracted_text": extract_result.extracted_text,
                                "confidence": 0.9 
                            })
                        else:
                            issues.append({
                                "type": "extraction_error",
                                "description": extract_result.message,
                                "severity": "medium",
                                "extract_id": extract.get("id"),
                                "details": {
                                    "status": extract_result.status,
                                    "explanation": extract_result.explanation
                                }
                            })
                elif technique_name == "text_normalization":
                    for extract in text_extracts:
                        normalized_text = self._normalize_text(extract.get("content", ""), technique_params)
                        
                        results.append({
                            "type": "normalized_text",
                            "extract_id": extract.get("id"),
                            "source": extract.get("source"),
                            "normalized_text": normalized_text,
                            "confidence": 1.0
                        })
                else:
                    issues.append({
                        "type": "unsupported_technique",
                        "description": f"Technique non supportée: {technique_name}",
                        "severity": "medium",
                        "details": {
                            "technique": technique_name,
                            "parameters": technique_params
                        }
                    })
            
            execution_time = time.time() - start_time
            metrics = {
                "execution_time": execution_time,
                "confidence": 0.9 if results else 0.0,
                "coverage": 1.0 if text_extracts and results else 0.0,
                "resource_usage": 0.5 
            }
            
            self.update_metrics(task_id_registered, metrics)
            
            status = "completed"
            if issues:
                status = "completed_with_issues"
            
            self.update_task_status(task_id_registered, status, {
                "message": f"Traitement terminé avec statut: {status}",
                "results_count": len(results),
                "issues_count": len(issues)
            })
            
            return self.format_result(task, results, metrics, issues, task_id_to_report=task_id_registered) 
        
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de la tâche {task_id_registered}: {e}")
            
            self.update_task_status(task_id_registered, "failed", {
                "message": f"Erreur lors du traitement: {str(e)}",
                "exception": str(e)
            })
            
            execution_time = time.time() - start_time
            metrics = {
                "execution_time": execution_time,
                "confidence": 0.0,
                "coverage": 0.0,
                "resource_usage": 0.5 
            }
            
            self.update_metrics(task_id_registered, metrics)
            
            return {
                "id": f"result-{task_id_registered}", 
                "task_id": task_id_registered, 
                "tactical_task_id": task.get("tactical_task_id"),
                "status": "failed",
                "outputs": {},
                "metrics": metrics,
                "issues": [{
                    "type": "execution_error",
                    "description": f"Erreur lors du traitement: {str(e)}",
                    "severity": "high",
                    "details": {
                        "exception": str(e)
                    }
                }]
            }
    
    async def _process_extract(self, extract: Dict[str, Any], parameters: Dict[str, Any]) -> ExtractResult:
        if not self.initialized:
            # Idem que pour process_task, l'initialisation devrait avoir eu lieu.
            if self.kernel is None or self.llm_service_id is None:
                self.logger.error("Kernel ou llm_service_id non configuré avant _process_extract.")
                return ExtractResult(status="error", message="Kernel ou llm_service_id non configuré", explanation="Configuration manquante")
            await self.initialize(self.kernel, self.llm_service_id)
            if not self.initialized:
                return ExtractResult(status="error", message="Agent non initialisé pour _process_extract", explanation="Initialisation échouée")

        source_info = {
            "source_name": extract.get("source", "Source inconnue"),
            "source_text": extract.get("content", "")
        }
        
        extract_name = extract.get("id", "Extrait sans nom")
        
        result = await self.agent.extract_from_name(source_info, extract_name) # Changed self.extract_agent to self.agent
        
        return result
    
    def _normalize_text(self, text: str, parameters: Dict[str, Any]) -> str:
        normalized_text = text
        
        if parameters.get("remove_stopwords", False):
            stopwords = ["le", "la", "les", "un", "une", "des", "et", "ou", "mais", "donc", "car", "ni", "or", "de", "est"] 
            words = normalized_text.split()
            normalized_text = " ".join([word for word in words if word.lower() not in stopwords])
        
        if parameters.get("lemmatize", False):
            self.logger.info("Lemmatisation demandée mais non implémentée.")
        
        return normalized_text

    async def shutdown(self) -> bool:
        """
        Arrête l'agent d'extraction et nettoie les ressources.
        
        Returns:
            True si l'arrêt a réussi, False sinon
        """
        try:
            self.logger.info("Arrêt de l'agent d'extraction...")
            
            # Nettoyer les ressources
            self.agent = None # Changed from self.extract_agent
            self.kernel = None
            self.llm_service_id = None # Clear llm_service_id as well
            self.initialized = False
            
            self.logger.info("Agent d'extraction arrêté avec succès.")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'arrêt de l'agent d'extraction: {e}")
            return False

    def _format_outputs(self, results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Formate la liste des résultats bruts en un dictionnaire d'outputs groupés par type.
        """
        outputs: Dict[str, List[Dict[str, Any]]] = {}
        if not results:
            # S'assurer que les clés attendues par les tests existent même si results est vide
            outputs["extracted_segments"] = []
            outputs["normalized_text"] = []
            # Ajoutez d'autres types de résultats attendus ici si nécessaire
            return outputs

        for res_item in results:
            res_type = res_item.get("type")
            if res_type:
                if res_type not in outputs:
                    outputs[res_type] = []
                # Crée une copie pour éviter de modifier l'original si besoin, et enlève la clé "type"
                # item_copy = {k: v for k, v in res_item.items() if k != "type"}
                # Pour l'instant, on garde l'item tel quel, car les tests pourraient vérifier la clé "type" aussi.
                outputs[res_type].append(res_item)
            else:
                # Gérer les items sans type, peut-être les mettre dans une catégorie "unknown"
                if "unknown_type_results" not in outputs:
                    outputs["unknown_type_results"] = []
                outputs["unknown_type_results"].append(res_item)
        
        # S'assurer que les clés attendues par les tests existent même si aucun résultat de ce type n'a été produit
        if "extracted_segments" not in outputs:
            outputs["extracted_segments"] = []
        if "normalized_text" not in outputs:
            outputs["normalized_text"] = []
            
        return outputs
    
    def format_result(self, task: Dict[str, Any], results: List[Dict[str, Any]], metrics: Dict[str, Any], issues: List[Dict[str, Any]], task_id_to_report: Optional[str] = None) -> Dict[str, Any]:
        final_task_id = task_id_to_report if task_id_to_report else task.get("id", f"unknown_task_{uuid.uuid4().hex[:8]}")
        return {
            "id": f"result-{final_task_id}",
            "task_id": final_task_id,
            "tactical_task_id": task.get("tactical_task_id"),
            "status": "completed" if not issues else "completed_with_issues",
            "outputs": self._format_outputs(results),
            "metrics": metrics,
            "issues": issues
        }