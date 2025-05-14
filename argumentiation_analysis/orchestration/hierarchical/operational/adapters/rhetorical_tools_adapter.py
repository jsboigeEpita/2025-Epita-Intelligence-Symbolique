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

from argumentiation_analysis.orchestration.hierarchical.operational.agent_interface import OperationalAgent
from argumentiation_analysis.orchestration.hierarchical.operational.state import OperationalState

# Import des outils d'analyse rhétorique améliorés
from argumentiation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer
from argumentiation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer
from argumentiation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator

# Import des nouveaux outils d'analyse rhétorique
from argumentiation_analysis.agents.tools.analysis.new.argument_structure_visualizer import ArgumentStructureVisualizer
from argumentiation_analysis.agents.tools.analysis.new.argument_coherence_evaluator import ArgumentCoherenceEvaluator
from argumentiation_analysis.agents.tools.analysis.new.semantic_argument_analyzer import SemanticArgumentAnalyzer
from argumentiation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import ContextualFallacyDetector

from argumentiation_analysis.paths import RESULTS_DIR



class RhetoricalToolsAdapter(OperationalAgent):
    """
    Adaptateur pour les outils d'analyse rhétorique.
    
    Cet adaptateur permet aux outils d'analyse rhétorique améliorés et nouveaux
    de fonctionner comme un agent opérationnel dans l'architecture hiérarchique.
    """
    
    def __init__(self, name: str = "RhetoricalTools", operational_state: Optional[OperationalState] = None):
        """
        Initialise un nouvel adaptateur pour les outils d'analyse rhétorique.
        
        Args:
            name: Nom de l'agent
            operational_state: État opérationnel à utiliser. Si None, un nouvel état est créé.
        """
        super().__init__(name, operational_state)
        self.logger = logging.getLogger(f"RhetoricalToolsAdapter.{name}")
        
        # Initialiser les outils d'analyse rhétorique améliorés
        self.complex_fallacy_analyzer = None
        self.contextual_fallacy_analyzer = None
        self.fallacy_severity_evaluator = None
        
        # Initialiser les nouveaux outils d'analyse rhétorique
        self.argument_structure_visualizer = None
        self.argument_coherence_evaluator = None
        self.semantic_argument_analyzer = None
        self.contextual_fallacy_detector = None
        
        self.initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialise les outils d'analyse rhétorique.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        if self.initialized:
            return True
        
        try:
            self.logger.info("Initialisation des outils d'analyse rhétorique...")
            
            # Initialiser les outils d'analyse rhétorique améliorés
            self.complex_fallacy_analyzer = EnhancedComplexFallacyAnalyzer()
            self.contextual_fallacy_analyzer = EnhancedContextualFallacyAnalyzer()
            self.fallacy_severity_evaluator = EnhancedFallacySeverityEvaluator()
            
            # Initialiser les nouveaux outils d'analyse rhétorique
            self.argument_structure_visualizer = ArgumentStructureVisualizer()
            self.argument_coherence_evaluator = ArgumentCoherenceEvaluator()
            self.semantic_argument_analyzer = SemanticArgumentAnalyzer()
            self.contextual_fallacy_detector = ContextualFallacyDetector()
            
            self.initialized = True
            self.logger.info("Outils d'analyse rhétorique initialisés avec succès.")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation des outils d'analyse rhétorique: {e}")
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
            success = await self.initialize()
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
                        analysis_results = self.complex_fallacy_analyzer.detect_composite_fallacies(arguments, context)
                        
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
                        analysis_results = self.contextual_fallacy_analyzer.analyze_contextual_fallacies(extract_content, context)
                        
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
                        evaluation_results = self.fallacy_severity_evaluator.evaluate_fallacy_severity(arguments, context)
                        
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
                        visualization_results = self.argument_structure_visualizer.visualize_argument_structure(
                            arguments, context, output_format
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
                        evaluation_results = self.argument_coherence_evaluator.evaluate_argument_coherence(arguments, context)
                        
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
                        analysis_results = self.semantic_argument_analyzer.analyze_multiple_arguments(arguments)
                        
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
                        detection_results = self.contextual_fallacy_detector.detect_contextual_fallacies(arguments, context)
                        
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