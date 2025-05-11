"""
Module définissant le Planificateur Stratégique de l'architecture hiérarchique.

Le Planificateur Stratégique est spécialisé dans la création de plans d'analyse structurés,
la décomposition des objectifs globaux en sous-objectifs cohérents, et l'établissement
des dépendances entre les différentes parties de l'analyse.
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

from argumentiation_analysis.orchestration.hierarchical.strategic.state import StrategicState


class StrategicPlanner:
    """
    Classe représentant le Planificateur Stratégique de l'architecture hiérarchique.
    
    Le Planificateur Stratégique est responsable de:
    - Créer des plans d'analyse structurés
    - Décomposer les objectifs globaux en sous-objectifs cohérents
    - Établir les dépendances entre les différentes parties de l'analyse
    - Définir les critères de succès pour chaque objectif
    - Ajuster les plans en fonction des feedbacks du niveau tactique
    """
    
    def __init__(self, strategic_state: Optional[StrategicState] = None):
        """
        Initialise un nouveau Planificateur Stratégique.
        
        Args:
            strategic_state: L'état stratégique à utiliser. Si None, un nouvel état est créé.
        """
        self.state = strategic_state if strategic_state else StrategicState()
        self.logger = logging.getLogger(__name__)
    
    def create_analysis_plan(self, text_metadata: Dict[str, Any], objectives: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Crée un plan d'analyse structuré basé sur les métadonnées du texte et les objectifs.
        
        Args:
            text_metadata: Métadonnées sur le texte à analyser (longueur, complexité, etc.)
            objectives: Liste des objectifs globaux définis
            
        Returns:
            Un plan d'analyse structuré
        """
        self.logger.info("Création d'un plan d'analyse structuré")
        
        # Analyser les caractéristiques du texte
        text_complexity = self._assess_text_complexity(text_metadata)
        
        # Décomposer les objectifs en phases d'analyse
        phases = self._decompose_objectives_into_phases(objectives, text_complexity)
        
        # Établir les dépendances entre les phases
        dependencies = self._establish_phase_dependencies(phases)
        
        # Définir les priorités des phases
        priorities = self._define_phase_priorities(phases, objectives)
        
        # Définir les critères de succès pour chaque phase
        success_criteria = self._define_success_criteria(phases, objectives)
        
        # Mettre à jour l'état stratégique avec le nouveau plan
        plan_update = {
            "phases": phases,
            "dependencies": dependencies,
            "priorities": priorities,
            "success_criteria": success_criteria
        }
        
        self.state.update_strategic_plan(plan_update)
        
        return self.state.strategic_plan
    
    def _assess_text_complexity(self, text_metadata: Dict[str, Any]) -> str:
        """
        Évalue la complexité du texte à analyser.
        
        Args:
            text_metadata: Métadonnées sur le texte
            
        Returns:
            Niveau de complexité ("low", "medium", "high")
        """
        # Cette méthode serait normalement plus sophistiquée, utilisant des métriques
        # linguistiques pour évaluer la complexité du texte
        
        length = text_metadata.get("length", 0)
        avg_sentence_length = text_metadata.get("avg_sentence_length", 0)
        vocabulary_diversity = text_metadata.get("vocabulary_diversity", 0)
        
        # Logique simplifiée pour déterminer la complexité
        if length > 5000 and avg_sentence_length > 20 and vocabulary_diversity > 0.7:
            return "high"
        elif length > 2000 and avg_sentence_length > 15 and vocabulary_diversity > 0.5:
            return "medium"
        else:
            return "low"
    
    def _decompose_objectives_into_phases(self, objectives: List[Dict[str, Any]], 
                                         text_complexity: str) -> List[Dict[str, Any]]:
        """
        Décompose les objectifs globaux en phases d'analyse.
        
        Args:
            objectives: Liste des objectifs globaux
            text_complexity: Niveau de complexité du texte
            
        Returns:
            Liste des phases d'analyse
        """
        phases = []
        
        # Phase 1: Analyse préliminaire (toujours présente)
        phase1 = {
            "id": "phase-1",
            "name": "Analyse préliminaire",
            "description": "Identification des éléments clés du texte",
            "objectives": [],
            "estimated_duration": "short" if text_complexity == "low" else "medium"
        }
        
        # Phase 2: Analyse approfondie (toujours présente)
        phase2 = {
            "id": "phase-2",
            "name": "Analyse approfondie",
            "description": "Détection des sophismes et analyse logique",
            "objectives": [],
            "estimated_duration": "medium" if text_complexity != "high" else "long"
        }
        
        # Phase 3: Synthèse et évaluation (toujours présente)
        phase3 = {
            "id": "phase-3",
            "name": "Synthèse et évaluation",
            "description": "Évaluation de la cohérence et synthèse finale",
            "objectives": [],
            "estimated_duration": "short" if text_complexity == "low" else "medium"
        }
        
        # Répartir les objectifs dans les phases appropriées
        for objective in objectives:
            obj_id = objective["id"]
            obj_description = objective["description"].lower()
            
            if "identifier" in obj_description or "extraire" in obj_description:
                phase1["objectives"].append(obj_id)
            elif "détecter" in obj_description or "analyser" in obj_description:
                phase2["objectives"].append(obj_id)
            elif "évaluer" in obj_description or "synthétiser" in obj_description:
                phase3["objectives"].append(obj_id)
            else:
                # Par défaut, ajouter à la phase 2
                phase2["objectives"].append(obj_id)
        
        phases.append(phase1)
        phases.append(phase2)
        phases.append(phase3)
        
        # Pour les textes très complexes, ajouter une phase intermédiaire
        if text_complexity == "high":
            intermediate_phase = {
                "id": "phase-2b",
                "name": "Analyse contextuelle",
                "description": "Analyse des relations contextuelles entre arguments",
                "objectives": [obj for obj in phase2["objectives"] if "contexte" in obj.lower()],
                "estimated_duration": "medium"
            }
            
            # Retirer ces objectifs de la phase 2
            phase2["objectives"] = [obj for obj in phase2["objectives"] 
                                   if obj not in intermediate_phase["objectives"]]
            
            # Insérer la phase intermédiaire
            phases.insert(2, intermediate_phase)
        
        return phases
    
    def _establish_phase_dependencies(self, phases: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Établit les dépendances entre les phases d'analyse.
        
        Args:
            phases: Liste des phases d'analyse
            
        Returns:
            Dictionnaire des dépendances entre phases
        """
        dependencies = {}
        
        # Par défaut, chaque phase dépend de la précédente
        for i in range(1, len(phases)):
            dependencies[phases[i]["id"]] = [phases[i-1]["id"]]
        
        return dependencies
    
    def _define_phase_priorities(self, phases: List[Dict[str, Any]], 
                                objectives: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Définit les priorités pour chaque phase en fonction des objectifs qu'elle contient.
        
        Args:
            phases: Liste des phases d'analyse
            objectives: Liste des objectifs globaux
            
        Returns:
            Dictionnaire des priorités par phase
        """
        priorities = {}
        objective_priorities = {obj["id"]: obj.get("priority", "medium") for obj in objectives}
        
        for phase in phases:
            phase_id = phase["id"]
            phase_objectives = phase["objectives"]
            
            # Déterminer la priorité de la phase en fonction des objectifs qu'elle contient
            if not phase_objectives:
                priorities[phase_id] = "medium"
                continue
            
            # Compter les priorités des objectifs dans cette phase
            priority_counts = {"high": 0, "medium": 0, "low": 0}
            
            for obj_id in phase_objectives:
                obj_priority = objective_priorities.get(obj_id, "medium")
                priority_counts[obj_priority] += 1
            
            # Déterminer la priorité globale de la phase
            if priority_counts["high"] > 0:
                priorities[phase_id] = "high"
            elif priority_counts["medium"] > 0:
                priorities[phase_id] = "medium"
            else:
                priorities[phase_id] = "low"
        
        return priorities
    
    def _define_success_criteria(self, phases: List[Dict[str, Any]], 
                               objectives: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Définit les critères de succès pour chaque phase.
        
        Args:
            phases: Liste des phases d'analyse
            objectives: Liste des objectifs globaux
            
        Returns:
            Dictionnaire des critères de succès par phase
        """
        success_criteria = {}
        objective_criteria = {obj["id"]: obj.get("success_criteria", "") for obj in objectives}
        
        for phase in phases:
            phase_id = phase["id"]
            phase_objectives = phase["objectives"]
            
            if not phase_objectives:
                success_criteria[phase_id] = "Complétion de la phase"
                continue
            
            # Combiner les critères de succès des objectifs de cette phase
            phase_criteria = []
            
            for obj_id in phase_objectives:
                obj_criterion = objective_criteria.get(obj_id, "")
                if obj_criterion:
                    phase_criteria.append(obj_criterion)
            
            if phase_criteria:
                success_criteria[phase_id] = "; ".join(phase_criteria)
            else:
                # Critères par défaut basés sur le nom de la phase
                if "préliminaire" in phase["name"].lower():
                    success_criteria[phase_id] = "Identification d'au moins 80% des éléments clés"
                elif "approfondie" in phase["name"].lower():
                    success_criteria[phase_id] = "Analyse détaillée d'au moins 70% des arguments"
                elif "synthèse" in phase["name"].lower():
                    success_criteria[phase_id] = "Évaluation cohérente de l'argumentation globale"
                else:
                    success_criteria[phase_id] = "Complétion satisfaisante de la phase"
        
        return success_criteria
    
    def adjust_plan(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ajuste le plan d'analyse en fonction du feedback reçu.
        
        Args:
            feedback: Feedback sur l'exécution du plan
            
        Returns:
            Le plan ajusté
        """
        self.logger.info("Ajustement du plan d'analyse basé sur le feedback")
        
        # Extraire les informations pertinentes du feedback
        progress = feedback.get("progress", {})
        issues = feedback.get("issues", [])
        
        # Identifier les phases problématiques
        problematic_phases = self._identify_problematic_phases(progress, issues)
        
        # Ajuster le plan pour les phases problématiques
        plan_adjustments = {}
        
        for phase_id, problems in problematic_phases.items():
            phase_adjustment = self._create_phase_adjustment(phase_id, problems)
            if phase_adjustment:
                plan_adjustments[phase_id] = phase_adjustment
        
        # Mettre à jour le plan stratégique si des ajustements sont nécessaires
        if plan_adjustments:
            # Préparer les mises à jour du plan
            plan_update = {
                "phases": [],
                "priorities": {},
                "success_criteria": {}
            }
            
            # Appliquer les ajustements aux phases existantes
            for phase in self.state.strategic_plan["phases"]:
                phase_id = phase["id"]
                if phase_id in plan_adjustments:
                    # Créer une copie de la phase avec les ajustements
                    adjusted_phase = phase.copy()
                    adjusted_phase.update(plan_adjustments[phase_id].get("phase_updates", {}))
                    plan_update["phases"].append(adjusted_phase)
                    
                    # Mettre à jour les priorités si nécessaire
                    if "priority" in plan_adjustments[phase_id]:
                        plan_update["priorities"][phase_id] = plan_adjustments[phase_id]["priority"]
                    
                    # Mettre à jour les critères de succès si nécessaire
                    if "success_criteria" in plan_adjustments[phase_id]:
                        plan_update["success_criteria"][phase_id] = plan_adjustments[phase_id]["success_criteria"]
            
            # Mettre à jour l'état stratégique
            self.state.update_strategic_plan(plan_update)
        
        return self.state.strategic_plan
    
    def _identify_problematic_phases(self, progress: Dict[str, Any], 
                                   issues: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Identifie les phases problématiques en fonction du progrès et des problèmes signalés.
        
        Args:
            progress: Informations sur la progression des phases
            issues: Liste des problèmes signalés
            
        Returns:
            Dictionnaire des phases problématiques avec leurs problèmes
        """
        problematic_phases = {}
        
        # Identifier les phases avec une progression insuffisante
        for phase_id, phase_progress in progress.items():
            if phase_progress.get("completion_rate", 1.0) < 0.5 and phase_progress.get("expected_completion_rate", 0.0) > 0.7:
                if phase_id not in problematic_phases:
                    problematic_phases[phase_id] = []
                
                problematic_phases[phase_id].append({
                    "type": "insufficient_progress",
                    "details": {
                        "actual": phase_progress.get("completion_rate", 0.0),
                        "expected": phase_progress.get("expected_completion_rate", 0.0)
                    }
                })
        
        # Ajouter les problèmes signalés par phase
        for issue in issues:
            phase_id = issue.get("phase_id")
            if phase_id:
                if phase_id not in problematic_phases:
                    problematic_phases[phase_id] = []
                
                problematic_phases[phase_id].append({
                    "type": issue.get("type", "unknown_issue"),
                    "details": issue.get("details", {})
                })
        
        return problematic_phases
    
    def _create_phase_adjustment(self, phase_id: str, 
                               problems: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Crée un ajustement pour une phase problématique.
        
        Args:
            phase_id: Identifiant de la phase
            problems: Liste des problèmes de la phase
            
        Returns:
            Ajustement à appliquer à la phase
        """
        adjustment = {
            "phase_updates": {}
        }
        
        for problem in problems:
            problem_type = problem.get("type")
            details = problem.get("details", {})
            
            if problem_type == "insufficient_progress":
                # Augmenter la durée estimée
                adjustment["phase_updates"]["estimated_duration"] = "long"
                # Augmenter la priorité
                adjustment["priority"] = "high"
            
            elif problem_type == "resource_shortage":
                # Pas d'ajustement direct du plan, géré par l'allocateur de ressources
                pass
            
            elif problem_type == "objective_unrealistic":
                # Ajuster les critères de succès
                if "suggested_criteria" in details:
                    adjustment["success_criteria"] = details["suggested_criteria"]
            
            elif problem_type == "dependency_issue":
                # Ajuster les dépendances (nécessiterait une mise à jour plus complexe)
                pass
        
        return adjustment if adjustment["phase_updates"] or "priority" in adjustment or "success_criteria" in adjustment else {}
    
    def decompose_objective(self, objective_id: str) -> List[Dict[str, Any]]:
        """
        Décompose un objectif global en sous-objectifs plus spécifiques.
        
        Args:
            objective_id: Identifiant de l'objectif à décomposer
            
        Returns:
            Liste des sous-objectifs
        """
        self.logger.info(f"Décomposition de l'objectif {objective_id}")
        
        # Trouver l'objectif dans l'état
        objective = None
        for obj in self.state.global_objectives:
            if obj["id"] == objective_id:
                objective = obj
                break
        
        if not objective:
            self.logger.warning(f"Objectif {objective_id} non trouvé")
            return []
        
        # Décomposer l'objectif en fonction de sa description
        description = objective["description"].lower()
        sub_objectives = []
        
        if "identifier" in description and "arguments" in description:
            sub_objectives.extend([
                {
                    "id": f"{objective_id}-sub1",
                    "description": "Identifier les prémisses explicites",
                    "parent_id": objective_id,
                    "priority": objective.get("priority", "medium")
                },
                {
                    "id": f"{objective_id}-sub2",
                    "description": "Identifier les conclusions explicites",
                    "parent_id": objective_id,
                    "priority": objective.get("priority", "medium")
                },
                {
                    "id": f"{objective_id}-sub3",
                    "description": "Identifier les prémisses implicites",
                    "parent_id": objective_id,
                    "priority": objective.get("priority", "medium")
                }
            ])
        
        elif "détecter" in description and "sophisme" in description:
            sub_objectives.extend([
                {
                    "id": f"{objective_id}-sub1",
                    "description": "Détecter les sophismes formels",
                    "parent_id": objective_id,
                    "priority": objective.get("priority", "medium")
                },
                {
                    "id": f"{objective_id}-sub2",
                    "description": "Détecter les sophismes informels",
                    "parent_id": objective_id,
                    "priority": objective.get("priority", "medium")
                },
                {
                    "id": f"{objective_id}-sub3",
                    "description": "Évaluer la gravité des sophismes",
                    "parent_id": objective_id,
                    "priority": objective.get("priority", "low")
                }
            ])
        
        elif "analyser" in description and "structure" in description:
            sub_objectives.extend([
                {
                    "id": f"{objective_id}-sub1",
                    "description": "Formaliser les arguments en logique propositionnelle",
                    "parent_id": objective_id,
                    "priority": objective.get("priority", "medium")
                },
                {
                    "id": f"{objective_id}-sub2",
                    "description": "Analyser la validité formelle des arguments",
                    "parent_id": objective_id,
                    "priority": objective.get("priority", "high")
                },
                {
                    "id": f"{objective_id}-sub3",
                    "description": "Identifier les relations entre arguments",
                    "parent_id": objective_id,
                    "priority": objective.get("priority", "medium")
                }
            ])
        
        elif "évaluer" in description and "cohérence" in description:
            sub_objectives.extend([
                {
                    "id": f"{objective_id}-sub1",
                    "description": "Évaluer la cohérence interne des arguments",
                    "parent_id": objective_id,
                    "priority": objective.get("priority", "high")
                },
                {
                    "id": f"{objective_id}-sub2",
                    "description": "Évaluer la cohérence entre les arguments",
                    "parent_id": objective_id,
                    "priority": objective.get("priority", "medium")
                },
                {
                    "id": f"{objective_id}-sub3",
                    "description": "Calculer un score global de cohérence",
                    "parent_id": objective_id,
                    "priority": objective.get("priority", "low")
                }
            ])
        
        # Si aucune décomposition spécifique n'a été trouvée, créer une décomposition générique
        if not sub_objectives:
            sub_objectives.extend([
                {
                    "id": f"{objective_id}-sub1",
                    "description": f"Première étape de {objective['description']}",
                    "parent_id": objective_id,
                    "priority": objective.get("priority", "medium")
                },
                {
                    "id": f"{objective_id}-sub2",
                    "description": f"Deuxième étape de {objective['description']}",
                    "parent_id": objective_id,
                    "priority": objective.get("priority", "medium")
                }
            ])
        
        return sub_objectives