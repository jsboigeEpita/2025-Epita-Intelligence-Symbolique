"""
Modèles Pydantic pour l'API REST JTMS
Définit les schémas de requêtes et réponses pour l'intégration JTMS.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union
from datetime import datetime

# Modèles de base pour les croyances et justifications


class BeliefInfo(BaseModel):
    """Informations sur une croyance."""

    name: str = Field(..., description="Nom unique de la croyance")
    valid: Optional[bool] = Field(
        None, description="Statut de validité (true/false/null)"
    )
    non_monotonic: bool = Field(
        False, description="Indique si la croyance est non-monotone"
    )
    justifications_count: int = Field(0, description="Nombre de justifications")
    implications_count: int = Field(0, description="Nombre d'implications")


class JustificationInfo(BaseModel):
    """Informations sur une justification."""

    in_beliefs: List[str] = Field([], description="Croyances positives (prémisses)")
    out_beliefs: List[str] = Field([], description="Croyances négatives (contraintes)")
    conclusion: str = Field(..., description="Croyance conclusion")
    is_valid: Optional[bool] = Field(None, description="Validité de la justification")


# Modèles de requêtes


class CreateBeliefRequest(BaseModel):
    """Requête de création de croyance."""

    belief_name: str = Field(..., description="Nom unique de la croyance")
    initial_value: Optional[str] = Field(
        "unknown", description="Valeur initiale: 'true', 'false', ou 'unknown'"
    )
    session_id: Optional[str] = Field(None, description="ID de session (optionnel)")
    instance_id: Optional[str] = Field(
        None, description="ID d'instance JTMS (optionnel)"
    )
    agent_id: str = Field("api_client", description="ID de l'agent créateur")


class AddJustificationRequest(BaseModel):
    """Requête d'ajout de justification."""

    in_beliefs: List[str] = Field([], description="Liste des croyances positives")
    out_beliefs: List[str] = Field([], description="Liste des croyances négatives")
    conclusion: str = Field(..., description="Croyance conclusion")
    session_id: Optional[str] = Field(None, description="ID de session (optionnel)")
    instance_id: Optional[str] = Field(
        None, description="ID d'instance JTMS (optionnel)"
    )
    agent_id: str = Field("api_client", description="ID de l'agent créateur")


class SetBeliefValidityRequest(BaseModel):
    """Requête de modification de validité."""

    belief_name: str = Field(..., description="Nom de la croyance")
    validity: bool = Field(..., description="Nouvelle valeur de validité")
    session_id: Optional[str] = Field(None, description="ID de session (optionnel)")
    instance_id: Optional[str] = Field(
        None, description="ID d'instance JTMS (optionnel)"
    )
    agent_id: str = Field("api_client", description="ID de l'agent")


class QueryBeliefsRequest(BaseModel):
    """Requête d'interrogation de croyances."""

    filter_status: str = Field(
        "all",
        description="Filtre: 'valid', 'invalid', 'unknown', 'non_monotonic', 'all'",
    )
    session_id: Optional[str] = Field(None, description="ID de session (optionnel)")
    instance_id: Optional[str] = Field(
        None, description="ID d'instance JTMS (optionnel)"
    )
    agent_id: str = Field("api_client", description="ID de l'agent demandeur")


class ExplainBeliefRequest(BaseModel):
    """Requête d'explication de croyance."""

    belief_name: str = Field(..., description="Nom de la croyance à expliquer")
    session_id: Optional[str] = Field(None, description="ID de session (optionnel)")
    instance_id: Optional[str] = Field(
        None, description="ID d'instance JTMS (optionnel)"
    )
    agent_id: str = Field("api_client", description="ID de l'agent demandeur")


class GetJTMSStateRequest(BaseModel):
    """Requête d'état complet JTMS."""

    include_graph: bool = Field(True, description="Inclure le graphe de justifications")
    include_statistics: bool = Field(True, description="Inclure les statistiques")
    session_id: Optional[str] = Field(None, description="ID de session (optionnel)")
    instance_id: Optional[str] = Field(
        None, description="ID d'instance JTMS (optionnel)"
    )
    agent_id: str = Field("api_client", description="ID de l'agent demandeur")


# Modèles de sessions


class CreateSessionRequest(BaseModel):
    """Requête de création de session."""

    agent_id: str = Field(..., description="ID de l'agent")
    session_name: Optional[str] = Field(
        None, description="Nom descriptif de la session"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        {}, description="Métadonnées additionnelles"
    )


class CreateCheckpointRequest(BaseModel):
    """Requête de création de checkpoint."""

    session_id: str = Field(..., description="ID de la session")
    description: Optional[str] = Field(None, description="Description du checkpoint")


class RestoreCheckpointRequest(BaseModel):
    """Requête de restauration de checkpoint."""

    session_id: str = Field(..., description="ID de la session")
    checkpoint_id: str = Field(..., description="ID du checkpoint à restaurer")


class UpdateSessionMetadataRequest(BaseModel):
    """Requête de mise à jour de métadonnées de session."""

    session_id: str = Field(..., description="ID de la session")
    metadata: Dict[str, Any] = Field(..., description="Nouvelles métadonnées")


# Modèles de réponses


class JTMSResponse(BaseModel):
    """Réponse de base pour les opérations JTMS."""

    status: str = Field(..., description="Statut de l'opération")
    operation: str = Field(..., description="Type d'opération effectuée")
    session_id: Optional[str] = Field(None, description="ID de session utilisé")
    instance_id: Optional[str] = Field(None, description="ID d'instance utilisé")
    agent_id: str = Field(..., description="ID de l'agent")
    timestamp: str = Field(..., description="Horodatage de l'opération")


class CreateBeliefResponse(JTMSResponse):
    """Réponse de création de croyance."""

    belief: BeliefInfo = Field(..., description="Informations sur la croyance créée")


class AddJustificationResponse(JTMSResponse):
    """Réponse d'ajout de justification."""

    justification: JustificationInfo = Field(
        ..., description="Informations sur la justification ajoutée"
    )
    conclusion_status: Optional[bool] = Field(
        None, description="Nouveau statut de la conclusion"
    )


class ExplainBeliefResponse(JTMSResponse):
    """Réponse d'explication de croyance."""

    belief_name: str = Field(..., description="Nom de la croyance expliquée")
    current_status: Optional[bool] = Field(None, description="Statut actuel")
    non_monotonic: bool = Field(False, description="Indique si non-monotone")
    justifications: List[JustificationInfo] = Field(
        [], description="Liste des justifications"
    )
    explanation_text: str = Field("", description="Explication textuelle")
    natural_language_summary: Optional[str] = Field(
        None, description="Résumé en langage naturel"
    )


class QueryBeliefsResponse(JTMSResponse):
    """Réponse d'interrogation de croyances."""

    total_beliefs: int = Field(0, description="Nombre total de croyances")
    filtered_count: int = Field(0, description="Nombre de croyances filtrées")
    filter_applied: Optional[str] = Field(None, description="Filtre appliqué")
    beliefs: List[BeliefInfo] = Field([], description="Liste des croyances")
    natural_language_summary: Optional[str] = Field(
        None, description="Résumé en langage naturel"
    )


class JTMSStatistics(BaseModel):
    """Statistiques du système JTMS."""

    total_beliefs: int = Field(0, description="Nombre total de croyances")
    valid_beliefs: int = Field(0, description="Croyances vraies")
    invalid_beliefs: int = Field(0, description="Croyances fausses")
    unknown_beliefs: int = Field(0, description="Croyances indéterminées")
    non_monotonic_beliefs: int = Field(0, description="Croyances non-monotones")
    total_justifications: int = Field(0, description="Nombre total de justifications")


class SessionInfo(BaseModel):
    """Informations sur une session."""

    session_id: str = Field(..., description="ID de la session")
    agent_id: str = Field(..., description="ID de l'agent propriétaire")
    session_name: str = Field(..., description="Nom de la session")
    created_at: str = Field(..., description="Date de création")
    last_accessed: str = Field(..., description="Dernier accès")
    checkpoint_count: int = Field(0, description="Nombre de checkpoints")


class GetJTMSStateResponse(JTMSResponse):
    """Réponse d'état complet JTMS."""

    beliefs: Dict[str, Any] = Field({}, description="État des croyances")
    justifications_graph: Optional[List[JustificationInfo]] = Field(
        None, description="Graphe de justifications"
    )
    statistics: Optional[JTMSStatistics] = Field(
        None, description="Statistiques du système"
    )
    session_info: Optional[SessionInfo] = Field(
        None, description="Informations de session"
    )
    natural_language_summary: Optional[str] = Field(
        None, description="Résumé en langage naturel"
    )


class SetBeliefValidityResponse(JTMSResponse):
    """Réponse de modification de validité."""

    belief_name: str = Field(..., description="Nom de la croyance modifiée")
    old_value: Optional[bool] = Field(None, description="Ancienne valeur")
    new_value: bool = Field(..., description="Nouvelle valeur")
    propagation_occurred: bool = Field(
        True, description="Indique si propagation effectuée"
    )


# Modèles de réponses pour les sessions


class CreateSessionResponse(BaseModel):
    """Réponse de création de session."""

    session_id: str = Field(..., description="ID de la session créée")
    agent_id: str = Field(..., description="ID de l'agent")
    session_name: str = Field(..., description="Nom de la session")
    created_at: str = Field(..., description="Date de création")
    status: str = Field("success", description="Statut de l'opération")


class SessionListResponse(BaseModel):
    """Réponse de liste de sessions."""

    sessions: List[SessionInfo] = Field([], description="Liste des sessions")
    total_count: int = Field(0, description="Nombre total de sessions")
    agent_filter: Optional[str] = Field(None, description="Filtre agent appliqué")
    status_filter: Optional[str] = Field(None, description="Filtre statut appliqué")


class CheckpointInfo(BaseModel):
    """Informations sur un checkpoint."""

    checkpoint_id: str = Field(..., description="ID du checkpoint")
    session_id: str = Field(..., description="ID de la session")
    created_at: str = Field(..., description="Date de création")
    description: str = Field(..., description="Description du checkpoint")
    auto_generated: bool = Field(False, description="Checkpoint automatique")
    session_version: int = Field(1, description="Version de session")


class CreateCheckpointResponse(BaseModel):
    """Réponse de création de checkpoint."""

    checkpoint_id: str = Field(..., description="ID du checkpoint créé")
    session_id: str = Field(..., description="ID de la session")
    description: str = Field(..., description="Description du checkpoint")
    created_at: str = Field(..., description="Date de création")
    status: str = Field("success", description="Statut de l'opération")


class RestoreCheckpointResponse(BaseModel):
    """Réponse de restauration de checkpoint."""

    session_id: str = Field(..., description="ID de la session")
    checkpoint_id: str = Field(..., description="ID du checkpoint restauré")
    restored_at: str = Field(..., description="Date de restauration")
    instances_restored: int = Field(0, description="Nombre d'instances restaurées")
    status: str = Field("success", description="Statut de l'opération")


# Modèles d'erreur


class JTMSError(BaseModel):
    """Modèle d'erreur JTMS."""

    error_type: str = Field(..., description="Type d'erreur")
    error_message: str = Field(..., description="Message d'erreur")
    error_details: Optional[Dict[str, Any]] = Field(
        None, description="Détails additionnels"
    )
    operation: Optional[str] = Field(None, description="Opération qui a échoué")
    session_id: Optional[str] = Field(None, description="ID de session concerné")
    instance_id: Optional[str] = Field(None, description="ID d'instance concerné")
    timestamp: str = Field(..., description="Horodatage de l'erreur")


# Modèles pour l'import/export


class ExportJTMSRequest(BaseModel):
    """Requête d'export JTMS."""

    session_id: Optional[str] = Field(None, description="ID de session (optionnel)")
    instance_id: Optional[str] = Field(
        None, description="ID d'instance JTMS (optionnel)"
    )
    format: str = Field("json", description="Format d'export: 'json', 'graphml', 'dot'")
    agent_id: str = Field("api_client", description="ID de l'agent demandeur")


class ImportJTMSRequest(BaseModel):
    """Requête d'import JTMS."""

    session_id: str = Field(..., description="ID de session de destination")
    state_data: str = Field(..., description="Données d'état sérialisées")
    format: str = Field("json", description="Format des données: 'json'")
    agent_id: str = Field("api_client", description="ID de l'agent importateur")


class ExportJTMSResponse(BaseModel):
    """Réponse d'export JTMS."""

    session_id: Optional[str] = Field(None, description="ID de session exporté")
    instance_id: str = Field(..., description="ID d'instance exporté")
    format: str = Field(..., description="Format d'export utilisé")
    exported_data: str = Field(..., description="Données exportées")
    export_timestamp: str = Field(..., description="Horodatage de l'export")
    status: str = Field("success", description="Statut de l'opération")


class ImportJTMSResponse(BaseModel):
    """Réponse d'import JTMS."""

    session_id: str = Field(..., description="ID de session de destination")
    new_instance_id: str = Field(..., description="ID de la nouvelle instance créée")
    format: str = Field(..., description="Format des données importées")
    beliefs_imported: int = Field(0, description="Nombre de croyances importées")
    justifications_imported: int = Field(
        0, description="Nombre de justifications importées"
    )
    import_timestamp: str = Field(..., description="Horodatage de l'import")
    status: str = Field("success", description="Statut de l'opération")


# Modèles de réponse pour le statut du plugin


class PluginStatusResponse(BaseModel):
    """Réponse du statut du plugin."""

    plugin_name: str = Field(..., description="Nom du plugin")
    semantic_kernel_available: bool = Field(
        ..., description="Semantic Kernel disponible"
    )
    functions_count: int = Field(..., description="Nombre de fonctions disponibles")
    functions: List[str] = Field(..., description="Liste des fonctions")
    jtms_service_active: bool = Field(..., description="Service JTMS actif")
    session_manager_active: bool = Field(
        ..., description="Gestionnaire de sessions actif"
    )
    default_session_id: Optional[str] = Field(None, description="Session par défaut")
    default_instance_id: Optional[str] = Field(None, description="Instance par défaut")
