"""
Module d'adaptation des outils d'analyse rhétorique pour l'architecture hiérarchique.

Ce module fournit un adaptateur qui permet aux outils d'analyse rhétorique améliorés
de fonctionner dans le cadre de l'architecture hiérarchique à trois niveaux.
"""

import os
import re
import json
import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path

from argumentation_analysis.orchestration.hierarchical.operational.agent_interface import OperationalAgent
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState
from argumentation_analysis.core.bootstrap import ProjectContext # Importer ProjectContext

# Placeholder pour l'agent rhétorique refactoré
# from argumentation_analysis.agents.core.rhetorical.rhetorical_agent import RhetoricalAnalysisAgent # TODO: Create this agent

# Les imports des outils spécifiques pourraient être retirés si l'agent les encapsule complètement.
# Pour l'instant, on les garde au cas où l'adaptateur aurait besoin de types ou de constantes.
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator
from argumentation_analysis.agents.tools.analysis.new.argument_structure_visualizer import ArgumentStructureVisualizer
from argumentation_analysis.agents.tools.analysis.new.argument_coherence_evaluator import ArgumentCoherenceEvaluator
from argumentation_analysis.agents.tools.analysis.new.semantic_argument_analyzer import SemanticArgumentAnalyzer
# L'import direct de ContextualFallacyDetector n'est plus nécessaire ici, il est géré par ProjectContext
# from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import ContextualFallacyDetector


from argumentation_analysis.paths import RESULTS_DIR


# Supposons qu'un agent RhetoricalAnalysisAgent sera créé et gérera ces outils.
# Pour l'instant, nous allons simuler son interface.
class MockRhetoricalAnalysisAgent:
    def __init__(self, kernel, agent_name, project_context: ProjectContext):
        self.kernel = kernel
        self.agent_name = agent_name
        self.logger = logging.getLogger(agent_name)
        self.project_context = project_context
        # L'initialisation se fait maintenant de manière paresseuse via le contexte
        self.complex_fallacy_analyzer = None # Remplacer par un getter si nécessaire
        self.contextual_fallacy_analyzer = None # Remplacer par un getter si nécessaire
        self.fallacy_severity_evaluator = None # Remplacer par un getter si nécessaire
        self.argument_structure_visualizer = None # Remplacer par un getter si nécessaire
        self.argument_coherence_evaluator = None # Remplacer par un getter si nécessaire
        self.semantic_argument_analyzer = None # Remplacer par un getter si nécessaire
        self.contextual_fallacy_detector = self.project_context.get_fallacy_detector()

    async def setup_agent_components(self, llm_service_id):
        self.logger.info(f"MockRhetoricalAnalysisAgent setup_agent_components called with {llm_service_id}")
        # En réalité, ici on configurerait les outils avec le kernel/llm_service si besoin.
        pass

    async def analyze_complex_fallacies(self, arguments: List[str], context: str, parameters: Optional[Dict] = None) -> Any:
        return self.complex_fallacy_analyzer.detect_composite_fallacies(arguments, context)

    async def analyze_contextual_fallacies(self, text: str, context: str, parameters: Optional[Dict] = None) -> Any:
        return self.contextual_fallacy_analyzer.analyze_contextual_fallacies(text, context)

    async def evaluate_fallacy_severity(self, arguments: List[str], context: str, parameters: Optional[Dict] = None) -> Any:
        return self.fallacy_severity_evaluator.evaluate_fallacy_severity(arguments, context)

    async def visualize_argument_structure(self, arguments: List[str], context: str, output_format: str = "json", parameters: Optional[Dict] = None) -> Any:
        return self.argument_structure_visualizer.visualize_argument_structure(arguments, context, output_format)

    async def evaluate_argument_coherence(self, arguments: List[str], context: str, parameters: Optional[Dict] = None) -> Any:
        return self.argument_coherence_evaluator.evaluate_argument_coherence(arguments, context)

    async def analyze_semantic_arguments(self, arguments: List[str], parameters: Optional[Dict] = None) -> Any:
        return self.semantic_argument_analyzer.analyze_multiple_arguments(arguments)
    
    async def detect_contextual_fallacies(self, arguments: List[str], context: str, parameters: Optional[Dict] = None) -> Any:
        return self.contextual_fallacy_detector.detect_contextual_fallacies(arguments, context)

# Remplacer par le vrai agent quand il sera créé
RhetoricalAnalysisAgent = MockRhetoricalAnalysisAgent



class RhetoricalToolsAdapter(OperationalAgent):
    """
    Adaptateur pour les outils d'analyse rhétorique.
    
    Cet adaptateur permet aux outils d'analyse rhétorique améliorés et nouveaux
    de fonctionner comme un agent opérationnel dans l'architecture hiérarchique.
    """
    
    def __init__(self, name: str = "RhetoricalTools", operational_state: Optional[OperationalState] = None, project_context: Optional[ProjectContext] = None):
        """
        Initialise un nouvel adaptateur pour les outils d'analyse rhétorique.
        
        Args:
            name: Nom de l'agent
            operational_state: État opérationnel à utiliser. Si None, un nouvel état est créé.
            project_context: Le contexte global du projet.
        """
        super().__init__(name, operational_state)
        self.logger = logging.getLogger(f"RhetoricalToolsAdapter.{name}")
        
        self.agent: Optional[RhetoricalAnalysisAgent] = None # Agent refactoré (ou son mock)
        self.kernel: Optional[Any] = None # Passé à initialize
        self.llm_service_id: Optional[str] = None # Passé à initialize
        self.project_context = project_context
        
        self.initialized = False
    
    async def initialize(self, kernel: Any, llm_service_id: str, project_context: ProjectContext) -> bool:
        """
        Initialise l'agent d'analyse rhétorique.
        
        Args:
            kernel: Le kernel Semantic Kernel à utiliser.
            llm_service_id: L'ID du service LLM à utiliser.
            project_context: Le contexte global du projet.

        Returns:
            True si l'initialisation a réussi, False sinon
        """
        if self.initialized:
            return True
        
        self.kernel = kernel
        self.llm_service_id = llm_service_id
        self.project_context = project_context

        if not self.project_context:
            self.logger.error("ProjectContext non fourni, impossible d'initialiser RhetoricalToolsAdapter.")
            return False

        try:
            self.logger.info("Initialisation de l'agent d'analyse rhétorique...")
            
            self.agent = RhetoricalAnalysisAgent(kernel=self.kernel, agent_name=f"{self.name}_RhetoricalAgent", project_context=self.project_context)
            await self.agent.setup_agent_components(llm_service_id=self.llm_service_id)
            
            if self.agent is None:
                 self.logger.error("Échec de l'initialisation de l'agent d'analyse rhétorique.")
                 return False

            self.initialized = True
            self.logger.info("Agent d'analyse rhétorique initialisé avec succès.")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation de l'agent d'analyse rhétorique: {e}")
            return False
    
    def get_capabilities(self) -> List[str]:
        """
        Retourne les capacités des outils d'analyse rhétorique.
        
        Returns:
            Liste des capacités des outils
        """
        return [
            "complex_fallacy_analysis",
            "contextual_fallacy_analysis",
            "fallacy_severity_evaluation",
            "argument_structure_visualization",
            "argument_coherence_evaluation",
            "semantic_argument_analysis",
            "contextual_fallacy_detection"
        ]
    
    def can_process_task(self, task: Dict[str, Any]) -> bool:
        """
        Vérifie si les outils peuvent traiter une tâche donnée.
        
        Args:
            task: La tâche à vérifier
            
        Returns:
            True si les outils peuvent traiter la tâche, False sinon
        """
        # Vérifier si les outils sont initialisés
        if not self.initialized:
            return False
        
        # Vérifier si les capacités requises sont fournies par ces outils
        required_capabilities = task.get("required_capabilities", [])
        agent_capabilities = self.get_capabilities()
        
        # Vérifier si au moins une des capacités requises est fournie par les outils
        return any(cap in agent_capabilities for cap in required_capabilities)
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite une tâche opérationnelle.
        
        Args:
            task: La tâche opérationnelle à traiter
            
        Returns:
            Le résultat du traitement de la tâche
        """
        # Vérifier si les outils sont initialisés
        if not self.initialized:
            if self.kernel is None or self.llm_service_id is None:
                self.logger.error("Kernel ou llm_service_id non configuré avant process_task pour RhetoricalToolsAdapter.")
                return {
                    "id": f"result-{task.get('id')}",
                    "task_id": task.get("id"),
                    "tactical_task_id": task.get("tactical_task_id"),
                    "status": "failed",
                    "outputs": {},
                    "metrics": {},
                    "issues": [{
                        "type": "configuration_error",
                        "description": "Kernel ou llm_service_id non configuré pour RhetoricalToolsAdapter",
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
                        "description": "Échec de l'initialisation des outils d'analyse rhétorique",
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
                if technique_name == "complex_fallacy_analysis":
                    # Analyser les sophismes complexes dans le texte
                    for extract in text_extracts:
                        extract_content = extract.get("content", "")
                        if not extract_content:
                            continue
                        
                        # Convertir le contenu en liste d'arguments
                        arguments = self._extract_arguments(extract_content)
                        
                        # Analyser les sophismes complexes
                        context = technique_params.get("context", "général")
                        analysis_results = await self.agent.analyze_complex_fallacies(
                            arguments=arguments,
                            context=context,
                            parameters=technique_params
                        )
                        
                        results.append({
                            "type": "complex_fallacy_analysis",
                            "extract_id": extract.get("id"),
                            "source": extract.get("source"),
                            "analysis_results": analysis_results,
                            "confidence": 0.8
                        })
                
                elif technique_name == "contextual_fallacy_analysis":
                    # Analyser les sophismes contextuels dans le texte
                    for extract in text_extracts:
                        extract_content = extract.get("content", "")
                        if not extract_content:
                            continue
                        
                        # Analyser les sophismes contextuels
                        context = technique_params.get("context", "général")
                        analysis_results = await self.agent.analyze_contextual_fallacies(
                            text=extract_content,
                            context=context,
                            parameters=technique_params
                        )
                        
                        results.append({
                            "type": "contextual_fallacy_analysis",
                            "extract_id": extract.get("id"),
                            "source": extract.get("source"),
                            "analysis_results": analysis_results,
                            "confidence": 0.8
                        })
                
                elif technique_name == "fallacy_severity_evaluation":
                    # Évaluer la gravité des sophismes dans le texte
                    for extract in text_extracts:
                        extract_content = extract.get("content", "")
                        if not extract_content:
                            continue
                        
                        # Convertir le contenu en liste d'arguments
                        arguments = self._extract_arguments(extract_content)
                        
                        # Évaluer la gravité des sophismes
                        context = technique_params.get("context", "général")
                        evaluation_results = await self.agent.evaluate_fallacy_severity(
                            arguments=arguments,
                            context=context,
                            parameters=technique_params
                        )
                        
                        results.append({
                            "type": "fallacy_severity_evaluation",
                            "extract_id": extract.get("id"),
                            "source": extract.get("source"),
                            "evaluation_results": evaluation_results,
                            "confidence": 0.8
                        })
                
                elif technique_name == "argument_structure_visualization":
                    # Visualiser la structure des arguments dans le texte
                    for extract in text_extracts:
                        extract_content = extract.get("content", "")
                        if not extract_content:
                            continue
                        
                        # Convertir le contenu en liste d'arguments
                        arguments = self._extract_arguments(extract_content)
                        
                        # Visualiser la structure des arguments
                        context = technique_params.get("context", "général")
                        output_format = technique_params.get("output_format", "json")
                        visualization_results = await self.agent.visualize_argument_structure(
                            arguments=arguments,
                            context=context,
                            output_format=output_format,
                            parameters=technique_params
                        )
                        
                        results.append({
                            "type": "argument_structure_visualization",
                            "extract_id": extract.get("id"),
                            "source": extract.get("source"),
                            "visualization_results": visualization_results,
                            "confidence": 0.8
                        })
                
                elif technique_name == "argument_coherence_evaluation":
                    # Évaluer la cohérence des arguments dans le texte
                    for extract in text_extracts:
                        extract_content = extract.get("content", "")
                        if not extract_content:
                            continue
                        
                        # Convertir le contenu en liste d'arguments
                        arguments = self._extract_arguments(extract_content)
                        
                        # Évaluer la cohérence des arguments
                        context = technique_params.get("context", "général")
                        evaluation_results = await self.agent.evaluate_argument_coherence(
                            arguments=arguments,
                            context=context,
                            parameters=technique_params
                        )
                        
                        results.append({
                            "type": "argument_coherence_evaluation",
                            "extract_id": extract.get("id"),
                            "source": extract.get("source"),
                            "evaluation_results": evaluation_results,
                            "confidence": 0.8
                        })
                
                elif technique_name == "semantic_argument_analysis":
                    # Analyser la sémantique des arguments dans le texte
                    for extract in text_extracts:
                        extract_content = extract.get("content", "")
                        if not extract_content:
                            continue
                        
                        # Convertir le contenu en liste d'arguments
                        arguments = self._extract_arguments(extract_content)
                        
                        # Analyser la sémantique des arguments
                        analysis_results = await self.agent.analyze_semantic_arguments(
                            arguments=arguments,
                            parameters=technique_params
                        )
                        
                        results.append({
                            "type": "semantic_argument_analysis",
                            "extract_id": extract.get("id"),
                            "source": extract.get("source"),
                            "analysis_results": analysis_results,
                            "confidence": 0.8
                        })
                
                elif technique_name == "contextual_fallacy_detection":
                    # Détecter les sophismes contextuels dans le texte
                    for extract in text_extracts:
                        extract_content = extract.get("content", "")
                        if not extract_content:
                            continue
                        
                        # Convertir le contenu en liste d'arguments
                        arguments = self._extract_arguments(extract_content)
                        
                        # Détecter les sophismes contextuels
                        context = technique_params.get("context", "général")
                        detection_results = await self.agent.detect_contextual_fallacies(
                            arguments=arguments,
                            context=context,
                            parameters=technique_params
                        )
                        
                        results.append({
                            "type": "contextual_fallacy_detection",
                            "extract_id": extract.get("id"),
                            "source": extract.get("source"),
                            "detection_results": detection_results,
                            "confidence": 0.8
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
    
    def format_result(self, task: Dict[str, Any], results: List[Dict[str, Any]], metrics: Dict[str, Any], issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Formate le résultat du traitement d'une tâche.
        
        Args:
            task: La tâche traitée
            results: Les résultats du traitement
            metrics: Les métriques du traitement
            issues: Les problèmes rencontrés
            
        Returns:
            Le résultat formaté
        """
        return {
            "id": f"result-{task.get('id')}",
            "task_id": task.get("id"),
            "tactical_task_id": task.get("tactical_task_id"),
            "status": "completed_with_issues" if issues else "completed",
            "outputs": {
                RESULTS_DIR: results
            },
            "metrics": metrics,
            "issues": issues
        }