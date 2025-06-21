"""
Module définissant le Coordinateur de Tâches de l'architecture hiérarchique.
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import uuid

from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.paths import RESULTS_DIR
from argumentation_analysis.core.communication import (
    MessageMiddleware, TacticalAdapter, OperationalAdapter,
    ChannelType, MessagePriority, Message, MessageType, AgentLevel
)


class TaskCoordinator:
    """
    Le `TaskCoordinator` (ou `TacticalManager`) est le pivot du niveau tactique.
    Il traduit les objectifs stratégiques en tâches concrètes, les assigne aux
    agents opérationnels appropriés et supervise leur exécution.

    Il gère les dépendances entre les tâches, traite les résultats et rapporte
    la progression au `StrategicManager`.

    Attributes:
        state (TacticalState): L'état interne du coordinateur.
        logger (logging.Logger): Le logger pour les événements.
        middleware (MessageMiddleware): Le middleware de communication.
        adapter (TacticalAdapter): L'adaptateur pour la communication tactique.
        agent_capabilities (Dict[str, List[str]]): Un mapping des agents à leurs capacités.
    """

    def __init__(self,
                 tactical_state: Optional[TacticalState] = None,
                 middleware: Optional[MessageMiddleware] = None):
        """
        Initialise une nouvelle instance du `TaskCoordinator`.

        Args:
            tactical_state (Optional[TacticalState]): L'état tactique initial à utiliser.
                Si `None`, un nouvel état `TacticalState` est instancié. Il suit les tâches,
                leurs dépendances, et les résultats intermédiaires.
            middleware (Optional[MessageMiddleware]): Le middleware de communication.
                Si `None`, un `MessageMiddleware` par défaut est créé pour gérer les
                échanges avec les niveaux stratégique et opérationnel.
        """
        self.state = tactical_state or TacticalState()
        self.logger = logging.getLogger(__name__)
        self.middleware = middleware or MessageMiddleware()
        self.adapter = TacticalAdapter(
            agent_id="tactical_coordinator",
            middleware=self.middleware
        )
        
        # Définir les capacités des agents opérationnels
        self.agent_capabilities = {
            "informal_analyzer": ["argument_identification", "fallacy_detection", "rhetorical_analysis"],
            "logic_analyzer": ["formal_logic", "validity_checking", "consistency_analysis"],
            "extract_processor": ["text_extraction", "preprocessing", "reference_management"],
            "visualizer": ["argument_visualization", "result_presentation", "summary_generation"],
            "data_extractor": ["entity_extraction", "relation_detection", "metadata_analysis"]
        }
        
        # S'abonner aux directives stratégiques
        self._subscribe_to_strategic_directives()
    
    def _log_action(self, action_type: str, description: str) -> None:
        """
        Enregistre une action tactique dans le journal.
        
        Args:
            action_type: Le type d'action
            description: La description de l'action
        """
        action = {
            "timestamp": datetime.now().isoformat(),
            "type": action_type,
            "description": description,
            "agent_id": "task_coordinator"
        }
        
        self.state.log_tactical_action(action)
        self.logger.info(f"Action tactique: {action_type} - {description}")
    
    def _subscribe_to_strategic_directives(self) -> None:
        """
        S'abonne aux messages provenant du niveau stratégique.

        Met en place un callback (`handle_directive`) qui réagit aux nouvelles
        directives, telles que la définition d'un nouvel objectif ou
        un ajustement stratégique.
        """

        async def handle_directive(message: Message) -> None:
            directive_type = message.content.get("directive_type")
            parameters = message.content.get("parameters", {})
            self.logger.info(f"Directive reçue: type='{directive_type}', sender='{message.sender}'")

            if directive_type == "new_strategic_goal":
                if not isinstance(parameters, dict) or not parameters.get("id"):
                    self.logger.error(f"Données d'objectif invalides: {parameters}")
                    return

                self.state.add_assigned_objective(parameters)
                tasks = self._decompose_objective_to_tasks(parameters)
                self._establish_task_dependencies(tasks)
                for task in tasks:
                    self.state.add_task(task)

                self._log_action("Décomposition d'objectif",f"Objectif {parameters.get('id')} décomposé en {len(tasks)} tâches")

                for task in tasks:
                    await self.assign_task_to_operational(task)

                self.adapter.send_report(
                    report_type="directive_acknowledgement",
                    content={"objective_id": parameters.get("id"),"tasks_created": len(tasks)},
                    recipient_id=message.sender)

            elif directive_type == "strategic_adjustment":
                self.logger.info("Ajustement stratégique reçu.")
                self._apply_strategic_adjustments(message.content)
                
                # Journaliser l'action
                self._log_action(
                    "Application d'ajustement stratégique",
                    "Application des ajustements stratégiques reçus"
                )
                
                # Envoyer un accusé de réception
                self.adapter.send_report(
                    report_type="adjustment_acknowledgement",
                    content={"status": "applied"},
                    recipient_id=message.sender,
                    priority=MessagePriority.NORMAL
                )
        
        # S'abonner aux directives stratégiques
        hierarchical_channel = self.middleware.get_channel(ChannelType.HIERARCHICAL)
        if hierarchical_channel:
            hierarchical_channel.subscribe(
                subscriber_id="tactical_coordinator",
                callback=handle_directive,
                filter_criteria={
                    "recipient": "tactical_coordinator",
                    "type": MessageType.COMMAND, # Rétabli à COMMAND
                    "sender_level": AgentLevel.STRATEGIC
                }
            )
            self.logger.info("Abonnement aux directives stratégiques effectué.")
        else:
            self.logger.error(f"Impossible de s'abonner aux directives stratégiques: Canal HIERARCHICAL non trouvé dans le middleware.")
    
    async def process_strategic_objectives(self, objectives: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Traite une liste d'objectifs stratégiques en les décomposant en un plan d'action tactique.

        Pour chaque objectif, cette méthode génère une série de tâches granulaires,
        établit les dépendances entre elles, les enregistre dans l'état tactique,
        et les assigne aux agents opérationnels appropriés.

        Args:
            objectives (List[Dict[str, Any]]): Une liste de dictionnaires, où chaque
                dictionnaire représente un objectif stratégique à atteindre.
            
        Returns:
            Dict[str, Any]: Un résumé de l'opération, incluant le nombre total de tâches
            créées et une cartographie des tâches par objectif.
        """
        self.logger.info(f"Traitement de {len(objectives)} objectifs stratégiques")
        
        # Ajouter les objectifs à l'état tactique
        for objective in objectives:
            self.state.add_assigned_objective(objective)
        
        # Décomposer chaque objectif en tâches
        all_tasks = []
        for objective in objectives:
            tasks = self._decompose_objective_to_tasks(objective)
            all_tasks.extend(tasks)
        
        # Établir les dépendances entre les tâches
        self._establish_task_dependencies(all_tasks)
        
        # Ajouter les tâches à l'état tactique
        for task in all_tasks:
            self.state.add_task(task)
        
        # Journaliser l'action
        self._log_action("Décomposition des objectifs",
                        f"Décomposition de {len(objectives)} objectifs en {len(all_tasks)} tâches")
        
        # Assigner les tâches aux agents opérationnels via le système de communication
        self.logger.info(f"Assignation de {len(all_tasks)} tâches globalement...")
        for task in all_tasks:
            await self.assign_task_to_operational(task)
        
        return {
            "tasks_created": len(all_tasks),
            "tasks_by_objective": {obj["id"]: [t["id"] for t in all_tasks if t["objective_id"] == obj["id"]]
                                 for obj in objectives}
        }
    
    async def assign_task_to_operational(self, task: Dict[str, Any]) -> None:
        """
        Assigne une tâche spécifique à un agent opérationnel compétent.

        La méthode détermine d'abord l'agent le plus qualifié en fonction des
        capacités requises par la tâche. Ensuite, elle envoie une directive
        d'assignation à cet agent via le middleware de communication.
        Si aucun agent spécifique n'est trouvé, la tâche est publiée sur un
        canal général pour que tout agent disponible puisse la prendre.

        Args:
            task (Dict[str, Any]): Le dictionnaire représentant la tâche à assigner.
                Doit contenir des clés comme `id`, `description`, et `required_capabilities`.
        """
        required_capabilities = task.get("required_capabilities", [])
        priority = task.get("priority", "medium")
        
        # Déterminer l'agent approprié
        recipient_id = self._determine_appropriate_agent(required_capabilities)
        
        # Mapper la priorité textuelle à l'énumération
        priority_map = {
            "high": MessagePriority.HIGH,
            "medium": MessagePriority.NORMAL,
            "low": MessagePriority.LOW
        }
        message_priority = priority_map.get(priority.lower(), MessagePriority.NORMAL)
        
        if recipient_id:
            # Assigner la tâche à un agent spécifique
            self.adapter.assign_task(
                task_type="operational_task",
                parameters=task,
                recipient_id=recipient_id,
                priority=message_priority,
                requires_ack=True,
                metadata={
                    "objective_id": task.get("objective_id"),
                    "task_origin": "tactical_coordinator"
                }
            )
            
            self.logger.info(f"Tâche {task.get('id')} assignée à {recipient_id} via adaptateur.")
        else:
            # Publier la tâche pour que n'importe quel agent avec les capacités requises puisse la prendre
            # S'assurer que le topic_id est valide et que le middleware est configuré pour le gérer.
            topic = f"operational_tasks.{'.'.join(sorted(list(set(required_capabilities))))}" # Normaliser le topic
            self.logger.info(f"Aucun agent spécifique trouvé pour la tâche {task.get('id')}. Publication sur le topic: {topic}")
            
            # Vérifier si le middleware existe avant de publier
            if self.middleware:
                self.middleware.publish(
                    # topic_id=topic, # Utiliser un ID de canal ou un topic plus générique si nécessaire
                    channel_id=self.adapter.hierarchical_channel_id, # Publier sur le canal hiérarchique principal
                    message=Message(
                        message_id=str(uuid.uuid4()),
                        sender_id="tactical_coordinator",
                        recipient_id="operational_level", # Ou un broadcast spécifique si le canal le supporte
                        message_type=MessageType.TASK_ASSIGNMENT, # Un type de message plus approprié
                        content={
                            "task_type": "operational_task", # Conserver pour la compatibilité
                            "task_data": task,
                            "required_capabilities": required_capabilities # Répéter pour le filtrage par les agents
                        },
                        priority=message_priority,
                        timestamp=datetime.now().isoformat(),
                        metadata={
                            "objective_id": task.get("objective_id"),
                            "task_origin": "tactical_coordinator"
                        }
                    )
                )
                self.logger.info(f"Tâche {task.get('id')} publiée sur le canal '{self.adapter.hierarchical_channel_id}' pour les agents avec capacités: {required_capabilities}")
            else:
                self.logger.error("Middleware non disponible. Impossible de publier la tâche.")
    
    def _determine_appropriate_agent(self, required_capabilities: List[str]) -> Optional[str]:
        """
        Détermine l'agent opérationnel approprié en fonction des capacités requises.
        
        Args:
            required_capabilities: Liste des capacités requises
            
        Returns:
            L'identifiant de l'agent approprié ou None si aucun agent spécifique n'est déterminé
        """
        # Compter les occurrences de chaque agent
        agent_counts = {}
        for capability in required_capabilities:
            for agent, capabilities in self.agent_capabilities.items():
                if capability in capabilities:
                    agent_counts[agent] = agent_counts.get(agent, 0) + 1
        
        # Trouver l'agent avec le plus grand nombre de capacités requises
        if agent_counts:
            return max(agent_counts.items(), key=lambda x: x[1])[0]
        
        return None
    
    async def decompose_strategic_goal(self, objective: Dict[str, Any]) -> Dict[str, Any]:
        """
        Décompose un objectif stratégique en un plan tactique (une liste de tâches).

        Cette méthode sert de point d'entrée pour la décomposition. Elle utilise
        `_decompose_objective_to_tasks` pour la logique de décomposition,
        établit les dépendances, et stocke les tâches générées dans l'état.

        Args:
            objective (Dict[str, Any]): L'objectif stratégique à décomposer.
            
        Returns:
            Dict[str, Any]: Un dictionnaire contenant la liste des tâches (`tasks`)
            qui composent le plan tactique pour cet objectif.
        """
        tasks = self._decompose_objective_to_tasks(objective)
        self._establish_task_dependencies(tasks)
        for task in tasks:
            self.state.add_task(task)
        
        self.logger.info(f"Objectif {objective.get('id')} décomposé en {len(tasks)} tâches (via decompose_strategic_goal).")
        return {"tasks": tasks}

    def _decompose_objective_to_tasks(self, objective: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Implémente la logique de décomposition d'un objectif en tâches granulaires.
        
        Cette méthode privée analyse la description d'un objectif stratégique
        pour en déduire une séquence de tâches opérationnelles. Par exemple, un objectif
        d'"identification d'arguments" sera décomposé en tâches d'extraction,
        d'identification de prémisses/conclusions, etc.

        Args:
            objective (Dict[str, Any]): Le dictionnaire de l'objectif à décomposer.
            
        Returns:
            List[Dict[str, Any]]: Une liste de dictionnaires, chaque dictionnaire
            représentant une tâche concrète avec ses propres exigences et métadonnées.
        """
        tasks = []
        obj_id = objective["id"]
        obj_description = objective["description"].lower()
        obj_priority = objective.get("priority", "medium")
        
        # Générer un identifiant de base pour les tâches
        base_task_id = f"task-{obj_id}-"
        
        # Décomposer en fonction du type d'objectif
        if "identifier" in obj_description and "arguments" in obj_description:
            # Objectif d'identification d'arguments
            tasks.extend([
                {
                    "id": f"{base_task_id}1",
                    "description": "Extraire les segments de texte contenant des arguments potentiels",
                    "objective_id": obj_id,
                    "estimated_duration": "short",
                    "required_capabilities": ["text_extraction"],
                    "priority": obj_priority
                },
                {
                    "id": f"{base_task_id}2",
                    "description": "Identifier les prémisses et conclusions explicites",
                    "objective_id": obj_id,
                    "estimated_duration": "medium",
                    "required_capabilities": ["argument_identification"],
                    "priority": obj_priority
                },
                {
                    "id": f"{base_task_id}3",
                    "description": "Identifier les prémisses implicites",
                    "objective_id": obj_id,
                    "estimated_duration": "medium",
                    "required_capabilities": ["argument_identification"],
                    "priority": obj_priority
                },
                {
                    "id": f"{base_task_id}4",
                    "description": "Structurer les arguments identifiés",
                    "objective_id": obj_id,
                    "estimated_duration": "short",
                    "required_capabilities": ["argument_identification"],
                    "priority": obj_priority
                }
            ])
        
        elif "détecter" in obj_description and "sophisme" in obj_description:
            # Objectif de détection de sophismes
            tasks.extend([
                {
                    "id": f"{base_task_id}1",
                    "description": "Analyser les arguments pour détecter les sophismes formels",
                    "objective_id": obj_id,
                    "estimated_duration": "medium",
                    "required_capabilities": ["fallacy_detection", "formal_logic"],
                    "priority": obj_priority
                },
                {
                    "id": f"{base_task_id}2",
                    "description": "Analyser les arguments pour détecter les sophismes informels",
                    "objective_id": obj_id,
                    "estimated_duration": "medium",
                    "required_capabilities": ["fallacy_detection", "rhetorical_analysis"],
                    "priority": obj_priority
                },
                {
                    "id": f"{base_task_id}3",
                    "description": "Classifier et documenter les sophismes détectés",
                    "objective_id": obj_id,
                    "estimated_duration": "short",
                    "required_capabilities": ["fallacy_detection"],
                    "priority": obj_priority
                }
            ])
        
        elif "analyser" in obj_description and "structure logique" in obj_description:
            # Objectif d'analyse de structure logique
            tasks.extend([
                {
                    "id": f"{base_task_id}1",
                    "description": "Formaliser les arguments en logique propositionnelle",
                    "objective_id": obj_id,
                    "estimated_duration": "medium",
                    "required_capabilities": ["formal_logic"],
                    "priority": obj_priority
                },
                {
                    "id": f"{base_task_id}2",
                    "description": "Vérifier la validité formelle des arguments",
                    "objective_id": obj_id,
                    "estimated_duration": "medium",
                    "required_capabilities": ["validity_checking"],
                    "priority": obj_priority
                },
                {
                    "id": f"{base_task_id}3",
                    "description": "Identifier les relations logiques entre arguments",
                    "objective_id": obj_id,
                    "estimated_duration": "medium",
                    "required_capabilities": ["formal_logic", "consistency_analysis"],
                    "priority": obj_priority
                }
            ])
        
        elif "évaluer" in obj_description and "cohérence" in obj_description:
            # Objectif d'évaluation de cohérence
            tasks.extend([
                {
                    "id": f"{base_task_id}1",
                    "description": "Analyser la cohérence interne des arguments",
                    "objective_id": obj_id,
                    "estimated_duration": "medium",
                    "required_capabilities": ["consistency_analysis"],
                    "priority": obj_priority
                },
                {
                    "id": f"{base_task_id}2",
                    "description": "Analyser la cohérence entre les différents arguments",
                    "objective_id": obj_id,
                    "estimated_duration": "medium",
                    "required_capabilities": ["consistency_analysis"],
                    "priority": obj_priority
                },
                {
                    "id": f"{base_task_id}3",
                    "description": "Générer un rapport de cohérence globale",
                    "objective_id": obj_id,
                    "estimated_duration": "short",
                    "required_capabilities": ["summary_generation"],
                    "priority": obj_priority
                }
            ])
        
        else:
            # Objectif générique
            tasks.extend([
                {
                    "id": f"{base_task_id}1",
                    "description": f"Analyser le texte pour {objective['description']}",
                    "objective_id": obj_id,
                    "estimated_duration": "medium",
                    "required_capabilities": ["text_extraction"],
                    "priority": obj_priority
                },
                {
                    "id": f"{base_task_id}2",
                    "description": f"Produire des résultats pour {objective['description']}",
                    "objective_id": obj_id,
                    "estimated_duration": "medium",
                    "required_capabilities": ["summary_generation"],
                    "priority": obj_priority
                }
            ])
        
        return tasks
    
    def _establish_task_dependencies(self, tasks: List[Dict[str, Any]]) -> None:
        """
        Établit les dépendances entre les tâches.
        
        Args:
            tasks: Liste des tâches
        """
        # Regrouper les tâches par objectif
        tasks_by_objective = {}
        for task in tasks:
            obj_id = task["objective_id"]
            if obj_id not in tasks_by_objective:
                tasks_by_objective[obj_id] = []
            tasks_by_objective[obj_id].append(task)
        
        # Pour chaque objectif, établir les dépendances séquentielles
        for obj_id, obj_tasks in tasks_by_objective.items():
            # Trier les tâches par leur identifiant (qui contient un numéro séquentiel)
            sorted_tasks = sorted(obj_tasks, key=lambda t: t["id"])
            
            # Établir les dépendances séquentielles
            for i in range(1, len(sorted_tasks)):
                prev_task = sorted_tasks[i-1]
                curr_task = sorted_tasks[i]
                self.state.add_task_dependency(prev_task["id"], curr_task["id"])
        
        # Établir des dépendances entre objectifs si nécessaire
        # (par exemple, l'identification des arguments doit précéder leur analyse)
        for task in tasks:
            task_desc = task["description"].lower()
            
            # Si la tâche concerne l'analyse d'arguments, elle dépend de l'identification
            if ("analyser" in task_desc or "évaluer" in task_desc) and "argument" in task_desc:
                # Chercher des tâches d'identification d'arguments
                for other_task in tasks:
                    other_desc = other_task["description"].lower()
                    if "identifier" in other_desc and "argument" in other_desc:
                        self.state.add_task_dependency(other_task["id"], task["id"])
    
    def _apply_strategic_adjustments(self, adjustments: Dict[str, Any]) -> None:
        """
        Applique les ajustements stratégiques reçus.
        
        Args:
            adjustments: Les ajustements à appliquer
        """
        # Appliquer les ajustements aux tâches
        if "objective_modifications" in adjustments:
            for mod in adjustments["objective_modifications"]:
                obj_id = mod.get("id")
                action = mod.get("action")
                
                if action == "modify" and obj_id:
                    # Mettre à jour les tâches associées à cet objectif
                    for status, tasks in self.state.tasks.items():
                        for i, task in enumerate(tasks):
                            if task.get("objective_id") == obj_id:
                                # Mettre à jour la priorité si nécessaire
                                if "priority" in mod.get("updates", {}):
                                    tasks[i]["priority"] = mod["updates"]["priority"]
                                    
                                    # Informer l'agent opérationnel du changement de priorité
                                    self.adapter.send_status_update(
                                        update_type="task_priority_change",
                                        status={
                                            "task_id": task["id"],
                                            "new_priority": mod["updates"]["priority"]
                                        },
                                        recipient_id=self._determine_appropriate_agent(task.get("required_capabilities", []))
                                    )
        
        # Appliquer les ajustements aux ressources
        if "resource_reallocation" in adjustments:
            # Informer les agents opérationnels des changements de ressources
            for resource, updates in adjustments["resource_reallocation"].items():
                if resource in self.agent_capabilities:
                    self.adapter.send_status_update(
                        update_type="resource_allocation_change",
                        status={
                            "resource": resource,
                            "updates": updates
                        },
                        recipient_id=resource
                    )
        
        # Journaliser l'application des ajustements
        self._log_action(
            "Application d'ajustements stratégiques",
            f"Ajustements appliqués: {', '.join(adjustments.keys())}"
        )
    
    def handle_task_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite le résultat d'une tâche reçue d'un agent opérationnel.

        Cette méthode met à jour l'état de la tâche (par exemple, de "en cours" à "terminée"),
        stocke les données de résultat, et vérifie si la complétion de cette tâche
        entraîne la complétion d'un objectif plus large. Si un objectif est
        entièrement atteint, un rapport est envoyé au niveau stratégique.

        Args:
            result (Dict[str, Any]): Le dictionnaire de résultat envoyé par un agent
                opérationnel. Doit contenir `tactical_task_id` et le statut de complétion.
            
        Returns:
            Dict[str, Any]: Un dictionnaire confirmant le statut du traitement du résultat.
        """
        task_id = result.get("task_id")
        tactical_task_id = result.get("tactical_task_id")
        
        if not tactical_task_id:
            self.logger.warning(f"Résultat reçu sans identifiant de tâche tactique: {result}")
            return {"status": "error", "message": "Identifiant de tâche tactique manquant"}
        
        # Mettre à jour le statut et la progression de la tâche
        if result.get("completion_status") == "completed" or result.get("status") == "completed":
            self.state.update_task_progress(tactical_task_id, 1.0)
        else:
            self.state.update_task_status(tactical_task_id, "failed")
        
        # Enregistrer le résultat
        self.state.add_intermediate_result(tactical_task_id, result)
        
        # Vérifier si toutes les tâches d'un objectif sont terminées
        objective_id = None
        for status, tasks in self.state.tasks.items():
            for task in tasks:
                if task.get("id") == tactical_task_id:
                    objective_id = task.get("objective_id")
                    break
            if objective_id:
                break
        
        if objective_id:
            # Vérifier si toutes les tâches de cet objectif sont terminées
            all_completed = True
            for status, tasks in self.state.tasks.items():
                if status not in ["completed", "failed"]:
                    for task in tasks:
                        if task.get("objective_id") == objective_id:
                            all_completed = False
                            break
                if not all_completed:
                    break
            
            if all_completed:
                # Envoyer un rapport de progression au niveau stratégique
                self.adapter.send_report(
                    report_type="objective_completion",
                    content={
                        "objective_id": objective_id,
                        "status": "completed",
                        RESULTS_DIR: self.state.get_objective_results(objective_id)
                    },
                    recipient_id="strategic_manager",
                    priority=MessagePriority.HIGH
                )
                
                self.logger.info(f"Objectif {objective_id} terminé, rapport envoyé au niveau stratégique")
        
        # Journaliser la réception du résultat
        self._log_action(
            "Réception de résultat",
            f"Résultat reçu pour la tâche {tactical_task_id}"
        )
        
        return {
            "status": "success",
            "message": f"Résultat de la tâche {tactical_task_id} traité avec succès"
        }
    
    def generate_status_report(self) -> Dict[str, Any]:
        """
        Génère un rapport de statut complet destiné au niveau stratégique.

        Ce rapport synthétise l'état actuel du niveau tactique, incluant :
        - La progression globale en pourcentage.
        - Le nombre de tâches par statut (terminée, en cours, etc.).
        - La progression détaillée pour chaque objectif stratégique.
        - Une liste des problèmes ou conflits identifiés.

        Le rapport est ensuite envoyé au `StrategicManager` via le middleware.

        Returns:
            Dict[str, Any]: Le rapport de statut détaillé.
        """
        # Calculer la progression globale
        total_tasks = 0
        completed_tasks = 0
        
        for status, tasks in self.state.tasks.items():
            total_tasks += len(tasks)
            if status == "completed":
                completed_tasks += len(tasks)
        
        overall_progress = completed_tasks / total_tasks if total_tasks > 0 else 0.0
        
        # Calculer la progression par objectif
        progress_by_objective = {}
        
        for obj in self.state.assigned_objectives:
            obj_id = obj["id"]
            obj_tasks = []
            
            for status, tasks in self.state.tasks.items():
                for task in tasks:
                    if task.get("objective_id") == obj_id:
                        obj_tasks.append((task, status))
            
            total_obj_tasks = len(obj_tasks)
            completed_obj_tasks = len([t for t, s in obj_tasks if s == "completed"])
            
            progress_by_objective[obj_id] = {
                "total_tasks": total_obj_tasks,
                "completed_tasks": completed_obj_tasks,
                "progress": completed_obj_tasks / total_obj_tasks if total_obj_tasks > 0 else 0.0
            }
        
        # Collecter les problèmes (utiliser identified_conflicts si issues n'existe pas)
        issues = []
        if hasattr(self.state, 'issues'):
            for issue in self.state.issues:
                issues.append(issue)
        else:
            # Utiliser identified_conflicts comme fallback
            for conflict in self.state.identified_conflicts:
                issues.append(conflict)
        
        # Créer le rapport
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_progress": overall_progress,
            "tasks_summary": {
                "total": total_tasks,
                "completed": completed_tasks,
                "in_progress": len(self.state.tasks.get("in_progress", [])),
                "pending": len(self.state.tasks.get("pending", [])),
                "failed": len(self.state.tasks.get("failed", []))
            },
            "progress_by_objective": progress_by_objective,
            "issues": issues
        }
        
        # Envoyer le rapport au niveau stratégique
        self.adapter.send_report(
            report_type="status_update",
            content=report,
            recipient_id="strategic_manager",
            priority=MessagePriority.NORMAL
        )
        
        self.logger.info("Rapport de statut généré et envoyé au niveau stratégique")
        
        return report

# Alias pour compatibilité avec les tests
TacticalCoordinator = TaskCoordinator