from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

class OrchestrationRequest(BaseModel):
    """
    Modèle pour les requêtes envoyées à l'OrchestrationService.
    Définit le contrat d'entrée pour toute interaction avec le guichet de service.
    """
    mode: Literal["direct_plugin_call", "workflow_execution"] = Field(
        ...,
        description="Le mode opérationnel qui détermine comment la requête sera traitée."
    )
    target: str = Field(
        ...,
        description="La cible de l'exécution. Pour le mode 'direct_plugin_call', il s'agit de 'plugin_name.capability_name'."
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Les arguments ou données à passer à la cible."
    )
    session_id: Optional[str] = Field(
        None,
        description="Identifiant de session optionnel pour les interactions avec état."
    )

class OrchestrationResponse(BaseModel):
    """
    Modèle pour les réponses retournées par l'OrchestrationService.
    Définit le contrat de sortie standardisé.
    """
    status: Literal["success", "error"] = Field(
        ...,
        description="Indique si l'exécution a réussi ou échoué."
    )
    result: Optional[Dict[str, Any]] = Field(
        None,
        description="Le dictionnaire contenant les données de sortie en cas de succès."
    )
    error_message: Optional[str] = Field(
        None,
        description="Un message décrivant l'erreur en cas d'échec."
    )

class Capability(BaseModel):
    """
    Définit une capacité unique d'un plugin, avec ses schémas d'entrée/sortie.
    """
    name: str = Field(..., description="Nom de la capacité.")
    description: str = Field(..., description="Description de ce que fait la capacité.")
    input_schema: Dict[str, Any] = Field(..., alias="input", description="Schéma JSON de l'objet d'entrée attendu.")
    output_schema: Dict[str, Any] = Field(..., alias="output", description="Schéma JSON de l'objet de sortie produit.")

class PluginManifest(BaseModel):
    """
    Modèle pour le fichier de manifeste 'plugin.yaml'.
    """
    manifest_version: str = Field(..., description="Version du schéma du manifeste.")
    plugin_name: str = Field(..., description="Nom unique du plugin.")
    plugin_type: Literal["WORKFLOW", "STANDARD"] = Field(..., description="Type de plugin, 'WORKFLOW' pour orchestrer d'autres plugins, 'STANDARD' pour une tâche atomique.")
    version: str = Field(..., description="Version sémantique du plugin.")
    description: str = Field(..., description="Description du rôle du plugin.")
    entrypoint: str = Field(..., description="Chemin d'importation vers la classe principale du plugin (ex: 'my_plugin.main.MyPlugin').")
    dependencies: List[str] = Field(default_factory=list, description="Liste des noms de plugins requis par ce plugin.")
    capabilities: List[Capability] = Field(..., description="Liste des capacités fournies par ce plugin.")


# Nouveaux modèles pour le benchmarking

class BenchmarkResult(BaseModel):
    """
    Enregistre le résultat d'une seule exécution dans une suite de benchmarks.
    """
    request_id: str = Field(..., description="ID de la requête d'orchestration associée.")
    is_success: bool = Field(..., description="True si l'exécution a réussi, False sinon.")
    duration_ms: float = Field(..., description="Temps d'exécution de la requête en millisecondes.")
    output: Optional[Dict[str, Any]] = Field(None, description="Sortie de l'exécution en cas de succès.")
    error: Optional[str] = Field(None, description="Message d'erreur en cas d'échec.")
    custom_metrics: Dict[str, Any] = Field(default_factory=dict, description="Métrique personnalisée pour cette exécution, ex: nombre de tokens.")

class BenchmarkSuiteResult(BaseModel):
    """
    Agrège les résultats d'une suite de benchmarks pour une capacité de plugin.
    """
    plugin_name: str = Field(..., description="Nom du plugin benchmarké.")
    capability_name: str = Field(..., description="Nom de la capacité benchmarkée.")
    total_runs: int = Field(..., description="Nombre total d'exécutions dans la suite.")
    successful_runs: int = Field(..., description="Nombre d'exécutions réussies.")
    failed_runs: int = Field(..., description="Nombre d'exécutions échouées.")
    
    total_duration_ms: float = Field(..., description="Durée totale de toutes les exécutions en millisecondes.")
    average_duration_ms: float = Field(..., description="Durée moyenne d'une exécution réussie en millisecondes.")
    min_duration_ms: float = Field(..., description="Durée minimale d'une exécution réussie en millisecondes.")
    max_duration_ms: float = Field(..., description="Durée maximale d'une exécution réussie en millisecondes.")
    
    results: List[BenchmarkResult] = Field(..., description="Liste détaillée des résultats de chaque exécution.")
    aggregated_custom_metrics: Dict[str, Any] = Field(default_factory=dict, description="Agrégation des métriques personnalisées sur toute la suite.")
