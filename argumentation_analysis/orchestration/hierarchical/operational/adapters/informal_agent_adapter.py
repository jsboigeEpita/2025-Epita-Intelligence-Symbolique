"""
Module d'adaptation de l'agent informel pour l'architecture hiérarchique.

Ce module fournit un adaptateur qui permet à l'agent informel existant
de fonctionner comme un agent opérationnel dans l'architecture hiérarchique.
"""

import os
import re
import json
import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

import semantic_kernel as sk # Kept for type hints if necessary, but direct use might be reduced
# from semantic_kernel.contents import ChatMessageContent, AuthorRole # Potentially unused if agent handles chat history
# from semantic_kernel.functions.kernel_arguments import KernelArguments # Potentially unused

from argumentation_analysis.orchestration.hierarchical.operational.agent_interface import OperationalAgent
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState

# Import de l'agent informel refactoré
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent

# Import des outils d'analyse rhétorique améliorés (conservés au cas où, mais l'agent devrait les gérer)
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator


class InformalAgentAdapter(OperationalAgent):
    """
    Adaptateur pour l'agent informel.
    
    Cet adaptateur permet à l'agent informel existant de fonctionner
    comme un agent opérationnel dans l'architecture hiérarchique.
    """
    
    def __init__(self, name: str = "InformalAgent", operational_state: Optional[OperationalState] = None):
        """
        Initialise un nouvel adaptateur pour l'agent informel.
        
        Args:
            name: Nom de l'agent
            operational_state: État opérationnel à utiliser. Si None, un nouvel état est créé.
        """
        super().__init__(name, operational_state)
        self.agent: Optional[InformalAnalysisAgent] = None # Agent refactoré
        self.kernel: Optional[sk.Kernel] = None # Passé à initialize
        self.llm_service_id: Optional[str] = None # Passé à initialize
        
        # Les outils sont maintenant gérés par l'agent via setup_agent_components
        # self.complex_fallacy_analyzer = None
        # self.contextual_fallacy_analyzer = None
        # self.fallacy_severity_evaluator = None
        
        self.initialized = False
        self.logger = logging.getLogger(f"InformalAgentAdapter.{name}")
    
    async def initialize(self, kernel: sk.Kernel, llm_service_id: str): # Prend kernel et llm_service_id
        """
        Initialise l'agent informel.

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
            self.logger.info("Initialisation de l'agent informel refactoré...")
            
            self.agent = InformalAnalysisAgent(kernel=self.kernel, agent_name=f"{self.name}_InformalAgent")
            self.agent.setup_agent_components(llm_service_id=self.llm_service_id)
            
            if self.agent is None: # Vérifier self.agent
                self.logger.error("Échec de l'initialisation de l'agent informel.")
                return False

            self.initialized = True
            self.logger.info("Agent informel refactoré initialisé avec succès.")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation de l'agent informel refactoré: {e}")
            return False
    
    def get_capabilities(self) -> List[str]:
        """
        Retourne les capacités de l'agent informel.
        
        Returns:
            Liste des capacités de l'agent
        """
        return [
            "argument_identification",
            "fallacy_detection",
            "fallacy_attribution",
            "fallacy_justification",
            "informal_analysis",
            "complex_fallacy_analysis",
            "contextual_fallacy_analysis",
            "fallacy_severity_evaluation"
        ]
    
    def can_process_task(self, task: Dict[str, Any]) -> bool:
        """
        Vérifie si l'agent peut traiter une tâche donnée.
        
        Args:
            task: La tâche à vérifier
            
        Returns:
            True si l'agent peut traiter la tâche, False sinon
        """
        # Vérifier si l'agent est initialisé
        if not self.initialized:
            return False
        
        # Vérifier si les capacités requises sont fournies par cet agent
        required_capabilities = task.get("required_capabilities", [])
        agent_capabilities = self.get_capabilities()
        
        # Vérifier si au moins une des capacités requises est fournie par l'agent
        return any(cap in agent_capabilities for cap in required_capabilities)
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite une tâche opérationnelle.
        
        Args:
            task: La tâche opérationnelle à traiter
            
        Returns:
            Le résultat du traitement de la tâche
        """
        # Vérifier si l'agent est initialisé
        if not self.initialized:
            if self.kernel is None or self.llm_service_id is None:
                self.logger.error("Kernel ou llm_service_id non configuré avant process_task pour l'agent informel.")
                return {
                    "id": f"result-{task.get('id')}",
                    "task_id": task.get("id"),
                    "tactical_task_id": task.get("tactical_task_id"),
                    "status": "failed",
                    "outputs": {},
                    "metrics": {},
                    "issues": [{
                        "type": "configuration_error",
                        "description": "Kernel ou llm_service_id non configuré pour l'agent informel",
                        "severity": "high"
                    }]
                }
            success = await self.initialize(self.kernel, self.llm_service_id)
            if not success:
                return {
                    "id": f"result-{task.get('id')}",
                    "task_id": task.get("id"),
                    "tactical_task_id": task.get("tactical_task_id"),
                    "status": "failed",
                    "outputs": {},
                    "metrics": {},
                    "issues": [{
                        "type": "initialization_error",
                        "description": "Échec de l'initialisation de l'agent informel",
                        "severity": "high"
                    }]
                }
        
        # Enregistrer la tâche dans l'état opérationnel
        task_id = self.register_task(task)
        
        # Mettre à jour le statut de la tâche
        self.update_task_status(task_id, "in_progress", {
            "message": "Traitement de la tâche en cours",
            "agent": self.name
        })
        
        # Mesurer le temps d'exécution
        start_time = time.time()
        
        try:
            # Extraire les informations nécessaires de la tâche
            techniques = task.get("techniques", [])
            text_extracts = task.get("text_extracts", [])
            parameters = task.get("parameters", {})
            
            # Vérifier si des extraits de texte sont fournis
            if not text_extracts:
                raise ValueError("Aucun extrait de texte fourni dans la tâche.")
            
            # Préparer les résultats
            results = []
            issues = []
            
            # Traiter chaque technique
            for technique in techniques:
                technique_name = technique.get("name", "")
                technique_params = technique.get("parameters", {})
                
                # Exécuter la technique appropriée
                if technique_name == "premise_conclusion_extraction":
                    # Identifier les arguments dans le texte
                    for extract in text_extracts:
                        extract_content = extract.get("content", "")
                        if not extract_content:
                            continue
                        
                        # Appel à la méthode de l'agent refactoré
                        identified_args_result = await self.agent.identify_arguments(
                            text=extract_content,
                            parameters=technique_params
                        )
                        # La structure de identified_args_result doit être vérifiée.
                        # Supposons qu'elle retourne une liste d'arguments structurés.
                        # Exemple: [{"premises": [...], "conclusion": "...", "confidence": 0.8}]
                        for arg_data in identified_args_result: # Ajuster selon la sortie réelle de l'agent
                            results.append({
                                "type": "identified_arguments",
                                "extract_id": extract.get("id"),
                                "source": extract.get("source"),
                                "premises": arg_data.get("premises", []),
                                "conclusion": arg_data.get("conclusion", ""),
                                "confidence": arg_data.get("confidence", 0.8)
                            })
                
                elif technique_name == "fallacy_pattern_matching":
                    for extract in text_extracts:
                        extract_content = extract.get("content", "")
                        if not extract_content:
                            continue
                        
                        # Appel à la méthode de l'agent refactoré
                        detected_fallacies_result = await self.agent.detect_fallacies(
                            text=extract_content,
                            parameters=technique_params
                        )
                        # Supposons que detected_fallacies_result retourne une liste de sophismes.
                        # Exemple: [{"fallacy_type": "...", "segment": "...", "explanation": "...", "confidence": 0.7}]
                        for fallacy_data in detected_fallacies_result: # Ajuster selon la sortie réelle
                            results.append({
                                "type": "identified_fallacies",
                                "extract_id": extract.get("id"),
                                "source": extract.get("source"),
                                "fallacy_type": fallacy_data.get("fallacy_type", ""),
                                "segment": fallacy_data.get("segment", ""),
                                "explanation": fallacy_data.get("explanation", ""),
                                "confidence": fallacy_data.get("confidence", 0.7)
                            })

                elif technique_name == "complex_fallacy_analysis": # Nouvelle gestion
                    for extract in text_extracts:
                        extract_content = extract.get("content", "")
                        if not extract_content:
                            continue
                        analysis_result = await self.agent.analyze_complex_fallacies(
                            text=extract_content,
                            parameters=technique_params
                        )
                        for fallacy_data in analysis_result: # Ajuster selon la sortie réelle
                             results.append({
                                "type": "complex_fallacies", # ou un type plus spécifique
                                "extract_id": extract.get("id"),
                                "source": extract.get("source"),
                                **fallacy_data # Intégrer les données du sophisme
                            })
                
                elif technique_name == "contextual_fallacy_analysis":
                    for extract in text_extracts:
                        extract_content = extract.get("content", "")
                        if not extract_content:
                            continue
                        
                        # Appel à la méthode de l'agent refactoré
                        contextual_fallacies_result = await self.agent.analyze_contextual_fallacies(
                            text=extract_content,
                            parameters=technique_params
                        )
                        # Supposons que contextual_fallacies_result retourne une liste de sophismes contextuels.
                        # Exemple: [{"fallacy_type": "...", "context": "...", "explanation": "...", "confidence": 0.7}]
                        for fallacy_data in contextual_fallacies_result: # Ajuster selon la sortie réelle
                            results.append({
                                "type": "contextual_fallacies",
                                "extract_id": extract.get("id"),
                                "source": extract.get("source"),
                                "fallacy_type": fallacy_data.get("fallacy_type", ""),
                                "context": fallacy_data.get("context", ""), # ou "segment"
                                "explanation": fallacy_data.get("explanation", ""),
                                "confidence": fallacy_data.get("confidence", 0.7)
                            })

                elif technique_name == "fallacy_severity_evaluation": # Nouvelle gestion
                    # Cette technique pourrait nécessiter des sophismes déjà identifiés en entrée
                    # ou opérer sur le texte brut. À adapter selon la logique de l'agent.
                    # Supposons qu'elle opère sur le texte brut pour l'instant.
                    for extract in text_extracts:
                        extract_content = extract.get("content", "")
                        if not extract_content:
                            continue
                        severity_results = await self.agent.evaluate_fallacy_severity(
                            text=extract_content, # ou identified_fallacies
                            parameters=technique_params
                        )
                        for severity_data in severity_results: # Ajuster selon la sortie réelle
                            results.append({
                                "type": "fallacy_severity",
                                "extract_id": extract.get("id"),
                                "source": extract.get("source"),
                                **severity_data # Intégrer les données de sévérité
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
            
            # Calculer les métriques
            execution_time = time.time() - start_time
            metrics = {
                "execution_time": execution_time,
                "confidence": 0.8 if results else 0.0,
                "coverage": 1.0 if text_extracts and results else 0.0,
                "resource_usage": 0.6  # Valeur arbitraire pour l'exemple
            }
            
            # Mettre à jour les métriques dans l'état opérationnel
            self.update_metrics(task_id, metrics)
            
            # Déterminer le statut final
            status = "completed"
            if issues:
                status = "completed_with_issues"
            
            # Mettre à jour le statut de la tâche
            self.update_task_status(task_id, status, {
                "message": f"Traitement terminé avec statut: {status}",
                "results_count": len(results),
                "issues_count": len(issues)
            })
            
            # Formater et retourner le résultat
            return self.format_result(task, results, metrics, issues)
        
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de la tâche {task_id}: {e}")
            
            # Mettre à jour le statut de la tâche
            self.update_task_status(task_id, "failed", {
                "message": f"Erreur lors du traitement: {str(e)}",
                "exception": str(e)
            })
            
            # Calculer les métriques
            execution_time = time.time() - start_time
            metrics = {
                "execution_time": execution_time,
                "confidence": 0.0,
                "coverage": 0.0,
                "resource_usage": 0.5  # Valeur arbitraire pour l'exemple
            }
            
            # Mettre à jour les métriques dans l'état opérationnel
            self.update_metrics(task_id, metrics)
            
            # Retourner un résultat d'erreur
            return {
                "id": f"result-{task_id}",
                "task_id": task_id,
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
    
    # Les méthodes _identify_arguments, _detect_fallacies, _analyze_contextual_fallacies
    # sont supprimées car leurs fonctionnalités sont maintenant dans self.agent.

    async def explore_fallacy_hierarchy(self, current_pk: int) -> Dict[str, Any]: # Devient async
        """
        Explore la hiérarchie des sophismes.
        
        Args:
            current_pk: PK du nœud à explorer
            
        Returns:
            Résultat de l'exploration
        """
        if not self.initialized:
            self.logger.warning("Agent informel non initialisé. Impossible d'explorer la hiérarchie des sophismes.")
            return {"error": "Agent informel non initialisé"}
        
        if not self.agent: # Vérifier si self.agent est initialisé
             self.logger.error("self.agent non initialisé dans explore_fallacy_hierarchy")
             return {"error": "Agent non initialisé"}

        try:
            # Appeler la fonction de l'agent refactoré
            result = await self.agent.explore_fallacy_hierarchy(current_pk=str(current_pk)) # Appel à l'agent
            # Pas besoin de json.loads si l'agent retourne déjà un dict
            return result
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exploration de la hiérarchie des sophismes: {e}")
            return {"error": str(e)}
    
    def _extract_arguments(self, text: str) -> List[str]:
        """
        Extrait les arguments d'un texte.
        
        Args:
            text: Le texte à analyser
            
        Returns:
            Liste des arguments extraits
        """
        # Méthode simple pour diviser le texte en arguments
        # Dans une implémentation réelle, on utiliserait une méthode plus sophistiquée
        
        # Diviser le texte en paragraphes
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # Si pas de paragraphes, diviser par phrases
        if not paragraphs:
            # Diviser le texte en phrases
            sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
            
            # Regrouper les phrases en arguments (par exemple, 3 phrases par argument)
            arguments = []
            for i in range(0, len(sentences), 3):
                arg = '. '.join(sentences[i:i+3])
                if arg:
                    arguments.append(arg + '.')
            
            return arguments
        
        return paragraphs
    
    async def get_fallacy_details(self, fallacy_pk: int) -> Dict[str, Any]: # Devient async
        """
        Obtient les détails d'un sophisme.
        
        Args:
            fallacy_pk: PK du sophisme
            
        Returns:
            Détails du sophisme
        """
        if not self.initialized:
            self.logger.warning("Agent informel non initialisé. Impossible d'obtenir les détails du sophisme.")
            return {"error": "Agent informel non initialisé"}

        if not self.agent: # Vérifier si self.agent est initialisé
             self.logger.error("self.agent non initialisé dans get_fallacy_details")
             return {"error": "Agent non initialisé"}

        try:
            # Appeler la fonction de l'agent refactoré
            result = await self.agent.get_fallacy_details(fallacy_pk=str(fallacy_pk)) # Appel à l'agent
            # Pas besoin de json.loads si l'agent retourne déjà un dict
            return result
        except Exception as e:
            self.logger.error(f"Erreur lors de l'obtention des détails du sophisme: {e}")
            return {"error": str(e)}