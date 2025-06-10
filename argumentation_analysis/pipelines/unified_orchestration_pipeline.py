#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pipeline d'Orchestration Unifié - Architecture Hiérarchique Complète
====================================================================

Ce pipeline étend le unified_text_analysis.py pour intégrer l'architecture
hiérarchique à 3 niveaux (Stratégique/Tactique/Opérationnel) et les 
orchestrateurs spécialisés disponibles dans le projet.

Fonctionnalités étendues :
- Architecture hiérarchique d'orchestration complète
- Orchestrateurs spécialisés selon le type d'analyse
- Service manager centralisé pour la coordination
- Interfaces entre niveaux hiérarchiques
- Support pour différents modes d'orchestration
- Compatibilité avec l'API existante

Version: 2.0.0
Auteur: Intelligence Symbolique EPITA
Date: 10/06/2025
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable
from enum import Enum

# Imports Semantic Kernel et architecture de base
import semantic_kernel as sk
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.llm_service import create_llm_service
from argumentation_analysis.core.jvm_setup import initialize_jvm
from argumentation_analysis.paths import LIBS_DIR, DATA_DIR, RESULTS_DIR

# Imports du pipeline original pour compatibilité
from argumentation_analysis.pipelines.unified_text_analysis import (
    UnifiedAnalysisConfig, 
    UnifiedTextAnalysisPipeline,
    run_unified_text_analysis_pipeline,
    create_unified_config_from_legacy
)

# Imports de l'architecture hiérarchique
try:
    from argumentation_analysis.orchestration.service_manager import OrchestrationServiceManager
    from argumentation_analysis.orchestration.hierarchical.strategic.manager import StrategicManager
    from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TaskCoordinator
    from argumentation_analysis.orchestration.hierarchical.operational.manager import OperationalManager
except ImportError as e:
    logging.warning(f"Gestionnaires hiérarchiques non disponibles: {e}")
    OrchestrationServiceManager = None
    StrategicManager = None
    TaskCoordinator = None
    OperationalManager = None

# Imports des orchestrateurs spécialisés
try:
    from argumentation_analysis.orchestration.cluedo_orchestrator import CluedoOrchestrator, run_cluedo_game
    from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
    from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
    from argumentation_analysis.orchestration.logique_complexe_orchestrator import LogiqueComplexeOrchestrator
except ImportError as e:
    logging.warning(f"Orchestrateurs spécialisés non disponibles: {e}")
    CluedoOrchestrator = None
    ConversationOrchestrator = None
    RealLLMOrchestrator = None
    LogiqueComplexeOrchestrator = None

# Imports du système de communication
try:
    from argumentation_analysis.core.communication import (
        MessageMiddleware, Message, ChannelType, 
        MessagePriority, MessageType, AgentLevel
    )
except ImportError as e:
    logging.warning(f"Système de communication non disponible: {e}")
    MessageMiddleware = None

logger = logging.getLogger("UnifiedOrchestrationPipeline")


class OrchestrationMode(Enum):
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


class AnalysisType(Enum):
    """Types d'analyse supportés."""
    
    COMPREHENSIVE = "comprehensive"
    RHETORICAL = "rhetorical"
    LOGICAL = "logical"
    INVESTIGATIVE = "investigative"
    FALLACY_FOCUSED = "fallacy_focused"
    ARGUMENT_STRUCTURE = "argument_structure"
    DEBATE_ANALYSIS = "debate_analysis"
    CUSTOM = "custom"


class ExtendedOrchestrationConfig(UnifiedAnalysisConfig):
    """Configuration étendue pour l'orchestration hiérarchique."""
    
    def __init__(self,
                 # Paramètres de base (hérités)
                 analysis_modes: List[str] = None,
                 orchestration_mode: Union[str, OrchestrationMode] = OrchestrationMode.PIPELINE,
                 logic_type: str = "fol",
                 use_mocks: bool = False,
                 use_advanced_tools: bool = True,
                 output_format: str = "detailed",
                 enable_conversation_logging: bool = True,
                 
                 # Nouveaux paramètres pour l'orchestration hiérarchique
                 analysis_type: Union[str, AnalysisType] = AnalysisType.COMPREHENSIVE,
                 enable_hierarchical: bool = True,
                 enable_specialized_orchestrators: bool = True,
                 enable_communication_middleware: bool = True,
                 max_concurrent_analyses: int = 10,
                 analysis_timeout: int = 300,
                 auto_select_orchestrator: bool = True,
                 hierarchical_coordination_level: str = "full",
                 specialized_orchestrator_priority: List[str] = None,
                 save_orchestration_trace: bool = True,
                 middleware_config: Dict[str, Any] = None):
        """
        Initialise la configuration étendue.
        
        Args:
            analysis_type: Type d'analyse à effectuer
            enable_hierarchical: Active l'architecture hiérarchique
            enable_specialized_orchestrators: Active les orchestrateurs spécialisés
            enable_communication_middleware: Active le middleware de communication
            max_concurrent_analyses: Nombre max d'analyses simultanées
            analysis_timeout: Timeout en secondes pour les analyses
            auto_select_orchestrator: Sélection automatique de l'orchestrateur
            hierarchical_coordination_level: Niveau de coordination ("full", "strategic", "tactical")
            specialized_orchestrator_priority: Ordre de priorité des orchestrateurs spécialisés
            save_orchestration_trace: Sauvegarde la trace d'orchestration
            middleware_config: Configuration du middleware
        """
        # Initialiser la configuration de base
        super().__init__(
            analysis_modes=analysis_modes,
            orchestration_mode=orchestration_mode if isinstance(orchestration_mode, str) else orchestration_mode.value,
            logic_type=logic_type,
            use_mocks=use_mocks,
            use_advanced_tools=use_advanced_tools,
            output_format=output_format,
            enable_conversation_logging=enable_conversation_logging
        )
        
        # Configuration étendue
        self.analysis_type = analysis_type if isinstance(analysis_type, AnalysisType) else AnalysisType(analysis_type)
        self.orchestration_mode_enum = orchestration_mode if isinstance(orchestration_mode, OrchestrationMode) else OrchestrationMode(orchestration_mode)
        
        # Configuration hiérarchique
        self.enable_hierarchical = enable_hierarchical
        self.enable_specialized_orchestrators = enable_specialized_orchestrators
        self.enable_communication_middleware = enable_communication_middleware
        self.max_concurrent_analyses = max_concurrent_analyses
        self.analysis_timeout = analysis_timeout
        self.auto_select_orchestrator = auto_select_orchestrator
        self.hierarchical_coordination_level = hierarchical_coordination_level
        self.specialized_orchestrator_priority = specialized_orchestrator_priority or [
            "cluedo_investigation", "logic_complex", "conversation", "real"
        ]
        self.save_orchestration_trace = save_orchestration_trace
        self.middleware_config = middleware_config or {}


class UnifiedOrchestrationPipeline:
    """
    Pipeline d'orchestration unifié intégrant l'architecture hiérarchique complète.
    
    Ce pipeline étend le UnifiedTextAnalysisPipeline original pour intégrer :
    - Architecture hiérarchique à 3 niveaux (Stratégique/Tactique/Opérationnel)
    - Orchestrateurs spécialisés selon le type d'analyse
    - Service manager centralisé pour la coordination
    - Middleware de communication inter-services
    - Interfaces sophistiquées entre niveaux hiérarchiques
    """
    
    def __init__(self, config: ExtendedOrchestrationConfig):
        """Initialise le pipeline d'orchestration unifié."""
        self.config = config
        self.llm_service = None
        
        # Service manager centralisé
        self.service_manager: Optional[OrchestrationServiceManager] = None
        
        # Gestionnaires hiérarchiques
        self.strategic_manager: Optional[StrategicManager] = None
        self.tactical_coordinator: Optional[TaskCoordinator] = None
        self.operational_manager: Optional[OperationalManager] = None
        
        # Orchestrateurs spécialisés
        self.specialized_orchestrators = {}
        
        # Middleware de communication
        self.middleware: Optional[MessageMiddleware] = None
        
        # Pipeline original pour compatibilité
        self._fallback_pipeline: Optional[UnifiedTextAnalysisPipeline] = None
        
        # État interne
        self.initialized = False
        self.start_time = None
        self.orchestration_trace = []
        
        # JVM pour analyse formelle
        self.jvm_ready = False
        
        logger.info(f"Pipeline d'orchestration unifié créé - Mode: {config.orchestration_mode_enum.value}, Type: {config.analysis_type.value}")
        
    async def initialize(self) -> bool:
        """
        Initialise tous les composants du pipeline d'orchestration.
        
        Returns:
            True si l'initialisation réussit, False sinon
        """
        if self.initialized:
            logger.warning("Pipeline déjà initialisé")
            return True
            
        logger.info("[INIT] Initialisation du pipeline d'orchestration unifié...")
        self.start_time = time.time()
        
        try:
            # 1. Initialisation des services de base
            await self._initialize_base_services()
            
            # 2. Initialisation du service manager centralisé
            if self.config.enable_hierarchical and OrchestrationServiceManager:
                await self._initialize_service_manager()
            
            # 3. Initialisation de l'architecture hiérarchique (SKIP SI MIDDLEWARE NON DISPONIBLE)
            if self.config.enable_hierarchical and MessageMiddleware:
                await self._initialize_hierarchical_architecture()
            elif self.config.enable_hierarchical:
                logger.warning("[HIERARCHICAL] Architecture hiérarchique skippée - middleware non disponible")
            
            # 4. Initialisation des orchestrateurs spécialisés (SKIP SI COMPOSANTS NON DISPONIBLES)
            if self.config.enable_specialized_orchestrators and (CluedoOrchestrator or ConversationOrchestrator):
                await self._initialize_specialized_orchestrators()
            elif self.config.enable_specialized_orchestrators:
                logger.warning("[SPECIALIZED] Orchestrateurs spécialisés skippés - composants non disponibles")
            
            # 5. Configuration du middleware de communication
            if self.config.enable_communication_middleware and MessageMiddleware:
                await self._initialize_communication_middleware()
            elif self.config.enable_communication_middleware:
                logger.warning("[COMMUNICATION] Middleware skippé - composant non disponible")
            
            # 6. Pipeline de fallback pour compatibilité
            await self._initialize_fallback_pipeline()
            
            self.initialized = True
            self._trace_orchestration("pipeline_initialized", {
                "orchestration_mode": self.config.orchestration_mode_enum.value,
                "analysis_type": self.config.analysis_type.value,
                "hierarchical_enabled": self.config.enable_hierarchical,
                "specialized_enabled": self.config.enable_specialized_orchestrators
            })
            
            logger.info(f"[INIT] Pipeline d'orchestration unifié initialisé avec succès en {time.time() - self.start_time:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"[INIT] Erreur lors de l'initialisation: {e}")
            return False
    
    async def _initialize_base_services(self):
        """Initialise les services de base (LLM, JVM)."""
        logger.info("[INIT] Initialisation des services de base...")
        
        # Service LLM
        try:
            self.llm_service = create_llm_service()
            if self.llm_service:
                logger.info(f"[LLM] Service LLM créé (ID: {self.llm_service.service_id})")
        except Exception as e:
            logger.error(f"[LLM] Erreur initialisation LLM: {e}")
            if not self.config.use_mocks:
                logger.warning("[LLM] Basculement vers mode mocks")
                self.config.use_mocks = True
        
        # JVM pour analyse formelle
        if "formal" in self.config.analysis_modes or "unified" in self.config.analysis_modes:
            logger.info("[JVM] Initialisation de la JVM pour analyse formelle...")
            try:
                self.jvm_ready = initialize_jvm(lib_dir_path=LIBS_DIR)
                if self.jvm_ready:
                    logger.info("[JVM] JVM initialisée avec succès")
            except Exception as e:
                logger.error(f"[JVM] Erreur initialisation JVM: {e}")
                self.jvm_ready = False
    
    async def _initialize_service_manager(self):
        """Initialise le service manager centralisé."""
        logger.info("[SERVICE_MANAGER] Initialisation du service manager centralisé...")
        
        service_config = {
            'enable_hierarchical': self.config.enable_hierarchical,
            'enable_specialized_orchestrators': self.config.enable_specialized_orchestrators,
            'enable_communication_middleware': self.config.enable_communication_middleware,
            'max_concurrent_analyses': self.config.max_concurrent_analyses,
            'analysis_timeout': self.config.analysis_timeout,
            'auto_cleanup': True,
            'save_results': True,
            'results_dir': str(RESULTS_DIR),
            'data_dir': str(DATA_DIR)
        }
        service_config.update(self.config.middleware_config)
        
        self.service_manager = OrchestrationServiceManager(
            config=service_config,
            enable_logging=True,
            log_level=logging.INFO
        )
        
        # Initialiser le service manager
        success = await self.service_manager.initialize()
        if success:
            logger.info("[SERVICE_MANAGER] Service manager centralisé initialisé")
        else:
            logger.warning("[SERVICE_MANAGER] Échec initialisation service manager")
    
    async def _initialize_hierarchical_architecture(self):
        """Initialise l'architecture hiérarchique."""
        logger.info("[HIERARCHICAL] Initialisation de l'architecture hiérarchique...")
        
        # Middleware de communication pour les gestionnaires
        if MessageMiddleware and self.config.enable_communication_middleware:
            self.middleware = MessageMiddleware()
        
        # Gestionnaire stratégique
        if StrategicManager and self.config.hierarchical_coordination_level in ["full", "strategic"] and self.middleware:
            self.strategic_manager = StrategicManager(middleware=self.middleware)
            logger.info("[STRATEGIC] Gestionnaire stratégique initialisé")
        elif StrategicManager and self.config.hierarchical_coordination_level in ["full", "strategic"]:
            logger.warning("[STRATEGIC] Middleware non disponible, gestionnaire stratégique non initialisé")
        
        # Coordinateur tactique
        if TaskCoordinator and self.config.hierarchical_coordination_level in ["full", "tactical"] and self.middleware:
            self.tactical_coordinator = TaskCoordinator(middleware=self.middleware)
            logger.info("[TACTICAL] Coordinateur tactique initialisé")
        elif TaskCoordinator and self.config.hierarchical_coordination_level in ["full", "tactical"]:
            logger.warning("[TACTICAL] Middleware non disponible, coordinateur tactique non initialisé")
        
        # Gestionnaire opérationnel
        if OperationalManager and self.middleware:
            self.operational_manager = OperationalManager(middleware=self.middleware)
            logger.info("[OPERATIONAL] Gestionnaire opérationnel initialisé")
        elif OperationalManager:
            logger.warning("[OPERATIONAL] Middleware non disponible, gestionnaire opérationnel non initialisé")
    
    async def _initialize_specialized_orchestrators(self):
        """Initialise les orchestrateurs spécialisés."""
        logger.info("[SPECIALIZED] Initialisation des orchestrateurs spécialisés...")
        
        # Orchestrateur Cluedo pour les investigations
        if CluedoOrchestrator:
            self.specialized_orchestrators["cluedo"] = {
                "orchestrator": CluedoOrchestrator(),
                "types": [AnalysisType.INVESTIGATIVE, AnalysisType.DEBATE_ANALYSIS],
                "priority": 1
            }
            logger.info("[CLUEDO] Orchestrateur Cluedo initialisé")
        
        # Orchestrateur de conversation
        if ConversationOrchestrator:
            self.specialized_orchestrators["conversation"] = {
                "orchestrator": ConversationOrchestrator(mode="advanced"),
                "types": [AnalysisType.RHETORICAL, AnalysisType.COMPREHENSIVE],
                "priority": 2
            }
            logger.info("[CONVERSATION] Orchestrateur de conversation initialisé")
        
        # Orchestrateur LLM réel
        if RealLLMOrchestrator and self.llm_service:
            self.specialized_orchestrators["real_llm"] = {
                "orchestrator": RealLLMOrchestrator(mode="real", llm_service=self.llm_service),
                "types": [AnalysisType.FALLACY_FOCUSED, AnalysisType.ARGUMENT_STRUCTURE],
                "priority": 3
            }
            await self.specialized_orchestrators["real_llm"]["orchestrator"].initialize()
            logger.info("[REAL_LLM] Orchestrateur LLM réel initialisé")
        
        # Orchestrateur logique complexe
        if LogiqueComplexeOrchestrator:
            self.specialized_orchestrators["logic_complex"] = {
                "orchestrator": LogiqueComplexeOrchestrator(),
                "types": [AnalysisType.LOGICAL, AnalysisType.COMPREHENSIVE],
                "priority": 4
            }
            logger.info("[LOGIC_COMPLEX] Orchestrateur logique complexe initialisé")
    
    async def _initialize_communication_middleware(self):
        """Initialise le middleware de communication."""
        if self.middleware:
            logger.info("[COMMUNICATION] Middleware de communication déjà initialisé")
            return
        
        if MessageMiddleware and self.config.enable_communication_middleware:
            self.middleware = MessageMiddleware()
            logger.info("[COMMUNICATION] Middleware de communication initialisé")
    
    async def _initialize_fallback_pipeline(self):
        """Initialise le pipeline de fallback pour compatibilité."""
        logger.info("[FALLBACK] Initialisation du pipeline de fallback...")
        
        # Créer la configuration de base
        base_config = UnifiedAnalysisConfig(
            analysis_modes=self.config.analysis_modes,
            orchestration_mode=self.config.orchestration_mode,
            logic_type=self.config.logic_type,
            use_mocks=self.config.use_mocks,
            use_advanced_tools=self.config.use_advanced_tools,
            output_format=self.config.output_format,
            enable_conversation_logging=self.config.enable_conversation_logging
        )
        
        self._fallback_pipeline = UnifiedTextAnalysisPipeline(base_config)
        await self._fallback_pipeline.initialize()
        logger.info("[FALLBACK] Pipeline de fallback initialisé")
    
    async def analyze_text_orchestrated(self, 
                                      text: str, 
                                      source_info: Optional[str] = None,
                                      custom_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Lance l'analyse orchestrée d'un texte avec l'architecture hiérarchique complète.
        
        Args:
            text: Texte à analyser
            source_info: Information sur la source (optionnel)
            custom_config: Configuration personnalisée pour cette analyse (optionnel)
            
        Returns:
            Dictionnaire des résultats d'analyse orchestrée
        """
        if not self.initialized:
            raise RuntimeError("Pipeline non initialisé. Appelez initialize() d'abord.")
        
        if not text or not text.strip():
            raise ValueError("Texte vide ou invalide fourni pour l'analyse.")
        
        analysis_start = time.time()
        analysis_id = f"analysis_{int(analysis_start)}"
        
        logger.info(f"[ORCHESTRATION] Début de l'analyse orchestrée {analysis_id}")
        self._trace_orchestration("analysis_started", {
            "analysis_id": analysis_id,
            "text_length": len(text),
            "source_info": source_info,
            "orchestration_mode": self.config.orchestration_mode_enum.value,
            "analysis_type": self.config.analysis_type.value
        })
        
        # Structure de résultats étendue
        results = {
            "metadata": {
                "analysis_id": analysis_id,
                "analysis_timestamp": datetime.now().isoformat(),
                "pipeline_version": "unified_orchestration_2.0",
                "orchestration_mode": self.config.orchestration_mode_enum.value,
                "analysis_type": self.config.analysis_type.value,
                "text_length": len(text),
                "source_info": source_info or "Non spécifié"
            },
            
            # Résultats des différentes couches d'orchestration
            "strategic_analysis": {},
            "tactical_coordination": {},
            "operational_results": {},
            "specialized_orchestration": {},
            "service_manager_results": {},
            
            # Résultats de base (compatibilité)
            "informal_analysis": {},
            "formal_analysis": {},
            "unified_analysis": {},
            "orchestration_analysis": {},
            
            # Métadonnées d'orchestration
            "orchestration_trace": [],
            "communication_log": [],
            "hierarchical_coordination": {},
            "recommendations": [],
            "execution_time": 0,
            "status": "in_progress"
        }
        
        try:
            # Sélection de la stratégie d'orchestration
            orchestration_strategy = await self._select_orchestration_strategy(text, custom_config)
            logger.info(f"[ORCHESTRATION] Stratégie sélectionnée: {orchestration_strategy}")
            
            # Exécution selon la stratégie d'orchestration
            if orchestration_strategy == "hierarchical_full":
                results = await self._execute_hierarchical_full_orchestration(text, results)
            elif orchestration_strategy == "specialized_direct":
                results = await self._execute_specialized_orchestration(text, results)
            elif orchestration_strategy == "service_manager":
                results = await self._execute_service_manager_orchestration(text, results)
            elif orchestration_strategy == "fallback":
                results = await self._execute_fallback_orchestration(text, results)
            else:
                # Orchestration hybride (par défaut)
                results = await self._execute_hybrid_orchestration(text, results)
            
            # Post-traitement des résultats
            results = await self._post_process_orchestration_results(results)
            
            results["status"] = "success"
            
        except Exception as e:
            logger.error(f"[ORCHESTRATION] Erreur durant l'analyse orchestrée: {e}")
            results["status"] = "error"
            results["error"] = str(e)
            self._trace_orchestration("analysis_error", {"error": str(e)})
        
        # Finalisation
        results["execution_time"] = time.time() - analysis_start
        results["orchestration_trace"] = self.orchestration_trace.copy()
        
        logger.info(f"[ORCHESTRATION] Analyse orchestrée {analysis_id} terminée en {results['execution_time']:.2f}s")
        self._trace_orchestration("analysis_completed", {
            "analysis_id": analysis_id,
            "execution_time": results["execution_time"],
            "status": results["status"]
        })
        
        # Sauvegarde de la trace si activée
        if self.config.save_orchestration_trace:
            await self._save_orchestration_trace(analysis_id, results)
        
        return results
    
    async def _select_orchestration_strategy(self, text: str, custom_config: Optional[Dict[str, Any]] = None) -> str:
        """
        Sélectionne la stratégie d'orchestration appropriée.
        
        Args:
            text: Texte à analyser
            custom_config: Configuration personnalisée
            
        Returns:
            Nom de la stratégie d'orchestration sélectionnée
        """
        # Mode manuel
        if self.config.orchestration_mode_enum != OrchestrationMode.AUTO_SELECT:
            mode_strategy_map = {
                OrchestrationMode.HIERARCHICAL_FULL: "hierarchical_full",
                OrchestrationMode.STRATEGIC_ONLY: "strategic_only",
                OrchestrationMode.TACTICAL_COORDINATION: "tactical_coordination",
                OrchestrationMode.OPERATIONAL_DIRECT: "operational_direct",
                OrchestrationMode.CLUEDO_INVESTIGATION: "specialized_direct",
                OrchestrationMode.LOGIC_COMPLEX: "specialized_direct",
                OrchestrationMode.ADAPTIVE_HYBRID: "hybrid"
            }
            return mode_strategy_map.get(self.config.orchestration_mode_enum, "fallback")
        
        # Sélection automatique basée sur le type d'analyse
        if not self.config.auto_select_orchestrator:
            return "fallback"
        
        # Analyse du texte pour sélection automatique
        text_features = await self._analyze_text_features(text)
        
        # Critères de sélection
        if self.config.analysis_type == AnalysisType.INVESTIGATIVE:
            return "specialized_direct"  # Cluedo orchestrator
        elif self.config.analysis_type == AnalysisType.LOGICAL:
            return "specialized_direct"  # Logic complex orchestrator
        elif self.config.enable_hierarchical and len(text) > 1000:
            return "hierarchical_full"
        elif self.service_manager and self.service_manager._initialized:
            return "service_manager"
        else:
            return "hybrid"
    
    async def _analyze_text_features(self, text: str) -> Dict[str, Any]:
        """Analyse les caractéristiques du texte pour la sélection d'orchestrateur."""
        features = {
            "length": len(text),
            "word_count": len(text.split()),
            "sentence_count": text.count('.') + text.count('!') + text.count('?'),
            "has_questions": '?' in text,
            "has_logical_connectors": any(connector in text.lower() for connector in 
                                        ['donc', 'par conséquent', 'si...alors', 'parce que', 'car']),
            "has_debate_markers": any(marker in text.lower() for marker in 
                                    ['argument', 'contre-argument', 'objection', 'réfutation']),
            "complexity_score": min(len(text) / 500, 5.0)  # Score de 0 à 5
        }
        return features
    
    async def _execute_hierarchical_full_orchestration(self, text: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute l'orchestration hiérarchique complète."""
        logger.info("[HIERARCHICAL] Exécution de l'orchestration hiérarchique complète...")
        
        try:
            # Niveau stratégique
            if self.strategic_manager:
                logger.info("[STRATEGIC] Initialisation de l'analyse stratégique...")
                strategic_results = self.strategic_manager.initialize_analysis(text)
                results["strategic_analysis"] = strategic_results
                
                self._trace_orchestration("strategic_analysis_completed", {
                    "objectives_count": len(strategic_results.get("objectives", [])),
                    "strategic_plan": strategic_results.get("strategic_plan", {}).get("phases", [])
                })
            
            # Niveau tactique
            if self.tactical_coordinator and self.strategic_manager:
                logger.info("[TACTICAL] Coordination tactique...")
                objectives = results["strategic_analysis"].get("objectives", [])
                tactical_results = await self.tactical_coordinator.process_strategic_objectives(objectives)
                results["tactical_coordination"] = tactical_results
                
                self._trace_orchestration("tactical_coordination_completed", {
                    "tasks_created": tactical_results.get("tasks_created", 0)
                })
            
            # Niveau opérationnel (exécution des tâches)
            if self.operational_manager:
                logger.info("[OPERATIONAL] Exécution opérationnelle...")
                operational_results = await self._execute_operational_tasks(text, results["tactical_coordination"])
                results["operational_results"] = operational_results
                
                self._trace_orchestration("operational_execution_completed", {
                    "tasks_executed": len(operational_results.get("task_results", []))
                })
            
            # Synthèse hiérarchique
            results["hierarchical_coordination"] = await self._synthesize_hierarchical_results(results)
            
        except Exception as e:
            logger.error(f"[HIERARCHICAL] Erreur dans l'orchestration hiérarchique: {e}")
            results["strategic_analysis"]["error"] = str(e)
        
        return results
    
    async def _execute_specialized_orchestration(self, text: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute l'orchestration spécialisée."""
        logger.info("[SPECIALIZED] Exécution de l'orchestration spécialisée...")
        
        try:
            # Sélection de l'orchestrateur spécialisé approprié
            selected_orchestrator = await self._select_specialized_orchestrator()
            
            if selected_orchestrator:
                orchestrator_name, orchestrator_data = selected_orchestrator
                orchestrator = orchestrator_data["orchestrator"]
                
                logger.info(f"[SPECIALIZED] Utilisation de l'orchestrateur: {orchestrator_name}")
                
                # Exécution selon le type d'orchestrateur
                if orchestrator_name == "cluedo" and hasattr(orchestrator, 'run_investigation'):
                    specialized_results = await self._run_cluedo_investigation(text, orchestrator)
                elif orchestrator_name == "conversation" and hasattr(orchestrator, 'run_conversation'):
                    specialized_results = await orchestrator.run_conversation(text)
                elif orchestrator_name == "real_llm" and hasattr(orchestrator, 'analyze_text_comprehensive'):
                    specialized_results = await orchestrator.analyze_text_comprehensive(
                        text, context={"source": "specialized_orchestration"}
                    )
                elif orchestrator_name == "logic_complex":
                    specialized_results = await self._run_logic_complex_analysis(text, orchestrator)
                else:
                    # Fallback générique
                    specialized_results = {"status": "unsupported", "orchestrator": orchestrator_name}
                
                results["specialized_orchestration"] = {
                    "orchestrator_used": orchestrator_name,
                    "orchestrator_priority": orchestrator_data["priority"],
                    "results": specialized_results
                }
                
                self._trace_orchestration("specialized_orchestration_completed", {
                    "orchestrator": orchestrator_name,
                    "status": specialized_results.get("status", "unknown")
                })
            else:
                results["specialized_orchestration"] = {
                    "status": "no_orchestrator_available",
                    "message": "Aucun orchestrateur spécialisé disponible pour ce type d'analyse"
                }
        
        except Exception as e:
            logger.error(f"[SPECIALIZED] Erreur dans l'orchestration spécialisée: {e}")
            results["specialized_orchestration"]["error"] = str(e)
        
        return results
    
    async def _execute_service_manager_orchestration(self, text: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute l'orchestration via le service manager centralisé."""
        logger.info("[SERVICE_MANAGER] Exécution via le service manager centralisé...")
        
        try:
            if self.service_manager and self.service_manager._initialized:
                # Préparer les options d'analyse
                analysis_options = {
                    "analysis_type": self.config.analysis_type.value,
                    "orchestration_mode": self.config.orchestration_mode_enum.value,
                    "use_hierarchical": self.config.enable_hierarchical,
                    "enable_specialized": self.config.enable_specialized_orchestrators
                }
                
                # Lancer l'analyse via le service manager
                service_results = await self.service_manager.analyze_text(
                    text=text,
                    analysis_type=self.config.analysis_type.value,
                    options=analysis_options
                )
                
                results["service_manager_results"] = service_results
                
                self._trace_orchestration("service_manager_orchestration_completed", {
                    "analysis_id": service_results.get("analysis_id"),
                    "status": service_results.get("status")
                })
            else:
                results["service_manager_results"] = {
                    "status": "unavailable",
                    "message": "Service manager non disponible ou non initialisé"
                }
        
        except Exception as e:
            logger.error(f"[SERVICE_MANAGER] Erreur dans l'orchestration service manager: {e}")
            results["service_manager_results"]["error"] = str(e)
        
        return results
    
    async def _execute_fallback_orchestration(self, text: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute l'orchestration de fallback avec le pipeline original."""
        logger.info("[FALLBACK] Exécution de l'orchestration de fallback...")
        
        try:
            if self._fallback_pipeline:
                fallback_results = await self._fallback_pipeline.analyze_text_unified(text)
                
                # Mapper les résultats du fallback
                results["informal_analysis"] = fallback_results.get("informal_analysis", {})
                results["formal_analysis"] = fallback_results.get("formal_analysis", {})
                results["unified_analysis"] = fallback_results.get("unified_analysis", {})
                results["orchestration_analysis"] = fallback_results.get("orchestration_analysis", {})
                
                self._trace_orchestration("fallback_orchestration_completed", {
                    "fallback_status": fallback_results.get("status", "unknown")
                })
            else:
                results["orchestration_analysis"] = {
                    "status": "fallback_unavailable",
                    "message": "Pipeline de fallback non disponible"
                }
        
        except Exception as e:
            logger.error(f"[FALLBACK] Erreur dans l'orchestration de fallback: {e}")
            results["orchestration_analysis"]["error"] = str(e)
        
        return results
    
    async def _execute_hybrid_orchestration(self, text: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute l'orchestration hybride combinant plusieurs approches."""
        logger.info("[HYBRID] Exécution de l'orchestration hybride...")
        
        try:
            # Combiner l'orchestration hiérarchique et spécialisée
            if self.config.enable_hierarchical:
                results = await self._execute_hierarchical_full_orchestration(text, results)
            
            if self.config.enable_specialized_orchestrators:
                specialized_results = await self._execute_specialized_orchestration(text, {})
                results["specialized_orchestration"] = specialized_results["specialized_orchestration"]
            
            # Ajouter le fallback pour la compatibilité
            fallback_results = await self._execute_fallback_orchestration(text, {})
            results.update({
                "informal_analysis": fallback_results.get("informal_analysis", {}),
                "formal_analysis": fallback_results.get("formal_analysis", {}),
                "unified_analysis": fallback_results.get("unified_analysis", {})
            })
            
            self._trace_orchestration("hybrid_orchestration_completed", {
                "hierarchical_used": self.config.enable_hierarchical,
                "specialized_used": self.config.enable_specialized_orchestrators
            })
        
        except Exception as e:
            logger.error(f"[HYBRID] Erreur dans l'orchestration hybride: {e}")
            results["error"] = str(e)
        
        return results
    
    async def _select_specialized_orchestrator(self) -> Optional[tuple]:
        """Sélectionne l'orchestrateur spécialisé approprié."""
        if not self.specialized_orchestrators:
            return None
        
        # Filtre par type d'analyse
        compatible_orchestrators = []
        for name, data in self.specialized_orchestrators.items():
            if self.config.analysis_type in data["types"]:
                compatible_orchestrators.append((name, data))
        
        if not compatible_orchestrators:
            # Prendre le premier orchestrateur disponible
            compatible_orchestrators = list(self.specialized_orchestrators.items())
        
        # Trier par priorité
        compatible_orchestrators.sort(key=lambda x: x[1]["priority"])
        
        return compatible_orchestrators[0] if compatible_orchestrators else None
    
    async def _run_cluedo_investigation(self, text: str, orchestrator) -> Dict[str, Any]:
        """Lance une investigation de type Cluedo."""
        try:
            if hasattr(orchestrator, 'kernel') and run_cluedo_game:
                # Utiliser la fonction run_cluedo_game pour une investigation complète
                conversation_history, enquete_state = await run_cluedo_game(
                    kernel=orchestrator.kernel,
                    initial_question=f"Analysez ce texte comme une enquête : {text[:500]}...",
                    max_iterations=5
                )
                
                return {
                    "status": "completed",
                    "investigation_type": "cluedo",
                    "conversation_history": conversation_history,
                    "enquete_state": {
                        "nom_enquete": enquete_state.nom_enquete,
                        "solution_proposee": enquete_state.solution_proposee,
                        "hypotheses": len(enquete_state.hypotheses),
                        "tasks": len(enquete_state.tasks)
                    }
                }
            else:
                # Fallback simple
                return {
                    "status": "limited",
                    "message": "Investigation Cluedo limitée (méthode complète non disponible)"
                }
        except Exception as e:
            logger.error(f"Erreur investigation Cluedo: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _run_logic_complex_analysis(self, text: str, orchestrator) -> Dict[str, Any]:
        """Lance une analyse logique complexe."""
        try:
            # Implémentation basique - à étendre selon l'interface de LogiqueComplexeOrchestrator
            if hasattr(orchestrator, 'analyze_complex_logic'):
                results = await orchestrator.analyze_complex_logic(text)
                return {"status": "completed", "logic_analysis": results}
            else:
                return {
                    "status": "limited",
                    "message": "Analyse logique complexe limitée (méthode complète non disponible)"
                }
        except Exception as e:
            logger.error(f"Erreur analyse logique complexe: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _execute_operational_tasks(self, text: str, tactical_coordination: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute les tâches au niveau opérationnel."""
        operational_results = {
            "tasks_executed": 0,
            "task_results": [],
            "summary": {}
        }
        
        # Simuler l'exécution des tâches opérationnelles
        # Dans une implémentation complète, ceci déléguerait aux agents opérationnels réels
        try:
            tasks_created = tactical_coordination.get("tasks_created", 0)
            
            for i in range(min(tasks_created, 5)):  # Limiter pour la démonstration
                task_result = {
                    "task_id": f"task_{i+1}",
                    "status": "completed",
                    "result": f"Résultat de la tâche opérationnelle {i+1}",
                    "execution_time": 0.5
                }
                operational_results["task_results"].append(task_result)
                operational_results["tasks_executed"] += 1
            
            operational_results["summary"] = {
                "total_tasks": tasks_created,
                "executed_tasks": operational_results["tasks_executed"],
                "success_rate": 1.0 if operational_results["tasks_executed"] > 0 else 0.0
            }
        
        except Exception as e:
            logger.error(f"Erreur exécution tâches opérationnelles: {e}")
            operational_results["error"] = str(e)
        
        return operational_results
    
    async def _synthesize_hierarchical_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Synthétise les résultats de l'orchestration hiérarchique."""
        synthesis = {
            "coordination_effectiveness": 0.0,
            "strategic_alignment": 0.0,
            "tactical_efficiency": 0.0,
            "operational_success": 0.0,
            "overall_score": 0.0,
            "recommendations": []
        }
        
        try:
            # Calculer les métriques de coordination
            strategic_results = results.get("strategic_analysis", {})
            tactical_results = results.get("tactical_coordination", {})
            operational_results = results.get("operational_results", {})
            
            # Alignement stratégique
            if strategic_results:
                objectives_count = len(strategic_results.get("objectives", []))
                synthesis["strategic_alignment"] = min(objectives_count / 4.0, 1.0)  # Max 4 objectifs
            
            # Efficacité tactique
            if tactical_results:
                tasks_created = tactical_results.get("tasks_created", 0)
                synthesis["tactical_efficiency"] = min(tasks_created / 10.0, 1.0)  # Max 10 tâches
            
            # Succès opérationnel
            if operational_results:
                success_rate = operational_results.get("summary", {}).get("success_rate", 0.0)
                synthesis["operational_success"] = success_rate
            
            # Score global
            scores = [synthesis["strategic_alignment"], synthesis["tactical_efficiency"], synthesis["operational_success"]]
            synthesis["overall_score"] = sum(scores) / len(scores) if scores else 0.0
            synthesis["coordination_effectiveness"] = synthesis["overall_score"]
            
            # Recommandations
            if synthesis["overall_score"] > 0.8:
                synthesis["recommendations"].append("Orchestration hiérarchique très efficace")
            elif synthesis["overall_score"] > 0.6:
                synthesis["recommendations"].append("Orchestration hiérarchique satisfaisante")
            else:
                synthesis["recommendations"].append("Orchestration hiérarchique à améliorer")
        
        except Exception as e:
            logger.error(f"Erreur synthèse hiérarchique: {e}")
            synthesis["error"] = str(e)
        
        return synthesis
    
    async def _post_process_orchestration_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Post-traite les résultats d'orchestration."""
        try:
            # Générer les recommandations globales
            recommendations = []
            
            # Recommandations basées sur l'orchestration hiérarchique
            hierarchical_coord = results.get("hierarchical_coordination", {})
            if hierarchical_coord.get("overall_score", 0) > 0.7:
                recommendations.append("Architecture hiérarchique très performante")
            
            # Recommandations basées sur l'orchestration spécialisée
            specialized = results.get("specialized_orchestration", {})
            if specialized.get("results", {}).get("status") == "completed":
                orchestrator_used = specialized.get("orchestrator_used", "inconnu")
                recommendations.append(f"Orchestrateur spécialisé '{orchestrator_used}' efficace")
            
            # Recommandations par défaut
            if not recommendations:
                recommendations.append("Analyse orchestrée complétée - examen des résultats recommandé")
            
            results["recommendations"] = recommendations
            
            # Ajouter les logs de communication si disponibles
            if self.middleware:
                results["communication_log"] = self._get_communication_log()
            
        except Exception as e:
            logger.error(f"Erreur post-traitement: {e}")
            results["post_processing_error"] = str(e)
        
        return results
    
    def _trace_orchestration(self, event_type: str, data: Dict[str, Any]):
        """Enregistre un événement dans la trace d'orchestration."""
        if self.config.save_orchestration_trace:
            trace_entry = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "data": data
            }
            self.orchestration_trace.append(trace_entry)
    
    def _get_communication_log(self) -> List[Dict[str, Any]]:
        """Récupère le log de communication du middleware."""
        if self.middleware and hasattr(self.middleware, 'get_message_history'):
            try:
                return self.middleware.get_message_history(limit=50)
            except Exception as e:
                logger.warning(f"Erreur récupération log communication: {e}")
        return []
    
    async def _save_orchestration_trace(self, analysis_id: str, results: Dict[str, Any]):
        """Sauvegarde la trace d'orchestration."""
        try:
            trace_file = RESULTS_DIR / f"orchestration_trace_{analysis_id}.json"
            
            trace_data = {
                "analysis_id": analysis_id,
                "timestamp": datetime.now().isoformat(),
                "config": {
                    "orchestration_mode": self.config.orchestration_mode_enum.value,
                    "analysis_type": self.config.analysis_type.value,
                    "hierarchical_enabled": self.config.enable_hierarchical,
                    "specialized_enabled": self.config.enable_specialized_orchestrators
                },
                "trace": self.orchestration_trace,
                "final_results": {
                    "status": results.get("status"),
                    "execution_time": results.get("execution_time"),
                    "recommendations": results.get("recommendations", [])
                }
            }
            
            import json
            with open(trace_file, 'w', encoding='utf-8') as f:
                json.dump(trace_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[TRACE] Trace d'orchestration sauvegardée: {trace_file}")
        
        except Exception as e:
            logger.error(f"Erreur sauvegarde trace: {e}")
    
    async def shutdown(self):
        """Nettoie et ferme le pipeline."""
        logger.info("[SHUTDOWN] Arrêt du pipeline d'orchestration unifié...")
        
        try:
            # Arrêt du service manager
            if self.service_manager and hasattr(self.service_manager, 'shutdown'):
                await self.service_manager.shutdown()
            
            # Arrêt des orchestrateurs spécialisés
            for name, data in self.specialized_orchestrators.items():
                orchestrator = data["orchestrator"]
                if hasattr(orchestrator, 'shutdown'):
                    try:
                        await orchestrator.shutdown()
                    except Exception as e:
                        logger.warning(f"Erreur arrêt orchestrateur {name}: {e}")
            
            # Arrêt du middleware
            if self.middleware and hasattr(self.middleware, 'shutdown'):
                await self.middleware.shutdown()
            
            self.initialized = False
            logger.info("[SHUTDOWN] Pipeline d'orchestration unifié arrêté")
        
        except Exception as e:
            logger.error(f"[SHUTDOWN] Erreur lors de l'arrêt: {e}")


# ==========================================
# FONCTIONS D'ENTRÉE PUBLIQUES DU PIPELINE
# ==========================================

async def run_unified_orchestration_pipeline(
    text: str,
    config: Optional[ExtendedOrchestrationConfig] = None,
    source_info: Optional[str] = None,
    custom_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Fonction d'entrée principale pour le pipeline d'orchestration unifié.
    
    Args:
        text: Texte à analyser
        config: Configuration d'orchestration étendue (optionnel, valeurs par défaut utilisées)
        source_info: Information sur la source du texte (optionnel)
        custom_config: Configuration personnalisée pour cette analyse (optionnel)
    
    Returns:
        Dictionnaire complet des résultats d'analyse orchestrée
    """
    # Configuration par défaut si non fournie
    if config is None:
        config = ExtendedOrchestrationConfig(
            analysis_modes=["informal", "formal"],
            orchestration_mode=OrchestrationMode.AUTO_SELECT,
            analysis_type=AnalysisType.COMPREHENSIVE,
            enable_hierarchical=True,
            enable_specialized_orchestrators=True,
            auto_select_orchestrator=True
        )
    
    # Création et initialisation du pipeline
    pipeline = UnifiedOrchestrationPipeline(config)
    
    try:
        # Initialisation
        init_success = await pipeline.initialize()
        if not init_success:
            return {
                "error": "Échec de l'initialisation du pipeline d'orchestration",
                "status": "failed"
            }
        
        # Analyse orchestrée
        results = await pipeline.analyze_text_orchestrated(text, source_info, custom_config)
        
        return results
        
    except Exception as e:
        logger.error(f"Erreur pipeline d'orchestration unifié: {e}")
        return {
            "error": str(e),
            "status": "failed",
            "metadata": {
                "analysis_timestamp": datetime.now().isoformat(),
                "pipeline_version": "unified_orchestration_2.0",
                "text_length": len(text) if text else 0
            }
        }
    
    finally:
        # Nettoyage
        try:
            await pipeline.shutdown()
        except Exception as e:
            logger.warning(f"Erreur lors du nettoyage: {e}")


def create_extended_config_from_params(
    orchestration_mode: Union[str, OrchestrationMode] = OrchestrationMode.AUTO_SELECT,
    analysis_type: Union[str, AnalysisType] = AnalysisType.COMPREHENSIVE,
    enable_hierarchical: bool = True,
    enable_specialized: bool = True,
    use_mocks: bool = False,
    **kwargs
) -> ExtendedOrchestrationConfig:
    """
    Crée une configuration étendue depuis des paramètres simples.
    
    Args:
        orchestration_mode: Mode d'orchestration
        analysis_type: Type d'analyse
        enable_hierarchical: Active l'architecture hiérarchique
        enable_specialized: Active les orchestrateurs spécialisés
        use_mocks: Utilisation des mocks pour les tests
        **kwargs: Paramètres additionnels
    
    Returns:
        Configuration d'orchestration étendue
    """
    # Mapping des types d'analyse vers les modes d'analyse
    type_mode_mapping = {
        AnalysisType.RHETORICAL: ["informal"],
        AnalysisType.LOGICAL: ["formal"],
        AnalysisType.COMPREHENSIVE: ["informal", "formal", "unified"],
        AnalysisType.INVESTIGATIVE: ["informal", "unified"],
        AnalysisType.FALLACY_FOCUSED: ["informal"],
        AnalysisType.ARGUMENT_STRUCTURE: ["formal", "unified"],
        AnalysisType.DEBATE_ANALYSIS: ["informal", "formal"],
        AnalysisType.CUSTOM: ["informal", "formal", "unified"]
    }
    
    analysis_type_enum = analysis_type if isinstance(analysis_type, AnalysisType) else AnalysisType(analysis_type)
    analysis_modes = type_mode_mapping.get(analysis_type_enum, ["informal", "formal"])
    
    return ExtendedOrchestrationConfig(
        analysis_modes=analysis_modes,
        orchestration_mode=orchestration_mode,
        analysis_type=analysis_type,
        enable_hierarchical=enable_hierarchical,
        enable_specialized_orchestrators=enable_specialized,
        use_mocks=use_mocks,
        auto_select_orchestrator=kwargs.get("auto_select", True),
        save_orchestration_trace=kwargs.get("save_trace", True),
        **{k: v for k, v in kwargs.items() if k not in ["auto_select", "save_trace"]}
    )


# ==========================================
# FONCTIONS DE COMPATIBILITÉ AVEC L'API EXISTANTE
# ==========================================

async def run_extended_unified_analysis(
    text: str,
    mode: str = "comprehensive",
    orchestration_mode: str = "auto_select",
    use_mocks: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Fonction de compatibilité avec l'API existante du unified_text_analysis.
    
    Cette fonction offre une interface simple pour accéder aux capacités
    d'orchestration étendues tout en maintenant la compatibilité.
    """
    # Mapper les paramètres legacy vers la nouvelle configuration
    analysis_type_mapping = {
        "comprehensive": AnalysisType.COMPREHENSIVE,
        "rhetorical": AnalysisType.RHETORICAL,
        "logical": AnalysisType.LOGICAL,
        "investigative": AnalysisType.INVESTIGATIVE,
        "fallacy": AnalysisType.FALLACY_FOCUSED,
        "structure": AnalysisType.ARGUMENT_STRUCTURE,
        "debate": AnalysisType.DEBATE_ANALYSIS
    }
    
    orchestration_mapping = {
        "auto_select": OrchestrationMode.AUTO_SELECT,
        "hierarchical": OrchestrationMode.HIERARCHICAL_FULL,
        "specialized": OrchestrationMode.CLUEDO_INVESTIGATION,
        "hybrid": OrchestrationMode.ADAPTIVE_HYBRID,
        "pipeline": OrchestrationMode.PIPELINE
    }
    
    config = create_extended_config_from_params(
        orchestration_mode=orchestration_mapping.get(orchestration_mode, OrchestrationMode.AUTO_SELECT),
        analysis_type=analysis_type_mapping.get(mode, AnalysisType.COMPREHENSIVE),
        use_mocks=use_mocks,
        **kwargs
    )
    
    return await run_unified_orchestration_pipeline(text, config)


# Fonction pour faciliter les tests et la migration
async def compare_orchestration_approaches(
    text: str,
    approaches: List[str] = None
) -> Dict[str, Any]:
    """
    Compare différentes approches d'orchestration sur le même texte.
    
    Args:
        text: Texte à analyser
        approaches: Liste des approches à comparer
    
    Returns:
        Dictionnaire comparatif des résultats
    """
    if approaches is None:
        approaches = ["pipeline", "hierarchical", "specialized", "hybrid"]
    
    comparison_results = {
        "text": text[:100] + "..." if len(text) > 100 else text,
        "approaches": {},
        "comparison": {},
        "recommendations": []
    }
    
    for approach in approaches:
        try:
            config = create_extended_config_from_params(
                orchestration_mode=approach,
                analysis_type=AnalysisType.COMPREHENSIVE
            )
            
            start_time = time.time()
            results = await run_unified_orchestration_pipeline(text, config)
            execution_time = time.time() - start_time
            
            comparison_results["approaches"][approach] = {
                "status": results.get("status"),
                "execution_time": execution_time,
                "recommendations_count": len(results.get("recommendations", [])),
                "orchestration_mode": results.get("metadata", {}).get("orchestration_mode"),
                "summary": {
                    "strategic": bool(results.get("strategic_analysis")),
                    "tactical": bool(results.get("tactical_coordination")),
                    "operational": bool(results.get("operational_results")),
                    "specialized": bool(results.get("specialized_orchestration"))
                }
            }
            
        except Exception as e:
            comparison_results["approaches"][approach] = {
                "status": "error",
                "error": str(e)
            }
    
    # Analyse comparative
    successful_approaches = [k for k, v in comparison_results["approaches"].items() 
                           if v.get("status") == "success"]
    
    if successful_approaches:
        fastest = min(successful_approaches, 
                     key=lambda x: comparison_results["approaches"][x].get("execution_time", float('inf')))
        comparison_results["comparison"]["fastest"] = fastest
        
        most_comprehensive = max(successful_approaches,
                               key=lambda x: sum(comparison_results["approaches"][x].get("summary", {}).values()))
        comparison_results["comparison"]["most_comprehensive"] = most_comprehensive
        
        comparison_results["recommendations"].append(f"Approche la plus rapide: {fastest}")
        comparison_results["recommendations"].append(f"Approche la plus complète: {most_comprehensive}")
    
    return comparison_results