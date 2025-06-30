#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Service d'orchestration de groupe chat pour l'analyse argumentative.

Ce module fournit GroupChatOrchestration qui coordonne les interactions
entre plusieurs agents dans un contexte de groupe chat.
"""

# ===== AUTO-ACTIVATION ENVIRONNEMENT =====
try:
    import argumentation_analysis.core.environment  # Auto-activation environnement intelligent
except ImportError:
    # Dans le contexte des tests, auto_env peut déjà être activé
    pass
# =========================================
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio

# Import du gestionnaire asynchrone
from ..utils.async_manager import AsyncManager, run_hybrid_safe, ensure_async, ensure_sync


class GroupChatOrchestration:
    """
    Service d'orchestration pour les discussions de groupe entre agents.
    
    Cette classe coordonne les interactions entre plusieurs agents
    d'analyse argumentative dans un contexte collaboratif.
    """
    
    def __init__(self):
        """Initialise le service d'orchestration de groupe chat."""
        self.logger = logging.getLogger(__name__)
        self.active_agents = {}
        self.conversation_history = []
        self.session_id = None
        self.async_manager = AsyncManager(max_workers=8, default_timeout=45.0)
        self._agent_communication_locks = {}
        self._health_status = {'status': 'healthy', 'last_check': datetime.now().isoformat()}
        
    def initialize_session(self, session_id: str, agents: Dict[str, Any]) -> bool:
        """
        Initialise une nouvelle session de groupe chat.
        
        Args:
            session_id: Identifiant unique de la session
            agents: Dictionnaire des agents participants
            
        Returns:
            True si l'initialisation réussit
        """
        try:
            self.session_id = session_id
            self.active_agents = agents.copy()
            self.conversation_history = []
            
            self.logger.info(f"Session de groupe chat initialisée: {session_id}")
            self.logger.info(f"Agents actifs: {list(agents.keys())}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation de la session: {e}")
            return False
    
    def add_message(self, agent_id: str, message: str, analysis_results: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Ajoute un message à la conversation du groupe.
        
        Args:
            agent_id: Identifiant de l'agent émetteur
            message: Contenu du message
            analysis_results: Résultats d'analyse optionnels
            
        Returns:
            Dictionnaire avec les détails du message ajouté
        """
        timestamp = datetime.now().isoformat()
        
        message_entry = {
            "timestamp": timestamp,
            "agent_id": agent_id,
            "message": message,
            "analysis_results": analysis_results or {},
            "message_id": len(self.conversation_history) + 1
        }
        
        self.conversation_history.append(message_entry)
        
        self.logger.info(f"Message ajouté par {agent_id}: {message[:100]}...")
        return message_entry
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Retourne un résumé de la conversation du groupe.
        
        Returns:
            Dictionnaire contenant le résumé de la conversation
        """
        total_messages = len(self.conversation_history)
        agents_participation = {}
        
        for message in self.conversation_history:
            agent_id = message["agent_id"]
            agents_participation[agent_id] = agents_participation.get(agent_id, 0) + 1
        
        return {
            "session_id": self.session_id,
            "total_messages": total_messages,
            "active_agents": list(self.active_agents.keys()),
            "agents_participation": agents_participation,
            "conversation_start": self.conversation_history[0]["timestamp"] if self.conversation_history else None,
            "last_activity": self.conversation_history[-1]["timestamp"] if self.conversation_history else None
        }
    
    def coordinate_analysis(self, text: str, target_agents: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Coordonne une analyse collaborative entre agents.
        
        Args:
            text: Texte à analyser
            target_agents: Liste des agents à impliquer (tous si None)
            
        Returns:
            Résultats consolidés de l'analyse collaborative
        """
        if not target_agents:
            target_agents = list(self.active_agents.keys())
        
        self.logger.info(f"Coordination d'analyse collaborative avec {len(target_agents)} agents")
        
        collaborative_results = {
            "text": text,
            "agents_involved": target_agents,
            "individual_results": {},
            "consolidated_analysis": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Simuler l'analyse par chaque agent
        for agent_id in target_agents:
            if agent_id in self.active_agents:
                # Mock des résultats d'analyse
                mock_result = {
                    "agent_id": agent_id,
                    "analysis_type": self._get_agent_type(agent_id),
                    "confidence": 0.85,
                    "findings": [f"Analyse de {agent_id} pour le texte"],
                    "processing_time": 1.2
                }
                collaborative_results["individual_results"][agent_id] = mock_result
        
        # Consolidation des résultats
        collaborative_results["consolidated_analysis"] = self._consolidate_results(
            collaborative_results["individual_results"]
        )
        
        return collaborative_results
    
    def _get_agent_type(self, agent_id: str) -> str:
        """Détermine le type d'un agent basé sur son ID."""
        if "informal" in agent_id.lower():
            return "informal_analysis"
        elif "logic" in agent_id.lower() or "fol" in agent_id.lower():
            return "formal_logic"
        elif "extract" in agent_id.lower():
            return "extraction"
        else:
            return "general_analysis"
    
    def _consolidate_results(self, individual_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Consolide les résultats individuels en une analyse unifiée.
        
        Args:
            individual_results: Résultats de chaque agent
            
        Returns:
            Analyse consolidée
        """
        consolidated = {
            "summary": "Analyse collaborative terminée",
            "agents_count": len(individual_results),
            "average_confidence": 0.0,
            "key_findings": [],
            "consensus_areas": [],
            "divergent_views": []
        }
        
        if individual_results:
            total_confidence = sum(result.get("confidence", 0) for result in individual_results.values())
            consolidated["average_confidence"] = total_confidence / len(individual_results)
            
            # Agrégation des découvertes
            for agent_id, result in individual_results.items():
                findings = result.get("findings", [])
                consolidated["key_findings"].extend(findings)
        
        return consolidated
    
    def get_agent_status(self) -> Dict[str, Any]:
        """
        Retourne le statut de tous les agents actifs.
        
        Returns:
            Dictionnaire du statut des agents
        """
        status = {}
        for agent_id, agent in self.active_agents.items():
            status[agent_id] = {
                "active": True,
                "type": self._get_agent_type(agent_id),
                "last_activity": None,  # À implémenter selon les besoins
                "capabilities": getattr(agent, 'get_agent_capabilities', lambda: {})()
            }
        
        return status
    
    def cleanup_session(self) -> bool:
        """
        Nettoie la session actuelle et libère les ressources.
        
        Returns:
            True si le nettoyage réussit
        """
        try:
            self.logger.info(f"Nettoyage de la session: {self.session_id}")
            
            self.active_agents.clear()
            self.conversation_history.clear()
            self.session_id = None
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors du nettoyage de la session: {e}")
            return False
    
    def coordinate_analysis_async(self, text: str, target_agents: Optional[List[str]] = None, timeout: float = 60.0) -> Dict[str, Any]:
        """
        Coordonne une analyse collaborative asynchrone entre agents.
        
        Args:
            text: Texte à analyser
            target_agents: Liste des agents à impliquer (tous si None)
            timeout: Timeout global en secondes
            
        Returns:
            Résultats consolidés de l'analyse collaborative asynchrone
        """
        if not target_agents:
            target_agents = list(self.active_agents.keys())
        
        self.logger.info(f"Coordination d'analyse asynchrone avec {len(target_agents)} agents")
        
        # Préparer les tâches d'analyse
        analysis_tasks = []
        for agent_id in target_agents:
            if agent_id in self.active_agents:
                task_def = {
                    'func': self._analyze_with_agent,
                    'args': (agent_id, text),
                    'kwargs': {},
                    'timeout': timeout / len(target_agents),
                    'fallback_result': {
                        "agent_id": agent_id,
                        "analysis_type": self._get_agent_type(agent_id),
                        "confidence": 0.0,
                        "findings": [],
                        "processing_time": 0.0,
                        "error": "Timeout ou erreur d'exécution"
                    }
                }
                analysis_tasks.append(task_def)
        
        # Exécuter les analyses en parallèle
        start_time = datetime.now()
        individual_results_list = self.async_manager.run_multiple_hybrid(
            analysis_tasks,
            max_concurrent=min(len(target_agents), 4),
            global_timeout=timeout
        )
        
        # Convertir la liste en dictionnaire
        individual_results = {}
        for i, result in enumerate(individual_results_list):
            if i < len(target_agents):
                agent_id = target_agents[i]
                individual_results[agent_id] = result
        
        # Résultats consolidés
        collaborative_results = {
            "text": text,
            "agents_involved": target_agents,
            "individual_results": individual_results,
            "consolidated_analysis": {},
            "timestamp": start_time.isoformat(),
            "execution_mode": "async",
            "total_processing_time": (datetime.now() - start_time).total_seconds()
        }
        
        # Consolidation des résultats avec gestion d'erreurs
        try:
            collaborative_results["consolidated_analysis"] = self._consolidate_results_robust(individual_results)
        except Exception as e:
            self.logger.error(f"Erreur lors de la consolidation: {e}")
            collaborative_results["consolidated_analysis"] = {
                "summary": "Erreur lors de la consolidation",
                "error": str(e)
            }
        
        return collaborative_results
    
    def _analyze_with_agent(self, agent_id: str, text: str) -> Dict[str, Any]:
        """
        Effectue l'analyse avec un agent spécifique (méthode robuste).
        
        Args:
            agent_id: Identifiant de l'agent
            text: Texte à analyser
            
        Returns:
            Résultats de l'analyse
        """
        start_time = datetime.now()
        
        try:
            agent = self.active_agents.get(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} non trouvé")
            
            # Lock pour éviter les conflits si l'agent n'est pas thread-safe
            if agent_id not in self._agent_communication_locks:
                self._agent_communication_locks[agent_id] = asyncio.Lock() if asyncio.iscoroutinefunction(getattr(agent, 'analyze_text', None)) else None
            
            # Simuler l'analyse (mockée pour les tests)
            analysis_result = {
                "agent_id": agent_id,
                "analysis_type": self._get_agent_type(agent_id),
                "confidence": 0.85 + (hash(text) % 15) / 100,  # Confidence réaliste
                "findings": [
                    f"Analyse de {agent_id} pour le texte: {text[:50]}...",
                    f"Détection de patterns par {agent_id}",
                    f"Évaluation contextuelle par {agent_id}"
                ],
                "processing_time": (datetime.now() - start_time).total_seconds(),
                "text_length": len(text),
                "agent_capabilities": getattr(agent, 'get_agent_capabilities', lambda: {})()
            }
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse avec {agent_id}: {e}")
            return {
                "agent_id": agent_id,
                "analysis_type": self._get_agent_type(agent_id),
                "confidence": 0.0,
                "findings": [],
                "processing_time": (datetime.now() - start_time).total_seconds(),
                "error": str(e)
            }
    
    def _consolidate_results_robust(self, individual_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Version robuste de la consolidation des résultats.
        
        Args:
            individual_results: Résultats de chaque agent
            
        Returns:
            Analyse consolidée avec gestion d'erreurs
        """
        valid_results = {
            agent_id: result for agent_id, result in individual_results.items()
            if not result.get("error") and result.get("confidence", 0) > 0
        }
        
        error_results = {
            agent_id: result for agent_id, result in individual_results.items()
            if result.get("error") or result.get("confidence", 0) == 0
        }
        
        consolidated = {
            "summary": f"Analyse collaborative terminée avec {len(valid_results)} agents réussis",
            "agents_count": len(individual_results),
            "successful_agents": len(valid_results),
            "failed_agents": len(error_results),
            "average_confidence": 0.0,
            "weighted_confidence": 0.0,
            "key_findings": [],
            "consensus_areas": [],
            "divergent_views": [],
            "error_summary": []
        }
        
        if valid_results:
            # Calculs de confiance
            confidences = [result.get("confidence", 0) for result in valid_results.values()]
            consolidated["average_confidence"] = sum(confidences) / len(confidences)
            
            # Confiance pondérée par le type d'agent
            weights = {"formal_logic": 1.2, "informal_analysis": 1.0, "extraction": 0.8, "general_analysis": 0.9}
            weighted_sum = 0
            total_weight = 0
            
            for result in valid_results.values():
                agent_type = result.get("analysis_type", "general_analysis")
                weight = weights.get(agent_type, 1.0)
                weighted_sum += result.get("confidence", 0) * weight
                total_weight += weight
            
            if total_weight > 0:
                consolidated["weighted_confidence"] = weighted_sum / total_weight
            
            # Agrégation des découvertes
            all_findings = []
            for agent_id, result in valid_results.items():
                findings = result.get("findings", [])
                for finding in findings:
                    all_findings.append({
                        "source_agent": agent_id,
                        "finding": finding,
                        "confidence": result.get("confidence", 0)
                    })
            
            # Trier par confiance
            all_findings.sort(key=lambda x: x["confidence"], reverse=True)
            consolidated["key_findings"] = all_findings[:10]  # Top 10
            
            # Identifier les consensus (findings similaires de plusieurs agents)
            finding_groups = {}
            for finding_obj in all_findings:
                finding_text = finding_obj["finding"]
                key_words = set(finding_text.lower().split()[:3])  # Premiers mots comme clé
                
                matched = False
                for existing_key, group in finding_groups.items():
                    if len(key_words.intersection(set(existing_key.split()))) >= 2:
                        group.append(finding_obj)
                        matched = True
                        break
                
                if not matched:
                    finding_groups[" ".join(list(key_words)[:3])] = [finding_obj]
            
            # Consensus = groupes avec plus d'un agent
            for key, group in finding_groups.items():
                if len(group) > 1:
                    agents_in_consensus = [f["source_agent"] for f in group]
                    avg_confidence = sum(f["confidence"] for f in group) / len(group)
                    consolidated["consensus_areas"].append({
                        "theme": key,
                        "agents": agents_in_consensus,
                        "confidence": avg_confidence,
                        "findings_count": len(group)
                    })
        
        # Résumé des erreurs
        if error_results:
            for agent_id, result in error_results.items():
                consolidated["error_summary"].append({
                    "agent_id": agent_id,
                    "error": result.get("error", "Échec d'analyse"),
                    "processing_time": result.get("processing_time", 0)
                })
        
        return consolidated
    
    def get_service_health(self) -> Dict[str, Any]:
        """
        Retourne l'état de santé du service d'orchestration.
        
        Returns:
            Dictionnaire de l'état de santé
        """
        try:
            # Vérifier l'état des agents
            agents_health = {}
            for agent_id, agent in self.active_agents.items():
                try:
                    if hasattr(agent, 'get_agent_capabilities'):
                        capabilities = agent.get_agent_capabilities()
                        agents_health[agent_id] = {
                            'status': 'healthy',
                            'capabilities': capabilities,
                            'type': self._get_agent_type(agent_id)
                        }
                    else:
                        agents_health[agent_id] = {
                            'status': 'limited',
                            'reason': 'Capabilities not available'
                        }
                except Exception as e:
                    agents_health[agent_id] = {
                        'status': 'unhealthy',
                        'error': str(e)
                    }
            
            # Statistiques des performances
            perf_stats = self.async_manager.get_performance_stats()
            
            # Mise à jour du statut global
            healthy_agents = len([a for a in agents_health.values() if a.get('status') == 'healthy'])
            total_agents = len(agents_health)
            
            if healthy_agents == total_agents and total_agents > 0:
                overall_status = 'healthy'
            elif healthy_agents > 0:
                overall_status = 'degraded'
            else:
                overall_status = 'unhealthy'
            
            self._health_status = {
                'status': overall_status,
                'last_check': datetime.now().isoformat(),
                'agents_health': agents_health,
                'performance_stats': perf_stats,
                'session_info': {
                    'active_session': self.session_id,
                    'conversation_messages': len(self.conversation_history),
                    'active_agents_count': len(self.active_agents)
                }
            }
            
            return self._health_status
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de santé: {e}")
            return {
                'status': 'error',
                'last_check': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def cleanup_session(self) -> bool:
        """
        Version améliorée du nettoyage de session.
        
        Returns:
            True si le nettoyage réussit
        """
        try:
            self.logger.info(f"Nettoyage de la session: {self.session_id}")
            
            # Arrêter les tâches asynchrones en cours
            try:
                self.async_manager.cleanup_completed_tasks(max_age_hours=0)
            except Exception as e:
                self.logger.warning(f"Erreur lors du nettoyage des tâches async: {e}")
            
            # Nettoyer les locks de communication
            self._agent_communication_locks.clear()
            
            # Nettoyage standard
            self.active_agents.clear()
            self.conversation_history.clear()
            self.session_id = None
            
            # Mise à jour du statut de santé
            self._health_status = {
                'status': 'healthy',
                'last_check': datetime.now().isoformat()
            }
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors du nettoyage de la session: {e}")
            return False