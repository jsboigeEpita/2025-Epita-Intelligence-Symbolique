#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration dynamique unifiée pour le système d'analyse rhétorique.

Ce module centralise tous les paramètres configurables pour permettre :
- Choix du type de logique (FOL/PL/Modal)
- Sélection des agents actifs
- Type d'orchestration
- Niveau de mocking (none/partial/full - AUTHENTICITÉ PAR DÉFAUT)
- Source d'analyse (Simple/Encrypted/File)
- Validation d'authenticité 100%

Objectif : Système authentique par défaut avec gpt-4o-mini et OpenAI.
TOUT EST CONFIGURÉ POUR L'AUTHENTICITÉ : Aucun mock par défaut.
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
    require_real_llm: bool = True  # Force l'utilisation de vrais LLM - AUTHENTIQUE PAR DÉFAUT
    
    # === Configuration LLM/Provider (AUTHENTICITÉ PAR DÉFAUT) ===
    default_model: str = "gpt-4o-mini"  # Modèle OpenAI par défaut - AUTHENTIQUE
    default_provider: str = "openai"    # Provider OpenAI par défaut - AUTHENTIQUE
    use_mock_llm: bool = False          # Désactivé par défaut - AUTHENTICITÉ
    use_authentic_llm: bool = True      # Activé par défaut - AUTHENTICITÉ
    
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
    
    # === Validation d'authenticité (TOUT AUTHENTIQUE PAR DÉFAUT) ===
    require_real_gpt: bool = True      # Force GPT-4o-mini réel - AUTHENTIQUE PAR DÉFAUT
    require_real_tweety: bool = True   # Force Tweety JAR authentique - AUTHENTIQUE PAR DÉFAUT
    require_full_taxonomy: bool = True # Force taxonomie 1000 nœuds - AUTHENTIQUE PAR DÉFAUT
    validate_tool_calls: bool = True   # Valide l'authenticité des tool calls - AUTHENTIQUE PAR DÉFAUT
    use_mock_services: bool = False    # Tous les services sont authentiques par défaut
    use_authentic_services: bool = True # Force les services authentiques par défaut
    
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
        """Applique les contraintes d'authenticité - AUTHENTICITÉ PAR DÉFAUT."""
        if self.mock_level == MockLevel.NONE:
            # Force l'authenticité complète - CONFIGURATION PAR DÉFAUT
            self.require_real_gpt = True
            self.require_real_tweety = True
            self.require_full_taxonomy = True
            self.validate_tool_calls = True
            self.taxonomy_size = TaxonomySize.FULL
            self.enable_cache = False
            self.use_mock_llm = False
            self.use_authentic_llm = True
            self.use_mock_services = False
            self.use_authentic_services = True
            self.default_model = "gpt-4o-mini"
            self.default_provider = "openai"

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
        """Configuration spécifique pour les services LLM - AUTHENTIQUE PAR DÉFAUT."""
        return {
            "require_real_service": self.require_real_gpt,
            "mock_level": self.mock_level.value,
            "validate_responses": self.validate_tool_calls,
            "timeout_seconds": self.timeout_seconds,
            "default_model": self.default_model,      # gpt-4o-mini par défaut
            "default_provider": self.default_provider, # openai par défaut
            "use_mock_llm": self.use_mock_llm,        # False par défaut
            "use_authentic_llm": self.use_authentic_llm # True par défaut
        }

    def get_taxonomy_config(self) -> Dict[str, Any]:
        """Configuration spécifique pour la taxonomie."""
        return {
            "size": self.taxonomy_size.value,
            "require_full_load": self.require_full_taxonomy,
            "node_count": 1000 if self.taxonomy_size == TaxonomySize.FULL else 3
        }

    def get_kernel_with_gpt4o_mini(self):
        """
        Crée un Kernel Semantic Kernel avec service LLM GPT-4o-mini authentique.
        
        Cette méthode est le pont principal entre UnifiedConfig et le service LLM réel.
        Elle respecte la configuration d'authenticité (mock_level=NONE par défaut).
        
        Returns:
            Kernel: Instance Semantic Kernel configurée avec GPT-4o-mini authentique
            
        Raises:
            ValueError: Si la configuration est incohérente pour l'authenticité
            RuntimeError: Si la création du service LLM échoue
        """
        from semantic_kernel import Kernel
        from argumentation_analysis.core.llm_service import create_llm_service
        
        # Validation d'authenticité stricte
        if self.mock_level != MockLevel.NONE:
            raise ValueError(
                f"get_kernel_with_gpt4o_mini() nécessite mock_level=NONE pour l'authenticité. "
                f"Trouvé: {self.mock_level.value}"
            )
        
        if not self.use_authentic_llm:
            raise ValueError(
                "get_kernel_with_gpt4o_mini() nécessite use_authentic_llm=True pour l'authenticité"
            )
        
        if self.use_mock_llm:
            raise ValueError(
                "get_kernel_with_gpt4o_mini() est incompatible avec use_mock_llm=True"
            )
        
        # Création du Kernel avec service LLM authentique
        kernel = Kernel()
        
        # Service LLM GPT-4o-mini authentique (jamais de mock)
        llm_service = create_llm_service(
            service_id="gpt-4o-mini-authentic",
            force_mock=False  # Force l'authenticité
        )
        
        # Ajout du service au kernel
        kernel.add_service(llm_service)
        
        # Log validation authenticité
        import logging
        logger = logging.getLogger("UnifiedConfig.Authentic")
        logger.info(f"✅ Kernel authentique créé - Service: {type(llm_service).__name__}")
        logger.info(f"✅ Model: {self.default_model}, Provider: {self.default_provider}")
        logger.info(f"✅ MockLevel: {self.mock_level.value}, Authentique: {self.use_authentic_llm}")
        
        return kernel

    def to_dict(self) -> Dict[str, Any]:
        """Convertit la configuration en dictionnaire."""
        return {
            "logic_type": self.logic_type.value,
            "agents": [agent.value for agent in self.agents],
            "orchestration_type": self.orchestration_type.value if hasattr(self.orchestration_type, 'value') else self.orchestration_type,
            "mock_level": self.mock_level.value,
            "taxonomy_size": self.taxonomy_size.value,
            "analysis_modes": self.analysis_modes,
            "enable_advanced_tools": self.enable_advanced_tools,
            "enable_jvm": self.enable_jvm,
            "require_real_llm": self.require_real_llm,
            "source_type": self.source_type.value,
            "output_format": self.output_format,
            "llm_config": {
                "default_model": self.default_model,
                "default_provider": self.default_provider,
                "use_mock_llm": self.use_mock_llm,
                "use_authentic_llm": self.use_authentic_llm
            },
            "authenticity": {
                "require_real_gpt": self.require_real_gpt,
                "require_real_tweety": self.require_real_tweety,
                "require_full_taxonomy": self.require_full_taxonomy,
                "validate_tool_calls": self.validate_tool_calls,
                "use_mock_services": self.use_mock_services,
                "use_authentic_services": self.use_authentic_services
            }
        }

# ==================== CONFIGURATIONS PRÉDÉFINIES ====================

class PresetConfigs:
    """Configurations prédéfinies pour différents cas d'usage."""
    
    @staticmethod
    def authentic_fol() -> UnifiedConfig:
        """Configuration authentique avec logique FOL - AUTHENTIQUE PAR DÉFAUT."""
        return UnifiedConfig(
            logic_type=LogicType.FOL,
            agents=[AgentType.INFORMAL, AgentType.FOL_LOGIC, AgentType.SYNTHESIS],
            orchestration_type=OrchestrationType.UNIFIED,
            mock_level=MockLevel.NONE,
            taxonomy_size=TaxonomySize.FULL,
            require_real_gpt=True,
            require_real_tweety=True,
            require_full_taxonomy=True,
            default_model="gpt-4o-mini",
            default_provider="openai",
            use_mock_llm=False,
            use_authentic_llm=True
        )
    
    @staticmethod
    def authentic_pl() -> UnifiedConfig:
        """Configuration authentique avec logique propositionnelle - AUTHENTIQUE PAR DÉFAUT."""
        return UnifiedConfig(
            logic_type=LogicType.PL,
            agents=[AgentType.INFORMAL, AgentType.FOL_LOGIC, AgentType.SYNTHESIS],
            orchestration_type=OrchestrationType.UNIFIED,
            mock_level=MockLevel.NONE,
            taxonomy_size=TaxonomySize.FULL,
            default_model="gpt-4o-mini",
            default_provider="openai",
            use_mock_llm=False,
            use_authentic_llm=True
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
    """Charge la configuration depuis les variables d'environnement - AUTHENTIQUE PAR DÉFAUT."""
    config = UnifiedConfig()  # Déjà configuré avec authenticité par défaut
    
    # Configuration de base
    if logic_type := os.getenv("UNIFIED_LOGIC_TYPE"):
        config.logic_type = LogicType(logic_type)
    
    if agents_str := os.getenv("UNIFIED_AGENTS"):
        config.agents = [AgentType(agent.strip()) for agent in agents_str.split(",")]
    
    if orch_type := os.getenv("UNIFIED_ORCHESTRATION"):
        config.orchestration_type = OrchestrationType(orch_type)
    
    if mock_level := os.getenv("UNIFIED_MOCK_LEVEL"):
        config.mock_level = MockLevel(mock_level)
    
    # Configuration LLM - AUTHENTIQUE PAR DÉFAUT
    config.default_model = os.getenv("UNIFIED_DEFAULT_MODEL", "gpt-4o-mini")
    config.default_provider = os.getenv("UNIFIED_DEFAULT_PROVIDER", "openai")
    
    # Flags d'authenticité - TRUE PAR DÉFAUT, peut être surchargé par l'env
    config.require_real_gpt = os.getenv("UNIFIED_REQUIRE_REAL_GPT", "true").lower() == "true"
    config.require_real_tweety = os.getenv("UNIFIED_REQUIRE_REAL_TWEETY", "true").lower() == "true"
    config.use_mock_llm = os.getenv("UNIFIED_USE_MOCK_LLM", "false").lower() == "true"
    config.use_authentic_llm = os.getenv("UNIFIED_USE_AUTHENTIC_LLM", "true").lower() == "true"
    config.use_mock_services = os.getenv("UNIFIED_USE_MOCK_SERVICES", "false").lower() == "true"
    config.use_authentic_services = os.getenv("UNIFIED_USE_AUTHENTIC_SERVICES", "true").lower() == "true"
    
    return config

def validate_config(config: UnifiedConfig) -> List[str]:
    """Valide une configuration et retourne les erreurs trouvées - AUTHENTIQUE PAR DÉFAUT."""
    errors = []
    
    # Vérification de cohérence mock vs authenticité
    if config.mock_level != MockLevel.NONE and config.require_real_gpt:
        errors.append("Mock level != none mais require_real_gpt=True")
    
    # Vérification de cohérence des flags LLM
    if config.use_mock_llm and config.use_authentic_llm:
        errors.append("use_mock_llm et use_authentic_llm ne peuvent pas être tous les deux True")
    
    if config.use_mock_services and config.use_authentic_services:
        errors.append("use_mock_services et use_authentic_services ne peuvent pas être tous les deux True")
    
    # Vérification modèle par défaut
    if config.default_model != "gpt-4o-mini":
        errors.append(f"default_model devrait être 'gpt-4o-mini' pour l'authenticité, trouvé: {config.default_model}")
    
    # Vérification provider par défaut
    if config.default_provider != "openai":
        errors.append(f"default_provider devrait être 'openai' pour l'authenticité, trouvé: {config.default_provider}")
    
    # Vérification disponibilité JVM
    if config.enable_jvm and not config.require_real_tweety:
        errors.append("JVM activée mais Tweety non-réel - Incohérent pour authenticité")
    
    # Vérification agents vs logique
    fol_agents = [AgentType.FOL_LOGIC, AgentType.LOGIC]
    if any(agent in config.agents for agent in fol_agents) and not config.enable_jvm:
        errors.append("Agents logiques nécessitent JVM")
    
    # Vérification authenticité complète pour mock_level=NONE
    if config.mock_level == MockLevel.NONE:
        authenticity_checks = [
            (config.use_mock_llm == False, "use_mock_llm devrait être False pour mock_level=NONE"),
            (config.use_authentic_llm == True, "use_authentic_llm devrait être True pour mock_level=NONE"),
            (config.use_mock_services == False, "use_mock_services devrait être False pour mock_level=NONE"),
            (config.use_authentic_services == True, "use_authentic_services devrait être True pour mock_level=NONE"),
            (config.require_real_gpt == True, "require_real_gpt devrait être True pour mock_level=NONE"),
            (config.require_real_tweety == True, "require_real_tweety devrait être True pour mock_level=NONE")
        ]
        
        for check, error_msg in authenticity_checks:
            if not check:
                errors.append(error_msg)
    
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
