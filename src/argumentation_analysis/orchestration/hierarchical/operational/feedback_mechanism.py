"""
Module définissant les mécanismes de feedback pour l'apprentissage continu des outils d'analyse rhétorique.

Ce module fournit des fonctionnalités pour collecter, traiter et appliquer les feedbacks
sur les résultats des outils d'analyse rhétorique, permettant ainsi leur amélioration continue.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path

from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState


class RhetoricalToolsFeedback:
    """
    Classe gérant les mécanismes de feedback pour les outils d'analyse rhétorique.
    
    Cette classe permet de collecter, traiter et appliquer les feedbacks sur les résultats
    des outils d'analyse rhétorique, facilitant ainsi leur apprentissage continu.
    """
    
    def __init__(self, feedback_storage_path: Optional[str] = None):
        """
        Initialise un nouveau gestionnaire de feedback.
        
        Args:
            feedback_storage_path: Chemin vers le répertoire de stockage des feedbacks.
                                  Si None, utilise le répertoire par défaut.
        """
        self.logger = logging.getLogger("RhetoricalToolsFeedback")
        
        # Définir le chemin de stockage des feedbacks
        if feedback_storage_path:
            self.feedback_storage_path = Path(feedback_storage_path)
        else:
            # Chemin par défaut dans le répertoire du projet
            self.feedback_storage_path = Path("argumentation_analysis/data/feedback")
        
        # Créer le répertoire s'il n'existe pas
        self.feedback_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Historique des feedbacks
        self.feedback_history = []
        
        # Statistiques des feedbacks
        self.feedback_stats = {
            "complex_fallacy_analysis": {"positive": 0, "negative": 0, "neutral": 0},
            "contextual_fallacy_analysis": {"positive": 0, "negative": 0, "neutral": 0},
            "fallacy_severity_evaluation": {"positive": 0, "negative": 0, "neutral": 0},
            "argument_structure_visualization": {"positive": 0, "negative": 0, "neutral": 0},
            "argument_coherence_evaluation": {"positive": 0, "negative": 0, "neutral": 0},
            "semantic_argument_analysis": {"positive": 0, "negative": 0, "neutral": 0},
            "contextual_fallacy_detection": {"positive": 0, "negative": 0, "neutral": 0}
        }
        
        # Charger les feedbacks existants
        self._load_feedback_history()
    
    def _load_feedback_history(self) -> None:
        """
        Charge l'historique des feedbacks depuis le stockage.
        """
        feedback_file = self.feedback_storage_path / "feedback_history.json"
        
        if feedback_file.exists():
            try:
                with open(feedback_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.feedback_history = data.get("feedback_history", [])
                    self.feedback_stats = data.get("feedback_stats", self.feedback_stats)
                
                self.logger.info(f"Historique de feedback chargé: {len(self.feedback_history)} entrées")
            except Exception as e:
                self.logger.error(f"Erreur lors du chargement de l'historique de feedback: {e}")
    
    def _save_feedback_history(self) -> None:
        """
        Sauvegarde l'historique des feedbacks dans le stockage.
        """
        feedback_file = self.feedback_storage_path / "feedback_history.json"
        
        try:
            with open(feedback_file, "w", encoding="utf-8") as f:
                json.dump({
                    "feedback_history": self.feedback_history,
                    "feedback_stats": self.feedback_stats
                }, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Historique de feedback sauvegardé: {len(self.feedback_history)} entrées")
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde de l'historique de feedback: {e}")
    
    def add_feedback(self, 
                    tool_type: str, 
                    result_id: str, 
                    feedback_type: str, 
                    feedback_content: Dict[str, Any],
                    source: str = "user") -> bool:
        """
        Ajoute un feedback pour un résultat d'analyse rhétorique.
        
        Args:
            tool_type: Type d'outil d'analyse rhétorique
            result_id: Identifiant du résultat
            feedback_type: Type de feedback ("positive", "negative", "neutral")
            feedback_content: Contenu détaillé du feedback
            source: Source du feedback (par défaut: "user")
            
        Returns:
            True si l'ajout a réussi, False sinon
        """
        if tool_type not in self.feedback_stats:
            self.logger.warning(f"Type d'outil inconnu: {tool_type}")
            return False
        
        if feedback_type not in ["positive", "negative", "neutral"]:
            self.logger.warning(f"Type de feedback invalide: {feedback_type}")
            return False
        
        # Créer l'entrée de feedback
        feedback_entry = {
            "id": f"feedback-{len(self.feedback_history) + 1}",
            "tool_type": tool_type,
            "result_id": result_id,
            "feedback_type": feedback_type,
            "feedback_content": feedback_content,
            "source": source,
            "timestamp": datetime.now().isoformat()
        }
        
        # Ajouter à l'historique
        self.feedback_history.append(feedback_entry)
        
        # Mettre à jour les statistiques
        self.feedback_stats[tool_type][feedback_type] += 1
        
        # Sauvegarder l'historique
        self._save_feedback_history()
        
        self.logger.info(f"Feedback ajouté pour {tool_type} (ID: {result_id}): {feedback_type}")
        
        return True
    
    def get_feedback_for_result(self, result_id: str) -> List[Dict[str, Any]]:
        """
        Récupère tous les feedbacks pour un résultat spécifique.
        
        Args:
            result_id: Identifiant du résultat
            
        Returns:
            Liste des feedbacks pour le résultat
        """
        return [feedback for feedback in self.feedback_history if feedback["result_id"] == result_id]
    
    def get_feedback_for_tool(self, tool_type: str) -> List[Dict[str, Any]]:
        """
        Récupère tous les feedbacks pour un type d'outil spécifique.
        
        Args:
            tool_type: Type d'outil d'analyse rhétorique
            
        Returns:
            Liste des feedbacks pour le type d'outil
        """
        return [feedback for feedback in self.feedback_history if feedback["tool_type"] == tool_type]
    
    def get_feedback_stats(self, tool_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Récupère les statistiques de feedback.
        
        Args:
            tool_type: Type d'outil d'analyse rhétorique (optionnel)
            
        Returns:
            Statistiques de feedback
        """
        if tool_type:
            if tool_type in self.feedback_stats:
                return {tool_type: self.feedback_stats[tool_type]}
            else:
                return {}
        
        return self.feedback_stats
    
    def apply_feedback_to_tool_parameters(self, 
                                         tool_type: str, 
                                         current_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applique les feedbacks accumulés pour ajuster les paramètres d'un outil.
        
        Args:
            tool_type: Type d'outil d'analyse rhétorique
            current_parameters: Paramètres actuels de l'outil
            
        Returns:
            Paramètres ajustés en fonction des feedbacks
        """
        # Récupérer les feedbacks pour ce type d'outil
        tool_feedbacks = self.get_feedback_for_tool(tool_type)
        
        if not tool_feedbacks:
            return current_parameters
        
        # Copier les paramètres actuels
        adjusted_parameters = current_parameters.copy()
        
        # Analyser les feedbacks pour ajuster les paramètres
        # Cette implémentation est simplifiée et devrait être adaptée selon les besoins spécifiques
        
        # Exemple: ajuster les seuils de confiance en fonction des feedbacks
        positive_count = sum(1 for fb in tool_feedbacks if fb["feedback_type"] == "positive")
        negative_count = sum(1 for fb in tool_feedbacks if fb["feedback_type"] == "negative")
        total_count = len(tool_feedbacks)
        
        if total_count > 0:
            feedback_ratio = (positive_count - negative_count) / total_count
            
            # Ajuster les seuils de confiance
            if "confidence_threshold" in adjusted_parameters:
                # Diminuer le seuil si beaucoup de feedbacks positifs, augmenter sinon
                current_threshold = adjusted_parameters["confidence_threshold"]
                adjustment = feedback_ratio * 0.05  # Ajustement maximum de ±5%
                adjusted_parameters["confidence_threshold"] = max(0.5, min(0.95, current_threshold - adjustment))
            
            # Ajuster d'autres paramètres selon les besoins
            
            self.logger.info(f"Paramètres ajustés pour {tool_type} en fonction de {total_count} feedbacks")
        
        return adjusted_parameters
    
    def generate_feedback_report(self) -> Dict[str, Any]:
        """
        Génère un rapport sur les feedbacks collectés.
        
        Returns:
            Rapport de feedback
        """
        # Calculer des statistiques globales
        total_feedbacks = len(self.feedback_history)
        positive_feedbacks = sum(1 for fb in self.feedback_history if fb["feedback_type"] == "positive")
        negative_feedbacks = sum(1 for fb in self.feedback_history if fb["feedback_type"] == "negative")
        neutral_feedbacks = sum(1 for fb in self.feedback_history if fb["feedback_type"] == "neutral")
        
        # Calculer des statistiques par outil
        tool_stats = {}
        for tool_type in self.feedback_stats:
            tool_feedbacks = self.get_feedback_for_tool(tool_type)
            if tool_feedbacks:
                tool_stats[tool_type] = {
                    "total": len(tool_feedbacks),
                    "positive": sum(1 for fb in tool_feedbacks if fb["feedback_type"] == "positive"),
                    "negative": sum(1 for fb in tool_feedbacks if fb["feedback_type"] == "negative"),
                    "neutral": sum(1 for fb in tool_feedbacks if fb["feedback_type"] == "neutral"),
                    "satisfaction_rate": sum(1 for fb in tool_feedbacks if fb["feedback_type"] == "positive") / len(tool_feedbacks)
                }
        
        # Générer le rapport
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_feedbacks": total_feedbacks,
            "feedback_distribution": {
                "positive": positive_feedbacks,
                "negative": negative_feedbacks,
                "neutral": neutral_feedbacks
            },
            "overall_satisfaction_rate": positive_feedbacks / total_feedbacks if total_feedbacks > 0 else 0,
            "tool_statistics": tool_stats,
            "recent_feedbacks": self.feedback_history[-10:] if len(self.feedback_history) > 10 else self.feedback_history
        }
        
        return report


class FeedbackManager:
    """
    Gestionnaire de feedback pour l'architecture hiérarchique.
    
    Cette classe coordonne la collecte et l'application des feedbacks à travers
    les différents niveaux de l'architecture hiérarchique.
    """
    
    def __init__(self, operational_state: Optional[OperationalState] = None):
        """
        Initialise un nouveau gestionnaire de feedback.
        
        Args:
            operational_state: État opérationnel à utiliser. Si None, un nouvel état est créé.
        """
        self.logger = logging.getLogger("FeedbackManager")
        self.operational_state = operational_state if operational_state else OperationalState()
        
        # Créer le gestionnaire de feedback pour les outils d'analyse rhétorique
        self.rhetorical_tools_feedback = RhetoricalToolsFeedback()
    
    def collect_feedback(self, 
                        level: str, 
                        tool_type: str, 
                        result_id: str, 
                        feedback_type: str, 
                        feedback_content: Dict[str, Any],
                        source: str = "user") -> bool:
        """
        Collecte un feedback et le transmet au gestionnaire approprié.
        
        Args:
            level: Niveau hiérarchique ("strategic", "tactical", "operational")
            tool_type: Type d'outil
            result_id: Identifiant du résultat
            feedback_type: Type de feedback ("positive", "negative", "neutral")
            feedback_content: Contenu détaillé du feedback
            source: Source du feedback
            
        Returns:
            True si la collecte a réussi, False sinon
        """
        if level == "operational" and tool_type in self.rhetorical_tools_feedback.feedback_stats:
            return self.rhetorical_tools_feedback.add_feedback(
                tool_type, result_id, feedback_type, feedback_content, source
            )
        
        self.logger.warning(f"Niveau ou type d'outil non supporté: {level}/{tool_type}")
        return False
    
    def apply_feedback(self, level: str, tool_type: str, current_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applique les feedbacks accumulés pour ajuster les paramètres d'un outil.
        
        Args:
            level: Niveau hiérarchique ("strategic", "tactical", "operational")
            tool_type: Type d'outil
            current_parameters: Paramètres actuels de l'outil
            
        Returns:
            Paramètres ajustés en fonction des feedbacks
        """
        if level == "operational" and tool_type in self.rhetorical_tools_feedback.feedback_stats:
            return self.rhetorical_tools_feedback.apply_feedback_to_tool_parameters(
                tool_type, current_parameters
            )
        
        return current_parameters
    
    def generate_feedback_report(self, level: Optional[str] = None) -> Dict[str, Any]:
        """
        Génère un rapport sur les feedbacks collectés.
        
        Args:
            level: Niveau hiérarchique (optionnel)
            
        Returns:
            Rapport de feedback
        """
        if level == "operational" or level is None:
            return self.rhetorical_tools_feedback.generate_feedback_report()
        
        return {"error": f"Niveau non supporté: {level}"}