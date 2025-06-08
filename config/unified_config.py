<<<<<<< MAIN
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration dynamique unifiée pour le système d'analyse rhétorique.

Ce module centralise tous les paramètres configurables pour permettre :
- Choix du type de logique (FOL/PL/Modal)
- Sélection des agents actifs
- Type d'orchestration
- Niveau de mocking (none/partial/full)
- Source d'analyse (Simple/Encrypted/File)
- Validation d'authenticité 100%

Objectif : Éliminer complètement les mocks et garantir des traces authentiques.
"""

import os
import enum
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path

# ==================== ÉNUMÉRATIONS ====================

class LogicType(enum.Enum):
    """Types de logique supportés pour l'analyse formelle."""
    MODAL = "modal"
    FOL = "fol"  # First-Order Logic (défaut recommandé)
    PL = "pl"    # Propositional Logic
    FIRST_ORDER = "first_order"  # Alias pour FOL

class MockLevel(enum.Enum):
    """Niveaux de mocking du système."""
    NONE = "none"        # Aucun mock - Authenticité 100%
    PARTIAL = "partial"  # Mocks limités pour développement
    FULL = "full"        # Tous les services mockés

class OrchestrationType(enum.Enum):
    """Types d'orchestration disponibles."""
    UNIFIED = "unified"           # Orchestration standard unifiée
    CONVERSATION = "conversation" # Orchestration conversationnelle
    CUSTOM = "custom"            # Orchestration personnalisée
    REAL = "real"                # Orchestration réelle (legacy)

class SourceType(enum.Enum):
    """Types de sources d'analyse."""
    SIMPLE = "simple"       # Source de démonstration
    ENCRYPTED = "encrypted" # Corpus chiffré
    FILE = "file"          # Fichier personnalisé
    COMPLEX = "complex"    # Alias pour encrypted

class TaxonomySize(enum.Enum):
    """Tailles de taxonomie disponibles."""
    FULL = "full"    # 1000 nœuds - Taxonomie complète
    MOCK = "mock"    # 3 nœuds - Taxonomie simplifiée pour tests

class AgentType(enum.Enum):
    """Types d'agents disponibles."""
    INFORMAL = "informal"
    LOGIC = "logic"
    FOL_LOGIC = "fol_logic"
    SYNTHESIS = "synthesis"
    EXTRACT = "extract"
    PM = "pm"

# ==================== CONFIGURATION PRINCIPALE ====================

@dataclass
class UnifiedConfig:
    """Configuration dynamique unifiée du système."""
    
    # === Configuration de base ===
    logic_type: LogicType = LogicType.FOL
    agents: List[AgentType] = field(default_factory=lambda: [
        AgentType.INFORMAL, 
        AgentType.FOL_LOGIC, 
        AgentType.SYNTHESIS
    ])
    orchestration_type: OrchestrationType = OrchestrationType.UNIFIED
    mock_level: MockLevel = MockLevel.NONE
    taxonomy_size: TaxonomySize = TaxonomySize.FULL
    
    # === Paramètres d'analyse ===
    analysis_modes: List[str] = field(default_factory=lambda: [
        "fallacies", "coherence", "semantic"
    ])
    enable_advanced_tools: bool = True
    enable_jvm: bool = True
    require_real_llm: bool = True  # Force l'utilisation de vrais LLM
    
    # === Configuration de source ===
    source_type: SourceType = SourceType.SIMPLE
    source_file: Optional[str] = None
    passphrase: Optional[str] = None
    passphrase_env_var: str = "TEXT_CONFIG_PASSPHRASE"
    
    # === Configuration de sortie ===
    output_format: str = "markdown"
    output_template: str = "default"
    output_mode: str = "both"
    output_path: Optional[str] = None
    
    # === Validation d'authenticité ===
    require_real_gpt: bool = True      # Force GPT-4o-mini réel
    require_real_tweety: bool = True   # Force Tweety JAR authentique
    require_full_taxonomy: bool = True # Force taxonomie 1000 nœuds
    validate_tool_calls: bool = True   # Valide l'authenticité des tool calls
    
    # === Logging et debug ===
    log_level: str = "INFO"
    enable_conversation_logging: bool = True
    enable_trace_validation: bool = True
    verbose: bool = False
    
    # === Performance ===
    timeout_seconds: int = 300
    max_retries: int = 3
    enable_cache: bool = False  # Désactivé pour authenticité

    def __post_init__(self):
        """Validation et normalisation de la configuration."""
        self._validate_configuration()
        self._normalize_agent_list()
        self._apply_authenticity_constraints()

    def _validate_configuration(self):
        """Valide la cohérence de la configuration."""
        # Validation du niveau de mock vs authenticité
        if self.mock_level != MockLevel.NONE:
            if self.require_real_gpt or self.require_real_tweety or self.require_full_taxonomy:
                raise ValueError(
                    f"Configuration incohérente: mock_level={self.mock_level.value} "
                    f"mais require_real_* activé. Pour l'authenticité 100%, "
                    f"utilisez mock_level=none."
                )
        
        # Validation agents vs logique
        if self.logic_type == LogicType.FOL and AgentType.LOGIC in self.agents:
            # Remplacer automatiquement par FOL_LOGIC
            self.agents = [AgentType.FOL_LOGIC if a == AgentType.LOGIC else a for a in self.agents]
        
        # Validation JVM vs agents formels
        if AgentType.FOL_LOGIC in self.agents and not self.enable_jvm:
            raise ValueError("FOL_LOGIC agent nécessite enable_jvm=True")

    def _normalize_agent_list(self):
        """Normalise la liste des agents selon le type de logique."""
        if self.logic_type in [LogicType.FOL, LogicType.FIRST_ORDER]:
            # Remplacer les agents logiques génériques par FOL
            self.agents = [
                AgentType.FOL_LOGIC if a == AgentType.LOGIC else a 
                for a in self.agents
            ]

    def _apply_authenticity_constraints(self):
        """Applique les contraintes d'authenticité si demandées."""
        if self.mock_level == MockLevel.NONE:
            # Force l'authenticité complète
            self.require_real_gpt = True
            self.require_real_tweety = True
            self.require_full_taxonomy = True
            self.validate_tool_calls = True
            self.taxonomy_size = TaxonomySize.FULL
            self.enable_cache = False

    def get_agent_classes(self) -> Dict[str, str]:
        """Retourne le mapping des types d'agents vers leurs classes."""
        mapping = {
            AgentType.INFORMAL: "InformalAnalysisAgent",
            AgentType.LOGIC: "ModalLogicAgent",  # Legacy
            AgentType.FOL_LOGIC: "FirstOrderLogicAgent",
            AgentType.SYNTHESIS: "SynthesisAgent",
            AgentType.EXTRACT: "ExtractAgent",
            AgentType.PM: "ProjectManagerAgent"
        }
        
        return {agent.value: mapping[agent] for agent in self.agents}

    def get_tweety_config(self) -> Dict[str, Any]:
        """Configuration spécifique pour TweetyProject."""
        return {
            "enable_jvm": self.enable_jvm,
            "require_real_jar": self.require_real_tweety,
            "logic_type": self.logic_type.value,
            "timeout_seconds": self.timeout_seconds
        }

    def get_llm_config(self) -> Dict[str, Any]:
        """Configuration spécifique pour les services LLM."""
        return {
            "require_real_service": self.require_real_gpt,
            "mock_level": self.mock_level.value,
            "validate_responses": self.validate_tool_calls,
            "timeout_seconds": self.timeout_seconds
        }

    def get_taxonomy_config(self) -> Dict[str, Any]:
        """Configuration spécifique pour la taxonomie."""
        return {
            "size": self.taxonomy_size.value,
            "require_full_load": self.require_full_taxonomy,
            "node_count": 1000 if self.taxonomy_size == TaxonomySize.FULL else 3
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convertit la configuration en dictionnaire."""
        return {
            "logic_type": self.logic_type.value,
            "agents": [agent.value for agent in self.agents],
            "orchestration_type": self.orchestration_type.value,
            "mock_level": self.mock_level.value,
            "taxonomy_size": self.taxonomy_size.value,
            "analysis_modes": self.analysis_modes,
            "enable_advanced_tools": self.enable_advanced_tools,
            "enable_jvm": self.enable_jvm,
            "require_real_llm": self.require_real_llm,
            "source_type": self.source_type.value,
            "output_format": self.output_format,
            "authenticity": {
                "require_real_gpt": self.require_real_gpt,
                "require_real_tweety": self.require_real_tweety,
                "require_full_taxonomy": self.require_full_taxonomy,
                "validate_tool_calls": self.validate_tool_calls
            }
        }

# ==================== CONFIGURATIONS PRÉDÉFINIES ====================

class PresetConfigs:
    """Configurations prédéfinies pour différents cas d'usage."""
    
    @staticmethod
    def authentic_fol() -> UnifiedConfig:
        """Configuration authentique avec logique FOL."""
        return UnifiedConfig(
            logic_type=LogicType.FOL,
            agents=[AgentType.INFORMAL, AgentType.FOL_LOGIC, AgentType.SYNTHESIS],
            orchestration_type=OrchestrationType.UNIFIED,
            mock_level=MockLevel.NONE,
            taxonomy_size=TaxonomySize.FULL,
            require_real_gpt=True,
            require_real_tweety=True,
            require_full_taxonomy=True
        )
    
    @staticmethod
    def authentic_pl() -> UnifiedConfig:
        """Configuration authentique avec logique propositionnelle."""
        return UnifiedConfig(
            logic_type=LogicType.PL,
            agents=[AgentType.INFORMAL, AgentType.FOL_LOGIC, AgentType.SYNTHESIS],
            orchestration_type=OrchestrationType.UNIFIED,
            mock_level=MockLevel.NONE,
            taxonomy_size=TaxonomySize.FULL
        )
    
    @staticmethod
    def development() -> UnifiedConfig:
        """Configuration pour développement avec mocks partiels."""
        return UnifiedConfig(
            logic_type=LogicType.PL,
            agents=[AgentType.INFORMAL, AgentType.SYNTHESIS],
            orchestration_type=OrchestrationType.UNIFIED,
            mock_level=MockLevel.PARTIAL,
            taxonomy_size=TaxonomySize.MOCK,
            enable_jvm=False,
            require_real_gpt=False,
            require_real_tweety=False,
            require_full_taxonomy=False
        )
    
    @staticmethod
    def testing() -> UnifiedConfig:
        """Configuration pour tests automatisés."""
        return UnifiedConfig(
            logic_type=LogicType.PL,
            agents=[AgentType.INFORMAL, AgentType.SYNTHESIS],
            orchestration_type=OrchestrationType.UNIFIED,
            mock_level=MockLevel.FULL,
            taxonomy_size=TaxonomySize.MOCK,
            enable_jvm=False,
            require_real_gpt=False,      # Cohérent avec mock_level=FULL
            require_real_tweety=False,   # Cohérent avec mock_level=FULL
            require_full_taxonomy=False, # Cohérent avec taxonomy_size=MOCK
            timeout_seconds=30
        )

# ==================== UTILITAIRES ====================

def load_config_from_env() -> UnifiedConfig:
    """Charge la configuration depuis les variables d'environnement."""
    config = UnifiedConfig()
    
    # Configuration de base
    if logic_type := os.getenv("UNIFIED_LOGIC_TYPE"):
        config.logic_type = LogicType(logic_type)
    
    if agents_str := os.getenv("UNIFIED_AGENTS"):
        config.agents = [AgentType(agent.strip()) for agent in agents_str.split(",")]
    
    if orch_type := os.getenv("UNIFIED_ORCHESTRATION"):
        config.orchestration_type = OrchestrationType(orch_type)
    
    if mock_level := os.getenv("UNIFIED_MOCK_LEVEL"):
        config.mock_level = MockLevel(mock_level)
    
    # Authenticity flags
    if os.getenv("UNIFIED_REQUIRE_REAL_GPT", "").lower() == "true":
        config.require_real_gpt = True
    
    if os.getenv("UNIFIED_REQUIRE_REAL_TWEETY", "").lower() == "true":
        config.require_real_tweety = True
    
    return config

def validate_config(config: UnifiedConfig) -> List[str]:
    """Valide une configuration et retourne les erreurs trouvées."""
    errors = []
    
    # Vérification de cohérence mock vs authenticité
    if config.mock_level != MockLevel.NONE and config.require_real_gpt:
        errors.append("Mock level != none mais require_real_gpt=True")
    
    # Vérification disponibilité JVM
    if config.enable_jvm and not config.require_real_tweety:
        errors.append("JVM activée mais Tweety non-réel - Incohérent pour authenticité")
    
    # Vérification agents vs logique
    fol_agents = [AgentType.FOL_LOGIC, AgentType.LOGIC]
    if any(agent in config.agents for agent in fol_agents) and not config.enable_jvm:
        errors.append("Agents logiques nécessitent JVM")
    
    return errors

# ==================== EXPORT ====================

__all__ = [
    "UnifiedConfig",
    "LogicType", 
    "MockLevel",
    "OrchestrationType",
    "SourceType",
    "TaxonomySize",
    "AgentType",
    "PresetConfigs",
    "load_config_from_env",
    "validate_config"
]

=======
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration dynamique unifiée pour le système d'analyse rhétorique.

Ce module centralise tous les paramètres configurables pour permettre :
- Choix du type de logique (FOL/PL/Modal)
- Sélection des agents actifs
- Type d'orchestration
- Niveau de mocking (none/partial/full)
- Source d'analyse (Simple/Encrypted/File)
- Validation d'authenticité 100%

Objectif : Éliminer complètement les mocks et garantir des traces authentiques.
"""

import os
import enum
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path

# ==================== ÉNUMÉRATIONS ====================

class LogicType(enum.Enum):
    """Types de logique supportés pour l'analyse formelle."""
    MODAL = "modal"
    FOL = "fol"  # First-Order Logic (défaut recommandé)
    PL = "pl"    # Propositional Logic
    FIRST_ORDER = "first_order"  # Alias pour FOL

class MockLevel(enum.Enum):
    """Niveaux de mocking du système."""
    NONE = "none"        # Aucun mock - Authenticité 100%
    PARTIAL = "partial"  # Mocks limités pour développement
    FULL = "full"        # Tous les services mockés

class OrchestrationType(enum.Enum):
    """Types d'orchestration disponibles."""
    UNIFIED = "unified"           # Orchestration standard unifiée
    CONVERSATION = "conversation" # Orchestration conversationnelle
    CUSTOM = "custom"            # Orchestration personnalisée
    REAL = "real"                # Orchestration réelle (legacy)

class SourceType(enum.Enum):
    """Types de sources d'analyse."""
    SIMPLE = "simple"       # Source de démonstration
    ENCRYPTED = "encrypted" # Corpus chiffré
    FILE = "file"          # Fichier personnalisé
    COMPLEX = "complex"    # Alias pour encrypted

class TaxonomySize(enum.Enum):
    """Tailles de taxonomie disponibles."""
    FULL = "full"    # 1000 nœuds - Taxonomie complète
    MOCK = "mock"    # 3 nœuds - Taxonomie simplifiée pour tests

class AgentType(enum.Enum):
    """Types d'agents disponibles."""
    INFORMAL = "informal"
    LOGIC = "logic"
    FOL_LOGIC = "fol_logic"
    SYNTHESIS = "synthesis"
    EXTRACT = "extract"
    PM = "pm"

# ==================== CONFIGURATION PRINCIPALE ====================

@dataclass
class UnifiedConfig:
    """Configuration dynamique unifiée du système."""
    
    # === Configuration de base ===
    logic_type: LogicType = LogicType.FOL
    agents: List[AgentType] = field(default_factory=lambda: [
        AgentType.INFORMAL, 
        AgentType.FOL_LOGIC, 
        AgentType.SYNTHESIS
    ])
    orchestration_type: OrchestrationType = OrchestrationType.UNIFIED
    mock_level: MockLevel = MockLevel.NONE
    taxonomy_size: TaxonomySize = TaxonomySize.FULL
    
    # === Paramètres d'analyse ===
    analysis_modes: List[str] = field(default_factory=lambda: [
        "fallacies", "coherence", "semantic"
    ])
    enable_advanced_tools: bool = True
    enable_jvm: bool = True
    require_real_llm: bool = True  # Force l'utilisation de vrais LLM
    
    # === Configuration de source ===
    source_type: SourceType = SourceType.SIMPLE
    source_file: Optional[str] = None
    passphrase: Optional[str] = None
    passphrase_env_var: str = "TEXT_CONFIG_PASSPHRASE"
    
    # === Configuration de sortie ===
    output_format: str = "markdown"
    output_template: str = "default"
    output_mode: str = "both"
    output_path: Optional[str] = None
    
    # === Validation d'authenticité ===
    require_real_gpt: bool = True      # Force GPT-4o-mini réel
    require_real_tweety: bool = True   # Force Tweety JAR authentique
    require_full_taxonomy: bool = True # Force taxonomie 1000 nœuds
    validate_tool_calls: bool = True   # Valide l'authenticité des tool calls
    
    # === Logging et debug ===
    log_level: str = "INFO"
    enable_conversation_logging: bool = True
    enable_trace_validation: bool = True
    verbose: bool = False
    
    # === Performance ===
    timeout_seconds: int = 300
    max_retries: int = 3
    enable_cache: bool = False  # Désactivé pour authenticité

    def __post_init__(self):
        """Validation et normalisation de la configuration."""
        self._validate_configuration()
        self._normalize_agent_list()
        self._apply_authenticity_constraints()

    def _validate_configuration(self):
        """Valide la cohérence de la configuration."""
        # Validation du niveau de mock vs authenticité
        if self.mock_level != MockLevel.NONE:
            if self.require_real_gpt or self.require_real_tweety or self.require_full_taxonomy:
                raise ValueError(
                    f"Configuration incohérente: mock_level={self.mock_level.value} "
                    f"mais require_real_* activé. Pour l'authenticité 100%, "
                    f"utilisez mock_level=none."
                )
        
        # Validation agents vs logique
        if self.logic_type == LogicType.FOL and AgentType.LOGIC in self.agents:
            # Remplacer automatiquement par FOL_LOGIC
            self.agents = [AgentType.FOL_LOGIC if a == AgentType.LOGIC else a for a in self.agents]
        
        # Validation JVM vs agents formels
        if AgentType.FOL_LOGIC in self.agents and not self.enable_jvm:
            raise ValueError("FOL_LOGIC agent nécessite enable_jvm=True")

    def _normalize_agent_list(self):
        """Normalise la liste des agents selon le type de logique."""
        if self.logic_type in [LogicType.FOL, LogicType.FIRST_ORDER]:
            # Remplacer les agents logiques génériques par FOL
            self.agents = [
                AgentType.FOL_LOGIC if a == AgentType.LOGIC else a 
                for a in self.agents
            ]

    def _apply_authenticity_constraints(self):
        """Applique les contraintes d'authenticité si demandées."""
        if self.mock_level == MockLevel.NONE:
            # Force l'authenticité complète
            self.require_real_gpt = True
            self.require_real_tweety = True
            self.require_full_taxonomy = True
            self.validate_tool_calls = True
            self.taxonomy_size = TaxonomySize.FULL
            self.enable_cache = False

    def get_agent_classes(self) -> Dict[str, str]:
        """Retourne le mapping des types d'agents vers leurs classes."""
        mapping = {
            AgentType.INFORMAL: "InformalAnalysisAgent",
            AgentType.LOGIC: "ModalLogicAgent",  # Legacy
            AgentType.FOL_LOGIC: "FirstOrderLogicAgent",
            AgentType.SYNTHESIS: "SynthesisAgent",
            AgentType.EXTRACT: "ExtractAgent",
            AgentType.PM: "ProjectManagerAgent"
        }
        
        return {agent.value: mapping[agent] for agent in self.agents}

    def get_tweety_config(self) -> Dict[str, Any]:
        """Configuration spécifique pour TweetyProject."""
        return {
            "enable_jvm": self.enable_jvm,
            "require_real_jar": self.require_real_tweety,
            "logic_type": self.logic_type.value,
            "timeout_seconds": self.timeout_seconds
        }

    def get_llm_config(self) -> Dict[str, Any]:
        """Configuration spécifique pour les services LLM."""
        return {
            "require_real_service": self.require_real_gpt,
            "mock_level": self.mock_level.value,
            "validate_responses": self.validate_tool_calls,
            "timeout_seconds": self.timeout_seconds
        }

    def get_taxonomy_config(self) -> Dict[str, Any]:
        """Configuration spécifique pour la taxonomie."""
        return {
            "size": self.taxonomy_size.value,
            "require_full_load": self.require_full_taxonomy,
            "node_count": 1000 if self.taxonomy_size == TaxonomySize.FULL else 3
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convertit la configuration en dictionnaire."""
        return {
            "logic_type": self.logic_type.value,
            "agents": [agent.value for agent in self.agents],
            "orchestration_type": self.orchestration_type.value,
            "mock_level": self.mock_level.value,
            "taxonomy_size": self.taxonomy_size.value,
            "analysis_modes": self.analysis_modes,
            "enable_advanced_tools": self.enable_advanced_tools,
            "enable_jvm": self.enable_jvm,
            "require_real_llm": self.require_real_llm,
            "source_type": self.source_type.value,
            "output_format": self.output_format,
            "authenticity": {
                "require_real_gpt": self.require_real_gpt,
                "require_real_tweety": self.require_real_tweety,
                "require_full_taxonomy": self.require_full_taxonomy,
                "validate_tool_calls": self.validate_tool_calls
            }
        }

# ==================== CONFIGURATIONS PRÉDÉFINIES ====================

class PresetConfigs:
    """Configurations prédéfinies pour différents cas d'usage."""
    
    @staticmethod
    def authentic_fol() -> UnifiedConfig:
        """Configuration authentique avec logique FOL."""
        return UnifiedConfig(
            logic_type=LogicType.FOL,
            agents=[AgentType.INFORMAL, AgentType.FOL_LOGIC, AgentType.SYNTHESIS],
            orchestration_type=OrchestrationType.UNIFIED,
            mock_level=MockLevel.NONE,
            taxonomy_size=TaxonomySize.FULL,
            require_real_gpt=True,
            require_real_tweety=True,
            require_full_taxonomy=True
        )
    
    @staticmethod
    def authentic_pl() -> UnifiedConfig:
        """Configuration authentique avec logique propositionnelle."""
        return UnifiedConfig(
            logic_type=LogicType.PL,
            agents=[AgentType.INFORMAL, AgentType.FOL_LOGIC, AgentType.SYNTHESIS],
            orchestration_type=OrchestrationType.UNIFIED,
            mock_level=MockLevel.NONE,
            taxonomy_size=TaxonomySize.FULL
        )
    
    @staticmethod
    def development() -> UnifiedConfig:
        """Configuration pour développement avec mocks partiels."""
        return UnifiedConfig(
            logic_type=LogicType.PL,
            agents=[AgentType.INFORMAL, AgentType.SYNTHESIS],
            orchestration_type=OrchestrationType.UNIFIED,
            mock_level=MockLevel.PARTIAL,
            taxonomy_size=TaxonomySize.MOCK,
            enable_jvm=False,
            require_real_gpt=False,
            require_real_tweety=False,
            require_full_taxonomy=False
        )
    
    @staticmethod
    def testing() -> UnifiedConfig:
        """Configuration pour tests automatisés."""
        return UnifiedConfig(
            logic_type=LogicType.PL,
            agents=[AgentType.INFORMAL, AgentType.SYNTHESIS],
            orchestration_type=OrchestrationType.UNIFIED,
            mock_level=MockLevel.FULL,
            taxonomy_size=TaxonomySize.MOCK,
            enable_jvm=False,
            require_real_gpt=False,      # Cohérent avec mock_level=FULL
            require_real_tweety=False,   # Cohérent avec mock_level=FULL
            require_full_taxonomy=False, # Cohérent avec taxonomy_size=MOCK
            timeout_seconds=30
        )

# ==================== UTILITAIRES ====================

def load_config_from_env() -> UnifiedConfig:
    """Charge la configuration depuis les variables d'environnement."""
    config = UnifiedConfig()
    
    # Configuration de base
    if logic_type := os.getenv("UNIFIED_LOGIC_TYPE"):
        config.logic_type = LogicType(logic_type)
    
    if agents_str := os.getenv("UNIFIED_AGENTS"):
        config.agents = [AgentType(agent.strip()) for agent in agents_str.split(",")]
    
    if orch_type := os.getenv("UNIFIED_ORCHESTRATION"):
        config.orchestration_type = OrchestrationType(orch_type)
    
    if mock_level := os.getenv("UNIFIED_MOCK_LEVEL"):
        config.mock_level = MockLevel(mock_level)
    
    # Authenticity flags
    if os.getenv("UNIFIED_REQUIRE_REAL_GPT", "").lower() == "true":
        config.require_real_gpt = True
    
    if os.getenv("UNIFIED_REQUIRE_REAL_TWEETY", "").lower() == "true":
        config.require_real_tweety = True
    
    return config

def validate_config(config: UnifiedConfig) -> List[str]:
    """Valide une configuration et retourne les erreurs trouvées."""
    errors = []
    
    # Vérification de cohérence mock vs authenticité
    if config.mock_level != MockLevel.NONE and config.require_real_gpt:
        errors.append("Mock level != none mais require_real_gpt=True")
    
    # Vérification disponibilité JVM
    if config.enable_jvm and not config.require_real_tweety:
        errors.append("JVM activée mais Tweety non-réel - Incohérent pour authenticité")
    
    # Vérification agents vs logique
    fol_agents = [AgentType.FOL_LOGIC, AgentType.LOGIC]
    if any(agent in config.agents for agent in fol_agents) and not config.enable_jvm:
        errors.append("Agents logiques nécessitent JVM")
    
    return errors

# ==================== EXPORT ====================

__all__ = [
    "UnifiedConfig",
    "LogicType", 
    "MockLevel",
    "OrchestrationType",
    "SourceType",
    "TaxonomySize",
    "AgentType",
    "PresetConfigs",
    "load_config_from_env",
    "validate_config"
]
>>>>>>> BACKUP
