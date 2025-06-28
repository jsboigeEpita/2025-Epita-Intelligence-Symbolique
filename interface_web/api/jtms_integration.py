#!/usr/bin/env python3
"""
API d'Intégration JTMS
=====================

Passerelle API pour l'intégration entre l'interface web Flask et les services JTMS backend.
Fournit une couche d'abstraction et de transformation des données.

Version: 1.0.0
Auteur: Intelligence Symbolique EPITA
Date: 11/06/2025
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from flask import current_app

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Exception personnalisée pour les erreurs d'API JTMS."""
    def __init__(self, message: str, error_code: str = "GENERIC_ERROR", status_code: int = 500):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)


class BeliefStatus(Enum):
    """Statuts possibles pour les croyances JTMS."""
    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"
    INCONSISTENT = "inconsistent"


@dataclass
class BeliefResponse:
    """Réponse API pour une croyance."""
    name: str
    status: BeliefStatus
    justifications: List[str]
    session_id: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour JSON."""
        return {
            "name": self.name,
            "status": self.status.value,
            "justifications": self.justifications,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata or {}
        }


@dataclass
class SessionResponse:
    """Réponse API pour une session JTMS."""
    session_id: str
    name: str
    description: str
    created_at: str
    last_modified: str
    belief_count: int
    justification_count: int
    status: str
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour JSON."""
        return {
            "session_id": self.session_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "last_modified": self.last_modified,
            "belief_count": self.belief_count,
            "justification_count": self.justification_count,
            "status": self.status,
            "metadata": self.metadata or {}
        }


@dataclass
class NetworkVisualizationData:
    """Données de visualisation pour le réseau JTMS."""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    statistics: Dict[str, Any]
    session_id: str
    generated_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour JSON."""
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "statistics": self.statistics,
            "session_id": self.session_id,
            "generated_at": self.generated_at
        }


class JTMSIntegrationAPI:
    """API principale d'intégration JTMS."""
    
    def __init__(self, jtms_service=None, session_manager=None, websocket_manager=None):
        """
        Initialise l'API d'intégration.
        
        Args:
            jtms_service: Service JTMS backend
            session_manager: Gestionnaire de sessions JTMS
            websocket_manager: Gestionnaire WebSocket pour temps réel
        """
        self.jtms_service = jtms_service
        self.session_manager = session_manager
        self.websocket_manager = websocket_manager
        self._cache = {}
        self._cache_ttl = timedelta(minutes=5)
        
    def _get_services(self):
        """Récupère les services depuis le contexte Flask si disponible."""
        if not self.jtms_service and current_app:
            self.jtms_service = current_app.config.get('JTMS_SERVICE')
            self.session_manager = current_app.config.get('JTMS_SESSION_MANAGER')
        
        if not self.jtms_service:
            raise APIError("Service JTMS non disponible", "SERVICE_UNAVAILABLE", 503)
    
    def _cache_key(self, *args) -> str:
        """Génère une clé de cache."""
        return "|".join(str(arg) for arg in args)
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Récupère une valeur du cache."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._cache_ttl:
                return value
            else:
                del self._cache[key]
        return None
    
    def _set_cache(self, key: str, value: Any):
        """Met en cache une valeur."""
        self._cache[key] = (value, datetime.now())
    
    # API des Sessions
    
    async def create_session(self, session_id: str = None, name: str = None, 
                           description: str = "") -> SessionResponse:
        """
        Crée une nouvelle session JTMS.
        
        Args:
            session_id: ID unique de la session (auto-généré si non fourni)
            name: Nom de la session
            description: Description de la session
            
        Returns:
            SessionResponse: Données de la session créée
        """
        self._get_services()
        
        if not session_id:
            session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        if not name:
            name = f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        try:
            # Créer la session via le service backend
            if self.session_manager:
                await self.session_manager.create_session(session_id, name, description)
            
            # Créer la réponse
            response = SessionResponse(
                session_id=session_id,
                name=name,
                description=description,
                created_at=datetime.now().isoformat(),
                last_modified=datetime.now().isoformat(),
                belief_count=0,
                justification_count=0,
                status="active"
            )
            
            # Notifier via WebSocket
            if self.websocket_manager:
                self.websocket_manager.broadcast_to_session(
                    session_id, "session_created", response.to_dict()
                )
            
            logger.info(f"Session JTMS créée: {session_id}")
            return response
            
        except Exception as e:
            logger.error(f"Erreur création session {session_id}: {e}")
            raise APIError(f"Erreur création session: {str(e)}", "SESSION_CREATION_ERROR")
    
    async def get_sessions(self) -> List[SessionResponse]:
        """
        Récupère toutes les sessions JTMS.
        
        Returns:
            List[SessionResponse]: Liste des sessions
        """
        self._get_services()
        
        cache_key = self._cache_key("sessions", "all")
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            sessions = []
            
            if self.session_manager:
                # Récupérer depuis le backend
                backend_sessions = await self.session_manager.list_sessions()
                
                for session_data in backend_sessions:
                    session = SessionResponse(
                        session_id=session_data.get('session_id', ''),
                        name=session_data.get('name', 'Session sans nom'),
                        description=session_data.get('description', ''),
                        created_at=session_data.get('created_at', datetime.now().isoformat()),
                        last_modified=session_data.get('last_modified', datetime.now().isoformat()),
                        belief_count=session_data.get('belief_count', 0),
                        justification_count=session_data.get('justification_count', 0),
                        status=session_data.get('status', 'active'),
                        metadata=session_data.get('metadata', {})
                    )
                    sessions.append(session)
            
            self._set_cache(cache_key, sessions)
            return sessions
            
        except Exception as e:
            logger.error(f"Erreur récupération sessions: {e}")
            raise APIError(f"Erreur récupération sessions: {str(e)}", "SESSIONS_FETCH_ERROR")
    
    async def get_session(self, session_id: str) -> SessionResponse:
        """
        Récupère une session spécifique.
        
        Args:
            session_id: ID de la session
            
        Returns:
            SessionResponse: Données de la session
        """
        self._get_services()
        
        cache_key = self._cache_key("session", session_id)
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            if self.session_manager:
                session_data = await self.session_manager.get_session(session_id)
                
                if not session_data:
                    raise APIError(f"Session {session_id} non trouvée", "SESSION_NOT_FOUND", 404)
                
                session = SessionResponse(
                    session_id=session_data.get('session_id', session_id),
                    name=session_data.get('name', 'Session sans nom'),
                    description=session_data.get('description', ''),
                    created_at=session_data.get('created_at', datetime.now().isoformat()),
                    last_modified=session_data.get('last_modified', datetime.now().isoformat()),
                    belief_count=session_data.get('belief_count', 0),
                    justification_count=session_data.get('justification_count', 0),
                    status=session_data.get('status', 'active'),
                    metadata=session_data.get('metadata', {})
                )
                
                self._set_cache(cache_key, session)
                return session
            else:
                # Session mock pour développement
                return SessionResponse(
                    session_id=session_id,
                    name=f"Session {session_id}",
                    description="Session de développement",
                    created_at=datetime.now().isoformat(),
                    last_modified=datetime.now().isoformat(),
                    belief_count=0,
                    justification_count=0,
                    status="active"
                )
                
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Erreur récupération session {session_id}: {e}")
            raise APIError(f"Erreur récupération session: {str(e)}", "SESSION_FETCH_ERROR")
    
    # API des Croyances
    
    async def add_belief(self, session_id: str, belief_name: str, 
                        initial_status: BeliefStatus = BeliefStatus.UNKNOWN) -> BeliefResponse:
        """
        Ajoute une croyance à une session.
        
        Args:
            session_id: ID de la session
            belief_name: Nom de la croyance
            initial_status: Statut initial de la croyance
            
        Returns:
            BeliefResponse: Données de la croyance créée
        """
        self._get_services()
        
        try:
            # Ajouter via le service backend
            if self.jtms_service:
                await self.jtms_service.add_belief(session_id, belief_name, initial_status.value)
            
            # Créer la réponse
            response = BeliefResponse(
                name=belief_name,
                status=initial_status,
                justifications=[],
                session_id=session_id,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            
            # Notifier via WebSocket
            if self.websocket_manager:
                self.websocket_manager.broadcast_belief_added(
                    session_id, belief_name, response.to_dict()
                )
            
            # Invalider le cache
            self._invalidate_session_cache(session_id)
            
            logger.info(f"Croyance ajoutée: {belief_name} dans session {session_id}")
            return response
            
        except Exception as e:
            logger.error(f"Erreur ajout croyance {belief_name}: {e}")
            raise APIError(f"Erreur ajout croyance: {str(e)}", "BELIEF_ADD_ERROR")
    
    async def get_beliefs(self, session_id: str) -> List[BeliefResponse]:
        """
        Récupère toutes les croyances d'une session.
        
        Args:
            session_id: ID de la session
            
        Returns:
            List[BeliefResponse]: Liste des croyances
        """
        self._get_services()
        
        cache_key = self._cache_key("beliefs", session_id)
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            beliefs = []
            
            if self.jtms_service:
                backend_beliefs = await self.jtms_service.get_beliefs(session_id)
                
                for belief_data in backend_beliefs:
                    belief = BeliefResponse(
                        name=belief_data.get('name', ''),
                        status=BeliefStatus(belief_data.get('status', 'unknown')),
                        justifications=belief_data.get('justifications', []),
                        session_id=session_id,
                        created_at=belief_data.get('created_at', datetime.now().isoformat()),
                        updated_at=belief_data.get('updated_at', datetime.now().isoformat()),
                        metadata=belief_data.get('metadata', {})
                    )
                    beliefs.append(belief)
            
            self._set_cache(cache_key, beliefs)
            return beliefs
            
        except Exception as e:
            logger.error(f"Erreur récupération croyances session {session_id}: {e}")
            raise APIError(f"Erreur récupération croyances: {str(e)}", "BELIEFS_FETCH_ERROR")
    
    # API de Visualisation
    
    async def get_network_visualization(self, session_id: str) -> NetworkVisualizationData:
        """
        Génère les données de visualisation du réseau JTMS.
        
        Args:
            session_id: ID de la session
            
        Returns:
            NetworkVisualizationData: Données pour la visualisation
        """
        self._get_services()
        
        cache_key = self._cache_key("network", session_id)
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            nodes = []
            edges = []
            statistics = {}
            
            # Récupérer les croyances
            beliefs = await self.get_beliefs(session_id)
            
            # Convertir en nœuds
            for belief in beliefs:
                color = self._get_belief_color(belief.status)
                nodes.append({
                    "id": belief.name,
                    "label": belief.name.replace("_", " ").title(),
                    "color": color,
                    "shape": "box",
                    "status": belief.status.value
                })
            
            # Récupérer les justifications (si disponible)
            if self.jtms_service:
                try:
                    justifications = await self.jtms_service.get_justifications(session_id)
                    
                    for just in justifications:
                        conclusion = just.get('conclusion', '')
                        premises = just.get('premises', [])
                        
                        for premise in premises:
                            edges.append({
                                "from": premise,
                                "to": conclusion,
                                "arrows": "to",
                                "color": "#007bff"
                            })
                            
                except Exception as e:
                    logger.warning(f"Impossible de récupérer les justifications: {e}")
            
            # Calculer les statistiques
            statistics = {
                "total_beliefs": len(beliefs),
                "valid_beliefs": sum(1 for b in beliefs if b.status == BeliefStatus.VALID),
                "invalid_beliefs": sum(1 for b in beliefs if b.status == BeliefStatus.INVALID),
                "unknown_beliefs": sum(1 for b in beliefs if b.status == BeliefStatus.UNKNOWN),
                "total_edges": len(edges),
                "network_density": len(edges) / max(1, len(nodes)) if nodes else 0
            }
            
            # Créer la réponse
            response = NetworkVisualizationData(
                nodes=nodes,
                edges=edges,
                statistics=statistics,
                session_id=session_id,
                generated_at=datetime.now().isoformat()
            )
            
            self._set_cache(cache_key, response)
            return response
            
        except Exception as e:
            logger.error(f"Erreur génération visualisation session {session_id}: {e}")
            raise APIError(f"Erreur génération visualisation: {str(e)}", "VISUALIZATION_ERROR")
    
    def _get_belief_color(self, status: BeliefStatus) -> Dict[str, str]:
        """Retourne la couleur d'un nœud selon le statut de la croyance."""
        colors = {
            BeliefStatus.VALID: {"background": "#28a745", "border": "#1e7e34"},
            BeliefStatus.INVALID: {"background": "#dc3545", "border": "#bd2130"},
            BeliefStatus.UNKNOWN: {"background": "#6c757d", "border": "#545b62"},
            BeliefStatus.INCONSISTENT: {"background": "#ffc107", "border": "#e0a800"}
        }
        return colors.get(status, colors[BeliefStatus.UNKNOWN])
    
    def _invalidate_session_cache(self, session_id: str):
        """Invalide le cache pour une session."""
        keys_to_remove = []
        for key in self._cache.keys():
            if session_id in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._cache[key]
    
    # API de Santé et Diagnostics
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Vérifie l'état de santé des services JTMS.
        
        Returns:
            Dict[str, Any]: État de santé des services
        """
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "services": {
                "jtms_service": "unknown",
                "session_manager": "unknown",
                "websocket_manager": "unknown"
            },
            "cache": {
                "entries": len(self._cache),
                "ttl_minutes": self._cache_ttl.total_seconds() / 60
            }
        }
        
        # Vérifier le service JTMS
        try:
            if self.jtms_service:
                # Test simple - vérifier si le service répond
                test_result = await self.jtms_service.health_check() if hasattr(self.jtms_service, 'health_check') else True
                health_status["services"]["jtms_service"] = "healthy" if test_result else "unhealthy"
            else:
                health_status["services"]["jtms_service"] = "unavailable"
        except Exception as e:
            health_status["services"]["jtms_service"] = f"error: {str(e)}"
        
        # Vérifier le gestionnaire de sessions
        try:
            if self.session_manager:
                health_status["services"]["session_manager"] = "healthy"
            else:
                health_status["services"]["session_manager"] = "unavailable"
        except Exception as e:
            health_status["services"]["session_manager"] = f"error: {str(e)}"
        
        # Vérifier le gestionnaire WebSocket
        try:
            if self.websocket_manager:
                stats = self.websocket_manager.get_client_stats()
                health_status["services"]["websocket_manager"] = "healthy"
                health_status["websocket"] = stats
            else:
                health_status["services"]["websocket_manager"] = "unavailable"
        except Exception as e:
            health_status["services"]["websocket_manager"] = f"error: {str(e)}"
        
        return health_status


# Instance globale de l'API
integration_api = JTMSIntegrationAPI()


def get_integration_api() -> JTMSIntegrationAPI:
    """Retourne l'instance globale de l'API d'intégration."""
    return integration_api


def initialize_integration_api(jtms_service=None, session_manager=None, websocket_manager=None):
    """Initialise l'API d'intégration avec les services fournis."""
    global integration_api
    integration_api = JTMSIntegrationAPI(jtms_service, session_manager, websocket_manager)
    logger.info("API d'intégration JTMS initialisée")


if __name__ == "__main__":
    # Test standalone de l'API
    import asyncio
    
    async def test_api():
        api = JTMSIntegrationAPI()
        
        # Test de santé
        health = await api.health_check()
        print("État de santé:", json.dumps(health, indent=2))
        
        # Test de session mock
        try:
            session = await api.create_session(name="Test Session")
            print("Session créée:", session.to_dict())
            
            # Test d'ajout de croyance
            belief = await api.add_belief(session.session_id, "test_belief")
            print("Croyance ajoutée:", belief.to_dict())
            
        except Exception as e:
            print(f"Erreur test: {e}")
    
    asyncio.run(test_api())