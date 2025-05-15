"""
Module définissant l'état du niveau opérationnel.

Cet état contient les informations pertinentes pour le niveau opérationnel,
notamment les tâches assignées, les extraits de texte à analyser, les résultats
d'analyse et les métriques opérationnelles.
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import uuid

class OperationalState:
    """
    Classe représentant l'état du niveau opérationnel.
    
    Cette classe encapsule toutes les données pertinentes pour le niveau opérationnel
    et fournit des méthodes pour manipuler ces données de manière contrôlée.
    """
    
    def __init__(self):
        """
        Initialise un nouvel état opérationnel.
        """
        # Tâches assignées par le niveau tactique
        self.assigned_tasks = []
        
        # Extraits de texte à analyser
        self.text_extracts = {}
        
        # Résultats d'analyse
        self.analysis_results = {
            "identified_arguments": [],
            "identified_fallacies": [],
            "formal_analyses": [],
            "extracted_data": {},
            "visualizations": [],
            # Résultats des outils d'analyse rhétorique améliorés
            "complex_fallacy_analyses": [],
            "contextual_fallacy_analyses": [],
            "fallacy_severity_evaluations": [],
            "argument_structure_visualizations": [],
            "argument_coherence_evaluations": [],
            "semantic_argument_analyses": [],
            "contextual_fallacy_detections": []
        }
        
        # Problèmes rencontrés
        self.encountered_issues = []
        
        # Métriques opérationnelles
        self.operational_metrics = {
            "processing_times": {},
            "confidence_scores": {},
            "coverage_metrics": {}
        }
        
        # Journal des actions opérationnelles
        self.operational_actions_log = []
        
        # Logger
        self.logger = logging.getLogger(__name__)
    
    def add_task(self, task: Dict[str, Any]) -> str:
        """
        Ajoute une tâche à l'état opérationnel.
        
        Args:
            task: La tâche à ajouter
            
        Returns:
            L'identifiant de la tâche
        """
        task_id = task.get("id", f"op-{uuid.uuid4().hex[:8]}")
        
        # Vérifier si la tâche existe déjà
        for existing_task in self.assigned_tasks:
            if existing_task.get("id") == task_id:
                self.logger.warning(f"La tâche {task_id} existe déjà dans l'état opérationnel.")
                return task_id
        
        # Ajouter la tâche
        task["status"] = "pending"
        task["assigned_at"] = datetime.now().isoformat()
        self.assigned_tasks.append(task)
        
        self.logger.info(f"Tâche {task_id} ajoutée à l'état opérationnel.")
        return task_id
    
    def update_task_status(self, task_id: str, status: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Met à jour le statut d'une tâche.
        
        Args:
            task_id: L'identifiant de la tâche
            status: Le nouveau statut
            details: Détails supplémentaires sur le changement de statut
            
        Returns:
            True si la mise à jour a réussi, False sinon
        """
        for task in self.assigned_tasks:
            if task.get("id") == task_id:
                old_status = task.get("status")
                task["status"] = status
                task["status_updated_at"] = datetime.now().isoformat()
                
                if details:
                    if "status_history" not in task:
                        task["status_history"] = []
                    
                    task["status_history"].append({
                        "from": old_status,
                        "to": status,
                        "timestamp": datetime.now().isoformat(),
                        "details": details
                    })
                
                self.logger.info(f"Statut de la tâche {task_id} mis à jour: {old_status} -> {status}")
                return True
        
        self.logger.warning(f"Impossible de mettre à jour le statut de la tâche {task_id}: tâche non trouvée.")
        return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère une tâche par son identifiant.
        
        Args:
            task_id: L'identifiant de la tâche
            
        Returns:
            La tâche ou None si elle n'existe pas
        """
        for task in self.assigned_tasks:
            if task.get("id") == task_id:
                return task
        
        return None
    
    def add_text_extract(self, extract_id: str, extract_data: Dict[str, Any]) -> bool:
        """
        Ajoute un extrait de texte à l'état opérationnel.
        
        Args:
            extract_id: L'identifiant de l'extrait
            extract_data: Les données de l'extrait
            
        Returns:
            True si l'ajout a réussi, False sinon
        """
        if extract_id in self.text_extracts:
            self.logger.warning(f"L'extrait {extract_id} existe déjà dans l'état opérationnel.")
            return False
        
        self.text_extracts[extract_id] = extract_data
        self.logger.info(f"Extrait {extract_id} ajouté à l'état opérationnel.")
        return True
    
    def add_analysis_result(self, result_type: str, result_data: Dict[str, Any]) -> str:
        """
        Ajoute un résultat d'analyse à l'état opérationnel.
        
        Args:
            result_type: Le type de résultat (identified_arguments, identified_fallacies, etc.)
            result_data: Les données du résultat
            
        Returns:
            L'identifiant du résultat
        """
        result_id = result_data.get("id", f"result-{uuid.uuid4().hex[:8]}")
        
        if result_type in self.analysis_results:
            result_data["id"] = result_id
            result_data["timestamp"] = datetime.now().isoformat()
            self.analysis_results[result_type].append(result_data)
            self.logger.info(f"Résultat d'analyse {result_id} de type {result_type} ajouté à l'état opérationnel.")
        else:
            self.logger.warning(f"Type de résultat inconnu: {result_type}")
            # Créer la catégorie si elle n'existe pas
            self.analysis_results[result_type] = [result_data]
            self.logger.info(f"Nouvelle catégorie de résultat créée: {result_type}")
        
        return result_id
    
    def add_issue(self, issue: Dict[str, Any]) -> str:
        """
        Ajoute un problème à l'état opérationnel.
        
        Args:
            issue: Le problème à ajouter
            
        Returns:
            L'identifiant du problème
        """
        issue_id = issue.get("id", f"issue-{uuid.uuid4().hex[:8]}")
        issue["id"] = issue_id
        issue["timestamp"] = datetime.now().isoformat()
        
        self.encountered_issues.append(issue)
        self.logger.info(f"Problème {issue_id} ajouté à l'état opérationnel.")
        
        return issue_id
    
    def update_metrics(self, task_id: str, metrics: Dict[str, Any]) -> bool:
        """
        Met à jour les métriques opérationnelles pour une tâche.
        
        Args:
            task_id: L'identifiant de la tâche
            metrics: Les métriques à mettre à jour
            
        Returns:
            True si la mise à jour a réussi, False sinon
        """
        # Mettre à jour les temps de traitement
        if "execution_time" in metrics:
            self.operational_metrics["processing_times"][task_id] = metrics["execution_time"]
        
        # Mettre à jour les scores de confiance
        if "confidence" in metrics:
            self.operational_metrics["confidence_scores"][task_id] = metrics["confidence"]
        
        # Mettre à jour les métriques de couverture
        if "coverage" in metrics:
            self.operational_metrics["coverage_metrics"][task_id] = metrics["coverage"]
        
        # Ajouter d'autres métriques spécifiques
        for key, value in metrics.items():
            if key not in ["execution_time", "confidence", "coverage"]:
                if key not in self.operational_metrics:
                    self.operational_metrics[key] = {}
                self.operational_metrics[key][task_id] = value
        
        self.logger.info(f"Métriques mises à jour pour la tâche {task_id}.")
        return True
    
    def log_action(self, action: str, details: Dict[str, Any]) -> None:
        """
        Enregistre une action dans le journal des actions opérationnelles.
        
        Args:
            action: L'action effectuée
            details: Les détails de l'action
        """
        log_entry = {
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "details": details
        }
        
        self.operational_actions_log.append(log_entry)
    
    def get_task_results(self, task_id: str) -> Dict[str, Any]:
        """
        Récupère tous les résultats associés à une tâche.
        
        Args:
            task_id: L'identifiant de la tâche
            
        Returns:
            Un dictionnaire contenant les résultats de la tâche
        """
        results = {}
        
        # Parcourir tous les types de résultats
        for result_type, result_list in self.analysis_results.items():
            task_results = []
            
            # Filtrer les résultats pour la tâche spécifiée
            for result in result_list:
                if result.get("task_id") == task_id:
                    task_results.append(result)
            
            if task_results:
                results[result_type] = task_results
        
        return results
    
    def get_task_issues(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Récupère tous les problèmes associés à une tâche.
        
        Args:
            task_id: L'identifiant de la tâche
            
        Returns:
            Une liste contenant les problèmes de la tâche
        """
        return [issue for issue in self.encountered_issues if issue.get("task_id") == task_id]
    
    def get_task_metrics(self, task_id: str) -> Dict[str, Any]:
        """
        Récupère toutes les métriques associées à une tâche.
        
        Args:
            task_id: L'identifiant de la tâche
            
        Returns:
            Un dictionnaire contenant les métriques de la tâche
        """
        metrics = {}
        
        # Parcourir toutes les catégories de métriques
        for metric_type, metric_dict in self.operational_metrics.items():
            if task_id in metric_dict:
                metrics[metric_type] = metric_dict[task_id]
        
        return metrics
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """
        Récupère toutes les tâches en attente.
        
        Returns:
            Une liste des tâches en attente
        """
        return [task for task in self.assigned_tasks if task.get("status") == "pending"]
    
    def get_in_progress_tasks(self) -> List[Dict[str, Any]]:
        """
        Récupère toutes les tâches en cours.
        
        Returns:
            Une liste des tâches en cours
        """
        return [task for task in self.assigned_tasks if task.get("status") == "in_progress"]
    
    def get_completed_tasks(self) -> List[Dict[str, Any]]:
        """
        Récupère toutes les tâches terminées.
        
        Returns:
            Une liste des tâches terminées
        """
        return [task for task in self.assigned_tasks if task.get("status") == "completed"]
    
    def get_failed_tasks(self) -> List[Dict[str, Any]]:
        """
        Récupère toutes les tâches échouées.
        
        Returns:
            Une liste des tâches échouées
        """
        return [task for task in self.assigned_tasks if task.get("status") == "failed"]
    
    def clear(self) -> None:
        """
        Réinitialise l'état opérationnel.
        """
        self.__init__()
        self.logger.info("État opérationnel réinitialisé.")