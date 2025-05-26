"""
Module d'adaptation de l'agent d'extraction pour l'architecture hiérarchique.

Ce module fournit un adaptateur qui permet à l'agent d'extraction existant
de fonctionner comme un agent opérationnel dans l'architecture hiérarchique.
"""

import os
import re
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import time
import uuid # Ajout de l'import uuid

from argumentation_analysis.orchestration.hierarchical.operational.agent_interface import OperationalAgent
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState
from argumentation_analysis.core.communication import MessageMiddleware 

from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent, setup_extract_agent
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
        self.extract_agent = None
        self.kernel = None
        self.initialized = False
        self.logger = logging.getLogger(f"ExtractAgentAdapter.{name}")
    
    async def initialize(self):
        """
        Initialise l'agent d'extraction.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        if self.initialized:
            return True
        
        try:
            self.logger.info("Initialisation de l'agent d'extraction...")
            self.kernel, self.extract_agent = await setup_extract_agent()
            
            if self.extract_agent is None:
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
            success = await self.initialize()
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
            await self.initialize() 
            if not self.initialized: 
                return ExtractResult(status="error", message="Agent non initialisé pour _process_extract", explanation="Initialisation échouée")

        source_info = {
            "source_name": extract.get("source", "Source inconnue"),
            "source_text": extract.get("content", "")
        }
        
        extract_name = extract.get("id", "Extrait sans nom")
        
        result = await self.extract_agent.extract_from_name(source_info, extract_name)
        
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
            self.extract_agent = None
            self.kernel = None
            self.initialized = False
            
            self.logger.info("Agent d'extraction arrêté avec succès.")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'arrêt de l'agent d'extraction: {e}")
            return False
    
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