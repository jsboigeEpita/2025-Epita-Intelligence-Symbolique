"""
Modèles de communication inter-agents pour l'intégration JTMS.
Définit les protocoles et structures de données pour les échanges entre Sherlock/Watson.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
import uuid

class MessageType(Enum):
    """Types de messages échangés entre agents"""
    BELIEF_SHARE = "belief_share"              # Partage de croyance
    VALIDATION_REQUEST = "validation_request"   # Demande de validation
    VALIDATION_RESPONSE = "validation_response" # Réponse de validation
    CRITIQUE_REQUEST = "critique_request"       # Demande de critique
    CRITIQUE_RESPONSE = "critique_response"     # Réponse de critique
    HYPOTHESIS_SHARE = "hypothesis_share"       # Partage d'hypothèse
    EVIDENCE_SHARE = "evidence_share"          # Partage d'évidence
    CONFLICT_NOTIFICATION = "conflict_notification"  # Notification de conflit
    CONFLICT_RESOLUTION = "conflict_resolution"      # Résolution de conflit
    SYNC_REQUEST = "sync_request"              # Demande de synchronisation
    SYNC_RESPONSE = "sync_response"            # Réponse de synchronisation
    STATUS_UPDATE = "status_update"           # Mise à jour de statut
    SESSION_CONTROL = "session_control"       # Contrôle de session
    ERROR_NOTIFICATION = "error_notification" # Notification d'erreur

class MessagePriority(Enum):
    """Priorités de messages"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
    URGENT = "urgent"

class CommunicationProtocolType(Enum):
    """Types de protocoles de communication"""
    DIRECT = "direct"                    # Communication directe
    HUB_MEDIATED = "hub_mediated"       # Médiation par hub
    BROADCAST = "broadcast"             # Diffusion générale
    REQUEST_RESPONSE = "request_response" # Requête-réponse
    SUBSCRIPTION = "subscription"        # Abonnement à des événements

class SyncOperationType(Enum):
    """Types d'opérations de synchronisation"""
    INCREMENTAL = "incremental"         # Sync incrémentale
    FULL = "full"                      # Sync complète
    SELECTIVE = "selective"            # Sync sélective
    BIDIRECTIONAL = "bidirectional"    # Sync bidirectionnelle
    MERGE = "merge"                    # Fusion de sessions

@dataclass
class MessageMetadata:
    """Métadonnées d'un message"""
    message_id: str
    timestamp: datetime
    sender_id: str
    receiver_id: str
    message_type: MessageType
    priority: MessagePriority
    
    # Tracking et traçabilité
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    reply_to: Optional[str] = None
    correlation_id: Optional[str] = None
    
    # Configuration de livraison
    requires_response: bool = False
    response_timeout: Optional[timedelta] = None
    max_retries: int = 3
    retry_count: int = 0
    
    # État du message
    delivery_status: str = "pending"  # pending, delivered, failed, expired
    processed_status: str = "unprocessed"  # unprocessed, processing, processed, error
    
    # Contexte d'investigation
    investigation_context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Génère un ID unique si non fourni"""
        if not self.message_id:
            timestamp_str = str(int(self.timestamp.timestamp()))
            self.message_id = f"msg_{uuid.uuid4().hex[:8]}_{timestamp_str}"
    
    def mark_delivered(self):
        """Marque le message comme livré"""
        self.delivery_status = "delivered"
    
    def mark_processed(self):
        """Marque le message comme traité"""
        self.processed_status = "processed"
    
    def mark_failed(self, reason: str = ""):
        """Marque le message comme échoué"""
        self.delivery_status = "failed"
        self.processed_status = "error"
        self.investigation_context["failure_reason"] = reason
    
    def increment_retry(self) -> bool:
        """Incrémente le compteur de tentatives"""
        self.retry_count += 1
        return self.retry_count <= self.max_retries
    
    def is_expired(self) -> bool:
        """Vérifie si le message a expiré"""
        if self.response_timeout:
            return datetime.now() - self.timestamp > self.response_timeout
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire"""
        return {
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat(),
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "message_type": self.message_type.value,
            "priority": self.priority.value,
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "reply_to": self.reply_to,
            "correlation_id": self.correlation_id,
            "requires_response": self.requires_response,
            "response_timeout": self.response_timeout.total_seconds() if self.response_timeout else None,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "delivery_status": self.delivery_status,
            "processed_status": self.processed_status,
            "investigation_context": self.investigation_context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageMetadata':
        """Création depuis un dictionnaire"""
        response_timeout = None
        if data.get("response_timeout"):
            response_timeout = timedelta(seconds=data["response_timeout"])
        
        return cls(
            message_id=data["message_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            sender_id=data["sender_id"],
            receiver_id=data["receiver_id"],
            message_type=MessageType(data["message_type"]),
            priority=MessagePriority(data["priority"]),
            session_id=data.get("session_id"),
            conversation_id=data.get("conversation_id"),
            reply_to=data.get("reply_to"),
            correlation_id=data.get("correlation_id"),
            requires_response=data.get("requires_response", False),
            response_timeout=response_timeout,
            max_retries=data.get("max_retries", 3),
            retry_count=data.get("retry_count", 0),
            delivery_status=data.get("delivery_status", "pending"),
            processed_status=data.get("processed_status", "unprocessed"),
            investigation_context=data.get("investigation_context", {})
        )

@dataclass
class AgentMessage:
    """
    Message échangé entre agents dans le système JTMS.
    Structure unifiée pour tous types de communication.
    """
    metadata: MessageMetadata
    payload: Dict[str, Any]
    
    # Validation et sécurité
    schema_version: str = "1.0"
    checksum: Optional[str] = None
    encryption_info: Optional[Dict[str, str]] = None
    
    def __post_init__(self):
        """Validation et initialisation post-création"""
        self._validate_payload()
        if not self.checksum:
            self.checksum = self._calculate_checksum()
    
    def _validate_payload(self):
        """Valide le payload selon le type de message"""
        message_type = self.metadata.message_type
        
        # Validations basiques selon le type
        required_fields = {
            MessageType.BELIEF_SHARE: ["belief_id", "belief_data"],
            MessageType.VALIDATION_REQUEST: ["target_belief", "validation_criteria"],
            MessageType.VALIDATION_RESPONSE: ["original_request_id", "validation_result"],
            MessageType.CRITIQUE_REQUEST: ["target_hypothesis", "critique_scope"],
            MessageType.CRITIQUE_RESPONSE: ["original_request_id", "critique_result"],
            MessageType.HYPOTHESIS_SHARE: ["hypothesis_id", "hypothesis_data"],
            MessageType.EVIDENCE_SHARE: ["evidence_id", "evidence_data"],
            MessageType.CONFLICT_NOTIFICATION: ["conflict_id", "conflict_details"],
            MessageType.CONFLICT_RESOLUTION: ["conflict_id", "resolution_strategy", "resolution_result"],
            MessageType.SYNC_REQUEST: ["sync_type", "source_data"],
            MessageType.SYNC_RESPONSE: ["sync_request_id", "sync_result"],
            MessageType.STATUS_UPDATE: ["status_type", "status_data"],
            MessageType.SESSION_CONTROL: ["control_action", "control_parameters"],
            MessageType.ERROR_NOTIFICATION: ["error_type", "error_details"]
        }
        
        if message_type in required_fields:
            missing_fields = [
                field for field in required_fields[message_type]
                if field not in self.payload
            ]
            
            if missing_fields:
                raise ValueError(f"Message {message_type.value} manque les champs: {missing_fields}")
    
    def _calculate_checksum(self) -> str:
        """Calcule un checksum simple du message"""
        import hashlib
        content = json.dumps(self.payload, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def verify_integrity(self) -> bool:
        """Vérifie l'intégrité du message"""
        return self.checksum == self._calculate_checksum()
    
    def is_response_to(self, other_message: 'AgentMessage') -> bool:
        """Vérifie si ce message est une réponse à un autre"""
        return (self.metadata.reply_to == other_message.metadata.message_id or
                self.metadata.correlation_id == other_message.metadata.message_id)
    
    def create_response(self, response_payload: Dict[str, Any], 
                       response_type: MessageType = None) -> 'AgentMessage':
        """Crée un message de réponse"""
        if not response_type:
            # Déduire le type de réponse
            response_mapping = {
                MessageType.VALIDATION_REQUEST: MessageType.VALIDATION_RESPONSE,
                MessageType.CRITIQUE_REQUEST: MessageType.CRITIQUE_RESPONSE,
                MessageType.SYNC_REQUEST: MessageType.SYNC_RESPONSE
            }
            response_type = response_mapping.get(self.metadata.message_type, MessageType.STATUS_UPDATE)
        
        response_metadata = MessageMetadata(
            message_id="",  # Sera généré automatiquement
            timestamp=datetime.now(),
            sender_id=self.metadata.receiver_id,
            receiver_id=self.metadata.sender_id,
            message_type=response_type,
            priority=self.metadata.priority,
            session_id=self.metadata.session_id,
            conversation_id=self.metadata.conversation_id,
            reply_to=self.metadata.message_id,
            correlation_id=self.metadata.correlation_id,
            investigation_context=dict(self.metadata.investigation_context)
        )
        
        # Ajouter référence à la demande originale
        enhanced_payload = {
            **response_payload,
            "original_request_id": self.metadata.message_id,
            "original_request_type": self.metadata.message_type.value
        }
        
        return AgentMessage(
            metadata=response_metadata,
            payload=enhanced_payload,
            schema_version=self.schema_version
        )
    
    def add_context(self, context_key: str, context_value: Any):
        """Ajoute du contexte au message"""
        self.metadata.investigation_context[context_key] = context_value
    
    def get_context(self, context_key: str, default: Any = None) -> Any:
        """Récupère du contexte du message"""
        return self.metadata.investigation_context.get(context_key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire"""
        return {
            "metadata": self.metadata.to_dict(),
            "payload": self.payload,
            "schema_version": self.schema_version,
            "checksum": self.checksum,
            "encryption_info": self.encryption_info
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """Création depuis un dictionnaire"""
        metadata = MessageMetadata.from_dict(data["metadata"])
        
        return cls(
            metadata=metadata,
            payload=data["payload"],
            schema_version=data.get("schema_version", "1.0"),
            checksum=data.get("checksum"),
            encryption_info=data.get("encryption_info")
        )
    
    def __str__(self) -> str:
        """Représentation textuelle"""
        return (f"AgentMessage({self.metadata.message_type.value}: "
                f"{self.metadata.sender_id} → {self.metadata.receiver_id}, "
                f"priority={self.metadata.priority.value})")

@dataclass
class CommunicationProtocol:
    """
    Définit un protocole de communication entre agents.
    Configure les règles et contraintes pour les échanges.
    """
    protocol_id: str
    protocol_type: CommunicationProtocolType
    name: str
    description: str = ""
    
    # Participants
    participating_agents: List[str] = field(default_factory=list)
    protocol_roles: Dict[str, str] = field(default_factory=dict)  # agent_id -> role
    
    # Configuration de messages
    supported_message_types: List[MessageType] = field(default_factory=list)
    message_routing: Dict[MessageType, str] = field(default_factory=dict)  # type -> routing_strategy
    
    # Contraintes de communication
    max_message_size: int = 1024 * 1024  # 1MB par défaut
    message_rate_limit: int = 100  # messages/minute par agent
    response_timeout: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    
    # Qualité de service
    delivery_guarantees: str = "at_least_once"  # at_most_once, at_least_once, exactly_once
    ordering_guarantees: str = "partial"  # none, partial, total
    persistence_required: bool = True
    
    # Gestion d'erreurs
    error_handling_strategy: str = "retry_and_escalate"
    max_retry_attempts: int = 3
    backoff_strategy: str = "exponential"
    
    # Métriques et monitoring
    enable_metrics: bool = True
    metrics_collection: Dict[str, bool] = field(default_factory=lambda: {
        "message_count": True,
        "latency": True,
        "error_rate": True,
        "throughput": True
    })
    
    # État du protocole
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    
    def add_agent(self, agent_id: str, role: str = "participant") -> bool:
        """Ajoute un agent au protocole"""
        if agent_id not in self.participating_agents:
            self.participating_agents.append(agent_id)
            self.protocol_roles[agent_id] = role
            return True
        return False
    
    def remove_agent(self, agent_id: str) -> bool:
        """Retire un agent du protocole"""
        if agent_id in self.participating_agents:
            self.participating_agents.remove(agent_id)
            self.protocol_roles.pop(agent_id, None)
            return True
        return False
    
    def can_send_message(self, sender_id: str, message_type: MessageType) -> Tuple[bool, str]:
        """Vérifie si un agent peut envoyer un type de message"""
        if not self.is_active:
            return False, "Protocole inactif"
        
        if sender_id not in self.participating_agents:
            return False, "Agent non participant"
        
        if message_type not in self.supported_message_types:
            return False, f"Type de message {message_type.value} non supporté"
        
        return True, "Autorisé"
    
    def get_routing_strategy(self, message_type: MessageType) -> str:
        """Retourne la stratégie de routage pour un type de message"""
        return self.message_routing.get(message_type, "direct")
    
    def validate_message(self, message: AgentMessage) -> Tuple[bool, List[str]]:
        """Valide un message selon le protocole"""
        errors = []
        
        # Vérifier la taille
        message_size = len(json.dumps(message.to_dict()))
        if message_size > self.max_message_size:
            errors.append(f"Message trop volumineux: {message_size} > {self.max_message_size}")
        
        # Vérifier l'intégrité
        if not message.verify_integrity():
            errors.append("Intégrité du message compromise")
        
        # Vérifier l'autorisation
        can_send, reason = self.can_send_message(
            message.metadata.sender_id, 
            message.metadata.message_type
        )
        if not can_send:
            errors.append(reason)
        
        return len(errors) == 0, errors
    
    def update_usage(self):
        """Met à jour les statistiques d'utilisation"""
        self.last_used = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire"""
        return {
            "protocol_id": self.protocol_id,
            "protocol_type": self.protocol_type.value,
            "name": self.name,
            "description": self.description,
            "participating_agents": self.participating_agents,
            "protocol_roles": self.protocol_roles,
            "supported_message_types": [mt.value for mt in self.supported_message_types],
            "message_routing": {mt.value: strategy for mt, strategy in self.message_routing.items()},
            "max_message_size": self.max_message_size,
            "message_rate_limit": self.message_rate_limit,
            "response_timeout": self.response_timeout.total_seconds(),
            "delivery_guarantees": self.delivery_guarantees,
            "ordering_guarantees": self.ordering_guarantees,
            "persistence_required": self.persistence_required,
            "error_handling_strategy": self.error_handling_strategy,
            "max_retry_attempts": self.max_retry_attempts,
            "backoff_strategy": self.backoff_strategy,
            "enable_metrics": self.enable_metrics,
            "metrics_collection": self.metrics_collection,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommunicationProtocol':
        """Création depuis un dictionnaire"""
        supported_message_types = [MessageType(mt) for mt in data.get("supported_message_types", [])]
        message_routing = {
            MessageType(mt): strategy 
            for mt, strategy in data.get("message_routing", {}).items()
        }
        
        return cls(
            protocol_id=data["protocol_id"],
            protocol_type=CommunicationProtocolType(data["protocol_type"]),
            name=data["name"],
            description=data.get("description", ""),
            participating_agents=data.get("participating_agents", []),
            protocol_roles=data.get("protocol_roles", {}),
            supported_message_types=supported_message_types,
            message_routing=message_routing,
            max_message_size=data.get("max_message_size", 1024 * 1024),
            message_rate_limit=data.get("message_rate_limit", 100),
            response_timeout=timedelta(seconds=data.get("response_timeout", 300)),
            delivery_guarantees=data.get("delivery_guarantees", "at_least_once"),
            ordering_guarantees=data.get("ordering_guarantees", "partial"),
            persistence_required=data.get("persistence_required", True),
            error_handling_strategy=data.get("error_handling_strategy", "retry_and_escalate"),
            max_retry_attempts=data.get("max_retry_attempts", 3),
            backoff_strategy=data.get("backoff_strategy", "exponential"),
            enable_metrics=data.get("enable_metrics", True),
            metrics_collection=data.get("metrics_collection", {}),
            is_active=data.get("is_active", True),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None
        )

@dataclass
class SyncOperation:
    """
    Opération de synchronisation entre agents ou sessions JTMS.
    Trace et gère les opérations de synchronisation complexes.
    """
    operation_id: str
    operation_type: SyncOperationType
    source_agent: str
    target_agents: List[str]
    
    # Configuration de l'opération
    sync_scope: Dict[str, Any] = field(default_factory=dict)  # Quoi synchroniser
    sync_filters: Dict[str, Any] = field(default_factory=dict)  # Filtres à appliquer
    conflict_resolution_strategy: str = "manual"  # manual, automatic, skip
    
    # État de l'opération
    status: str = "pending"  # pending, running, completed, failed, cancelled
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    progress: float = 0.0  # 0.0 - 1.0
    
    # Résultats
    sync_results: Dict[str, Any] = field(default_factory=dict)
    conflicts_detected: List[Dict[str, Any]] = field(default_factory=list)
    conflicts_resolved: List[Dict[str, Any]] = field(default_factory=list)
    
    # Métriques
    items_synchronized: int = 0
    items_skipped: int = 0
    items_failed: int = 0
    
    # Contexte et traçabilité
    session_context: Dict[str, Any] = field(default_factory=dict)
    operation_log: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """Génère un ID unique si non fourni"""
        if not self.operation_id:
            timestamp_str = str(int(datetime.now().timestamp()))
            self.operation_id = f"sync_{uuid.uuid4().hex[:8]}_{timestamp_str}"
    
    def start(self) -> bool:
        """Démarre l'opération de synchronisation"""
        if self.status == "pending":
            self.status = "running"
            self.start_time = datetime.now()
            self.progress = 0.0
            
            self.log_event("operation_started", {
                "source_agent": self.source_agent,
                "target_agents": self.target_agents,
                "operation_type": self.operation_type.value
            })
            
            return True
        return False
    
    def complete(self, final_results: Dict[str, Any] = None):
        """Complète l'opération"""
        self.status = "completed"
        self.end_time = datetime.now()
        self.progress = 1.0
        
        if final_results:
            self.sync_results.update(final_results)
        
        self.log_event("operation_completed", {
            "duration_seconds": self.duration_seconds,
            "items_synchronized": self.items_synchronized,
            "conflicts_resolved": len(self.conflicts_resolved)
        })
    
    def fail(self, error_reason: str):
        """Marque l'opération comme échouée"""
        self.status = "failed"
        self.end_time = datetime.now()
        
        self.log_event("operation_failed", {
            "error_reason": error_reason,
            "progress_at_failure": self.progress
        })
    
    def cancel(self, reason: str = ""):
        """Annule l'opération"""
        self.status = "cancelled"
        self.end_time = datetime.now()
        
        self.log_event("operation_cancelled", {
            "reason": reason,
            "progress_at_cancellation": self.progress
        })
    
    def update_progress(self, new_progress: float, message: str = ""):
        """Met à jour le progrès"""
        self.progress = max(0.0, min(1.0, new_progress))
        
        if message:
            self.log_event("progress_update", {
                "progress": self.progress,
                "message": message
            })
    
    def add_conflict(self, conflict_data: Dict[str, Any]):
        """Ajoute un conflit détecté"""
        conflict = {
            **conflict_data,
            "detected_at": datetime.now().isoformat(),
            "operation_id": self.operation_id
        }
        
        self.conflicts_detected.append(conflict)
        
        self.log_event("conflict_detected", {
            "conflict_id": conflict.get("conflict_id", "unknown"),
            "conflict_type": conflict.get("type", "unknown")
        })
    
    def resolve_conflict(self, conflict_id: str, resolution_data: Dict[str, Any]):
        """Résout un conflit"""
        resolution = {
            **resolution_data,
            "conflict_id": conflict_id,
            "resolved_at": datetime.now().isoformat(),
            "operation_id": self.operation_id
        }
        
        self.conflicts_resolved.append(resolution)
        
        self.log_event("conflict_resolved", {
            "conflict_id": conflict_id,
            "resolution_strategy": resolution_data.get("strategy", "unknown")
        })
    
    def log_event(self, event_type: str, event_data: Dict[str, Any]):
        """Ajoute un événement au log"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "event_data": event_data
        }
        
        self.operation_log.append(event)
    
    @property
    def duration_seconds(self) -> float:
        """Durée de l'opération en secondes"""
        if self.start_time:
            end_time = self.end_time or datetime.now()
            return (end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def is_active(self) -> bool:
        """Vérifie si l'opération est active"""
        return self.status in ["pending", "running"]
    
    @property
    def is_completed(self) -> bool:
        """Vérifie si l'opération est terminée"""
        return self.status in ["completed", "failed", "cancelled"]
    
    def get_summary(self) -> Dict[str, Any]:
        """Retourne un résumé de l'opération"""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type.value,
            "status": self.status,
            "progress": self.progress,
            "duration_seconds": self.duration_seconds,
            "items_synchronized": self.items_synchronized,
            "items_skipped": self.items_skipped,
            "items_failed": self.items_failed,
            "conflicts_detected": len(self.conflicts_detected),
            "conflicts_resolved": len(self.conflicts_resolved),
            "source_agent": self.source_agent,
            "target_agents": self.target_agents
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire"""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type.value,
            "source_agent": self.source_agent,
            "target_agents": self.target_agents,
            "sync_scope": self.sync_scope,
            "sync_filters": self.sync_filters,
            "conflict_resolution_strategy": self.conflict_resolution_strategy,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "progress": self.progress,
            "sync_results": self.sync_results,
            "conflicts_detected": self.conflicts_detected,
            "conflicts_resolved": self.conflicts_resolved,
            "items_synchronized": self.items_synchronized,
            "items_skipped": self.items_skipped,
            "items_failed": self.items_failed,
            "session_context": self.session_context,
            "operation_log": self.operation_log,
            "summary": self.get_summary()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SyncOperation':
        """Création depuis un dictionnaire"""
        start_time = None
        if data.get("start_time"):
            start_time = datetime.fromisoformat(data["start_time"])
        
        end_time = None
        if data.get("end_time"):
            end_time = datetime.fromisoformat(data["end_time"])
        
        return cls(
            operation_id=data["operation_id"],
            operation_type=SyncOperationType(data["operation_type"]),
            source_agent=data["source_agent"],
            target_agents=data["target_agents"],
            sync_scope=data.get("sync_scope", {}),
            sync_filters=data.get("sync_filters", {}),
            conflict_resolution_strategy=data.get("conflict_resolution_strategy", "manual"),
            status=data.get("status", "pending"),
            start_time=start_time,
            end_time=end_time,
            progress=data.get("progress", 0.0),
            sync_results=data.get("sync_results", {}),
            conflicts_detected=data.get("conflicts_detected", []),
            conflicts_resolved=data.get("conflicts_resolved", []),
            items_synchronized=data.get("items_synchronized", 0),
            items_skipped=data.get("items_skipped", 0),
            items_failed=data.get("items_failed", 0),
            session_context=data.get("session_context", {}),
            operation_log=data.get("operation_log", [])
        )

# === FONCTIONS UTILITAIRES ===

def create_sherlock_watson_protocol() -> CommunicationProtocol:
    """Crée un protocole de communication optimisé pour Sherlock/Watson"""
    protocol = CommunicationProtocol(
        protocol_id="sherlock_watson_v1",
        protocol_type=CommunicationProtocolType.HUB_MEDIATED,
        name="Sherlock-Watson Investigation Protocol",
        description="Protocole optimisé pour la collaboration Sherlock/Watson avec JTMS",
        supported_message_types=[
            MessageType.BELIEF_SHARE,
            MessageType.VALIDATION_REQUEST,
            MessageType.VALIDATION_RESPONSE,
            MessageType.CRITIQUE_REQUEST,
            MessageType.CRITIQUE_RESPONSE,
            MessageType.HYPOTHESIS_SHARE,
            MessageType.EVIDENCE_SHARE,
            MessageType.CONFLICT_NOTIFICATION,
            MessageType.CONFLICT_RESOLUTION,
            MessageType.SYNC_REQUEST,
            MessageType.SYNC_RESPONSE,
            MessageType.STATUS_UPDATE
        ],
        message_routing={
            MessageType.VALIDATION_REQUEST: "hub_mediated",
            MessageType.CRITIQUE_REQUEST: "hub_mediated",
            MessageType.BELIEF_SHARE: "broadcast",
            MessageType.CONFLICT_RESOLUTION: "hub_mediated"
        },
        response_timeout=timedelta(minutes=2),
        delivery_guarantees="at_least_once",
        ordering_guarantees="partial"
    )
    
    return protocol

def create_validation_request_message(sender_id: str, receiver_id: str, 
                                    belief_id: str, validation_criteria: Dict[str, Any],
                                    session_id: str = None) -> AgentMessage:
    """Crée un message de demande de validation"""
    metadata = MessageMetadata(
        message_id="",
        timestamp=datetime.now(),
        sender_id=sender_id,
        receiver_id=receiver_id,
        message_type=MessageType.VALIDATION_REQUEST,
        priority=MessagePriority.HIGH,
        session_id=session_id,
        requires_response=True,
        response_timeout=timedelta(minutes=5)
    )
    
    payload = {
        "target_belief": belief_id,
        "validation_criteria": validation_criteria,
        "timestamp": datetime.now().isoformat()
    }
    
    return AgentMessage(metadata=metadata, payload=payload)

def create_critique_request_message(sender_id: str, receiver_id: str,
                                  hypothesis_data: Dict[str, Any],
                                  session_id: str = None) -> AgentMessage:
    """Crée un message de demande de critique"""
    metadata = MessageMetadata(
        message_id="",
        timestamp=datetime.now(),
        sender_id=sender_id,
        receiver_id=receiver_id,
        message_type=MessageType.CRITIQUE_REQUEST,
        priority=MessagePriority.NORMAL,
        session_id=session_id,
        requires_response=True,
        response_timeout=timedelta(minutes=3)
    )
    
    payload = {
        "target_hypothesis": hypothesis_data,
        "critique_scope": ["logical_consistency", "evidence_support", "completeness"],
        "timestamp": datetime.now().isoformat()
    }
    
    return AgentMessage(metadata=metadata, payload=payload)

def create_sync_request_message(sender_id: str, receiver_id: str,
                               sync_type: str, source_data: Dict[str, Any],
                               session_id: str = None) -> AgentMessage:
    """Crée un message de demande de synchronisation"""
    metadata = MessageMetadata(
        message_id="",
        timestamp=datetime.now(),
        sender_id=sender_id,
        receiver_id=receiver_id,
        message_type=MessageType.SYNC_REQUEST,
        priority=MessagePriority.NORMAL,
        session_id=session_id,
        requires_response=True,
        response_timeout=timedelta(minutes=10)
    )
    
    payload = {
        "sync_type": sync_type,
        "source_data": source_data,
        "timestamp": datetime.now().isoformat()
    }
    
    return AgentMessage(metadata=metadata, payload=payload)