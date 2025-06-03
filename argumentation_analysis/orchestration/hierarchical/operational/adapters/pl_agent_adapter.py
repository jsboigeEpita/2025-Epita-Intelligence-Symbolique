"""
Module d'adaptation de l'agent de logique propositionnelle pour l'architecture hiérarchique.

Ce module fournit un adaptateur qui permet à l'agent de logique propositionnelle existant
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

import semantic_kernel as sk # Kept for type hints if necessary
# from semantic_kernel.contents import ChatMessageContent, AuthorRole # Potentially unused
# from semantic_kernel.functions.kernel_arguments import KernelArguments # Potentially unused

from argumentation_analysis.orchestration.hierarchical.operational.agent_interface import OperationalAgent
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState

# Import de l'agent PL refactoré
from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent # Modifié
from argumentation_analysis.core.jvm_setup import initialize_jvm # Kept

from argumentation_analysis.paths import RESULTS_DIR



class PLAgentAdapter(OperationalAgent):
    """
    Adaptateur pour l'agent de logique propositionnelle.
    
    Cet adaptateur permet à l'agent de logique propositionnelle existant de fonctionner
    comme un agent opérationnel dans l'architecture hiérarchique.
    """
    
    def __init__(self, name: str = "PLAgent", operational_state: Optional[OperationalState] = None):
        """
        Initialise un nouvel adaptateur pour l'agent de logique propositionnelle.
        
        Args:
            name: Nom de l'agent
            operational_state: État opérationnel à utiliser. Si None, un nouvel état est créé.
        """
        super().__init__(name, operational_state)
        self.agent: Optional[PropositionalLogicAgent] = None # Agent refactoré, type mis à jour
        self.kernel: Optional[sk.Kernel] = None # Passé à initialize
        self.llm_service_id: Optional[str] = None # Passé à initialize
        self.initialized = False
        self.logger = logging.getLogger(f"PLAgentAdapter.{name}")
    
    async def initialize(self, kernel: sk.Kernel, llm_service_id: str): # Prend kernel et llm_service_id
        """
        Initialise l'agent de logique propositionnelle.

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
            self.logger.info("Initialisation de l'agent de logique propositionnelle refactoré...")
            
            # S'assurer que la JVM est démarrée
            jvm_ready = initialize_jvm()
            if not jvm_ready:
                self.logger.error("Échec du démarrage de la JVM.")
                return False
            
            # Utiliser le nom de classe corrigé et ajouter logic_type_name
            self.agent = PropositionalLogicAgent(
                kernel=self.kernel,
                agent_name=f"{self.name}_PLAgent",
                logic_type_name="propositional" # ou le type spécifique attendu par l'agent
            )
            await self.agent.setup_agent_components(llm_service_id=self.llm_service_id)

            if self.agent is None: # Vérifier self.agent
                self.logger.error("Échec de l'initialisation de l'agent PL.")
                return False
            
            self.initialized = True
            self.logger.info("Agent de logique propositionnelle refactoré initialisé avec succès.")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation de l'agent de logique propositionnelle refactoré: {e}")
            return False
    
    def get_capabilities(self) -> List[str]:
        """
        Retourne les capacités de l'agent de logique propositionnelle.
        
        Returns:
            Liste des capacités de l'agent
        """
        return [
            "formal_logic",
            "propositional_logic",
            "validity_checking",
            "consistency_analysis"
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
                self.logger.error("Kernel ou llm_service_id non configuré avant process_task pour l'agent PL.")
                return {
                    "id": f"result-{task.get('id')}",
                    "task_id": task.get("id"),
                    "tactical_task_id": task.get("tactical_task_id"),
                    "status": "failed",
                    "outputs": {},
                    "metrics": {},
                    "issues": [{
                        "type": "configuration_error",
                        "description": "Kernel ou llm_service_id non configuré pour l'agent PL",
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
                        "description": "Échec de l'initialisation de l'agent de logique propositionnelle",
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
                if technique_name == "propositional_logic_formalization":
                    # Formaliser les arguments en logique propositionnelle
                    for extract in text_extracts:
                        extract_content = extract.get("content", "")
                        if not extract_content:
                            continue
                        
                        # Appel à la méthode de l'agent refactoré
                        formalization_result = await self.agent.formalize_to_pl(
                            text=extract_content,
                            parameters=technique_params
                        )
                        # Supposons que formalization_result est une chaîne (le belief_set) ou None
                        if formalization_result:
                            results.append({
                                "type": "formal_analyses", # ou "pl_formalization"
                                "extract_id": extract.get("id"),
                                "source": extract.get("source"),
                                "belief_set": formalization_result,
                                "formalism": "propositional_logic",
                                "confidence": 0.8
                            })
                        else:
                            issues.append({
                                "type": "formalization_error",
                                "description": "Échec de la formalisation en logique propositionnelle par l'agent.",
                                "severity": "medium",
                                "extract_id": extract.get("id")
                            })
                
                elif technique_name == "validity_checking":
                    for extract in text_extracts:
                        extract_content = extract.get("content", "")
                        if not extract_content:
                            continue
                        
                        # Appel à la méthode de l'agent refactoré
                        # Cette méthode devrait gérer la formalisation, la génération de requêtes et leur exécution.
                        validity_analysis_result = await self.agent.check_pl_validity(
                            text=extract_content,
                            parameters=technique_params
                        )
                        # Supposons que validity_analysis_result est un dict avec belief_set, queries, results, interpretation
                        if validity_analysis_result and validity_analysis_result.get("belief_set"):
                            results.append({
                                "type": "validity_analysis",
                                "extract_id": extract.get("id"),
                                "source": extract.get("source"),
                                "belief_set": validity_analysis_result.get("belief_set"),
                                "queries": validity_analysis_result.get("queries", []),
                                "results": validity_analysis_result.get("results", []), # Note: clé "results" au lieu de RESULTS_DIR
                                "interpretation": validity_analysis_result.get("interpretation", ""),
                                "confidence": validity_analysis_result.get("confidence", 0.8)
                            })
                        else:
                            issues.append({
                                "type": "validity_checking_error",
                                "description": "Échec de la vérification de validité par l'agent.",
                                "severity": "medium",
                                "extract_id": extract.get("id"),
                                "details": validity_analysis_result.get("error_details") if validity_analysis_result else "No details"
                            })
                
                elif technique_name == "consistency_checking":
                    for extract in text_extracts:
                        extract_content = extract.get("content", "")
                        if not extract_content:
                            continue
                        
                        # Appel à la méthode de l'agent refactoré
                        consistency_analysis_result = await self.agent.check_pl_consistency(
                            text=extract_content, # ou un belief_set pré-formalisé si disponible
                            parameters=technique_params
                        )
                        # Supposons que consistency_analysis_result est un dict avec belief_set, is_consistent, explanation
                        if consistency_analysis_result and "is_consistent" in consistency_analysis_result:
                            results.append({
                                "type": "consistency_analysis",
                                "extract_id": extract.get("id"),
                                "source": extract.get("source"),
                                "belief_set": consistency_analysis_result.get("belief_set"), # L'agent pourrait retourner le belief_set utilisé
                                "is_consistent": consistency_analysis_result.get("is_consistent", False),
                                "explanation": consistency_analysis_result.get("explanation", ""),
                                "confidence": consistency_analysis_result.get("confidence", 0.8)
                            })
                        else:
                            issues.append({
                                "type": "consistency_checking_error",
                                "description": "Échec de la vérification de cohérence par l'agent.",
                                "severity": "medium",
                                "extract_id": extract.get("id"),
                                "details": consistency_analysis_result.get("error_details") if consistency_analysis_result else "No details"
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
                "resource_usage": 0.7  # Valeur arbitraire pour l'exemple
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
    
    # Les méthodes _text_to_belief_set, _generate_and_execute_queries, _generate_queries,
    # _execute_query, _interpret_results, _check_consistency sont supprimées
    # car leurs fonctionnalités sont maintenant dans self.agent.
    pass # Placeholder if no other methods are defined after this.