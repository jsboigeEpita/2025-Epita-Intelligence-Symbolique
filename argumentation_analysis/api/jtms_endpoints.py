"""
Endpoints API REST pour l'intégration JTMS
Expose les fonctionnalités du service JTMS via une API REST complète.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List, Optional, Dict, Any
import json
from datetime import datetime
import asyncio

# Import des modèles
from .jtms_models import (
    # Requêtes
    CreateBeliefRequest, AddJustificationRequest, SetBeliefValidityRequest,
    QueryBeliefsRequest, ExplainBeliefRequest, GetJTMSStateRequest,
    CreateSessionRequest, CreateCheckpointRequest, RestoreCheckpointRequest,
    UpdateSessionMetadataRequest, ExportJTMSRequest, ImportJTMSRequest,
    
    # Réponses
    CreateBeliefResponse, AddJustificationResponse, ExplainBeliefResponse,
    QueryBeliefsResponse, GetJTMSStateResponse, SetBeliefValidityResponse,
    CreateSessionResponse, SessionListResponse, CreateCheckpointResponse,
    RestoreCheckpointResponse, ExportJTMSResponse, ImportJTMSResponse,
    PluginStatusResponse, JTMSError,
    
    # Modèles de données
    BeliefInfo, JustificationInfo, SessionInfo, CheckpointInfo, JTMSStatistics
)

# Import des services
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from services.jtms_service import JTMSService
from services.jtms_session_manager import JTMSSessionManager
from plugins.semantic_kernel.jtms_plugin import JTMSSemanticKernelPlugin, create_jtms_plugin

# Router principal pour les endpoints JTMS
jtms_router = APIRouter(prefix="/jtms", tags=["JTMS"])

# Services globaux (seront initialisés au démarrage de l'application)
_jtms_service: Optional[JTMSService] = None
_session_manager: Optional[JTMSSessionManager] = None
_sk_plugin: Optional[JTMSSemanticKernelPlugin] = None

def get_jtms_service() -> JTMSService:
    """Dependency injection pour le service JTMS."""
    global _jtms_service
    if _jtms_service is None:
        _jtms_service = JTMSService()
    return _jtms_service

def get_session_manager() -> JTMSSessionManager:
    """Dependency injection pour le gestionnaire de sessions."""
    global _session_manager, _jtms_service
    if _session_manager is None:
        if _jtms_service is None:
            _jtms_service = JTMSService()
        _session_manager = JTMSSessionManager(_jtms_service)
    return _session_manager

def get_sk_plugin() -> JTMSSemanticKernelPlugin:
    """Dependency injection pour le plugin Semantic Kernel."""
    global _sk_plugin, _jtms_service, _session_manager
    if _sk_plugin is None:
        if _jtms_service is None:
            _jtms_service = JTMSService()
        if _session_manager is None:
            _session_manager = JTMSSessionManager(_jtms_service)
        _sk_plugin = create_jtms_plugin(_jtms_service, _session_manager)
    return _sk_plugin

async def handle_jtms_error(operation: str, error: Exception, **context) -> JTMSError:
    """Gestionnaire d'erreurs centralisé pour les opérations JTMS."""
    error_type = type(error).__name__
    error_message = str(error)
    
    return JTMSError(
        error_type=error_type,
        error_message=error_message,
        error_details=context,
        operation=operation,
        session_id=context.get("session_id"),
        instance_id=context.get("instance_id"),
        timestamp=datetime.now().isoformat()
    )

# ===== ENDPOINTS POUR LES CROYANCES =====

@jtms_router.post("/beliefs", response_model=CreateBeliefResponse)
async def create_belief(
    request: CreateBeliefRequest,
    jtms_service: JTMSService = Depends(get_jtms_service),
    session_manager: JTMSSessionManager = Depends(get_session_manager)
):
    """
    Crée une nouvelle croyance dans le système JTMS.
    
    Gère automatiquement la création de sessions et d'instances si nécessaires.
    """
    try:
        # Assurer la session et instance
        session_id = request.session_id
        instance_id = request.instance_id
        
        if not session_id:
            session_id = await session_manager.create_session(
                agent_id=request.agent_id,
                session_name=f"API_Session_{request.agent_id}",
                metadata={"created_by": "jtms_api", "auto_created": True}
            )
        
        if not instance_id:
            instance_id = await jtms_service.create_jtms_instance(
                session_id=session_id,
                strict_mode=False
            )
            await session_manager.add_jtms_instance_to_session(session_id, instance_id)
        
        # Convertir la valeur initiale
        initial_value = None
        if request.initial_value == "true":
            initial_value = True
        elif request.initial_value == "false":
            initial_value = False
        
        # Créer la croyance
        result = await jtms_service.create_belief(
            instance_id=instance_id,
            belief_name=request.belief_name,
            initial_value=initial_value
        )
        
        # Construire la réponse
        belief_info = BeliefInfo(
            name=result["name"],
            valid=result["valid"],
            non_monotonic=result["non_monotonic"],
            justifications_count=result["justifications_count"],
            implications_count=result["implications_count"]
        )
        
        return CreateBeliefResponse(
            status="success",
            operation="create_belief",
            session_id=session_id,
            instance_id=instance_id,
            agent_id=request.agent_id,
            timestamp=datetime.now().isoformat(),
            belief=belief_info
        )
        
    except Exception as e:
        error = await handle_jtms_error(
            "create_belief", e,
            session_id=request.session_id,
            instance_id=request.instance_id,
            belief_name=request.belief_name
        )
        raise HTTPException(status_code=400, detail=error.dict())

@jtms_router.post("/justifications", response_model=AddJustificationResponse)
async def add_justification(
    request: AddJustificationRequest,
    jtms_service: JTMSService = Depends(get_jtms_service),
    session_manager: JTMSSessionManager = Depends(get_session_manager)
):
    """
    Ajoute une justification (règle de déduction) au système JTMS.
    """
    try:
        # Assurer la session et instance
        session_id = request.session_id
        instance_id = request.instance_id
        
        if not session_id:
            session_id = await session_manager.create_session(
                agent_id=request.agent_id,
                session_name=f"API_Session_{request.agent_id}",
                metadata={"created_by": "jtms_api", "auto_created": True}
            )
        
        if not instance_id:
            instance_id = await jtms_service.create_jtms_instance(
                session_id=session_id,
                strict_mode=False
            )
            await session_manager.add_jtms_instance_to_session(session_id, instance_id)
        
        # Ajouter la justification
        result = await jtms_service.add_justification(
            instance_id=instance_id,
            in_beliefs=request.in_beliefs,
            out_beliefs=request.out_beliefs,
            conclusion=request.conclusion
        )
        
        # Construire la réponse
        justification_info = JustificationInfo(
            in_beliefs=result["in_beliefs"],
            out_beliefs=result["out_beliefs"],
            conclusion=result["conclusion"]
        )
        
        return AddJustificationResponse(
            status="success",
            operation="add_justification",
            session_id=session_id,
            instance_id=instance_id,
            agent_id=request.agent_id,
            timestamp=datetime.now().isoformat(),
            justification=justification_info,
            conclusion_status=result["conclusion_status"]
        )
        
    except Exception as e:
        error = await handle_jtms_error(
            "add_justification", e,
            session_id=request.session_id,
            instance_id=request.instance_id,
            conclusion=request.conclusion
        )
        raise HTTPException(status_code=400, detail=error.dict())

@jtms_router.post("/beliefs/validity", response_model=SetBeliefValidityResponse)
async def set_belief_validity(
    request: SetBeliefValidityRequest,
    jtms_service: JTMSService = Depends(get_jtms_service)
):
    """
    Définit la validité d'une croyance et propage les changements.
    """
    try:
        if not request.instance_id:
            raise ValueError("Instance ID requis pour cette opération")
        
        result = await jtms_service.set_belief_validity(
            instance_id=request.instance_id,
            belief_name=request.belief_name,
            validity=request.validity
        )
        
        return SetBeliefValidityResponse(
            status="success",
            operation="set_belief_validity",
            session_id=request.session_id,
            instance_id=request.instance_id,
            agent_id=request.agent_id,
            timestamp=datetime.now().isoformat(),
            belief_name=result["belief_name"],
            old_value=result["old_value"],
            new_value=result["new_value"],
            propagation_occurred=result["propagation_occurred"]
        )
        
    except Exception as e:
        error = await handle_jtms_error(
            "set_belief_validity", e,
            session_id=request.session_id,
            instance_id=request.instance_id,
            belief_name=request.belief_name
        )
        raise HTTPException(status_code=400, detail=error.dict())

@jtms_router.post("/beliefs/explain", response_model=ExplainBeliefResponse)
async def explain_belief(
    request: ExplainBeliefRequest,
    jtms_service: JTMSService = Depends(get_jtms_service)
):
    """
    Génère une explication détaillée pour une croyance donnée.
    """
    try:
        if not request.instance_id:
            raise ValueError("Instance ID requis pour cette opération")
        
        result = await jtms_service.explain_belief(
            instance_id=request.instance_id,
            belief_name=request.belief_name
        )
        
        # Convertir les justifications
        justifications = [
            JustificationInfo(
                in_beliefs=[b["name"] for b in j["in_beliefs"]],
                out_beliefs=[b["name"] for b in j["out_beliefs"]],
                conclusion=j["conclusion"],
                is_valid=j["is_valid"]
            )
            for j in result["justifications"]
        ]
        
        return ExplainBeliefResponse(
            status="success",
            operation="explain_belief",
            session_id=request.session_id,
            instance_id=request.instance_id,
            agent_id=request.agent_id,
            timestamp=datetime.now().isoformat(),
            belief_name=result["belief_name"],
            current_status=result["current_status"],
            non_monotonic=result["non_monotonic"],
            justifications=justifications,
            explanation_text=result["explanation_text"],
            natural_language_summary=f"La croyance '{request.belief_name}' est actuellement " +
                                   ("vraie" if result["current_status"] is True else 
                                    "fausse" if result["current_status"] is False else "inconnue")
        )
        
    except Exception as e:
        error = await handle_jtms_error(
            "explain_belief", e,
            session_id=request.session_id,
            instance_id=request.instance_id,
            belief_name=request.belief_name
        )
        raise HTTPException(status_code=400, detail=error.dict())

@jtms_router.post("/beliefs/query", response_model=QueryBeliefsResponse)
async def query_beliefs(
    request: QueryBeliefsRequest,
    jtms_service: JTMSService = Depends(get_jtms_service)
):
    """
    Interroge et filtre les croyances selon leur statut.
    """
    try:
        if not request.instance_id:
            raise ValueError("Instance ID requis pour cette opération")
        
        # Valider le filtre
        valid_filters = ["valid", "invalid", "unknown", "non_monotonic", "all"]
        if request.filter_status not in valid_filters:
            raise ValueError(f"Filtre invalide: {request.filter_status}")
        
        filter_param = None if request.filter_status == "all" else request.filter_status
        
        result = await jtms_service.query_beliefs(
            instance_id=request.instance_id,
            filter_status=filter_param
        )
        
        # Convertir les croyances
        beliefs = [
            BeliefInfo(
                name=b["name"],
                valid=b["valid"],
                non_monotonic=b["non_monotonic"],
                justifications_count=b["justifications_count"],
                implications_count=b["implications_count"]
            )
            for b in result["beliefs"]
        ]
        
        return QueryBeliefsResponse(
            status="success",
            operation="query_beliefs",
            session_id=request.session_id,
            instance_id=request.instance_id,
            agent_id=request.agent_id,
            timestamp=datetime.now().isoformat(),
            total_beliefs=result["total_beliefs"],
            filtered_count=result["filtered_count"],
            filter_applied=result["filter_applied"],
            beliefs=beliefs,
            natural_language_summary=f"Trouvé {result['filtered_count']} croyances avec le filtre '{request.filter_status}'"
        )
        
    except Exception as e:
        error = await handle_jtms_error(
            "query_beliefs", e,
            session_id=request.session_id,
            instance_id=request.instance_id,
            filter_status=request.filter_status
        )
        raise HTTPException(status_code=400, detail=error.dict())

@jtms_router.post("/state", response_model=GetJTMSStateResponse)
async def get_jtms_state(
    request: GetJTMSStateRequest,
    jtms_service: JTMSService = Depends(get_jtms_service),
    session_manager: JTMSSessionManager = Depends(get_session_manager)
):
    """
    Récupère l'état complet du système JTMS.
    """
    try:
        if not request.instance_id:
            raise ValueError("Instance ID requis pour cette opération")
        
        result = await jtms_service.get_jtms_state(instance_id=request.instance_id)
        
        # Récupérer les informations de session si disponibles
        session_info = None
        if request.session_id:
            try:
                session_data = await session_manager.get_session(request.session_id)
                session_info = SessionInfo(
                    session_id=session_data["session_id"],
                    agent_id=session_data["agent_id"],
                    session_name=session_data["session_name"],
                    created_at=session_data["created_at"],
                    last_accessed=session_data["last_accessed"],
                    checkpoint_count=session_data.get("checkpoint_count", 0)
                )
            except:
                pass  # Session info optionnelle
        
        # Construire les justifications si demandées
        justifications_graph = None
        if request.include_graph and "justifications_graph" in result:
            justifications_graph = [
                JustificationInfo(
                    in_beliefs=j["in_beliefs"],
                    out_beliefs=j["out_beliefs"],
                    conclusion=j["conclusion"]
                )
                for j in result["justifications_graph"]
            ]
        
        # Construire les statistiques si demandées
        statistics = None
        if request.include_statistics and "statistics" in result:
            stats = result["statistics"]
            statistics = JTMSStatistics(
                total_beliefs=stats["total_beliefs"],
                valid_beliefs=stats["valid_beliefs"],
                invalid_beliefs=stats["invalid_beliefs"],
                unknown_beliefs=stats["unknown_beliefs"],
                non_monotonic_beliefs=stats["non_monotonic_beliefs"],
                total_justifications=stats["total_justifications"]
            )
        
        return GetJTMSStateResponse(
            status="success",
            operation="get_jtms_state",
            session_id=request.session_id,
            instance_id=request.instance_id,
            agent_id=request.agent_id,
            timestamp=datetime.now().isoformat(),
            beliefs=result["beliefs"],
            justifications_graph=justifications_graph,
            statistics=statistics,
            session_info=session_info,
            natural_language_summary=f"État JTMS contenant {len(result['beliefs'])} croyances"
        )
        
    except Exception as e:
        error = await handle_jtms_error(
            "get_jtms_state", e,
            session_id=request.session_id,
            instance_id=request.instance_id
        )
        raise HTTPException(status_code=400, detail=error.dict())

# ===== ENDPOINTS POUR LES SESSIONS =====

@jtms_router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(
    request: CreateSessionRequest,
    session_manager: JTMSSessionManager = Depends(get_session_manager)
):
    """
    Crée une nouvelle session JTMS pour un agent.
    """
    try:
        session_id = await session_manager.create_session(
            agent_id=request.agent_id,
            session_name=request.session_name,
            metadata=request.metadata
        )
        
        session_data = await session_manager.get_session(session_id)
        
        return CreateSessionResponse(
            session_id=session_id,
            agent_id=session_data["agent_id"],
            session_name=session_data["session_name"],
            created_at=session_data["created_at"],
            status="success"
        )
        
    except Exception as e:
        error = await handle_jtms_error(
            "create_session", e,
            agent_id=request.agent_id
        )
        raise HTTPException(status_code=400, detail=error.dict())

@jtms_router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    agent_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    session_manager: JTMSSessionManager = Depends(get_session_manager)
):
    """
    Liste les sessions selon les critères spécifiés.
    """
    try:
        sessions_data = await session_manager.list_sessions(
            agent_id=agent_id,
            status=status_filter
        )
        
        sessions = [
            SessionInfo(
                session_id=s["session_id"],
                agent_id=s["agent_id"],
                session_name=s["session_name"],
                created_at=s["created_at"],
                last_accessed=s["last_accessed"],
                checkpoint_count=s.get("checkpoint_count", 0)
            )
            for s in sessions_data
        ]
        
        return SessionListResponse(
            sessions=sessions,
            total_count=len(sessions),
            agent_filter=agent_id,
            status_filter=status_filter
        )
        
    except Exception as e:
        error = await handle_jtms_error(
            "list_sessions", e,
            agent_id=agent_id,
            status_filter=status_filter
        )
        raise HTTPException(status_code=400, detail=error.dict())

@jtms_router.post("/sessions/checkpoints", response_model=CreateCheckpointResponse)
async def create_checkpoint(
    request: CreateCheckpointRequest,
    session_manager: JTMSSessionManager = Depends(get_session_manager)
):
    """
    Crée un checkpoint pour une session.
    """
    try:
        checkpoint_id = await session_manager.create_checkpoint(
            session_id=request.session_id,
            description=request.description
        )
        
        return CreateCheckpointResponse(
            checkpoint_id=checkpoint_id,
            session_id=request.session_id,
            description=request.description or f"Checkpoint {datetime.now().strftime('%H:%M:%S')}",
            created_at=datetime.now().isoformat(),
            status="success"
        )
        
    except Exception as e:
        error = await handle_jtms_error(
            "create_checkpoint", e,
            session_id=request.session_id
        )
        raise HTTPException(status_code=400, detail=error.dict())

@jtms_router.post("/sessions/restore", response_model=RestoreCheckpointResponse)
async def restore_checkpoint(
    request: RestoreCheckpointRequest,
    session_manager: JTMSSessionManager = Depends(get_session_manager)
):
    """
    Restaure une session à partir d'un checkpoint.
    """
    try:
        success = await session_manager.restore_checkpoint(
            session_id=request.session_id,
            checkpoint_id=request.checkpoint_id
        )
        
        if not success:
            raise ValueError("Échec de la restauration du checkpoint")
        
        # Compter les instances restaurées
        session_data = await session_manager.get_session(request.session_id)
        instances_count = len(session_data.get("jtms_instances", []))
        
        return RestoreCheckpointResponse(
            session_id=request.session_id,
            checkpoint_id=request.checkpoint_id,
            restored_at=datetime.now().isoformat(),
            instances_restored=instances_count,
            status="success"
        )
        
    except Exception as e:
        error = await handle_jtms_error(
            "restore_checkpoint", e,
            session_id=request.session_id,
            checkpoint_id=request.checkpoint_id
        )
        raise HTTPException(status_code=400, detail=error.dict())

# ===== ENDPOINTS POUR L'IMPORT/EXPORT =====

@jtms_router.post("/export", response_model=ExportJTMSResponse)
async def export_jtms_state(
    request: ExportJTMSRequest,
    jtms_service: JTMSService = Depends(get_jtms_service)
):
    """
    Exporte l'état d'une instance JTMS.
    """
    try:
        if not request.instance_id:
            raise ValueError("Instance ID requis pour l'export")
        
        exported_data = await jtms_service.export_jtms_state(
            instance_id=request.instance_id,
            format=request.format
        )
        
        return ExportJTMSResponse(
            session_id=request.session_id,
            instance_id=request.instance_id,
            format=request.format,
            exported_data=exported_data,
            export_timestamp=datetime.now().isoformat(),
            status="success"
        )
        
    except Exception as e:
        error = await handle_jtms_error(
            "export_jtms_state", e,
            session_id=request.session_id,
            instance_id=request.instance_id
        )
        raise HTTPException(status_code=400, detail=error.dict())

@jtms_router.post("/import", response_model=ImportJTMSResponse)
async def import_jtms_state(
    request: ImportJTMSRequest,
    jtms_service: JTMSService = Depends(get_jtms_service)
):
    """
    Importe un état JTMS dans une session.
    """
    try:
        new_instance_id = await jtms_service.import_jtms_state(
            session_id=request.session_id,
            state_data=request.state_data,
            format=request.format
        )
        
        # Compter les éléments importés
        state = await jtms_service.get_jtms_state(new_instance_id)
        beliefs_count = len(state["beliefs"])
        justifications_count = len(state.get("justifications_graph", []))
        
        return ImportJTMSResponse(
            session_id=request.session_id,
            new_instance_id=new_instance_id,
            format=request.format,
            beliefs_imported=beliefs_count,
            justifications_imported=justifications_count,
            import_timestamp=datetime.now().isoformat(),
            status="success"
        )
        
    except Exception as e:
        error = await handle_jtms_error(
            "import_jtms_state", e,
            session_id=request.session_id
        )
        raise HTTPException(status_code=400, detail=error.dict())

# ===== ENDPOINTS POUR LE PLUGIN SEMANTIC KERNEL =====

@jtms_router.get("/plugin/status", response_model=PluginStatusResponse)
async def get_plugin_status(
    sk_plugin: JTMSSemanticKernelPlugin = Depends(get_sk_plugin)
):
    """
    Récupère le statut du plugin Semantic Kernel.
    """
    try:
        status = await sk_plugin.get_plugin_status()
        
        return PluginStatusResponse(
            plugin_name=status["plugin_name"],
            semantic_kernel_available=status["semantic_kernel_available"],
            functions_count=status["functions_count"],
            functions=status["functions"],
            jtms_service_active=status["jtms_service_active"],
            session_manager_active=status["session_manager_active"],
            default_session_id=status["default_session_id"],
            default_instance_id=status["default_instance_id"]
        )
        
    except Exception as e:
        error = await handle_jtms_error("get_plugin_status", e)
        raise HTTPException(status_code=500, detail=error.dict())

# ===== ENDPOINTS DE CONVENANCE POUR LES FONCTIONS SK =====

@jtms_router.post("/sk/create_belief")
async def sk_create_belief(
    belief_name: str,
    initial_value: str = "unknown",
    session_id: str = "",
    instance_id: str = "",
    agent_id: str = "api_client",
    sk_plugin: JTMSSemanticKernelPlugin = Depends(get_sk_plugin)
):
    """
    Endpoint de convenance pour la fonction SK create_belief.
    """
    try:
        result = await sk_plugin.create_belief(
            belief_name=belief_name,
            initial_value=initial_value,
            session_id=session_id,
            instance_id=instance_id,
            agent_id=agent_id
        )
        return {"result": json.loads(result)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@jtms_router.post("/sk/add_justification")
async def sk_add_justification(
    in_beliefs: str,
    out_beliefs: str,
    conclusion: str,
    session_id: str = "",
    instance_id: str = "",
    agent_id: str = "api_client",
    sk_plugin: JTMSSemanticKernelPlugin = Depends(get_sk_plugin)
):
    """
    Endpoint de convenance pour la fonction SK add_justification.
    """
    try:
        result = await sk_plugin.add_justification(
            in_beliefs=in_beliefs,
            out_beliefs=out_beliefs,
            conclusion=conclusion,
            session_id=session_id,
            instance_id=instance_id,
            agent_id=agent_id
        )
        return {"result": json.loads(result)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@jtms_router.post("/sk/explain_belief")
async def sk_explain_belief(
    belief_name: str,
    session_id: str = "",
    instance_id: str = "",
    agent_id: str = "api_client",
    sk_plugin: JTMSSemanticKernelPlugin = Depends(get_sk_plugin)
):
    """
    Endpoint de convenance pour la fonction SK explain_belief.
    """
    try:
        result = await sk_plugin.explain_belief(
            belief_name=belief_name,
            session_id=session_id,
            instance_id=instance_id,
            agent_id=agent_id
        )
        return {"result": json.loads(result)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@jtms_router.post("/sk/query_beliefs")
async def sk_query_beliefs(
    filter_status: str = "all",
    session_id: str = "",
    instance_id: str = "",
    agent_id: str = "api_client",
    sk_plugin: JTMSSemanticKernelPlugin = Depends(get_sk_plugin)
):
    """
    Endpoint de convenance pour la fonction SK query_beliefs.
    """
    try:
        result = await sk_plugin.query_beliefs(
            filter_status=filter_status,
            session_id=session_id,
            instance_id=instance_id,
            agent_id=agent_id
        )
        return {"result": json.loads(result)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@jtms_router.post("/sk/get_jtms_state")
async def sk_get_jtms_state(
    include_graph: str = "true",
    include_statistics: str = "true",
    session_id: str = "",
    instance_id: str = "",
    agent_id: str = "api_client",
    sk_plugin: JTMSSemanticKernelPlugin = Depends(get_sk_plugin)
):
    """
    Endpoint de convenance pour la fonction SK get_jtms_state.
    """
    try:
        result = await sk_plugin.get_jtms_state(
            include_graph=include_graph,
            include_statistics=include_statistics,
            session_id=session_id,
            instance_id=instance_id,
            agent_id=agent_id
        )
        return {"result": json.loads(result)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Fonction d'initialisation pour configurer les services globaux
async def initialize_jtms_services():
    """
    Initialise les services JTMS globaux.
    À appeler au démarrage de l'application FastAPI.
    """
    global _jtms_service, _session_manager, _sk_plugin
    
    _jtms_service = JTMSService()
    _session_manager = JTMSSessionManager(_jtms_service)
    _sk_plugin = create_jtms_plugin(_jtms_service, _session_manager)
    
    # Nettoyage automatique des sessions expirées
    async def cleanup_expired_sessions():
        while True:
            try:
                await asyncio.sleep(3600)  # Chaque heure
                await _session_manager.cleanup_expired_sessions()
            except Exception:
                pass  # Ignore les erreurs de nettoyage
    
    # Lancer la tâche de nettoyage en arrière-plan
    asyncio.create_task(cleanup_expired_sessions())