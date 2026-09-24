from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Optional

from .fallacy_detection import FallacyTier


class AnalysisOptions(BaseModel):
    """What ``POST /api/analyze`` computes besides the structure (#2526)."""

    model_config = ConfigDict(extra="forbid")

    detect_fallacies: bool = Field(
        default=False,
        description="Run the pipeline's fallacy detector (an LLM call for the "
        "``llm`` tier: a key, and tens of seconds).",
    )
    fallacy_tier: FallacyTier = "llm"


class AnalysisRequest(BaseModel):
    text: str
    options: AnalysisOptions = Field(default_factory=AnalysisOptions)


class StatusResponse(BaseModel):
    status: str
    service_status: Dict


class Example(BaseModel):
    title: str
    text: str
    type: str


class ExampleResponse(BaseModel):
    examples: List[Example]


# --- Modèles pour l'analyse de Framework d'Argumentation de Dung ---


class FrameworkAnalysisOptions(BaseModel):
    """Options pour l'analyse du framework."""

    semantics: str = "preferred"
    compute_extensions: bool = True
    include_visualization: bool = False


class FrameworkAnalysisRequest(BaseModel):
    """
    Modèle de requête pour l'analyse d'un framework d'argumentation.
    """

    arguments: List[str]
    attacks: List[List[str]]  # e.g., [["a", "b"], ["b", "c"]]
    options: Optional[FrameworkAnalysisOptions] = None


class ArgumentStatus(BaseModel):
    """Statut d'un argument individuel."""

    credulously_accepted: bool
    skeptically_accepted: bool
    grounded_accepted: bool
    stable_accepted: bool


class GraphProperties(BaseModel):
    """Propriétés structurelles du graphe d'argumentation."""

    num_arguments: int
    num_attacks: int
    has_cycles: bool
    cycles: List[List[str]]
    self_attacking_nodes: List[str]


class Extensions(BaseModel):
    """Conteneur pour toutes les extensions sémantiques."""

    grounded: List[str]
    preferred: List[List[str]]
    stable: List[List[str]]
    complete: List[List[str]]
    admissible: List[List[str]]
    ideal: List[str]
    semi_stable: List[List[str]]


class FrameworkAnalysisResult(BaseModel):
    """Contient les résultats détaillés de l'analyse du framework."""

    extensions: Optional[Extensions] = None
    argument_status: Dict[str, ArgumentStatus]
    graph_properties: GraphProperties


class FrameworkAnalysisResponse(BaseModel):
    """
    Modèle de réponse pour l'analyse complète du framework, enveloppé dans une clé 'analysis'.
    """

    analysis: FrameworkAnalysisResult


# --- Modèles pour le service d'analyse de sophismes informels (Facade) ---


class InformalAnalysisRequest(BaseModel):
    """
    Modèle de requête pour le service d'analyse de sophismes informels.
    """

    text: str
    strategy: Optional[str] = "auto"


class InformalAnalysisResponse(BaseModel):
    """
    Modèle de réponse pour le service d'analyse de sophismes informels.
    """

    status: str
    strategy: str
    result: Dict
