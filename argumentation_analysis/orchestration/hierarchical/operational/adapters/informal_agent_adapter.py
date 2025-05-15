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

import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from semantic_kernel.functions.kernel_arguments import KernelArguments

from argumentation_analysis.orchestration.hierarchical.operational.agent_interface import OperationalAgent
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState

# Import de l'agent informel existant
from argumentation_analysis.agents.core.informal.informal_definitions import InformalAnalysisPlugin, setup_informal_kernel, INFORMAL_AGENT_INSTRUCTIONS
from argumentation_analysis.core.llm_service import create_llm_service

# Import des outils d'analyse rhétorique améliorés
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
        self.kernel = None
        self.informal_plugin = None
        self.informal_agent = None
        self.llm_service = None
        
        # Outils d'analyse rhétorique améliorés
        self.complex_fallacy_analyzer = None
        self.contextual_fallacy_analyzer = None
        self.fallacy_severity_evaluator = None
        
        self.initialized = False
        self.logger = logging.getLogger(f"InformalAgentAdapter.{name}")
    
    async def initialize(self):
        """
        Initialise l'agent informel.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        if self.initialized:
            return True
        
        try:
            self.logger.info("Initialisation de l'agent informel...")
            
            # Créer le service LLM
            self.llm_service = create_llm_service()
            if not self.llm_service:
                self.logger.error("Échec de la création du service LLM.")
                return False
            
            # Créer le kernel
            self.kernel = sk.Kernel()
            self.kernel.add_service(self.llm_service)
            
            # Créer le plugin informel
            self.informal_plugin = InformalAnalysisPlugin()
            
            # Initialiser les outils d'analyse rhétorique améliorés
            self.complex_fallacy_analyzer = EnhancedComplexFallacyAnalyzer()
            self.contextual_fallacy_analyzer = EnhancedContextualFallacyAnalyzer()
            self.fallacy_severity_evaluator = EnhancedFallacySeverityEvaluator()
            
            # Configurer le kernel pour l'agent informel
            setup_informal_kernel(self.kernel, self.llm_service)
            
            # Créer l'agent informel
            prompt_exec_settings = self.kernel.get_prompt_execution_settings_from_service_id(self.llm_service.service_id)
            self.informal_agent = sk.ChatCompletionAgent(
                kernel=self.kernel,
                service=self.llm_service,
                name="InformalAgent",
                instructions=INFORMAL_AGENT_INSTRUCTIONS,
                arguments=KernelArguments(settings=prompt_exec_settings)
            )
            
            self.initialized = True
            self.logger.info("Agent informel initialisé avec succès.")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation de l'agent informel: {e}")
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
                        
                        arguments = await self._identify_arguments(extract_content, technique_params)
                        
                        for arg in arguments:
                            results.append({
                                "type": "identified_arguments",
                                "extract_id": extract.get("id"),
                                "source": extract.get("source"),
                                "premises": arg.get("premises", []),
                                "conclusion": arg.get("conclusion", ""),
                                "confidence": arg.get("confidence", 0.8)
                            })
                
                elif technique_name == "fallacy_pattern_matching":
                    # Détecter les sophismes dans le texte
                    for extract in text_extracts:
                        extract_content = extract.get("content", "")
                        if not extract_content:
                            continue
                        
                        # Utiliser l'analyseur de sophismes amélioré
                        arguments = self._extract_arguments(extract_content)
                        context = technique_params.get("context", "général")
                        
                        # Détecter les sophismes avec l'outil amélioré
                        fallacies = []
                        if self.contextual_fallacy_analyzer:
                            analysis_results = self.contextual_fallacy_analyzer.analyze_contextual_fallacies(extract_content, context)
                            for fallacy in analysis_results.get("identified_fallacies", []):
                                fallacies.append({
                                    "fallacy_type": fallacy.get("fallacy_type", ""),
                                    "segment": fallacy.get("segment", ""),
                                    "explanation": fallacy.get("explanation", ""),
                                    "confidence": fallacy.get("confidence", 0.7)
                                })
                        else:
                            # Utiliser la méthode originale si l'outil amélioré n'est pas disponible
                            fallacies = await self._detect_fallacies(extract_content, technique_params)
                        
                        for fallacy in fallacies:
                            results.append({
                                "type": "identified_fallacies",
                                "extract_id": extract.get("id"),
                                "source": extract.get("source"),
                                "fallacy_type": fallacy.get("fallacy_type", ""),
                                "segment": fallacy.get("segment", ""),
                                "explanation": fallacy.get("explanation", ""),
                                "confidence": fallacy.get("confidence", 0.7)
                            })
                
                elif technique_name == "contextual_fallacy_analysis":
                    # Analyser les sophismes dans le contexte
                    for extract in text_extracts:
                        extract_content = extract.get("content", "")
                        if not extract_content:
                            continue
                        
                        # Utiliser l'analyseur de sophismes contextuels amélioré
                        arguments = self._extract_arguments(extract_content)
                        context = technique_params.get("context", "général")
                        
                        # Analyser les sophismes contextuels avec l'outil amélioré
                        contextual_fallacies = []
                        if self.complex_fallacy_analyzer:
                            analysis_results = self.complex_fallacy_analyzer.analyze_inter_argument_coherence(arguments, context)
                            for fallacy in analysis_results.get("contradictions", []):
                                contextual_fallacies.append({
                                    "fallacy_type": fallacy.get("contradiction_type", "Contradiction contextuelle"),
                                    "context": fallacy.get("description", ""),
                                    "explanation": fallacy.get("explanation", ""),
                                    "confidence": fallacy.get("confidence", 0.7)
                                })
                        else:
                            # Utiliser la méthode originale si l'outil amélioré n'est pas disponible
                            contextual_fallacies = await self._analyze_contextual_fallacies(extract_content, technique_params)
                        
                        for fallacy in contextual_fallacies:
                            results.append({
                                "type": "contextual_fallacies",
                                "extract_id": extract.get("id"),
                                "source": extract.get("source"),
                                "fallacy_type": fallacy.get("fallacy_type", ""),
                                "context": fallacy.get("context", ""),
                                "explanation": fallacy.get("explanation", ""),
                                "confidence": fallacy.get("confidence", 0.7)
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
    
    async def _identify_arguments(self, text: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identifie les arguments dans un texte.
        
        Args:
            text: Le texte à analyser
            parameters: Les paramètres d'identification
            
        Returns:
            Liste des arguments identifiés
        """
        # Vérifier si l'agent est initialisé
        if not self.initialized:
            await self.initialize()
        
        try:
            # Créer un message de chat pour l'agent
            chat_message = ChatMessageContent(
                role=AuthorRole.USER,
                content=f"Identifie les arguments dans ce texte:\n\n{text}"
            )
            
            # Appeler l'agent informel
            response_content = ""
            async for chunk in self.informal_agent.invoke([chat_message]):
                if hasattr(chunk, 'content') and chunk.content:
                    response_content = chunk.content
                    break  # Prendre seulement la première réponse complète
            
            # Analyser la réponse pour extraire les arguments
            arguments = []
            
            # Rechercher un bloc JSON dans la réponse
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_content)
            if json_match:
                try:
                    json_data = json.loads(json_match.group(1))
                    if isinstance(json_data, list):
                        arguments = json_data
                    elif isinstance(json_data, dict) and "arguments" in json_data:
                        arguments = json_data["arguments"]
                except json.JSONDecodeError:
                    pass
            
            # Si aucun JSON n'est trouvé, essayer d'extraire les arguments manuellement
            if not arguments:
                # Rechercher les arguments dans le texte
                arg_matches = re.finditer(r'Argument\s+(\d+):\s*\n\s*Prémisses?\s*:\s*(.*?)\n\s*Conclusion\s*:\s*(.*?)(?:\n|$)', 
                                         response_content, re.DOTALL)
                
                for match in arg_matches:
                    arg_num = match.group(1)
                    premises_text = match.group(2).strip()
                    conclusion = match.group(3).strip()
                    
                    # Extraire les prémisses individuelles
                    premises = []
                    for premise in re.split(r'\n\s*-\s*|\n\s*\d+\.\s*', premises_text):
                        premise = premise.strip()
                        if premise:
                            premises.append(premise)
                    
                    arguments.append({
                        "id": f"arg-{arg_num}",
                        "premises": premises,
                        "conclusion": conclusion,
                        "confidence": 0.8  # Valeur arbitraire pour l'exemple
                    })
            
            return arguments
        
        except Exception as e:
            self.logger.error(f"Erreur lors de l'identification des arguments: {e}")
            return []
    
    async def _detect_fallacies(self, text: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Détecte les sophismes dans un texte.
        
        Args:
            text: Le texte à analyser
            parameters: Les paramètres de détection
            
        Returns:
            Liste des sophismes détectés
        """
        # Vérifier si l'agent est initialisé
        if not self.initialized:
            await self.initialize()
        
        try:
            # Créer un message de chat pour l'agent
            chat_message = ChatMessageContent(
                role=AuthorRole.USER,
                content=f"Analyse ce texte pour détecter les sophismes:\n\n{text}"
            )
            
            # Appeler l'agent informel
            response_content = ""
            async for chunk in self.informal_agent.invoke([chat_message]):
                if hasattr(chunk, 'content') and chunk.content:
                    response_content = chunk.content
                    break  # Prendre seulement la première réponse complète
            
            # Analyser la réponse pour extraire les sophismes
            fallacies = []
            
            # Rechercher un bloc JSON dans la réponse
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_content)
            if json_match:
                try:
                    json_data = json.loads(json_match.group(1))
                    if isinstance(json_data, list):
                        fallacies = json_data
                    elif isinstance(json_data, dict) and "fallacies" in json_data:
                        fallacies = json_data["fallacies"]
                except json.JSONDecodeError:
                    pass
            
            # Si aucun JSON n'est trouvé, essayer d'extraire les sophismes manuellement
            if not fallacies:
                # Rechercher les sophismes dans le texte
                fallacy_matches = re.finditer(r'Sophisme\s+(\d+):\s*\n\s*Type\s*:\s*(.*?)\n\s*Segment\s*:\s*(.*?)\n\s*Explication\s*:\s*(.*?)(?:\n\s*Sophisme|$)', 
                                            response_content, re.DOTALL)
                
                for match in fallacy_matches:
                    fallacy_num = match.group(1)
                    fallacy_type = match.group(2).strip()
                    segment = match.group(3).strip()
                    explanation = match.group(4).strip()
                    
                    fallacies.append({
                        "id": f"fallacy-{fallacy_num}",
                        "fallacy_type": fallacy_type,
                        "segment": segment,
                        "explanation": explanation,
                        "confidence": 0.7  # Valeur arbitraire pour l'exemple
                    })
            
            return fallacies
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la détection des sophismes: {e}")
            return []
    
    async def _analyze_contextual_fallacies(self, text: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyse les sophismes dans le contexte.
        
        Args:
            text: Le texte à analyser
            parameters: Les paramètres d'analyse
            
        Returns:
            Liste des sophismes contextuels
        """
        # Vérifier si l'agent est initialisé
        if not self.initialized:
            await self.initialize()
        
        try:
            # Créer un message de chat pour l'agent
            chat_message = ChatMessageContent(
                role=AuthorRole.USER,
                content=f"Analyse ce texte pour détecter les sophismes contextuels:\n\n{text}"
            )
            
            # Appeler l'agent informel
            response_content = ""
            async for chunk in self.informal_agent.invoke([chat_message]):
                if hasattr(chunk, 'content') and chunk.content:
                    response_content = chunk.content
                    break  # Prendre seulement la première réponse complète
            
            # Analyser la réponse pour extraire les sophismes contextuels
            contextual_fallacies = []
            
            # Rechercher un bloc JSON dans la réponse
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_content)
            if json_match:
                try:
                    json_data = json.loads(json_match.group(1))
                    if isinstance(json_data, list):
                        contextual_fallacies = json_data
                    elif isinstance(json_data, dict) and "contextual_fallacies" in json_data:
                        contextual_fallacies = json_data["contextual_fallacies"]
                except json.JSONDecodeError:
                    pass
            
            # Si aucun JSON n'est trouvé, essayer d'extraire les sophismes contextuels manuellement
            if not contextual_fallacies:
                # Rechercher les sophismes contextuels dans le texte
                fallacy_matches = re.finditer(r'Sophisme contextuel\s+(\d+):\s*\n\s*Type\s*:\s*(.*?)\n\s*Contexte\s*:\s*(.*?)\n\s*Explication\s*:\s*(.*?)(?:\n\s*Sophisme|$)', 
                                            response_content, re.DOTALL)
                
                for match in fallacy_matches:
                    fallacy_num = match.group(1)
                    fallacy_type = match.group(2).strip()
                    context = match.group(3).strip()
                    explanation = match.group(4).strip()
                    
                    contextual_fallacies.append({
                        "id": f"ctx-fallacy-{fallacy_num}",
                        "fallacy_type": fallacy_type,
                        "context": context,
                        "explanation": explanation,
                        "confidence": 0.7  # Valeur arbitraire pour l'exemple
                    })
            
            return contextual_fallacies
        
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse des sophismes contextuels: {e}")
            return []
    
    def explore_fallacy_hierarchy(self, current_pk: int) -> Dict[str, Any]:
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
        
        try:
            # Appeler la fonction du plugin
            result_json = self.informal_plugin.explore_fallacy_hierarchy(str(current_pk))
            
            # Convertir le résultat JSON en dictionnaire
            result = json.loads(result_json)
            
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
    
    def get_fallacy_details(self, fallacy_pk: int) -> Dict[str, Any]:
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
        
        try:
            # Appeler la fonction du plugin
            result_json = self.informal_plugin.get_fallacy_details(str(fallacy_pk))
            
            # Convertir le résultat JSON en dictionnaire
            result = json.loads(result_json)
            
            return result
        except Exception as e:
            self.logger.error(f"Erreur lors de l'obtention des détails du sophisme: {e}")
            return {"error": str(e)}