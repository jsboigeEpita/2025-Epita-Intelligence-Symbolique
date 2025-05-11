"""
Module définissant le Résolveur de Conflits de l'architecture hiérarchique.

Le Résolveur de Conflits est responsable de la détection et de l'analyse des contradictions
dans les résultats, de l'arbitrage entre différentes interprétations ou analyses, et du
maintien de la cohérence globale de l'analyse.
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import uuid

from argumentiation_analysis.orchestration.hierarchical.tactical.state import TacticalState


class ConflictResolver:
    """
    Classe représentant le Résolveur de Conflits de l'architecture hiérarchique.
    
    Le Résolveur de Conflits est responsable de:
    - Détecter et analyser les contradictions dans les résultats
    - Arbitrer entre différentes interprétations ou analyses
    - Appliquer des heuristiques de résolution de conflits
    - Maintenir la cohérence globale de l'analyse
    - Escalader les conflits non résolus au niveau stratégique
    """
    
    def __init__(self, tactical_state: Optional[TacticalState] = None):
        """
        Initialise un nouveau Résolveur de Conflits.
        
        Args:
            tactical_state: L'état tactique à utiliser. Si None, un nouvel état est créé.
        """
        self.state = tactical_state if tactical_state else TacticalState()
        self.logger = logging.getLogger(__name__)
        
        # Stratégies de résolution de conflits
        self.resolution_strategies = {
            "contradiction": self._resolve_contradiction,
            "overlap": self._resolve_overlap,
            "inconsistency": self._resolve_inconsistency,
            "ambiguity": self._resolve_ambiguity
        }
    
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
            "agent_id": "conflict_resolver"
        }
        
        self.state.log_tactical_action(action)
        self.logger.info(f"Action tactique: {action_type} - {description}")
    
    def detect_conflicts(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Détecte les conflits potentiels dans les résultats fournis.
        
        Args:
            results: Résultats à analyser pour détecter des conflits
            
        Returns:
            Liste des conflits détectés
        """
        self.logger.info("Détection de conflits dans les résultats")
        
        conflicts = []
        
        # Récupérer les résultats existants pour comparaison
        existing_results = {}
        for task_id, result in self.state.intermediate_results.items():
            # Trouver l'objectif associé à cette tâche
            task_objective_id = None
            for status, tasks in self.state.tasks.items():
                for task in tasks:
                    if task["id"] == task_id:
                        task_objective_id = task.get("objective_id")
                        break
                if task_objective_id:
                    break
            
            if task_objective_id:
                if task_objective_id not in existing_results:
                    existing_results[task_objective_id] = {}
                existing_results[task_objective_id][task_id] = result
        
        # Vérifier les conflits potentiels
        if "identified_arguments" in results:
            conflicts.extend(self._check_argument_conflicts(results["identified_arguments"], existing_results))
        
        if "identified_fallacies" in results:
            conflicts.extend(self._check_fallacy_conflicts(results["identified_fallacies"], existing_results))
        
        if "formal_analyses" in results:
            conflicts.extend(self._check_formal_analysis_conflicts(results["formal_analyses"], existing_results))
        
        # Ajouter les conflits détectés à l'état
        for conflict in conflicts:
            self.state.add_conflict(conflict)
        
        # Journaliser l'action
        self._log_action("Détection de conflits", 
                        f"Détection de {len(conflicts)} conflits dans les résultats")
        
        return conflicts
    
    def _check_argument_conflicts(self, arguments: List[Dict[str, Any]], 
                                existing_results: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Vérifie les conflits entre les arguments identifiés.
        
        Args:
            arguments: Liste des arguments à vérifier
            existing_results: Résultats existants pour comparaison
            
        Returns:
            Liste des conflits détectés
        """
        conflicts = []
        
        # Parcourir tous les objectifs et leurs résultats
        for obj_id, obj_results in existing_results.items():
            for task_id, result in obj_results.items():
                if "identified_arguments" not in result:
                    continue
                
                existing_arguments = result["identified_arguments"]
                
                # Comparer les arguments
                for new_arg in arguments:
                    for existing_arg in existing_arguments:
                        # Vérifier les contradictions
                        if self._are_arguments_contradictory(new_arg, existing_arg):
                            conflict_id = f"conflict-{uuid.uuid4().hex[:8]}"
                            conflicts.append({
                                "id": conflict_id,
                                "type": "contradiction",
                                "description": "Contradiction entre arguments identifiés",
                                "involved_tasks": [task_id],  # La tâche actuelle serait ajoutée plus tard
                                "severity": "medium",
                                "details": {
                                    "argument1": new_arg,
                                    "argument2": existing_arg
                                }
                            })
                        
                        # Vérifier les chevauchements
                        elif self._are_arguments_overlapping(new_arg, existing_arg):
                            conflict_id = f"conflict-{uuid.uuid4().hex[:8]}"
                            conflicts.append({
                                "id": conflict_id,
                                "type": "overlap",
                                "description": "Chevauchement entre arguments identifiés",
                                "involved_tasks": [task_id],  # La tâche actuelle serait ajoutée plus tard
                                "severity": "low",
                                "details": {
                                    "argument1": new_arg,
                                    "argument2": existing_arg
                                }
                            })
        
        return conflicts
    
    def _check_fallacy_conflicts(self, fallacies: List[Dict[str, Any]], 
                               existing_results: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Vérifie les conflits entre les sophismes détectés.
        
        Args:
            fallacies: Liste des sophismes à vérifier
            existing_results: Résultats existants pour comparaison
            
        Returns:
            Liste des conflits détectés
        """
        conflicts = []
        
        # Parcourir tous les objectifs et leurs résultats
        for obj_id, obj_results in existing_results.items():
            for task_id, result in obj_results.items():
                if "identified_fallacies" not in result:
                    continue
                
                existing_fallacies = result["identified_fallacies"]
                
                # Comparer les sophismes
                for new_fallacy in fallacies:
                    for existing_fallacy in existing_fallacies:
                        # Vérifier les contradictions dans la classification
                        if self._are_fallacies_contradictory(new_fallacy, existing_fallacy):
                            conflict_id = f"conflict-{uuid.uuid4().hex[:8]}"
                            conflicts.append({
                                "id": conflict_id,
                                "type": "contradiction",
                                "description": "Contradiction dans la classification des sophismes",
                                "involved_tasks": [task_id],  # La tâche actuelle serait ajoutée plus tard
                                "severity": "medium",
                                "details": {
                                    "fallacy1": new_fallacy,
                                    "fallacy2": existing_fallacy
                                }
                            })
        
        return conflicts
    
    def _check_formal_analysis_conflicts(self, analyses: List[Dict[str, Any]], 
                                       existing_results: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Vérifie les conflits entre les analyses formelles.
        
        Args:
            analyses: Liste des analyses formelles à vérifier
            existing_results: Résultats existants pour comparaison
            
        Returns:
            Liste des conflits détectés
        """
        conflicts = []
        
        # Parcourir tous les objectifs et leurs résultats
        for obj_id, obj_results in existing_results.items():
            for task_id, result in obj_results.items():
                if "formal_analyses" not in result:
                    continue
                
                existing_analyses = result["formal_analyses"]
                
                # Comparer les analyses formelles
                for new_analysis in analyses:
                    for existing_analysis in existing_analyses:
                        # Vérifier les contradictions dans les conclusions de validité
                        if self._are_formal_analyses_contradictory(new_analysis, existing_analysis):
                            conflict_id = f"conflict-{uuid.uuid4().hex[:8]}"
                            conflicts.append({
                                "id": conflict_id,
                                "type": "contradiction",
                                "description": "Contradiction dans les analyses formelles",
                                "involved_tasks": [task_id],  # La tâche actuelle serait ajoutée plus tard
                                "severity": "high",
                                "details": {
                                    "analysis1": new_analysis,
                                    "analysis2": existing_analysis
                                }
                            })
        
        return conflicts
    
    def _are_arguments_contradictory(self, arg1: Dict[str, Any], arg2: Dict[str, Any]) -> bool:
        """
        Détermine si deux arguments sont contradictoires.
        
        Args:
            arg1: Premier argument
            arg2: Deuxième argument
            
        Returns:
            True si les arguments sont contradictoires, False sinon
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: vérifier si les conclusions sont opposées
        
        if "conclusion" in arg1 and "conclusion" in arg2:
            conclusion1 = arg1["conclusion"].lower()
            conclusion2 = arg2["conclusion"].lower()
            
            # Vérifier les marqueurs de contradiction
            contradiction_markers = [
                ("est", "n'est pas"),
                ("peut", "ne peut pas"),
                ("doit", "ne doit pas"),
                ("vrai", "faux"),
                ("toujours", "jamais")
            ]
            
            for pos, neg in contradiction_markers:
                if (pos in conclusion1 and neg in conclusion2) or (neg in conclusion1 and pos in conclusion2):
                    return True
        
        return False
    
    def _are_arguments_overlapping(self, arg1: Dict[str, Any], arg2: Dict[str, Any]) -> bool:
        """
        Détermine si deux arguments se chevauchent (concernent le même sujet).
        
        Args:
            arg1: Premier argument
            arg2: Deuxième argument
            
        Returns:
            True si les arguments se chevauchent, False sinon
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: vérifier si les sujets sont similaires
        
        if "subject" in arg1 and "subject" in arg2:
            subject1 = arg1["subject"].lower()
            subject2 = arg2["subject"].lower()
            
            # Vérifier si les sujets sont similaires
            return subject1 == subject2 or subject1 in subject2 or subject2 in subject1
        
        return False
    
    def _are_fallacies_contradictory(self, fallacy1: Dict[str, Any], fallacy2: Dict[str, Any]) -> bool:
        """
        Détermine si deux classifications de sophismes sont contradictoires.
        
        Args:
            fallacy1: Premier sophisme
            fallacy2: Deuxième sophisme
            
        Returns:
            True si les classifications sont contradictoires, False sinon
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: vérifier si les types sont différents pour le même segment
        
        if "segment" in fallacy1 and "segment" in fallacy2 and "type" in fallacy1 and "type" in fallacy2:
            segment1 = fallacy1["segment"].lower()
            segment2 = fallacy2["segment"].lower()
            type1 = fallacy1["type"].lower()
            type2 = fallacy2["type"].lower()
            
            # Si les segments sont similaires mais les types sont différents
            segment_similarity = segment1 == segment2 or segment1 in segment2 or segment2 in segment1
            type_difference = type1 != type2
            
            return segment_similarity and type_difference
        
        return False
    
    def _are_formal_analyses_contradictory(self, analysis1: Dict[str, Any], analysis2: Dict[str, Any]) -> bool:
        """
        Détermine si deux analyses formelles sont contradictoires.
        
        Args:
            analysis1: Première analyse
            analysis2: Deuxième analyse
            
        Returns:
            True si les analyses sont contradictoires, False sinon
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: vérifier si les conclusions de validité sont opposées
        
        if "argument_id" in analysis1 and "argument_id" in analysis2 and "is_valid" in analysis1 and "is_valid" in analysis2:
            arg_id1 = analysis1["argument_id"]
            arg_id2 = analysis2["argument_id"]
            is_valid1 = analysis1["is_valid"]
            is_valid2 = analysis2["is_valid"]
            
            # Si les arguments sont les mêmes mais les conclusions de validité sont opposées
            return arg_id1 == arg_id2 and is_valid1 != is_valid2
        
        return False
    
    def resolve_conflict(self, conflict_id: str) -> Dict[str, Any]:
        """
        Tente de résoudre un conflit identifié.
        
        Args:
            conflict_id: Identifiant du conflit à résoudre
            
        Returns:
            Un dictionnaire contenant le résultat de la résolution
        """
        self.logger.info(f"Tentative de résolution du conflit {conflict_id}")
        
        # Trouver le conflit dans l'état
        conflict = None
        for c in self.state.identified_conflicts:
            if c["id"] == conflict_id:
                conflict = c
                break
        
        if not conflict:
            return {"status": "error", "message": f"Conflit {conflict_id} non trouvé"}
        
        # Vérifier si le conflit est déjà résolu
        if conflict.get("resolved", False):
            return {"status": "already_resolved", "resolution": conflict.get("resolution", {})}
        
        # Appliquer la stratégie de résolution appropriée
        conflict_type = conflict.get("type", "contradiction")
        resolution_strategy = self.resolution_strategies.get(conflict_type, self._resolve_contradiction)
        
        resolution = resolution_strategy(conflict)
        
        # Mettre à jour l'état avec la résolution
        resolution_success = self.state.resolve_conflict(conflict_id, resolution)
        
        if not resolution_success:
            return {"status": "error", "message": "Échec de la mise à jour de l'état"}
        
        # Journaliser l'action
        self._log_action("Résolution de conflit", 
                        f"Résolution du conflit {conflict_id} de type {conflict_type}")
        
        return {
            "status": "success",
            "conflict_id": conflict_id,
            "conflict_type": conflict_type,
            "resolution": resolution
        }
    
    def _resolve_contradiction(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Résout un conflit de type contradiction.
        
        Args:
            conflict: Le conflit à résoudre
            
        Returns:
            La résolution du conflit
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: choisir l'option avec la plus grande confiance
        
        details = conflict.get("details", {})
        
        if "argument1" in details and "argument2" in details:
            arg1 = details["argument1"]
            arg2 = details["argument2"]
            
            # Choisir l'argument avec la plus grande confiance
            confidence1 = arg1.get("confidence", 0.5)
            confidence2 = arg2.get("confidence", 0.5)
            
            if confidence1 >= confidence2:
                chosen_arg = arg1
                rejected_arg = arg2
            else:
                chosen_arg = arg2
                rejected_arg = arg1
            
            return {
                "method": "confidence_based",
                "chosen_option": chosen_arg,
                "rejected_option": rejected_arg,
                "rationale": f"Choix basé sur la confiance: {max(confidence1, confidence2):.2f} > {min(confidence1, confidence2):.2f}"
            }
        
        elif "fallacy1" in details and "fallacy2" in details:
            fallacy1 = details["fallacy1"]
            fallacy2 = details["fallacy2"]
            
            # Choisir le sophisme avec la plus grande confiance
            confidence1 = fallacy1.get("confidence", 0.5)
            confidence2 = fallacy2.get("confidence", 0.5)
            
            if confidence1 >= confidence2:
                chosen_fallacy = fallacy1
                rejected_fallacy = fallacy2
            else:
                chosen_fallacy = fallacy2
                rejected_fallacy = fallacy1
            
            return {
                "method": "confidence_based",
                "chosen_option": chosen_fallacy,
                "rejected_option": rejected_fallacy,
                "rationale": f"Choix basé sur la confiance: {max(confidence1, confidence2):.2f} > {min(confidence1, confidence2):.2f}"
            }
        
        elif "analysis1" in details and "analysis2" in details:
            analysis1 = details["analysis1"]
            analysis2 = details["analysis2"]
            
            # Choisir l'analyse avec la plus grande confiance
            confidence1 = analysis1.get("confidence", 0.5)
            confidence2 = analysis2.get("confidence", 0.5)
            
            if confidence1 >= confidence2:
                chosen_analysis = analysis1
                rejected_analysis = analysis2
            else:
                chosen_analysis = analysis2
                rejected_analysis = analysis1
            
            return {
                "method": "confidence_based",
                "chosen_option": chosen_analysis,
                "rejected_option": rejected_analysis,
                "rationale": f"Choix basé sur la confiance: {max(confidence1, confidence2):.2f} > {min(confidence1, confidence2):.2f}"
            }
        
        # Résolution par défaut
        return {
            "method": "default",
            "rationale": "Résolution par défaut: conflit non résolu, escalade nécessaire"
        }
    
    def _resolve_overlap(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Résout un conflit de type chevauchement.
        
        Args:
            conflict: Le conflit à résoudre
            
        Returns:
            La résolution du conflit
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: fusionner les arguments qui se chevauchent
        
        details = conflict.get("details", {})
        
        if "argument1" in details and "argument2" in details:
            arg1 = details["argument1"]
            arg2 = details["argument2"]
            
            # Créer un argument fusionné
            merged_arg = {
                "id": f"merged-{uuid.uuid4().hex[:8]}",
                "premises": list(set(arg1.get("premises", []) + arg2.get("premises", []))),
                "conclusion": arg1.get("conclusion") if arg1.get("confidence", 0.5) >= arg2.get("confidence", 0.5) else arg2.get("conclusion"),
                "confidence": max(arg1.get("confidence", 0.5), arg2.get("confidence", 0.5)),
                "source": f"Fusion de {arg1.get('id', 'arg1')} et {arg2.get('id', 'arg2')}"
            }
            
            return {
                "method": "merge",
                "merged_result": merged_arg,
                "original_options": [arg1, arg2],
                "rationale": "Fusion des arguments qui se chevauchent"
            }
        
        # Résolution par défaut
        return {
            "method": "default",
            "rationale": "Résolution par défaut: maintien des deux options"
        }
    
    def _resolve_inconsistency(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Résout un conflit de type incohérence.
        
        Args:
            conflict: Le conflit à résoudre
            
        Returns:
            La résolution du conflit
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: choisir l'option la plus récente
        
        return {
            "method": "recency",
            "rationale": "Choix de l'option la plus récente"
        }
    
    def _resolve_ambiguity(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Résout un conflit de type ambiguïté.
        
        Args:
            conflict: Le conflit à résoudre
            
        Returns:
            La résolution du conflit
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: conserver les deux interprétations
        
        return {
            "method": "preserve_both",
            "rationale": "Conservation des deux interprétations possibles"
        }
    
    def escalate_unresolved_conflicts(self) -> List[Dict[str, Any]]:
        """
        Identifie les conflits qui n'ont pas pu être résolus et doivent être escaladés.
        
        Returns:
            Liste des conflits à escalader
        """
        self.logger.info("Identification des conflits à escalader")
        
        conflicts_to_escalate = []
        
        for conflict in self.state.identified_conflicts:
            # Vérifier si le conflit est déjà résolu
            if conflict.get("resolved", False):
                resolution = conflict.get("resolution", {})
                method = resolution.get("method")
                
                # Si la méthode de résolution est "default", le conflit n'a pas été résolu correctement
                if method == "default":
                    conflicts_to_escalate.append({
                        "conflict_id": conflict["id"],
                        "conflict_type": conflict.get("type", "unknown"),
                        "description": conflict.get("description", ""),
                        "severity": conflict.get("severity", "medium"),
                        "involved_tasks": conflict.get("involved_tasks", []),
                        "resolution_attempt": resolution
                    })
            else:
                # Si le conflit n'est pas résolu du tout
                conflicts_to_escalate.append({
                    "conflict_id": conflict["id"],
                    "conflict_type": conflict.get("type", "unknown"),
                    "description": conflict.get("description", ""),
                    "severity": conflict.get("severity", "medium"),
                    "involved_tasks": conflict.get("involved_tasks", []),
                    "resolution_attempt": None
                })
        
        # Journaliser l'action
        self._log_action("Escalade de conflits", 
                        f"Escalade de {len(conflicts_to_escalate)} conflits non résolus")
        
        return conflicts_to_escalate