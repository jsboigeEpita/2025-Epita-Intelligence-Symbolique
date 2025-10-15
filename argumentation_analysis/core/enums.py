import enum


class OrchestrationMode(enum.Enum):
    """Modes d'orchestration disponibles."""

    # Modes de base (compatibilité)
    PIPELINE = "pipeline"
    REAL = "real"
    CONVERSATION = "conversation"

    # Modes hiérarchiques
    HIERARCHICAL_FULL = "hierarchical_full"
    STRATEGIC_ONLY = "strategic_only"
    TACTICAL_COORDINATION = "tactical_coordination"
    OPERATIONAL_DIRECT = "operational_direct"

    # Modes spécialisés
    CLUEDO_INVESTIGATION = "cluedo_investigation"
    LOGIC_COMPLEX = "logic_complex"
    ADAPTIVE_HYBRID = "adaptive_hybrid"

    # Mode automatique
    AUTO_SELECT = "auto_select"


class AnalysisType(enum.Enum):
    """Types d'analyse supportés."""

    COMPREHENSIVE = "comprehensive"
    RHETORICAL = "rhetorical"
    LOGICAL = "logical"
    INVESTIGATIVE = "investigative"
    FALLACY_FOCUSED = "fallacy_focused"
    ARGUMENT_STRUCTURE = "argument_structure"
    DEBATE_ANALYSIS = "debate_analysis"
    CUSTOM = "custom"
