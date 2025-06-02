"""
Module définissant l'interface entre les niveaux tactique et opérationnel.

Cette interface définit comment les plans tactiques sont traduits en tâches opérationnelles
et comment les résultats opérationnels sont remontés au niveau tactique.
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import uuid

from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState
from argumentation_analysis.paths import DATA_DIR, RESULTS_DIR
from argumentation_analysis.core.communication import (
    MessageMiddleware, TacticalAdapter, OperationalAdapter,
    ChannelType, MessagePriority, Message, MessageType, AgentLevel
)


class TacticalOperationalInterface:
    """
    Classe représentant l'interface entre les niveaux tactique et opérationnel.
    
    Cette interface est responsable de:
    - Traduire les tâches tactiques en tâches opérationnelles spécifiques
    - Transmettre le contexte local nécessaire aux agents opérationnels
    - Remonter les résultats d'analyse du niveau opérationnel au niveau tactique
    - Remonter les métriques d'exécution du niveau opérationnel au niveau tactique
    - Gérer les signalements de problèmes entre les niveaux
    
    Cette interface utilise le système de communication multi-canal pour faciliter
    les échanges entre les niveaux tactique et opérationnel.
    """
    
    def __init__(self, tactical_state: Optional[TacticalState] = None,
               operational_state: Optional[OperationalState] = None,
               middleware: Optional[MessageMiddleware] = None):
        """
        Initialise une nouvelle interface tactique-opérationnelle.
        
        Args:
            tactical_state: L'état tactique à utiliser. Si None, un nouvel état est créé.
            operational_state: L'état opérationnel à utiliser. Si None, un nouvel état est créé.
            middleware: Le middleware de communication à utiliser. Si None, un nouveau middleware est créé.
        """
        self.tactical_state = tactical_state if tactical_state else TacticalState()
        # Note: Comme OperationalState n'est pas encore implémenté, nous utilisons None pour l'instant
        # Dans une implémentation complète, il faudrait créer une instance d'OperationalState
        self.operational_state = operational_state
        self.logger = logging.getLogger(__name__)
        
        # Initialiser le middleware de communication
        self.middleware = middleware if middleware else MessageMiddleware()
        
        # Créer les adaptateurs pour les niveaux tactique et opérationnel
        self.tactical_adapter = TacticalAdapter(
            agent_id="tactical_interface",
            middleware=self.middleware
        )
        
        self.operational_adapter = OperationalAdapter(
            agent_id="operational_interface",
            middleware=self.middleware
        )
    
    def translate_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traduit une tâche tactique en tâche opérationnelle.
        
        Args:
            task: La tâche tactique à traduire
            
        Returns:
            Un dictionnaire contenant la tâche opérationnelle
        """
        self.logger.info(f"Traduction de la tâche {task.get('id', 'unknown')} en tâche opérationnelle")
        
        # Créer un identifiant unique pour la tâche opérationnelle
        operational_task_id = f"op-{task.get('id', uuid.uuid4().hex[:8])}"
        
        # Extraire les informations pertinentes de la tâche tactique
        task_description = task.get("description", "")
        objective_id = task.get("objective_id", "")
        required_capabilities = task.get("required_capabilities", [])
        priority = task.get("priority", "medium")
        
        # Déterminer les techniques à appliquer en fonction des capacités requises
        techniques = self._determine_techniques(required_capabilities)
        
        # Déterminer les extraits de texte pertinents
        text_extracts = self._determine_relevant_extracts(task_description, objective_id)
        
        # Créer la tâche opérationnelle
        operational_task = {
            "id": operational_task_id,
            "tactical_task_id": task.get("id"),
            "description": task_description,
            "objective_id": objective_id,
            "techniques": techniques,
            "text_extracts": text_extracts,
            "parameters": self._determine_execution_parameters(task),
            "expected_outputs": self._determine_expected_outputs(task),
            "priority": priority,
            "deadline": self._determine_deadline(task)
        }
        
        # Ajouter le contexte local
        operational_task["context"] = {
            "position_in_workflow": self._determine_position_in_workflow(task),
            "related_tasks": self._find_related_tasks(task),
            "dependencies": self._translate_dependencies(task),
            "constraints": self._determine_constraints(task)
        }
        
        # Assigner la tâche via le système de communication
        task_priority = self._map_priority_to_enum(priority)
        
        # Déterminer l'agent opérationnel approprié en fonction des capacités requises
        recipient_id = self._determine_appropriate_agent(required_capabilities)
        
        if recipient_id:
            # Assigner la tâche à un agent spécifique
            self.tactical_adapter.assign_task(
                task_type="operational_task",
                parameters=operational_task,
                recipient_id=recipient_id,
                priority=task_priority,
                requires_ack=True,
                metadata={
                    "objective_id": objective_id,
                    "task_origin": "tactical_interface"
                }
            )
            
            self.logger.info(f"Tâche opérationnelle {operational_task_id} assignée à {recipient_id}")
        else:
            # Publier la tâche pour que n'importe quel agent avec les capacités requises puisse la prendre
            self.middleware.publish(
                topic_id=f"operational_tasks.{'.'.join(required_capabilities)}",
                sender="tactical_interface",
                sender_level=AgentLevel.TACTICAL,
                content={
                    "task_type": "operational_task",
                    "task_data": operational_task
                },
                priority=task_priority,
                metadata={
                    "objective_id": objective_id,
                    "requires_capabilities": required_capabilities
                }
            )
            
            self.logger.info(f"Tâche opérationnelle {operational_task_id} publiée pour les agents avec capacités: {required_capabilities}")
        
        return operational_task
    
    def _determine_techniques(self, required_capabilities: List[str]) -> List[Dict[str, Any]]:
        """
        Détermine les techniques à appliquer en fonction des capacités requises.
        
        Args:
            required_capabilities: Liste des capacités requises
            
        Returns:
            Liste des techniques à appliquer
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: mapper les capacités à des techniques
        
        techniques = []
        
        capability_technique_mapping = {
            "argument_identification": [
                {
                    "name": "premise_conclusion_extraction",
                    "parameters": {
                        "confidence_threshold": 0.7,
                        "include_implicit": True
                    }
                },
                {
                    "name": "argument_structure_analysis",
                    "parameters": {
                        "detail_level": "medium"
                    }
                }
            ],
            "fallacy_detection": [
                {
                    "name": "fallacy_pattern_matching",
                    "parameters": {
                        "taxonomy": "standard",
                        "confidence_threshold": 0.6
                    }
                },
                {
                    "name": "contextual_fallacy_analysis",
                    "parameters": {
                        "consider_context": True
                    }
                }
            ],
            # Nouvelles techniques pour les outils d'analyse rhétorique améliorés
            "complex_fallacy_analysis": [
                {
                    "name": "complex_fallacy_analysis",
                    "parameters": {
                        "context": "général",
                        "confidence_threshold": 0.7,
                        "include_composite_fallacies": True
                    }
                }
            ],
            "contextual_fallacy_analysis": [
                {
                    "name": "contextual_fallacy_analysis",
                    "parameters": {
                        "context": "général",
                        "consider_domain": True,
                        "consider_audience": True
                    }
                }
            ],
            "fallacy_severity_evaluation": [
                {
                    "name": "fallacy_severity_evaluation",
                    "parameters": {
                        "context": "général",
                        "include_impact_analysis": True
                    }
                }
            ],
            "argument_structure_visualization": [
                {
                    "name": "argument_structure_visualization",
                    "parameters": {
                        "context": "général",
                        "output_format": "json"
                    }
                }
            ],
            "argument_coherence_evaluation": [
                {
                    "name": "argument_coherence_evaluation",
                    "parameters": {
                        "context": "général",
                        "evaluate_logical_coherence": True,
                        "evaluate_thematic_coherence": True
                    }
                }
            ],
            "semantic_argument_analysis": [
                {
                    "name": "semantic_argument_analysis",
                    "parameters": {
                        "include_component_analysis": True,
                        "include_semantic_relations": True
                    }
                }
            ],
            "contextual_fallacy_detection": [
                {
                    "name": "contextual_fallacy_detection",
                    "parameters": {
                        "context": "général",
                        "confidence_threshold": 0.7
                    }
                }
            ],
            "formal_logic": [
                {
                    "name": "propositional_logic_formalization",
                    "parameters": {
                        "simplify": True
                    }
                },
                {
                    "name": "validity_checking",
                    "parameters": {
                        "method": "truth_table"
                    }
                }
            ],
            "validity_checking": [
                {
                    "name": "formal_validity_analysis",
                    "parameters": {
                        "check_soundness": True
                    }
                }
            ],
            "consistency_analysis": [
                {
                    "name": "consistency_checking",
                    "parameters": {
                        "scope": "local"
                    }
                }
            ],
            "text_extraction": [
                {
                    "name": "relevant_segment_extraction",
                    "parameters": {
                        "window_size": 3
                    }
                }
            ],
            "preprocessing": [
                {
                    "name": "text_normalization",
                    "parameters": {
                        "remove_stopwords": False,
                        "lemmatize": True
                    }
                }
            ],
            "argument_visualization": [
                {
                    "name": "argument_graph_generation",
                    "parameters": {
                        "format": "hierarchical"
                    }
                }
            ],
            "summary_generation": [
                {
                    "name": "structured_summary",
                    "parameters": {
                        "max_length": 500,
                        "include_metadata": True
                    }
                }
            ]
        }
        
        # Ajouter les techniques correspondant aux capacités requises
        for capability in required_capabilities:
            if capability in capability_technique_mapping:
                techniques.extend(capability_technique_mapping[capability])
        
        return techniques
    
    def _determine_relevant_extracts(self, task_description: str, objective_id: str) -> List[Dict[str, Any]]:
        """
        Détermine les extraits de texte pertinents pour la tâche.
        
        Args:
            task_description: Description de la tâche
            objective_id: Identifiant de l'objectif associé
            
        Returns:
            Liste des extraits de texte pertinents
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: créer un extrait générique
        
        # Dans une implémentation réelle, on analyserait le texte brut pour extraire
        # les segments pertinents en fonction de la description de la tâche
        
        return [
            {
                "id": f"extract-{uuid.uuid4().hex[:8]}",
                "source": "raw_text",
                "content": "Extrait complet du texte à analyser",
                "relevance": "high"
            }
        ]
    
    def _determine_execution_parameters(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Détermine les paramètres d'exécution pour la tâche.
        
        Args:
            task: La tâche tactique
            
        Returns:
            Un dictionnaire contenant les paramètres d'exécution
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: définir des paramètres génériques
        
        estimated_duration = task.get("estimated_duration", "medium")
        priority = task.get("priority", "medium")
        
        # Mapper la durée estimée à des paramètres d'exécution
        duration_mapping = {
            "short": {
                "timeout": 30,  # secondes
                "max_iterations": 2
            },
            "medium": {
                "timeout": 60,  # secondes
                "max_iterations": 3
            },
            "long": {
                "timeout": 120,  # secondes
                "max_iterations": 5
            }
        }
        
        # Mapper la priorité à des paramètres d'exécution
        priority_mapping = {
            "high": {
                "precision_target": 0.9,
                "recall_target": 0.8
            },
            "medium": {
                "precision_target": 0.8,
                "recall_target": 0.7
            },
            "low": {
                "precision_target": 0.7,
                "recall_target": 0.6
            }
        }
        
        execution_params = {
            **duration_mapping.get(estimated_duration, duration_mapping["medium"]),
            **priority_mapping.get(priority, priority_mapping["medium"]),
            "detail_level": "high" if priority == "high" else "medium"
        }
        
        return execution_params
    
    def _determine_expected_outputs(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Détermine les outputs attendus pour la tâche.
        
        Args:
            task: La tâche tactique
            
        Returns:
            Un dictionnaire contenant les outputs attendus
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: déterminer les outputs en fonction de la description
        
        task_description = task.get("description", "").lower()
        required_capabilities = task.get("required_capabilities", [])
        
        # Vérifier si des capacités d'analyse rhétorique améliorées sont requises
        if "complex_fallacy_analysis" in required_capabilities:
            return {
                "complex_fallacy_analysis": {
                    "format": "object",
                    "schema": {
                        "individual_fallacies_count": "integer",
                        "basic_combinations": "list[object]",
                        "advanced_combinations": "list[object]",
                        "fallacy_patterns": "list[object]",
                        "composite_severity": "object"
                    }
                }
            }
        elif "contextual_fallacy_analysis" in required_capabilities:
            return {
                "contextual_fallacy_analysis": {
                    "format": "object",
                    "schema": {
                        "identified_fallacies": "list[object]",
                        "context_factors": "object",
                        "context_impact": "object"
                    }
                }
            }
        elif "fallacy_severity_evaluation" in required_capabilities:
            return {
                "fallacy_severity_evaluation": {
                    "format": "object",
                    "schema": {
                        "fallacies": "list[object]",
                        "severity_scores": "object",
                        "impact_analysis": "object"
                    }
                }
            }
        elif "argument_structure_visualization" in required_capabilities:
            return {
                "argument_structure_visualization": {
                    "format": "object",
                    "schema": {
                        "visualizations": "object",
                        "argument_count": "integer",
                        "context": "string"
                    }
                }
            }
        elif "argument_coherence_evaluation" in required_capabilities:
            return {
                "argument_coherence_evaluation": {
                    "format": "object",
                    "schema": {
                        "overall_coherence": "object",
                        "coherence_by_type": "object",
                        "recommendations": "list[string]"
                    }
                }
            }
        elif "semantic_argument_analysis" in required_capabilities:
            return {
                "semantic_argument_analysis": {
                    "format": "object",
                    "schema": {
                        "arguments": "list[object]",
                        "comparison": "object",
                        "semantic_relations": "object"
                    }
                }
            }
        elif "contextual_fallacy_detection" in required_capabilities:
            return {
                "contextual_fallacy_detection": {
                    "format": "object",
                    "schema": {
                        "detected_fallacies": "list[object]",
                        "context_factors": "object"
                    }
                }
            }
        elif "identifier" in task_description and "argument" in task_description:
            return {
                "identified_arguments": {
                    "format": "list",
                    "schema": {
                        "id": "string",
                        "premises": "list[string]",
                        "conclusion": "string",
                        "confidence": "float"
                    }
                }
            }
        elif "sophisme" in task_description:
            return {
                "identified_fallacies": {
                    "format": "list",
                    "schema": {
                        "id": "string",
                        "type": "string",
                        "segment": "string",
                        "explanation": "string",
                        "confidence": "float"
                    }
                }
            }
        elif "formaliser" in task_description or "validité" in task_description:
            return {
                "formal_analyses": {
                    "format": "list",
                    "schema": {
                        "argument_id": "string",
                        "formalization": "string",
                        "is_valid": "boolean",
                        "explanation": "string"
                    }
                }
            }
        elif "cohérence" in task_description:
            return {
                "coherence_analysis": {
                    "format": "object",
                    "schema": {
                        "score": "float",
                        "inconsistencies": "list[object]",
                        "explanation": "string"
                    }
                }
            }
        else:
            return {
                "generic_result": {
                    "format": "object",
                    "schema": {
                        "content": "string",
                        "metadata": "object"
                    }
                }
            }
    
    def _determine_deadline(self, task: Dict[str, Any]) -> Optional[str]:
        """
        Détermine la deadline pour la tâche.
        
        Args:
            task: La tâche tactique
            
        Returns:
            La deadline au format ISO ou None
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: pas de deadline spécifique
        
        return None
    
    def _determine_position_in_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Détermine la position de la tâche dans le workflow.
        
        Args:
            task: La tâche tactique
            
        Returns:
            Un dictionnaire décrivant la position dans le workflow
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: déterminer la position en fonction de l'identifiant
        
        task_id = task.get("id", "")
        
        # Extraire le numéro de séquence de l'identifiant (supposé être au format "task-obj-N")
        sequence_number = 0
        parts = task_id.split("-")
        if len(parts) > 2:
            try:
                sequence_number = int(parts[-1])
            except ValueError:
                sequence_number = 0
        
        # Déterminer la phase en fonction du numéro de séquence
        if sequence_number == 1:
            phase = "initial"
        elif sequence_number == 2:
            phase = "intermediate"
        else:
            phase = "final"
        
        return {
            "phase": phase,
            "sequence_number": sequence_number,
            "is_first": sequence_number == 1,
            "is_last": False  # Impossible de déterminer sans connaître toutes les tâches
        }
    
    def _find_related_tasks(self, task: Dict[str, Any]) -> List[str]:
        """
        Trouve les tâches liées à une tâche donnée.
        
        Args:
            task: La tâche tactique
            
        Returns:
            Liste des identifiants des tâches liées
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: trouver les tâches avec le même objectif
        
        related_tasks = []
        task_id = task.get("id")
        objective_id = task.get("objective_id")
        
        if not objective_id:
            return related_tasks
        
        # Parcourir toutes les tâches dans l'état tactique
        for status, tasks in self.tactical_state.tasks.items():
            for other_task in tasks:
                if other_task.get("id") != task_id and other_task.get("objective_id") == objective_id:
                    related_tasks.append(other_task.get("id"))
        
        return related_tasks
    
    def _translate_dependencies(self, task: Dict[str, Any]) -> List[str]:
        """
        Traduit les dépendances tactiques en dépendances opérationnelles.
        
        Args:
            task: La tâche tactique
            
        Returns:
            Liste des identifiants des dépendances opérationnelles
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: convertir les identifiants des dépendances
        
        task_id = task.get("id")
        dependencies = self.tactical_state.get_task_dependencies(task_id)
        
        # Convertir les identifiants tactiques en identifiants opérationnels
        operational_dependencies = [f"op-{dep_id}" for dep_id in dependencies]
        
        return operational_dependencies
    
    def _determine_constraints(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Détermine les contraintes pour la tâche.
        
        Args:
            task: La tâche tactique
            
        Returns:
            Un dictionnaire contenant les contraintes
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: définir des contraintes génériques
        
        priority = task.get("priority", "medium")
        
        # Définir les contraintes en fonction de la priorité
        if priority == "high":
            return {
                "max_runtime": 120,  # secondes
                "min_confidence": 0.8,
                "max_memory": "1GB"
            }
        elif priority == "medium":
            return {
                "max_runtime": 60,  # secondes
                "min_confidence": 0.7,
                "max_memory": "512MB"
            }
        else:
            return {
                "max_runtime": 30,  # secondes
                "min_confidence": 0.6,
                "max_memory": "256MB"
            }
    
    def process_operational_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite un résultat opérationnel et le traduit en information tactique.
        
        Args:
            result: Le résultat opérationnel
            
        Returns:
            Un dictionnaire contenant l'information tactique
        """
        self.logger.info(f"Traitement du résultat opérationnel de la tâche {result.get('task_id', 'unknown')}")
        
        # Extraire les informations pertinentes du résultat
        task_id = result.get("task_id")
        operational_task_id = result.get("id")
        tactical_task_id = result.get("tactical_task_id")
        outputs = result.get("outputs", {})
        metrics = result.get("metrics", {})
        issues = result.get("issues", [])
        
        # Traduire en résultat tactique
        tactical_result = {
            "task_id": tactical_task_id,
            "completion_status": result.get("status", "completed"),
            RESULTS_DIR: self._translate_outputs(outputs),
            "execution_metrics": self._translate_metrics(metrics),
            "issues": self._translate_issues(issues)
        }
        
        # Recevoir les résultats via le système de communication
        pending_results = self.tactical_adapter.receive_task_result(
            timeout=0.1,  # Vérification rapide des résultats en attente
            filter_criteria={"tactical_task_id": tactical_task_id} if tactical_task_id else None
        )
        
        if pending_results:
            # Mettre à jour le résultat avec les informations reçues
            result_content = pending_results.content.get(DATA_DIR, {})
            
            if "outputs" in result_content:
                tactical_result[RESULTS_DIR].update(self._translate_outputs(result_content["outputs"]))
            
            if "metrics" in result_content:
                tactical_result["execution_metrics"].update(self._translate_metrics(result_content["metrics"]))
            
            if "issues" in result_content:
                tactical_result["issues"].extend(self._translate_issues(result_content["issues"]))
            
            # Envoyer un accusé de réception
            self.tactical_adapter.send_report(
                report_type="result_acknowledgement",
                content={"task_id": tactical_task_id, "status": "received"},
                recipient_id=pending_results.sender
            )
        
        return tactical_result
    
    def _translate_outputs(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traduit les outputs opérationnels en résultats tactiques.
        
        Args:
            outputs: Les outputs opérationnels
            
        Returns:
            Un dictionnaire contenant les résultats tactiques
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: copier les outputs tels quels
        
        # Dans une implémentation réelle, on pourrait agréger ou transformer les résultats
        
        return outputs
    
    def _translate_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traduit les métriques opérationnelles en métriques tactiques.
        
        Args:
            metrics: Les métriques opérationnelles
            
        Returns:
            Un dictionnaire contenant les métriques tactiques
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: extraire les métriques pertinentes
        
        return {
            "processing_time": metrics.get("execution_time", 0.0),
            "confidence_score": metrics.get("confidence", 0.0),
            "coverage": metrics.get("coverage", 0.0),
            "resource_usage": metrics.get("resource_usage", 0.0)
        }
    
    def _translate_issues(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Traduit les problèmes opérationnels en problèmes tactiques.
        
        Args:
            issues: Les problèmes opérationnels
            
        Returns:
            Liste des problèmes tactiques
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: traduire les types de problèmes
        
        tactical_issues = []
        
        for issue in issues:
            issue_type = issue.get("type")
            
            if issue_type == "execution_error":
                tactical_issues.append({
                    "type": "task_failure",
                    "description": issue.get("description", "Erreur d'exécution"),
                    "severity": issue.get("severity", "medium"),
                    "details": issue.get("details", {})
                })
            elif issue_type == "timeout":
                tactical_issues.append({
                    "type": "task_timeout",
                    "description": "Délai d'exécution dépassé",
                    "severity": "high",
                    "details": issue.get("details", {})
                })
            elif issue_type == "low_confidence":
                tactical_issues.append({
                    "type": "low_quality",
                    "description": "Résultat de faible confiance",
                    "severity": "medium",
                    "details": issue.get("details", {})
                })
            else:
                # Copier le problème tel quel
                tactical_issues.append(issue)
        
        return tactical_issues
    
    def _map_priority_to_enum(self, priority: str) -> MessagePriority:
        """
        Convertit une priorité textuelle en valeur d'énumération MessagePriority.
        
        Args:
            priority: La priorité textuelle ("high", "medium", "low")
            
        Returns:
            La valeur d'énumération MessagePriority correspondante
        """
        priority_map = {
            "high": MessagePriority.HIGH,
            "medium": MessagePriority.NORMAL,
            "low": MessagePriority.LOW
        }
        
        return priority_map.get(priority.lower(), MessagePriority.NORMAL)
    
    def _determine_appropriate_agent(self, required_capabilities: List[str]) -> Optional[str]:
        """
        Détermine l'agent opérationnel approprié en fonction des capacités requises.
        
        Args:
            required_capabilities: Liste des capacités requises
            
        Returns:
            L'identifiant de l'agent approprié ou None si aucun agent spécifique n'est déterminé
        """
        # Cette méthode serait normalement plus sophistiquée, utilisant potentiellement
        # un registre d'agents avec leurs capacités
        
        # Exemple simple: mapper les capacités à des agents spécifiques
        capability_agent_mapping = {
            "argument_identification": "informal_analyzer",
            "fallacy_detection": "informal_analyzer",
            "rhetorical_analysis": "informal_analyzer",
            "formal_logic": "logic_analyzer",
            "validity_checking": "logic_analyzer",
            "consistency_analysis": "logic_analyzer",
            "text_extraction": "extract_processor",
            "preprocessing": "extract_processor",
            "reference_management": "extract_processor",
            "argument_visualization": "visualizer",
            "result_presentation": "visualizer",
            "summary_generation": "visualizer",
            # Nouvelles capacités pour les outils d'analyse rhétorique améliorés
            "complex_fallacy_analysis": "rhetorical",
            "contextual_fallacy_analysis": "rhetorical",
            "fallacy_severity_evaluation": "rhetorical",
            "argument_structure_visualization": "rhetorical",
            "argument_coherence_evaluation": "rhetorical",
            "semantic_argument_analysis": "rhetorical",
            "contextual_fallacy_detection": "rhetorical"
        }
        
        # Compter les occurrences de chaque agent
        agent_counts = {}
        for capability in required_capabilities:
            if capability in capability_agent_mapping:
                agent = capability_agent_mapping[capability]
                agent_counts[agent] = agent_counts.get(agent, 0) + 1
        
        # Trouver l'agent avec le plus grand nombre de capacités requises
        if agent_counts:
            return max(agent_counts.items(), key=lambda x: x[1])[0]
        
        return None
    
    def subscribe_to_operational_updates(self, update_types: List[str], callback: callable) -> str:
        """
        S'abonne aux mises à jour des agents opérationnels.
        
        Args:
            update_types: Types de mises à jour (task_progress, resource_usage, etc.)
            callback: Fonction de rappel à appeler lors de la réception d'une mise à jour
            
        Returns:
            Un identifiant d'abonnement
        """
        return self.tactical_adapter.subscribe_to_operational_updates(
            update_types=update_types,
            callback=callback
        )
    
    def request_operational_status(self, agent_id: str, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """
        Demande le statut d'un agent opérationnel.
        
        Args:
            agent_id: Identifiant de l'agent opérationnel
            timeout: Délai d'attente maximum en secondes
            
        Returns:
            Le statut de l'agent ou None si timeout
        """
        try:
            response = self.tactical_adapter.request_strategic_guidance(
                request_type="operational_status",
                parameters={"agent_id": agent_id},
                recipient_id=agent_id,
                timeout=timeout
            )
            
            if response:
                self.logger.info(f"Statut de l'agent {agent_id} reçu")
                return response
            else:
                self.logger.warning(f"Délai d'attente dépassé pour la demande de statut de l'agent {agent_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la demande de statut de l'agent {agent_id}: {str(e)}")
            return None