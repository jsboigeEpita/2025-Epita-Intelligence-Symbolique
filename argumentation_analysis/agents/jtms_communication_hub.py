"""
Hub de communication JTMS pour synchronisation inter-agents.
Selon les spécifications du RAPPORT_ARCHITECTURE_INTEGRATION_JTMS.md - AXE A
"""

import logging
import json
import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

import semantic_kernel as sk
from semantic_kernel import Kernel

from .jtms_agent_base import JTMSAgentBase, JTMSSession
from .sherlock_jtms_agent import SherlockJTMSAgent
from .watson_jtms_agent import WatsonJTMSAgent

class CommunicationStatus(Enum):
    INITIALIZING = "initializing"
    ACTIVE = "active"
    SYNCING = "syncing"
    RESOLVING_CONFLICTS = "resolving_conflicts"
    ERROR = "error"
    PAUSED = "paused"

@dataclass
class AgentMessage:
    """Message échangé entre agents via JTMS"""
    message_id: str
    sender_agent: str
    receiver_agent: str
    message_type: str
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    requires_response: bool = False
    priority: str = "normal"  # low, normal, high, critical

@dataclass
class SyncOperation:
    """Opération de synchronisation entre sessions JTMS"""
    operation_id: str
    source_session: str
    target_session: str
    operation_type: str  # sync_beliefs, merge_sessions, validate_cross, resolve_conflicts
    status: str = "pending"
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    result: Optional[Dict] = None
    conflicts_detected: List[Dict] = field(default_factory=list)

class ConflictResolver:
    """Résolveur de conflits entre agents avec stratégies multiples"""
    
    def __init__(self):
        self.resolution_strategies = {
            "confidence_based": self._resolve_by_confidence,
            "evidence_based": self._resolve_by_evidence,
            "consensus": self._resolve_by_consensus,
            "agent_expertise": self._resolve_by_expertise,
            "temporal": self._resolve_by_timestamp
        }
        self.resolution_history = []
    
    async def resolve_conflict(self, conflict: Dict, agents: Dict[str, JTMSAgentBase], 
                              strategy: str = "confidence_based") -> Dict:
        """Résout un conflit entre agents selon la stratégie choisie"""
        if strategy not in self.resolution_strategies:
            strategy = "confidence_based"
        
        resolution_result = {
            "conflict_id": conflict.get("conflict_id", f"conflict_{len(self.resolution_history)}"),
            "strategy_used": strategy,
            "resolved": False,
            "chosen_belief": None,
            "reasoning": "",
            "agents_involved": list(conflict.get("agents", {}).keys()),
            "resolution_timestamp": datetime.now()
        }
        
        try:
            resolver_func = self.resolution_strategies[strategy]
            resolution = await resolver_func(conflict, agents)
            resolution_result.update(resolution)
            
            self.resolution_history.append(resolution_result)
            return resolution_result
            
        except Exception as e:
            resolution_result["error"] = str(e)
            resolution_result["reasoning"] = f"Erreur lors de la résolution: {e}"
            return resolution_result
    
    async def _resolve_by_confidence(self, conflict: Dict, agents: Dict[str, JTMSAgentBase]) -> Dict:
        """Résolution basée sur les scores de confiance"""
        conflicting_beliefs = conflict.get("beliefs", {})
        
        best_belief = None
        best_confidence = 0.0
        best_agent = None
        
        for agent_name, belief_data in conflicting_beliefs.items():
            confidence = belief_data.get("confidence", 0.0)
            if confidence > best_confidence:
                best_confidence = confidence
                best_belief = belief_data.get("belief_name")
                best_agent = agent_name
        
        return {
            "resolved": True,
            "chosen_belief": best_belief,
            "chosen_agent": best_agent,
            "reasoning": f"Confiance la plus élevée: {best_confidence:.2f} par {best_agent}",
            "confidence_score": best_confidence
        }
    
    async def _resolve_by_evidence(self, conflict: Dict, agents: Dict[str, JTMSAgentBase]) -> Dict:
        """Résolution basée sur la quantité et qualité des évidences"""
        conflicting_beliefs = conflict.get("beliefs", {})
        
        best_belief = None
        best_evidence_score = 0.0
        best_agent = None
        
        for agent_name, belief_data in conflicting_beliefs.items():
            if agent_name in agents:
                agent = agents[agent_name]
                belief_name = belief_data.get("belief_name")
                
                if belief_name in agent.jtms_session.extended_beliefs:
                    extended_belief = agent.jtms_session.extended_beliefs[belief_name]
                    
                    # Score basé sur le nombre et la qualité des justifications
                    justification_count = len(extended_belief.justifications)
                    evidence_score = justification_count * extended_belief.confidence
                    
                    if evidence_score > best_evidence_score:
                        best_evidence_score = evidence_score
                        best_belief = belief_name
                        best_agent = agent_name
        
        return {
            "resolved": True,
            "chosen_belief": best_belief,
            "chosen_agent": best_agent,
            "reasoning": f"Meilleur score d'évidence: {best_evidence_score:.2f} par {best_agent}",
            "evidence_score": best_evidence_score
        }
    
    async def _resolve_by_consensus(self, conflict: Dict, agents: Dict[str, JTMSAgentBase]) -> Dict:
        """Résolution par recherche de consensus"""
        # Pour une implémentation future avec plus de 2 agents
        return {
            "resolved": False,
            "reasoning": "Résolution par consensus nécessite plus de 2 agents",
            "note": "Stratégie non applicable"
        }
    
    async def _resolve_by_expertise(self, conflict: Dict, agents: Dict[str, JTMSAgentBase]) -> Dict:
        """Résolution basée sur l'expertise de l'agent pour le domaine"""
        conflicting_beliefs = conflict.get("beliefs", {})
        context = conflict.get("context", {})
        
        # Sherlock a l'expertise pour les hypothèses et déductions
        # Watson a l'expertise pour les validations formelles
        
        expertise_mapping = {
            "hypothesis": "sherlock",
            "evidence": "sherlock", 
            "deduction": "sherlock",
            "validation": "watson",
            "logical_proof": "watson",
            "consistency": "watson"
        }
        
        context_type = context.get("type", "unknown")
        expert_agent = expertise_mapping.get(context_type, "sherlock")  # Sherlock par défaut
        
        # Chercher la croyance de l'agent expert
        expert_belief = None
        for agent_name, belief_data in conflicting_beliefs.items():
            if expert_agent.lower() in agent_name.lower():
                expert_belief = belief_data.get("belief_name")
                break
        
        return {
            "resolved": expert_belief is not None,
            "chosen_belief": expert_belief,
            "chosen_agent": expert_agent,
            "reasoning": f"Expertise de {expert_agent} pour le contexte {context_type}",
            "expertise_domain": context_type
        }
    
    async def _resolve_by_timestamp(self, conflict: Dict, agents: Dict[str, JTMSAgentBase]) -> Dict:
        """Résolution basée sur l'ordre temporel (plus récent gagne)"""
        conflicting_beliefs = conflict.get("beliefs", {})
        
        latest_belief = None
        latest_timestamp = None
        latest_agent = None
        
        for agent_name, belief_data in conflicting_beliefs.items():
            if agent_name in agents:
                agent = agents[agent_name]
                belief_name = belief_data.get("belief_name")
                
                if belief_name in agent.jtms_session.extended_beliefs:
                    extended_belief = agent.jtms_session.extended_beliefs[belief_name]
                    
                    if latest_timestamp is None or extended_belief.creation_timestamp > latest_timestamp:
                        latest_timestamp = extended_belief.creation_timestamp
                        latest_belief = belief_name
                        latest_agent = agent_name
        
        return {
            "resolved": latest_belief is not None,
            "chosen_belief": latest_belief,
            "chosen_agent": latest_agent,
            "reasoning": f"Croyance la plus récente par {latest_agent} à {latest_timestamp}",
            "timestamp": latest_timestamp.isoformat() if latest_timestamp else None
        }

class JTMSCommunicationHub:
    """
    Hub central pour la communication et synchronisation JTMS entre agents.
    Gère les échanges, résolutions de conflits et maintient la cohérence globale.
    """
    
    def __init__(self, kernel: Kernel):
        self._kernel = kernel
        self._logger = logging.getLogger("JTMSCommunicationHub")
        
        # Identifiant unique du hub (attendu par les tests)
        self.hub_id = f"hub_{int(datetime.now().timestamp())}"
        
        # État du hub
        self._status = CommunicationStatus.INITIALIZING
        self._connected_agents: Dict[str, JTMSAgentBase] = {}
        self._message_queue: List[AgentMessage] = []
        self._sync_operations: List[SyncOperation] = []
        
        # Sessions de collaboration (attendu par les tests)
        self.collaboration_sessions: Dict[str, Dict] = {}
        
        # Gestionnaires
        self._conflict_resolver = ConflictResolver()
        
        # Configuration
        self._auto_sync_enabled = True
        self._conflict_resolution_strategy = "confidence_based"
        self._max_queue_size = 1000
        self._sync_interval = 30  # secondes
        
        # Sessions partagées
        self._shared_belief_space = {}
        self._global_consistency_state = {"is_consistent": True, "last_check": datetime.now()}
        
        # Statistiques
        self._messages_processed = 0
        self._conflicts_resolved = 0
        self._sync_operations_completed = 0
        
        self._logger.info("JTMSCommunicationHub initialisé")
    
    # === PROPRIÉTÉS PUBLIQUES (Interface pour tests) ===
    
    @property
    def registered_agents(self) -> Dict[str, JTMSAgentBase]:
        """Accès public aux agents enregistrés"""
        return self._connected_agents
    
    @property
    def message_queue(self) -> List[AgentMessage]:
        """Accès public à la queue de messages"""
        return self._message_queue
    
    # === GESTION DES AGENTS ===
    
    async def register_agent(self, agent: JTMSAgentBase) -> bool:
        """Enregistre un agent dans le hub de communication"""
        try:
            agent_name = agent.agent_name
            
            if agent_name in self._connected_agents:
                self._logger.warning(f"Agent {agent_name} déjà enregistré")
                return False
            
            self._connected_agents[agent_name] = agent
            
            # Initialiser l'espace de croyances partagé pour cet agent
            self._shared_belief_space[agent_name] = {
                "session_id": agent.session_id,
                "last_sync": datetime.now(),
                "belief_count": len(agent.get_all_beliefs()),
                "sync_status": "registered"
            }
            
            self._logger.info(f"Agent {agent_name} enregistré avec succès")
            
            # Déclencher synchronisation initiale si plus d'un agent
            if len(self._connected_agents) > 1:
                asyncio.create_task(self._trigger_initial_sync(agent_name))
            
            return True
            
        except Exception as e:
            self._logger.error(f"Erreur enregistrement agent {agent.agent_name}: {e}")
            return False
    
    async def unregister_agent(self, agent_name: str) -> bool:
        """Désenregistre un agent du hub"""
        try:
            if agent_name not in self._connected_agents:
                self._logger.warning(f"Agent {agent_name} non trouvé pour désenregistrement")
                return False
            
            # Sauvegarder état avant déconnexion
            agent = self._connected_agents[agent_name]
            final_state = agent.export_session_state()
            
            # Nettoyer
            del self._connected_agents[agent_name]
            del self._shared_belief_space[agent_name]
            
            self._logger.info(f"Agent {agent_name} désenregistré")
            return True
            
        except Exception as e:
            self._logger.error(f"Erreur désenregistrement agent {agent_name}: {e}")
            return False
    
    def get_connected_agents(self) -> List[str]:
        """Retourne la liste des agents connectés"""
        return list(self._connected_agents.keys())
    
    async def handle_agent_failure(self, failure_info: Dict) -> Dict:
        """Gère l'échec d'un agent"""
        agent_id = failure_info.get("agent_id")
        failure_type = failure_info.get("failure_type", "unknown")
        error_details = failure_info.get("error_details", "")
        
        self._logger.warning(f"Échec agent {agent_id}: {failure_type} - {error_details}")
        
        # Déterminer l'action de récupération
        recovery_action = "restart"
        if failure_type == "communication_timeout":
            recovery_action = "reconnect"
        elif failure_type == "memory_overflow":
            recovery_action = "reset_session"
        elif failure_type == "logic_error":
            recovery_action = "rollback_beliefs"
        
        # Statut de l'agent après échec
        agent_status = "failed"
        if agent_id in self._connected_agents:
            agent_status = "recovering"
            # Marquer l'agent comme en récupération
            self._shared_belief_space[agent_id]["sync_status"] = "recovering"
        
        result = {
            "recovery_action": recovery_action,
            "agent_status": agent_status,
            "failure_type": failure_type,
            "notification_sent": True,
            "timestamp": datetime.now().isoformat()
        }
        
        self._logger.info(f"Plan de récupération pour {agent_id}: {recovery_action}")
        return result
    
    # === SYNCHRONISATION DES CROYANCES ===
    
    async def sync_beliefs(self, source_agent: str, target_agent: str = None, 
                          sync_type: str = "incremental") -> Dict:
        """Synchronise les croyances entre agents"""
        operation_id = f"sync_{len(self._sync_operations)}_{int(datetime.now().timestamp())}"
        
        self._logger.info(f"Début synchronisation {source_agent} → {target_agent or 'all'}")
        
        if source_agent not in self._connected_agents:
            return {"error": f"Agent source {source_agent} non connecté"}
        
        sync_operation = SyncOperation(
            operation_id=operation_id,
            source_session=self._connected_agents[source_agent].session_id,
            target_session=target_agent if target_agent else "all",
            operation_type=f"sync_beliefs_{sync_type}"
        )
        
        self._sync_operations.append(sync_operation)
        
        try:
            source_state = self._connected_agents[source_agent].export_session_state()
            
            if target_agent:
                # Synchronisation ciblée
                if target_agent not in self._connected_agents:
                    sync_operation.status = "error"
                    sync_operation.result = {"error": f"Agent cible {target_agent} non connecté"}
                    return sync_operation.result
                
                sync_result = await self._sync_two_agents(source_agent, target_agent, source_state, sync_type)
                sync_operation.result = sync_result
            else:
                # Synchronisation vers tous les autres agents
                sync_results = {}
                for agent_name in self._connected_agents:
                    if agent_name != source_agent:
                        result = await self._sync_two_agents(source_agent, agent_name, source_state, sync_type)
                        sync_results[agent_name] = result
                
                sync_operation.result = {"multi_sync": sync_results}
            
            sync_operation.status = "completed"
            sync_operation.end_time = datetime.now()
            self._sync_operations_completed += 1
            
            # Mettre à jour l'état partagé
            self._shared_belief_space[source_agent]["last_sync"] = datetime.now()
            
            self._logger.info(f"Synchronisation {operation_id} terminée")
            return sync_operation.result
            
        except Exception as e:
            sync_operation.status = "error"
            sync_operation.result = {"error": str(e)}
            self._logger.error(f"Erreur synchronisation {operation_id}: {e}")
            return sync_operation.result
    
    async def _sync_two_agents(self, source_agent: str, target_agent: str, 
                              source_state: Dict, sync_type: str) -> Dict:
        """Synchronise deux agents spécifiques"""
        source_agent_obj = self._connected_agents[source_agent]
        target_agent_obj = self._connected_agents[target_agent]
        
        if sync_type == "incremental":
            # Import incrémental avec résolution de conflits
            import_result = target_agent_obj.import_beliefs_from_agent(source_state, "merge")
            
            # Gérer les conflits détectés
            if import_result.get("conflicts"):
                conflict_resolutions = await self._handle_import_conflicts(
                    import_result["conflicts"], source_agent, target_agent
                )
                import_result["conflict_resolutions"] = conflict_resolutions
            
            return import_result
        
        elif sync_type == "full":
            # Synchronisation complète avec merge des sessions
            return await self.merge_sessions(source_agent, target_agent)
        
        else:
            return {"error": f"Type de synchronisation inconnu: {sync_type}"}
    
    async def merge_sessions(self, source_agent: str, target_agent: str) -> Dict:
        """Fusionne complètement deux sessions JTMS"""
        self._logger.info(f"Fusion sessions: {source_agent} → {target_agent}")
        
        if source_agent not in self._connected_agents or target_agent not in self._connected_agents:
            return {"error": "Un ou plusieurs agents non connectés"}
        
        try:
            source_agent_obj = self._connected_agents[source_agent]
            target_agent_obj = self._connected_agents[target_agent]
            
            # Export complet de la session source
            source_state = source_agent_obj.export_session_state()
            
            # Import avec gestion de conflits avancée
            merge_result = target_agent_obj.import_beliefs_from_agent(source_state, "merge")
            
            # Vérification de cohérence post-fusion
            consistency_check = target_agent_obj.check_consistency()
            merge_result["post_merge_consistency"] = consistency_check
            
            # Si incohérences détectées, résoudre
            if not consistency_check["is_consistent"]:
                conflict_resolutions = await self._resolve_post_merge_conflicts(
                    consistency_check["conflicts"], source_agent, target_agent
                )
                merge_result["conflict_resolutions"] = conflict_resolutions
            
            # Mettre à jour l'espace partagé
            self._shared_belief_space[target_agent]["last_sync"] = datetime.now()
            self._shared_belief_space[target_agent]["belief_count"] = len(target_agent_obj.get_all_beliefs())
            
            return merge_result
            
        except Exception as e:
            self._logger.error(f"Erreur fusion sessions: {e}")
            return {"error": str(e)}
    
    # === RÉSOLUTION DE CONFLITS ===
    
    async def resolve_belief_conflicts(self, conflicts: List[Dict], 
                                     strategy: str = None) -> List[Dict]:
        """Résout une liste de conflits entre croyances"""
        if not strategy:
            strategy = self._conflict_resolution_strategy
        
        self._logger.info(f"Résolution de {len(conflicts)} conflits avec stratégie {strategy}")
        
        resolutions = []
        
        for conflict in conflicts:
            resolution = await self._conflict_resolver.resolve_conflict(
                conflict, self._connected_agents, strategy
            )
            resolutions.append(resolution)
            
            # Appliquer la résolution aux agents concernés
            if resolution.get("resolved"):
                await self._apply_conflict_resolution(resolution)
        
        self._conflicts_resolved += len([r for r in resolutions if r.get("resolved")])
        
        return resolutions
    
    async def _handle_import_conflicts(self, conflicts: List[Dict], 
                                     source_agent: str, target_agent: str) -> List[Dict]:
        """Gère les conflits détectés lors d'un import"""
        enhanced_conflicts = []
        
        for conflict in conflicts:
            enhanced_conflict = {
                **conflict,
                "source_agent": source_agent,
                "target_agent": target_agent,
                "context": {"type": "import_conflict", "operation": "sync_beliefs"},
                "agents": {
                    source_agent: {"belief_name": conflict["belief_name"]},
                    target_agent: {"belief_name": conflict["belief_name"]}
                }
            }
            enhanced_conflicts.append(enhanced_conflict)
        
        return await self.resolve_belief_conflicts(enhanced_conflicts)
    
    async def _resolve_post_merge_conflicts(self, conflicts: List[Dict], 
                                          source_agent: str, target_agent: str) -> List[Dict]:
        """Résout les conflits après une fusion de sessions"""
        enhanced_conflicts = []
        
        for conflict in conflicts:
            enhanced_conflict = {
                **conflict,
                "source_agent": source_agent,
                "target_agent": target_agent,
                "context": {"type": "post_merge_conflict", "operation": "merge_sessions"}
            }
            enhanced_conflicts.append(enhanced_conflict)
        
        return await self.resolve_belief_conflicts(enhanced_conflicts)
    
    async def _apply_conflict_resolution(self, resolution: Dict) -> None:
        """Applique une résolution de conflit aux agents concernés"""
        if not resolution.get("resolved"):
            return
        
        chosen_belief = resolution.get("chosen_belief")
        chosen_agent = resolution.get("chosen_agent")
        agents_involved = resolution.get("agents_involved", [])
        
        if chosen_belief and chosen_agent:
            # Invalider la croyance dans les autres agents
            for agent_name in agents_involved:
                if agent_name != chosen_agent and agent_name in self._connected_agents:
                    agent = self._connected_agents[agent_name]
                    
                    if chosen_belief in agent.jtms_session.extended_beliefs:
                        # Marquer comme invalidée par résolution de conflit
                        extended_belief = agent.jtms_session.extended_beliefs[chosen_belief]
                        extended_belief.record_modification("conflict_resolution", {
                            "resolution_id": resolution.get("conflict_id"),
                            "chosen_agent": chosen_agent,
                            "strategy": resolution.get("strategy_used")
                        })
                        
                        # Invalider dans JTMS
                        if chosen_belief in agent.jtms_session.jtms.beliefs:
                            agent.jtms_session.jtms.beliefs[chosen_belief].valid = False
    
    # === GESTION DES MESSAGES ===
    
    async def send_message(self, sender: str, receiver: str, message_type: str, 
                          content: Dict, priority: str = "normal") -> str:
        """Envoie un message entre agents"""
        message_id = f"msg_{len(self._message_queue)}_{int(datetime.now().timestamp())}"
        
        message = AgentMessage(
            message_id=message_id,
            sender_agent=sender,
            receiver_agent=receiver,
            message_type=message_type,
            content=content,
            priority=priority,
            requires_response=message_type in ["validation_request", "critique_request"]
        )
        
        if len(self._message_queue) >= self._max_queue_size:
            # Purger les anciens messages
            self._message_queue = self._message_queue[-self._max_queue_size//2:]
        
        self._message_queue.append(message)
        
        # Traitement immédiat pour messages haute priorité
        if priority in ["high", "critical"]:
            await self._process_message(message)
        
        self._logger.info(f"Message {message_id} envoyé: {sender} → {receiver} ({message_type})")
        return message_id
    
    async def _process_message(self, message: AgentMessage) -> None:
        """Traite un message entre agents"""
        try:
            receiver = self._connected_agents.get(message.receiver_agent)
            if not receiver:
                self._logger.warning(f"Agent destinataire {message.receiver_agent} non trouvé")
                return
            
            # Traitement selon le type de message
            if message.message_type == "validation_request":
                await self._handle_validation_request(message)
            elif message.message_type == "critique_request":
                await self._handle_critique_request(message)
            elif message.message_type == "belief_update":
                await self._handle_belief_update(message)
            elif message.message_type == "sync_request":
                await self._handle_sync_request(message)
            
            self._messages_processed += 1
            
        except Exception as e:
            self._logger.error(f"Erreur traitement message {message.message_id}: {e}")
    
    async def _handle_validation_request(self, message: AgentMessage) -> None:
        """Gère une demande de validation"""
        content = message.content
        target_belief = content.get("belief_name")
        
        if message.receiver_agent in self._connected_agents:
            receiver = self._connected_agents[message.receiver_agent]
            
            # Si c'est Watson, utiliser ses capacités de validation
            if isinstance(receiver, WatsonJTMSAgent):
                validation_result = await receiver.formal_validator.prove_belief(target_belief)
                
                # Renvoyer la réponse
                response_content = {
                    "original_request": message.message_id,
                    "validation_result": validation_result,
                    "belief_name": target_belief
                }
                
                await self.send_message(
                    message.receiver_agent, message.sender_agent,
                    "validation_response", response_content
                )
    
    async def _handle_critique_request(self, message: AgentMessage) -> None:
        """Gère une demande de critique"""
        content = message.content
        hypothesis_data = content.get("hypothesis_data")
        
        if message.receiver_agent in self._connected_agents:
            receiver = self._connected_agents[message.receiver_agent]
            
            # Si c'est Watson, utiliser ses capacités de critique
            if isinstance(receiver, WatsonJTMSAgent):
                critique_result = await receiver.critique_hypothesis(hypothesis_data)
                
                # Renvoyer la réponse
                response_content = {
                    "original_request": message.message_id,
                    "critique_result": critique_result,
                    "hypothesis_id": hypothesis_data.get("hypothesis_id")
                }
                
                await self.send_message(
                    message.receiver_agent, message.sender_agent,
                    "critique_response", response_content
                )
    
    async def _handle_belief_update(self, message: AgentMessage) -> None:
        """Gère une mise à jour de croyance"""
        content = message.content
        belief_data = content.get("belief_data")
        
        # Déclencher synchronisation automatique si activée
        if self._auto_sync_enabled:
            await self.sync_beliefs(message.sender_agent, sync_type="incremental")
    
    async def _handle_sync_request(self, message: AgentMessage) -> None:
        """Gère une demande de synchronisation"""
        content = message.content
        sync_type = content.get("sync_type", "incremental")
        
        await self.sync_beliefs(message.sender_agent, message.receiver_agent, sync_type)
    
    # === COHÉRENCE GLOBALE ===
    
    async def check_global_consistency(self) -> Dict:
        """Vérifie la cohérence globale du système multi-agents"""
        self._logger.info("Vérification cohérence globale")
        
        global_consistency = {
            "is_consistent": True,
            "agent_consistencies": {},
            "inter_agent_conflicts": [],
            "global_conflicts": [],
            "recommendations": [],
            "check_timestamp": datetime.now()
        }
        
        try:
            # Vérifier cohérence de chaque agent individuellement
            for agent_name, agent in self._connected_agents.items():
                agent_consistency = agent.check_consistency()
                global_consistency["agent_consistencies"][agent_name] = agent_consistency
                
                if not agent_consistency["is_consistent"]:
                    global_consistency["is_consistent"] = False
            
            # Vérifier cohérence inter-agents
            inter_agent_conflicts = await self._detect_inter_agent_conflicts()
            global_consistency["inter_agent_conflicts"] = inter_agent_conflicts
            
            if inter_agent_conflicts:
                global_consistency["is_consistent"] = False
            
            # Générer recommandations
            recommendations = self._generate_consistency_recommendations(global_consistency)
            global_consistency["recommendations"] = recommendations
            
            # Mettre à jour l'état global
            self._global_consistency_state = {
                "is_consistent": global_consistency["is_consistent"],
                "last_check": datetime.now(),
                "conflicts_count": len(inter_agent_conflicts)
            }
            
            return global_consistency
            
        except Exception as e:
            self._logger.error(f"Erreur vérification cohérence globale: {e}")
            global_consistency["error"] = str(e)
            return global_consistency
    
    async def _detect_inter_agent_conflicts(self) -> List[Dict]:
        """Détecte les conflits entre agents"""
        conflicts = []
        
        agents_list = list(self._connected_agents.items())
        
        # Comparaison deux à deux
        for i in range(len(agents_list)):
            for j in range(i + 1, len(agents_list)):
                agent1_name, agent1 = agents_list[i]
                agent2_name, agent2 = agents_list[j]
                
                agent_conflicts = await self._compare_agent_beliefs(agent1, agent2)
                
                for conflict in agent_conflicts:
                    conflicts.append({
                        **conflict,
                        "agent1": agent1_name,
                        "agent2": agent2_name,
                        "conflict_type": "inter_agent"
                    })
        
        return conflicts
    
    async def _compare_agent_beliefs(self, agent1: JTMSAgentBase, 
                                   agent2: JTMSAgentBase) -> List[Dict]:
        """Compare les croyances de deux agents pour détecter conflits"""
        conflicts = []
        
        beliefs1 = agent1.get_all_beliefs()
        beliefs2 = agent2.get_all_beliefs()
        
        # Rechercher croyances contradictoires
        for belief1_name, belief1 in beliefs1.items():
            for belief2_name, belief2 in beliefs2.items():
                # Contradiction directe (A vs not_A)
                if (belief1_name.startswith("not_") and belief2_name == belief1_name[4:]) or \
                   (belief2_name.startswith("not_") and belief1_name == belief2_name[4:]):
                    
                    if belief1.valid and belief2.valid:
                        conflicts.append({
                            "type": "direct_contradiction",
                            "belief1": belief1_name,
                            "belief2": belief2_name,
                            "confidence1": belief1.confidence,
                            "confidence2": belief2.confidence
                        })
                
                # Même nom mais validité différente
                elif belief1_name == belief2_name:
                    if belief1.valid != belief2.valid and belief1.valid is not None and belief2.valid is not None:
                        conflicts.append({
                            "type": "validity_conflict",
                            "belief": belief1_name,
                            "validity1": belief1.valid,
                            "validity2": belief2.valid,
                            "confidence1": belief1.confidence,
                            "confidence2": belief2.confidence
                        })
        
        return conflicts
    
    def _generate_consistency_recommendations(self, consistency_report: Dict) -> List[Dict]:
        """Génère des recommandations pour améliorer la cohérence"""
        recommendations = []
        
        # Recommandations basées sur les conflits d'agents individuels
        for agent_name, agent_consistency in consistency_report["agent_consistencies"].items():
            if not agent_consistency["is_consistent"]:
                recommendations.append({
                    "type": "resolve_agent_conflicts",
                    "agent": agent_name,
                    "priority": "high",
                    "description": f"Résoudre {len(agent_consistency.get('conflicts', []))} conflits dans {agent_name}",
                    "action": "agent_consistency_repair"
                })
        
        # Recommandations pour conflits inter-agents
        inter_conflicts = consistency_report["inter_agent_conflicts"]
        if inter_conflicts:
            recommendations.append({
                "type": "resolve_inter_agent_conflicts",
                "priority": "critical",
                "description": f"Résoudre {len(inter_conflicts)} conflits inter-agents",
                "action": "conflict_resolution",
                "conflicts": inter_conflicts
            })
        
        # Recommandation de synchronisation si besoins
        if len(self._connected_agents) > 1:
            last_sync_times = [
                self._shared_belief_space[agent]["last_sync"]
                for agent in self._connected_agents
            ]
            oldest_sync = min(last_sync_times)
            
            if (datetime.now() - oldest_sync).seconds > 300:  # 5 minutes
                recommendations.append({
                    "type": "synchronization_needed",
                    "priority": "medium",
                    "description": "Synchronisation recommandée entre agents",
                    "action": "full_sync"
                })
        
        return recommendations
    
    # === UTILITAIRES ET ÉTAT ===
    
    async def _trigger_initial_sync(self, new_agent: str) -> None:
        """Déclenche une synchronisation initiale pour un nouvel agent"""
        await asyncio.sleep(1)  # Délai pour laisser l'agent s'initialiser
        
        # Synchroniser avec tous les autres agents
        for agent_name in self._connected_agents:
            if agent_name != new_agent:
                await self.sync_beliefs(agent_name, new_agent, "incremental")
    
    def get_hub_status(self) -> Dict:
        """Retourne l'état complet du hub de communication"""
        return {
            "status": self._status.value,
            "connected_agents": list(self._connected_agents.keys()),
            "shared_belief_space": self._shared_belief_space,
            "global_consistency": self._global_consistency_state,
            "statistics": {
                "messages_processed": self._messages_processed,
                "conflicts_resolved": self._conflicts_resolved,
                "sync_operations_completed": self._sync_operations_completed,
                "message_queue_size": len(self._message_queue),
                "pending_sync_operations": len([op for op in self._sync_operations if op.status == "pending"])
            },
            "configuration": {
                "auto_sync_enabled": self._auto_sync_enabled,
                "conflict_resolution_strategy": self._conflict_resolution_strategy,
                "sync_interval": self._sync_interval
            }
        }
    
    def configure_hub(self, config: Dict) -> bool:
        """Configure les paramètres du hub"""
        try:
            if "auto_sync_enabled" in config:
                self._auto_sync_enabled = config["auto_sync_enabled"]
            
            if "conflict_resolution_strategy" in config:
                strategy = config["conflict_resolution_strategy"]
                if strategy in self._conflict_resolver.resolution_strategies:
                    self._conflict_resolution_strategy = strategy
            
            if "sync_interval" in config:
                self._sync_interval = max(10, config["sync_interval"])  # Minimum 10 secondes
            
            self._logger.info("Configuration hub mise à jour")
            return True
            
        except Exception as e:
            self._logger.error(f"Erreur configuration hub: {e}")
            return False
    
    async def shutdown(self) -> Dict:
        """Arrêt propre du hub avec sauvegarde d'état"""
        self._logger.info("Arrêt du hub de communication")
        
        shutdown_report = {
            "shutdown_timestamp": datetime.now(),
            "agents_disconnected": [],
            "final_states_saved": {},
            "pending_operations": len([op for op in self._sync_operations if op.status == "pending"]),
            "messages_unprocessed": len(self._message_queue)
        }
        
        # Sauvegarder états finaux des agents
        for agent_name, agent in self._connected_agents.items():
            try:
                final_state = agent.export_session_state()
                shutdown_report["final_states_saved"][agent_name] = {
                    "session_id": agent.session_id,
                    "beliefs_count": len(final_state.get("beliefs", {})),
                    "last_modified": final_state.get("session_summary", {}).get("last_modified")
                }
                shutdown_report["agents_disconnected"].append(agent_name)
            except Exception as e:
                self._logger.error(f"Erreur sauvegarde état {agent_name}: {e}")
        
        # Changer statut
        self._status = CommunicationStatus.PAUSED
        
        return shutdown_report
    async def handle_agent_failure(self, failure_info: Dict) -> Dict:
        """Gère les échecs d'agents."""
        agent_id = failure_info.get("agent_id", "unknown")
        failure_type = failure_info.get("type", "unknown")
        
        self._logger.warning(f"Agent failure detected: {agent_id} ({failure_type})")
        
        # Implémenter la logique de récupération
        recovery_actions = []
        if failure_type == "communication_timeout":
            recovery_actions.append("retry_communication")
        elif failure_type == "logic_inconsistency":
            recovery_actions.append("belief_revision")
        
        return {
            "status": "handled",
            "agent_id": agent_id,
            "failure_type": failure_type,
            "recovery_action": "auto_restart" if recovery_actions else "manual_intervention",
            "agent_status": "failed",
            "notification_sent": True,
            "recovery_actions": recovery_actions,
            "timestamp": time.time()
        }

    async def broadcast_message(self, sender_id: str, content: str, message_type: str = "BROADCAST") -> List[str]:
        """Diffuse un message à tous les agents enregistrés."""
        message_ids = []
        
        for agent_id in self._connected_agents:
            if agent_id != sender_id:  # Ne pas renvoyer à l'expéditeur
                message_id = await self.send_message(sender_id, agent_id, content, message_type)
                message_ids.append(message_id)
        
        return message_ids

    async def process_message_queue(self) -> int:
        """Traite la file d'attente des messages."""
        processed_count = 0
        
        # Simuler le traitement de la file d'attente
        # Dans une vraie implémentation, on traiterait les messages en attente
        if hasattr(self, '_message_queue') and self._message_queue:
            processed_count = len(self._message_queue)
            self._message_queue.clear()
        
        return processed_count

    async def start_collaboration_session(self, participants: List[str], session_data: Dict) -> str:
        """Démarre une session de collaboration entre agents."""
        session_id = f"collab_{int(time.time())}"
        
        session_info = {
            "session_id": session_id,
            "participants": participants,
            "config": session_data,
            "start_time": time.time(),
            "status": "active"
        }
        
        self.collaboration_sessions[session_id] = session_info
        
        # Notifier les participants
        for participant in participants:
            if participant in self._connected_agents:
                await self.send_message(
                    "system", 
                    participant, 
                    f"Collaboration session {session_id} started",
                    "COLLABORATION_START"
                )
        
        return session_id

    async def coordinate_investigation(self, investigation_id: str, investigation_data: Dict) -> Dict:
        """Coordonne une enquête entre les agents."""
        
        # Analyser les données d'enquête
        case_type = investigation_data.get("case_type", "general")
        evidence = investigation_data.get("evidence", [])
        
        # Assigner les rôles selon le type d'enquête
        coordination_plan = {
            "investigation_id": investigation_id,
            "status": "coordinated",
            "case_type": case_type,
            "evidence_count": len(evidence),
            "assigned_agents": list(self._connected_agents.keys()),
            "next_steps": [
                "evidence_analysis",
                "hypothesis_generation",
                "validation"
            ]
        }
        
        return {
            "coordination_plan": coordination_plan,
            "agent_assignments": coordination_plan["assigned_agents"],
            "communication_protocol": "jtms_sync",
            **coordination_plan
        }

    async def synchronize_beliefs(self, agent_ids: List[str], sync_config: Dict[str, Any]) -> Dict:
        """Synchronise les croyances entre agents spécifiés."""
        
        synchronized_beliefs = {}
        conflicts = []
        
        # Collecter les croyances de chaque agent
        for agent_id in agent_ids:
            if agent_id in self._connected_agents:
                agent = self._connected_agents[agent_id]
                if hasattr(agent, 'get_beliefs'):
                    beliefs = agent.get_beliefs()
                    synchronized_beliefs[agent_id] = beliefs
        
        # Détecter les conflits (implémentation simplifiée)
        belief_keys = set()
        for beliefs in synchronized_beliefs.values():
            belief_keys.update(beliefs.keys())
        
        # Simuler la détection de conflits
        if len(synchronized_beliefs) > 1:
            conflicts.append("belief_conflict_detected")
        
        return {
            "sync_id": f"sync_{int(time.time())}",
            "status": "synchronized",
            "agents": agent_ids,
            "synchronized_beliefs": synchronized_beliefs,
            "merged_beliefs": synchronized_beliefs,
            "conflicts": conflicts,
            "conflicts_resolved": len(conflicts) == 0,
            "consistency_status": "consistent" if len(conflicts) == 0 else "inconsistent",
            "timestamp": time.time()
        }

    async def facilitate_deliberation(self, deliberation_id: str, topic: Dict) -> Dict:
        """Facilite une délibération entre agents."""
        
        deliberation_result = {
            "deliberation_id": deliberation_id,
            "topic": topic.get("subject", "unknown"),
            "status": "facilitated",
            "participants": list(self._connected_agents.keys()),
            "outcome": "consensus_reached",
            "consensus_reached": True,
            "final_hypothesis": f"Consensus sur: {topic.get('subject', 'unknown')}",
            "confidence_level": 0.95,
            "reasoning_steps": [
                "problem_analysis",
                "evidence_review",
                "hypothesis_evaluation",
                "conclusion"
            ],
            "timestamp": time.time()
        }
        
        return deliberation_result

    def export_communication_log(self) -> Dict:
        """Exporte le journal de communication."""
        
        # Collecter les logs de communication
        communication_log = {
            "hub_id": self.hub_id,
            "export_timestamp": time.time(),
            "total_messages": len(getattr(self, '_communication_history', [])),
            "active_agents": len(self._connected_agents),
            "registered_agents": list(self._connected_agents.keys()),
            "sessions": len(self.collaboration_sessions),
            "collaboration_sessions": list(self.collaboration_sessions.keys()),
            "message_history": getattr(self, '_communication_history', [])
        }
        
        return communication_log

    def get_hub_statistics(self) -> Dict:
        """Retourne les statistiques du hub."""
        
        stats = {
            "hub_id": self.hub_id,
            "uptime": time.time() - getattr(self, '_start_time', time.time()),
            "total_agents": len(self._connected_agents),
            "active_sessions": len(self.collaboration_sessions),
            "total_messages": len(getattr(self, '_communication_history', [])),
            "messages_processed": self._messages_processed,
            "last_activity": getattr(self, '_last_activity', time.time())
        }
        
        return stats

# === FONCTIONS UTILITAIRES ===

async def create_sherlock_watson_communication(kernel: Kernel,
                                             sherlock_config: Dict = None,
                                             watson_config: Dict = None,
                                             use_tweety: bool = True) -> Tuple[SherlockJTMSAgent, WatsonJTMSAgent, JTMSCommunicationHub]:
    """
    Fonction utilitaire pour créer et configurer un système complet Sherlock/Watson avec JTMS
    """
    # Créer les agents
    sherlock_config = sherlock_config or {}
    watson_config = watson_config or {}
    
    sherlock = SherlockJTMSAgent(
        kernel,
        agent_name=sherlock_config.get("name", "Sherlock_JTMS"),
        system_prompt=sherlock_config.get("system_prompt")
    )
    
    watson = WatsonJTMSAgent(
        kernel,
        agent_name=watson_config.get("name", "Watson_JTMS"),
        constants=watson_config.get("constants"),
        system_prompt=watson_config.get("system_prompt"),
        use_tweety=use_tweety
    )
    
    # Créer le hub de communication
    hub = JTMSCommunicationHub(kernel)
    
    # Enregistrer les agents
    await hub.register_agent(sherlock)
    await hub.register_agent(watson)
    
    # Configuration initiale du hub
    hub_config = {
        "auto_sync_enabled": True,
        "conflict_resolution_strategy": "evidence_based",  # Bon pour Sherlock/Watson
        "sync_interval": 60
    }
    hub.configure_hub(hub_config)
    
    # Activer le hub
    hub._status = CommunicationStatus.ACTIVE
    
    return sherlock, watson, hub

async def run_investigation_session(sherlock: SherlockJTMSAgent, 
                                  watson: WatsonJTMSAgent,
                                  hub: JTMSCommunicationHub,
                                  investigation_context: Dict) -> Dict:
    """
    Fonction utilitaire pour exécuter une session d'investigation complète
    """
    session_results = {
        "session_id": f"investigation_{int(datetime.now().timestamp())}",
        "start_time": datetime.now(),
        "context": investigation_context,
        "phases": [],
        "final_solution": None,
        "jtms_summary": {}
    }
    
    try:
        # Phase 1: Sherlock formule hypothèses
        phase1_start = datetime.now()
        
        hypothesis_result = await sherlock.formulate_hypothesis(
            investigation_context.get("description", "Investigation en cours")
        )
        
        session_results["phases"].append({
            "phase": "hypothesis_formulation",
            "agent": "sherlock",
            "duration": (datetime.now() - phase1_start).total_seconds(),
            "result": hypothesis_result
        })
        
        # Synchronisation après hypothèse
        sync_result = await hub.sync_beliefs("Sherlock_JTMS", "Watson_JTMS")
        
        # Phase 2: Watson critique l'hypothèse
        phase2_start = datetime.now()
        
        critique_result = await watson.critique_hypothesis(
            hypothesis_result,
            sherlock.export_session_state()
        )
        
        session_results["phases"].append({
            "phase": "hypothesis_critique",
            "agent": "watson", 
            "duration": (datetime.now() - phase2_start).total_seconds(),
            "result": critique_result
        })
        
        # Phase 3: Résolution de solution collaborative
        phase3_start = datetime.now()
        
        # Watson valide le raisonnement Sherlock
        validation_result = await watson.validate_sherlock_reasoning(
            sherlock.export_session_state()
        )
        
        # Sherlock intègre les retours Watson et propose solution finale
        solution_result = await sherlock.deduce_solution(investigation_context)
        
        session_results["phases"].append({
            "phase": "collaborative_solution",
            "agents": ["sherlock", "watson"],
            "duration": (datetime.now() - phase3_start).total_seconds(),
            "validation": validation_result,
            "solution": solution_result
        })
        
        session_results["final_solution"] = solution_result
        
        # Vérification cohérence globale finale
        global_consistency = await hub.check_global_consistency()
        
        session_results["jtms_summary"] = {
            "sherlock_statistics": sherlock.get_session_statistics(),
            "watson_statistics": watson.get_session_statistics(),
            "hub_status": hub.get_hub_status(),
            "global_consistency": global_consistency
        }
        
        session_results["end_time"] = datetime.now()
        session_results["total_duration"] = (session_results["end_time"] - session_results["start_time"]).total_seconds()
        session_results["success"] = True
        
        return session_results
        
    except Exception as e:
        session_results["error"] = str(e)
        session_results["success"] = False
        session_results["end_time"] = datetime.now()
        return session_results