#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SYSTÈME DE DÉMONSTRATION ÉDUCATIF - EPITA Intelligence Symbolique
===============================================================

Script consolidé intégrant les meilleurs éléments de :
- demos/demo_unified_system.py (architecture modulaire 8+ modes)
- scripts/demo/run_rhetorical_analysis_demo.py (démo sophistiquée)
- scripts/diagnostic/test_micro_orchestration.py (orchestration multi-agents)
- scripts/demo/run_rhetorical_analysis_phase2_authentic.py (capture conversations)
- examples/logic_agents/combined_logic_example.py (agents logiques combinés)

Innovations intégrées :
- Orchestration conversationnelle ProjectManager + InformalAgent + ModalLogicAgent
- Capture complète des messages entre agents avec logging détaillé
- Interface pédagogique progressive pour étudiants EPITA
- Métriques éducatives avec temps, complexité, étapes d'apprentissage
- Génération de rapports markdown avec explications pédagogiques
- Support multi-langues (français prioritaire)
- Mode interactif avec validation progressive

Author: Système de Consolidation Intelligent
Date: 2025-06-10
Version: 1.0.0
"""

import asyncio
import logging
import time
import json
import os
import sys
import gzip
import argparse
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import semantic_kernel as sk

# Configuration encodage Windows
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Ajouter la racine du projet au sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Force l'exécution authentique (pas de mocks en mode pédagogique)
os.environ["FORCE_AUTHENTIC_EXECUTION"] = "true"
os.environ["DISABLE_MOCKS_EDUCATIONAL"] = "true"
os.environ["ENABLE_EDUCATIONAL_MODE"] = "true"
os.environ["EPITA_PEDAGOGICAL_SYSTEM"] = "true"

try:
    # Imports de l'écosystème refactorisé
    from argumentation_analysis.pipelines.unified_text_analysis import UnifiedTextAnalysisPipeline, UnifiedAnalysisConfig
    from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator, RealConversationLogger
    from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
    from argumentation_analysis.core.source_management import UnifiedSourceManager, UnifiedSourceType, UnifiedSourceConfig
    from argumentation_analysis.core.report_generation import UnifiedReportGenerator, ReportConfiguration, ReportMetadata
    from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
    from argumentation_analysis.core.llm_service import create_llm_service
    from argumentation_analysis.core.jvm_setup import initialize_jvm
    from argumentation_analysis.utils.tweety_error_analyzer import TweetyErrorAnalyzer
    from argumentation_analysis.utils.core_utils.crypto_utils import load_encryption_key, decrypt_data_with_fernet
    from argumentation_analysis.models.extract_definition import ExtractDefinitions
    from argumentation_analysis.paths import DATA_DIR, PROJECT_ROOT_DIR, LIBS_DIR
    from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory
    from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
    from argumentation_analysis.agents.core.logic.first_order_logic_agent import FirstOrderLogicAgent
    from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent
    from argumentation_analysis.agents.core.synthesis.synthesis_agent import SynthesisAgent
    from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer
    from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer
    from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator
    from argumentation_analysis.reporting.real_time_trace_analyzer import (
        RealTimeTraceAnalyzer, global_trace_analyzer, start_conversation_capture,
        stop_conversation_capture, get_conversation_report, save_conversation_report
    )
    EDUCATIONAL_COMPONENTS_AVAILABLE = True
except ImportError as e:
    EDUCATIONAL_COMPONENTS_AVAILABLE = False
    print(f"[WARNING] Certains composants éducatifs non disponibles: {e}")

# Configuration des chemins pour le système éducatif
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOGS_DIR = PROJECT_ROOT_DIR / "logs" / "educational"
REPORTS_DIR = PROJECT_ROOT_DIR / "reports" / "educational"
EDUCATIONAL_RESOURCES_DIR = PROJECT_ROOT_DIR / "temp_cache_test" / "educational"

# Créer les répertoires nécessaires
for directory in [LOGS_DIR, REPORTS_DIR, EDUCATIONAL_RESOURCES_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Configuration du logger éducatif
logger = logging.getLogger("EducationalShowcaseSystem")

class EducationalMode(Enum):
    """Modes d'apprentissage progressifs pour étudiants EPITA."""
    DEBUTANT = "debutant"                    # Démos guidées + explications
    INTERMEDIAIRE = "intermediaire"          # Analyses interactives + exercices
    EXPERT = "expert"                        # Orchestration complète + métriques
    SHERLOCK_WATSON = "sherlock_watson"      # Investigation déductive
    EINSTEIN_ORACLE = "einstein_oracle"      # Raisonnement complexe
    CLUEDO_ENHANCED = "cluedo_enhanced"      # Déduction collaborative
    MICRO_ORCHESTRATION = "micro_orchestration"  # Orchestration simplifiée
    COMPREHENSIVE_ANALYSIS = "comprehensive_analysis"  # Analyse complète multi-agents

class EducationalLanguage(Enum):
    """Langues supportées pour l'interface pédagogique."""
    FRANCAIS = "fr"
    ENGLISH = "en"
    ESPANOL = "es"

@dataclass
class ConversationMessage:
    """Message conversationnel entre agents."""
    timestamp: str
    agent: str
    message: str
    message_type: str = "conversation"  # conversation, tool_call, state_update
    duration_ms: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EducationalMetrics:
    """Métriques pédagogiques pour l'apprentissage."""
    learning_level: str = ""
    complexity_score: float = 0.0
    interaction_count: int = 0
    cognitive_load: str = "low"  # low, medium, high, extreme
    understanding_checkpoints: List[str] = field(default_factory=list)
    time_per_concept: Dict[str, float] = field(default_factory=dict)
    student_feedback_score: float = 0.0
    pedagogical_effectiveness: float = 0.0

@dataclass
class EducationalConfiguration:
    """Configuration complète pour le système éducatif."""
    mode: EducationalMode = EducationalMode.DEBUTANT
    language: EducationalLanguage = EducationalLanguage.FRANCAIS
    student_level: str = "L3"  # L1, L2, L3, M1, M2
    enable_conversation_capture: bool = True
    enable_step_by_step: bool = True
    enable_interactive_feedback: bool = True
    enable_advanced_metrics: bool = False
    enable_real_llm: bool = True
    max_conversation_length: int = 50
    explanation_detail_level: str = "medium"  # basic, medium, detailed, expert
    enable_visual_diagrams: bool = True
    enable_progress_tracking: bool = True
    
    def get_difficulty_config(self) -> Dict[str, Any]:
        """Retourne la configuration de difficulté selon le niveau étudiant."""
        configs = {
            "L1": {"complexity": 0.3, "concepts": ["sophismes_basiques"], "explanation": "detailed"},
            "L2": {"complexity": 0.5, "concepts": ["sophismes", "logique_prop"], "explanation": "medium"},
            "L3": {"complexity": 0.7, "concepts": ["logique_complete", "orchestration"], "explanation": "medium"},
            "M1": {"complexity": 0.8, "concepts": ["orchestration_avancee", "synthesis"], "explanation": "basic"},
            "M2": {"complexity": 1.0, "concepts": ["recherche_avancee"], "explanation": "expert"}
        }
        return configs.get(self.student_level, configs["L3"])

class EducationalConversationLogger:
    """Logger spécialisé pour capturer les conversations pédagogiques."""
    
    def __init__(self, config: EducationalConfiguration):
        self.config = config
        self.conversations: List[ConversationMessage] = []
        self.max_conversations = config.max_conversation_length
        self.current_phase = ""
        
    def log_agent_message(self, agent: str, message: str, phase: str = "", context: Dict = None):
        """Log un message conversationnel d'agent avec contexte pédagogique."""
        if len(self.conversations) >= self.max_conversations:
            return
            
        # Traduire selon la langue configurée
        translated_message = self._translate_message(message, agent)
        
        msg = ConversationMessage(
            timestamp=datetime.now().isoformat(),
            agent=agent,
            message=translated_message,
            message_type="conversation",
            context=context or {"phase": phase, "educational_level": self.config.student_level}
        )
        
        self.conversations.append(msg)
        
        # Log immédiat pour le suivi pédagogique
        logger.info(f"[CONVERSATION-{phase.upper()}] {agent}: {translated_message[:100]}...")
    
    def log_tool_interaction(self, agent: str, tool: str, args: str, result: str, duration_ms: float):
        """Log une interaction d'outil avec métriques pédagogiques."""
        if len(self.conversations) >= self.max_conversations:
            return
            
        tool_message = self._format_tool_message(agent, tool, args, result, duration_ms)
        
        msg = ConversationMessage(
            timestamp=datetime.now().isoformat(),
            agent=agent,
            message=tool_message,
            message_type="tool_call",
            duration_ms=duration_ms,
            context={"tool": tool, "performance": "normal" if duration_ms < 5000 else "slow"}
        )
        
        self.conversations.append(msg)
        logger.debug(f"[TOOL] {agent}.{tool}: {duration_ms:.1f}ms")
    
    def log_educational_checkpoint(self, checkpoint: str, explanation: str):
        """Log un point de contrôle pédagogique."""
        checkpoint_message = self._format_checkpoint(checkpoint, explanation)
        
        msg = ConversationMessage(
            timestamp=datetime.now().isoformat(),
            agent="SystemePedagogique",
            message=checkpoint_message,
            message_type="checkpoint",
            context={"checkpoint": checkpoint, "level": self.config.student_level}
        )
        
        self.conversations.append(msg)
        logger.info(f"[CHECKPOINT] {checkpoint}: {explanation}")
    
    def _translate_message(self, message: str, agent: str) -> str:
        """Traduit les messages selon la langue configurée."""
        if self.config.language == EducationalLanguage.FRANCAIS:
            translations = {
                "InformalAgent": "Agent d'Analyse Rhétorique",
                "ModalLogicAgent": "Agent de Logique Modale", 
                "ProjectManager": "Gestionnaire de Projet",
                "SynthesisAgent": "Agent de Synthèse",
                "Hello": "Bonjour",
                "Analysis complete": "Analyse terminée",
                "Processing": "En cours de traitement",
                "Error": "Erreur"
            }
            
            translated = message
            for en, fr in translations.items():
                translated = translated.replace(en, fr)
            return translated
        return message
    
    def _format_tool_message(self, agent: str, tool: str, args: str, result: str, duration_ms: float) -> str:
        """Formate un message d'outil pour l'apprentissage."""
        if self.config.language == EducationalLanguage.FRANCAIS:
            return f"[OUTIL] {agent} utilise {tool} avec {args[:30]}... → {result[:50]}... ({duration_ms:.1f}ms)"
        return f"[TOOL] {agent} uses {tool} with {args[:30]}... → {result[:50]}... ({duration_ms:.1f}ms)"
    
    def _format_checkpoint(self, checkpoint: str, explanation: str) -> str:
        """Formate un checkpoint pédagogique."""
        if self.config.language == EducationalLanguage.FRANCAIS:
            return f"✓ Point de contrôle atteint: {checkpoint}. {explanation}"
        return f"✓ Checkpoint reached: {checkpoint}. {explanation}"

class EducationalProjectManager:
    """Project Manager spécialisé pour l'orchestration pédagogique multi-agents."""
    
    def __init__(self, config: EducationalConfiguration):
        self.config = config
        self.conversation_logger = EducationalConversationLogger(config)
        self.metrics = EducationalMetrics(learning_level=config.mode.value)
        self.agents: Dict[str, Any] = {}
        self.start_time = time.time()
        self.current_phase = "initialisation"
        
    async def initialize_educational_agents(self, llm_service) -> bool:
        """Initialise les agents pédagogiques selon le niveau de l'étudiant."""
        self.conversation_logger.log_agent_message(
            "ProjectManager",
            f"Bonjour ! Je suis votre gestionnaire de projet pour cette session d'apprentissage niveau {self.config.student_level}. Initialisation des agents spécialisés...",
            "initialisation"
        )
        
        try:
            kernel = sk.Kernel()
            kernel.add_service(llm_service)
            
            # Configuration des agents selon le niveau de difficulté
            difficulty_config = self.config.get_difficulty_config()
            concepts = difficulty_config["concepts"]
            
            # Agent d'analyse rhétorique (toujours présent)
            if "sophismes_basiques" in concepts or "sophismes" in concepts:
                self.agents["informal"] = EnhancedContextualFallacyAnalyzer()
                self.conversation_logger.log_agent_message(
                    "AgentRhetorique", 
                    "Salut ! Je suis l'agent spécialisé dans l'analyse des sophismes et arguments fallacieux. Je vais vous aider à identifier les erreurs de raisonnement.",
                    "initialisation"
                )
            
            # Agents logiques selon le niveau
            if "logique_prop" in concepts or "logique_complete" in concepts:
                prop_agent = LogicAgentFactory.create_agent("propositional", kernel, llm_service.service_id)
                if prop_agent:
                    self.agents["propositional"] = prop_agent
                    self.conversation_logger.log_agent_message(
                        "AgentLogiquePropositionelle",
                        "Bonjour ! Je me spécialise dans la logique propositionnelle. Je vais analyser les implications et les connecteurs logiques.",
                        "initialisation"
                    )
            
            if "logique_complete" in concepts:
                modal_agent = LogicAgentFactory.create_agent("modal", kernel, llm_service.service_id)
                if modal_agent:
                    self.agents["modal"] = modal_agent
                    self.conversation_logger.log_agent_message(
                        "AgentLogiqueModale",
                        "Salut ! J'analyse la logique modale - nécessité, possibilité, et modalités complexes. Prêt pour des analyses sophistiquées !",
                        "initialisation"
                    )
            
            # Agent de synthèse pour niveaux avancés
            if "orchestration_avancee" in concepts or "synthesis" in concepts:
                synthesis_agent = SynthesisAgent(
                    kernel=kernel, 
                    agent_name="EducationalSynthesis",
                    enable_advanced_features=(self.config.student_level in ["M1", "M2"])
                )
                synthesis_agent.setup_agent_components(llm_service.service_id)
                self.agents["synthesis"] = synthesis_agent
                
                self.conversation_logger.log_agent_message(
                    "AgentSynthese",
                    "Bonjour ! Je coordonne l'analyse unifiée en combinant tous les résultats. Je vais synthétiser les découvertes de mes collègues.",
                    "initialisation"
                )
            
            self.conversation_logger.log_educational_checkpoint(
                "AgentsInitialises",
                f"{len(self.agents)} agents spécialisés prêts pour le niveau {self.config.student_level}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des agents: {e}")
            return False
    
    async def orchestrate_educational_analysis(self, text_to_analyze: str) -> Dict[str, Any]:
        """Orchestre l'analyse pédagogique avec interactions entre agents."""
        self.current_phase = "analyse"
        results = {"agents_results": {}, "conversations": [], "metrics": {}}
        
        self.conversation_logger.log_agent_message(
            "ProjectManager",
            f"Nous allons maintenant analyser ce texte ensemble. J'ai {len(self.agents)} agents prêts à collaborer. Commençons !",
            "analyse"
        )
        
        # Phase 1: Analyse rhétorique si disponible
        if "informal" in self.agents:
            await self._run_informal_analysis(text_to_analyze, results)
        
        # Phase 2: Analyses logiques selon le niveau
        if "propositional" in self.agents:
            await self._run_propositional_analysis(text_to_analyze, results)
            
        if "modal" in self.agents:
            await self._run_modal_analysis(text_to_analyze, results)
        
        # Phase 3: Synthèse si agent disponible
        if "synthesis" in self.agents:
            await self._run_synthesis_analysis(text_to_analyze, results)
        
        # Phase 4: Coordination finale du PM
        await self._finalize_educational_analysis(results)
        
        return results
    
    async def _run_informal_analysis(self, text: str, results: Dict[str, Any]):
        """Exécute l'analyse rhétorique avec explications pédagogiques."""
        start_time = time.time()
        
        self.conversation_logger.log_agent_message(
            "AgentRhetorique",
            "Je commence l'analyse des sophismes. Je vais examiner les arguments pour détecter les erreurs de raisonnement courantes...",
            "analyse_rhetorique"
        )
        
        try:
            context = f"Analyse pédagogique niveau {self.config.student_level} - Débat argumentatif"
            informal_results = self.agents["informal"].analyze_fallacies_with_context(text, context)
            
            duration_ms = (time.time() - start_time) * 1000
            
            self.conversation_logger.log_tool_interaction(
                "AgentRhetorique", "analyse_sophismes", 
                f"texte:{len(text)}chars,contexte:{context[:30]}",
                f"sophismes_detectes:{len(informal_results.get('fallacies', []))}",
                duration_ms
            )
            
            # Message éducatif selon les résultats
            fallacies_count = len(informal_results.get('fallacies', []))
            if fallacies_count > 0:
                self.conversation_logger.log_agent_message(
                    "AgentRhetorique",
                    f"Excellente nouvelle ! J'ai détecté {fallacies_count} sophismes dans ce texte. Cela nous donne de beaux exemples à étudier ensemble !",
                    "analyse_rhetorique"
                )
            else:
                self.conversation_logger.log_agent_message(
                    "AgentRhetorique", 
                    "Intéressant ! Ce texte semble bien construit sur le plan rhétorique. C'est rare et mérite notre attention !",
                    "analyse_rhetorique"
                )
            
            results["agents_results"]["informal"] = informal_results
            self.metrics.interaction_count += 1
            
        except Exception as e:
            logger.error(f"Erreur analyse rhétorique: {e}")
            results["agents_results"]["informal"] = {"error": str(e)}
    
    async def _run_propositional_analysis(self, text: str, results: Dict[str, Any]):
        """Exécute l'analyse de logique propositionnelle avec pédagogie."""
        start_time = time.time()
        
        self.conversation_logger.log_agent_message(
            "AgentLogiquePropositionelle",
            "À mon tour ! Je vais convertir ce texte en formules logiques propositionnelles. Les connecteurs ET, OU, IMPLIQUE vont révéler leur structure...",
            "analyse_logique"
        )
        
        try:
            agent = self.agents["propositional"]
            belief_set, status = await agent.text_to_belief_set(text)
            
            if belief_set:
                is_consistent, details = agent.is_consistent(belief_set)
                queries = await agent.generate_queries(text, belief_set)
                
                duration_ms = (time.time() - start_time) * 1000
                
                self.conversation_logger.log_tool_interaction(
                    "AgentLogiquePropositionelle", "analyse_logique",
                    f"texte_vers_formules:{len(text)}chars",
                    f"coherent:{is_consistent},requetes:{len(queries)}",
                    duration_ms
                )
                
                consistency_msg = "cohérent" if is_consistent else "incohérent"
                self.conversation_logger.log_agent_message(
                    "AgentLogiquePropositionelle",
                    f"Analyse terminée ! Le texte est logiquement {consistency_msg}. J'ai généré {len(queries)} requêtes pour tester la validité des arguments.",
                    "analyse_logique"
                )
                
                results["agents_results"]["propositional"] = {
                    "status": "success",
                    "consistency": is_consistent,
                    "queries_count": len(queries),
                    "belief_set_size": len(belief_set.content)
                }
            else:
                results["agents_results"]["propositional"] = {"status": "failed", "reason": status}
                
            self.metrics.interaction_count += 1
            
        except Exception as e:
            logger.error(f"Erreur analyse propositionnelle: {e}")
            results["agents_results"]["propositional"] = {"error": str(e)}
    
    async def _run_modal_analysis(self, text: str, results: Dict[str, Any]):
        """Exécute l'analyse de logique modale avec explications."""
        start_time = time.time()
        
        self.conversation_logger.log_agent_message(
            "AgentLogiqueModale",
            "Passons aux choses sérieuses ! Je vais analyser les modalités - ce qui est nécessaire, possible, ou obligatoire dans ce raisonnement...",
            "analyse_modale"
        )
        
        try:
            agent = self.agents["modal"]
            belief_set, status = await agent.text_to_belief_set(text)
            
            if belief_set:
                is_consistent, details = agent.is_consistent(belief_set)
                queries = await agent.generate_queries(text, belief_set)
                
                duration_ms = (time.time() - start_time) * 1000
                
                self.conversation_logger.log_tool_interaction(
                    "AgentLogiqueModale", "analyse_modale",
                    f"modalites_extraction:{len(text)}chars",
                    f"modal_coherent:{is_consistent},requetes_modales:{len(queries)}",
                    duration_ms
                )
                
                modal_complexity = "simple" if len(queries) < 3 else "complexe"
                self.conversation_logger.log_agent_message(
                    "AgentLogiqueModale",
                    f"Fascinant ! Ce texte présente une structure modale {modal_complexity}. Les modalités révèlent des nuances importantes dans l'argumentation.",
                    "analyse_modale"
                )
                
                results["agents_results"]["modal"] = {
                    "status": "success", 
                    "modal_consistency": is_consistent,
                    "modal_queries": len(queries),
                    "complexity": modal_complexity
                }
            else:
                results["agents_results"]["modal"] = {"status": "failed", "reason": status}
                
            self.metrics.interaction_count += 1
            
        except Exception as e:
            logger.error(f"Erreur analyse modale: {e}")
            results["agents_results"]["modal"] = {"error": str(e)}
    
    async def _run_synthesis_analysis(self, text: str, results: Dict[str, Any]):
        """Exécute la synthèse unifiée avec coordination pédagogique."""
        start_time = time.time()
        
        self.conversation_logger.log_agent_message(
            "AgentSynthese",
            "Maintenant, je vais combiner toutes ces analyses ! Je vais créer une synthèse cohérente de tous les résultats obtenus par mes collègues.",
            "synthese"
        )
        
        try:
            agent = self.agents["synthesis"]
            unified_report = await agent.synthesize_analysis(text)
            
            duration_ms = (time.time() - start_time) * 1000
            
            self.conversation_logger.log_tool_interaction(
                "AgentSynthese", "synthese_unifiee",
                f"resultats_combines:{len(results['agents_results'])}agents",
                f"synthese_generee:duree_{unified_report.total_processing_time_ms:.0f}ms",
                duration_ms
            )
            
            # Génération du rapport textuel
            text_report = await agent.generate_report(unified_report)
            
            self.conversation_logger.log_agent_message(
                "AgentSynthese",
                f"Synthèse terminée ! J'ai intégré les analyses rhétoriques et logiques. Le rapport final révèle des insights précieux sur la structure argumentative.",
                "synthese"
            )
            
            results["agents_results"]["synthesis"] = {
                "status": "success",
                "overall_validity": unified_report.overall_validity,
                "confidence_level": unified_report.confidence_level,
                "contradictions": len(unified_report.contradictions_identified),
                "recommendations": len(unified_report.recommendations),
                "text_report": text_report
            }
            
            self.metrics.interaction_count += 1
            
        except Exception as e:
            logger.error(f"Erreur synthèse: {e}")
            results["agents_results"]["synthesis"] = {"error": str(e)}
    
    async def _finalize_educational_analysis(self, results: Dict[str, Any]):
        """Finalise l'analyse avec coordination du Project Manager."""
        total_duration = time.time() - self.start_time
        
        # Calcul des métriques pédagogiques
        successful_agents = len([r for r in results["agents_results"].values() if r.get("status") == "success"])
        self.metrics.pedagogical_effectiveness = successful_agents / len(self.agents) if self.agents else 0
        self.metrics.complexity_score = min(1.0, self.metrics.interaction_count / 10.0)
        
        # Message final de coordination
        self.conversation_logger.log_agent_message(
            "ProjectManager",
            f"Excellente collaboration ! L'analyse est terminée en {total_duration:.1f} secondes. "
            f"{successful_agents}/{len(self.agents)} agents ont réussi leur mission. "
            f"Vous avez maintenant une compréhension complète de ce texte argumentatif !",
            "finalisation"
        )
        
        # Checkpoint pédagogique final
        self.conversation_logger.log_educational_checkpoint(
            "AnalyseComplete",
            f"Session d'apprentissage réussie avec {self.metrics.interaction_count} interactions et "
            f"{self.metrics.pedagogical_effectiveness:.0%} d'efficacité pédagogique"
        )
        
        # Stocker les conversations et métriques
        results["conversations"] = [msg.__dict__ for msg in self.conversation_logger.conversations]
        results["metrics"] = self.metrics.__dict__
        results["total_duration_seconds"] = total_duration

class EducationalTextLibrary:
    """Bibliothèque de textes pré-intégrés pour les démonstrations pédagogiques."""
    
    @staticmethod
    def get_sample_texts() -> Dict[str, Dict[str, str]]:
        """Retourne des textes d'exemple adaptés aux différents niveaux."""
        return {
            "L1_sophismes_basiques": {
                "title": "Débat sur les Réseaux Sociaux",
                "content": """
                Les réseaux sociaux sont dangereux car mon professeur l'a dit.
                Tous les jeunes qui utilisent Instagram deviennent narcissiques.
                Si on autorise TikTok, bientôt tous nos enfants seront addicts aux écrans.
                Donc, il faut interdire tous les réseaux sociaux.
                """,
                "expected_fallacies": ["Appel à l'autorité", "Généralisation abusive", "Pente glissante"],
                "difficulty": "Facile"
            },
            
            "L2_logique_propositionnelle": {
                "title": "Argumentation sur l'Écologie",
                "content": """
                Si nous réduisons les émissions de CO2, alors le réchauffement climatique ralentira.
                Nous devons soit investir dans le nucléaire, soit développer les énergies renouvelables.
                Si le réchauffement climatique ralentit, alors les écosystèmes se stabiliseront.
                Nous ne pouvons pas à la fois fermer les centrales nucléaires et ignorer les renouvelables.
                Donc, les écosystèmes peuvent se stabiliser.
                """,
                "expected_logic": ["Implications", "Disjonctions", "Négations"],
                "difficulty": "Modéré"
            },
            
            "L3_logique_modale": {
                "title": "Éthique de l'Intelligence Artificielle",
                "content": """
                Il est nécessaire que les IA respectent les droits humains.
                Il est possible que les IA développent une conscience.
                Si une IA peut souffrir, alors il est obligatoire de protéger ses droits.
                Il n'est pas certain que nous puissions contrôler une IA superintelligente.
                Donc, nous devons nous préparer à coexister avec des entités conscientes.
                """,
                "expected_modalities": ["Nécessité", "Possibilité", "Obligation", "Incertitude"],
                "difficulty": "Avancé"
            },
            
            "M1_orchestration_complexe": {
                "title": "Débat Multi-dimensionnel sur la Génétique",
                "content": """
                L'édition génétique CRISPR peut éliminer les maladies héréditaires.
                Cependant, tous les scientifiques qui soutiennent CRISPR sont financés par BigPharma.
                Si nous modifions les gènes, nous risquons de créer des inégalités génétiques.
                Il est nécessaire de réguler ces technologies, mais il est possible qu'elles sauvent des vies.
                Les parents ont le droit de vouloir le meilleur pour leurs enfants.
                Donc, nous devons soit accepter CRISPR avec régulation, soit interdire toute modification génétique.
                """,
                "complexity": "Multi-agents requis",
                "expected_analysis": ["Sophismes", "Logique propositionnelle", "Modalités", "Synthèse"],
                "difficulty": "Expert"
            }
        }

class EducationalShowcaseSystem:
    """
    Système principal de démonstration éducatif pour EPITA.
    Orchestration multi-agents avec interface pédagogique progressive.
    """
    
    def __init__(self, config: EducationalConfiguration):
        self.config = config
        self.project_manager = EducationalProjectManager(config)
        self.text_library = EducationalTextLibrary()
        self.llm_service = None
        self.jvm_initialized = False
        
        # Configuration des logs éducatifs
        self._setup_educational_logging()
        
    def _setup_educational_logging(self):
        """Configure le logging spécialisé pour l'éducation."""
        log_file = LOGS_DIR / f"educational_session_{TIMESTAMP}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(log_file, mode='w', encoding='utf-8')
            ]
        )
        
        logger.info(f"Système éducatif initialisé - Mode: {self.config.mode.value}, Niveau: {self.config.student_level}")
    
    async def initialize_system(self) -> bool:
        """Initialise le système éducatif complet."""
        print("=" * 80)
        print("🎓 SYSTÈME DE DÉMONSTRATION ÉDUCATIF EPITA")
        print("   Intelligence Symbolique - Analyse Rhétorique Multi-agents")
        print("=" * 80)
        print()
        
        try:
            # 1. Initialisation JVM pour TweetyProject
            print("🔧 Initialisation de l'environnement logique...")
            if EDUCATIONAL_COMPONENTS_AVAILABLE:
                self.jvm_initialized = initialize_jvm()
                if self.jvm_initialized:
                    print("   ✓ TweetyProject initialisé avec succès")
                else:
                    print("   ⚠ TweetyProject non disponible - mode dégradé")
            
            # 2. Initialisation du service LLM
            print("🤖 Initialisation des services d'intelligence artificielle...")
            if self.config.enable_real_llm:
                self.llm_service = create_llm_service("auto", prefer_azure=True)
                if self.llm_service:
                    print(f"   ✓ Service LLM configuré: {self.llm_service.service_id}")
                else:
                    print("   ❌ Impossible d'initialiser le service LLM")
                    return False
            
            # 3. Initialisation des agents pédagogiques
            print("👥 Initialisation des agents pédagogiques...")
            agents_ready = await self.project_manager.initialize_educational_agents(self.llm_service)
            if agents_ready:
                agent_count = len(self.project_manager.agents)
                print(f"   ✓ {agent_count} agents spécialisés prêts pour le niveau {self.config.student_level}")
            else:
                print("   ❌ Erreur lors de l'initialisation des agents")
                return False
            
            print()
            print("🚀 Système éducatif prêt ! Commençons l'apprentissage...")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation: {e}")
            print(f"   ❌ Erreur: {e}")
            return False
    
    async def run_educational_demo(self, text_content: str = None) -> Dict[str, Any]:
        """Exécute une démonstration éducative complète."""
        start_time = time.time()
        
        # Sélection du texte
        if not text_content:
            text_content = self._select_appropriate_text()
        
        print(f"\n📚 Texte sélectionné pour analyse (niveau {self.config.student_level}):")
        print("-" * 60)
        print(text_content[:200] + "..." if len(text_content) > 200 else text_content)
        print("-" * 60)
        
        # Exécution de l'analyse orchestrée
        print(f"\n🔬 Début de l'analyse collaborative...")
        
        results = await self.project_manager.orchestrate_educational_analysis(text_content)
        
        # Calcul des métriques finales
        total_duration = time.time() - start_time
        results["session_metrics"] = {
            "total_duration_seconds": total_duration,
            "student_level": self.config.student_level,
            "mode": self.config.mode.value,
            "agents_used": len(self.project_manager.agents),
            "conversations_captured": len(results.get("conversations", [])),
            "educational_effectiveness": results.get("metrics", {}).get("pedagogical_effectiveness", 0)
        }
        
        # Génération du rapport pédagogique
        educational_report = self._generate_educational_report(text_content, results)
        results["educational_report"] = educational_report
        
        print(f"\n✅ Analyse terminée en {total_duration:.1f} secondes!")
        print(f"📊 {len(results.get('conversations', []))} interactions capturées")
        print(f"🎯 Efficacité pédagogique: {results['session_metrics']['educational_effectiveness']:.0%}")
        
        return results
    
    def _select_appropriate_text(self) -> str:
        """Sélectionne un texte approprié selon la configuration."""
        sample_texts = self.text_library.get_sample_texts()
        
        # Sélection selon le niveau étudiant
        level_mapping = {
            "L1": "L1_sophismes_basiques",
            "L2": "L2_logique_propositionnelle", 
            "L3": "L3_logique_modale",
            "M1": "M1_orchestration_complexe",
            "M2": "M1_orchestration_complexe"
        }
        
        text_key = level_mapping.get(self.config.student_level, "L2_logique_propositionnelle")
        selected_text = sample_texts.get(text_key, sample_texts["L2_logique_propositionnelle"])
        
        return selected_text["content"].strip()
    
    def _generate_educational_report(self, text_analyzed: str, results: Dict[str, Any]) -> str:
        """Génère un rapport markdown éducatif avec explications pédagogiques."""
        report_lines = []
        
        # En-tête du rapport
        report_lines.extend([
            "# 🎓 RAPPORT D'ANALYSE ÉDUCATIF EPITA",
            "",
            f"**Mode d'apprentissage:** {self.config.mode.value.title()}",
            f"**Niveau étudiant:** {self.config.student_level}",
            f"**Langue:** {self.config.language.value}",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            ""
        ])
        
        # Texte analysé
        report_lines.extend([
            "## 📚 Texte Analysé",
            "",
            "```",
            text_analyzed,
            "```",
            ""
        ])
        
        # Métriques de session
        session_metrics = results.get("session_metrics", {})
        report_lines.extend([
            "## 📊 Métriques Pédagogiques",
            "",
            f"- **Durée totale:** {session_metrics.get('total_duration_seconds', 0):.1f} secondes",
            f"- **Agents utilisés:** {session_metrics.get('agents_used', 0)}",
            f"- **Interactions capturées:** {session_metrics.get('conversations_captured', 0)}",
            f"- **Efficacité pédagogique:** {session_metrics.get('educational_effectiveness', 0):.0%}",
            ""
        ])
        
        # Résultats par agent
        agents_results = results.get("agents_results", {})
        if agents_results:
            report_lines.extend([
                "## 🤖 Analyses des Agents Spécialisés",
                ""
            ])
            
            for agent_name, agent_result in agents_results.items():
                agent_title = {
                    "informal": "🎭 Agent d'Analyse Rhétorique",
                    "propositional": "⚡ Agent de Logique Propositionnelle", 
                    "modal": "🌀 Agent de Logique Modale",
                    "synthesis": "🔮 Agent de Synthèse"
                }.get(agent_name, f"🔧 Agent {agent_name.title()}")
                
                report_lines.extend([
                    f"### {agent_title}",
                    ""
                ])
                
                if agent_result.get("error"):
                    report_lines.extend([
                        f"❌ **Erreur:** {agent_result['error']}",
                        ""
                    ])
                else:
                    # Formatage spécifique selon le type d'agent
                    if agent_name == "informal":
                        fallacies_count = len(agent_result.get("fallacies", []))
                        report_lines.extend([
                            f"- **Sophismes détectés:** {fallacies_count}",
                            f"- **Analyse contextuelle:** Réussie" if fallacies_count > 0 else "- **Analyse contextuelle:** Texte bien construit",
                            ""
                        ])
                    
                    elif agent_name in ["propositional", "modal"]:
                        consistency = agent_result.get("consistency", False)
                        queries_count = agent_result.get("queries_count", 0)
                        report_lines.extend([
                            f"- **Cohérence logique:** {'✓ Cohérent' if consistency else '❌ Incohérent'}",
                            f"- **Requêtes générées:** {queries_count}",
                            ""
                        ])
                    
                    elif agent_name == "synthesis":
                        validity = agent_result.get("overall_validity", "Inconnue")
                        confidence = agent_result.get("confidence_level", 0)
                        report_lines.extend([
                            f"- **Validité globale:** {validity}",
                            f"- **Niveau de confiance:** {confidence:.0%}",
                            f"- **Contradictions:** {agent_result.get('contradictions', 0)}",
                            f"- **Recommandations:** {agent_result.get('recommendations', 0)}",
                            ""
                        ])
        
        # Conversations capturées
        conversations = results.get("conversations", [])
        if conversations and self.config.enable_conversation_capture:
            report_lines.extend([
                "## 💬 Conversations Entre Agents",
                "",
                "*Les agents ont collaboré et échangé leurs analyses:*",
                ""
            ])
            
            # Sélectionner les conversations les plus importantes
            important_conversations = [
                conv for conv in conversations 
                if conv.get("message_type") == "conversation" and 
                not conv.get("message", "").startswith("[TOOL]")
            ][:10]  # Limiter à 10 pour la lisibilité
            
            for conv in important_conversations:
                agent_name = conv.get("agent", "Unknown")
                message = conv.get("message", "")
                timestamp = conv.get("timestamp", "")
                
                report_lines.extend([
                    f"**{agent_name}** _{timestamp.split('T')[1][:8] if 'T' in timestamp else ''}_:",
                    f"> {message}",
                    ""
                ])
        
        # Recommandations pédagogiques
        report_lines.extend([
            "## 🎯 Recommandations Pédagogiques",
            ""
        ])
        
        effectiveness = session_metrics.get("educational_effectiveness", 0)
        if effectiveness >= 0.8:
            report_lines.extend([
                "✅ **Excellente session d'apprentissage !**",
                "- Tous les agents ont collaboré efficacement",
                "- Les concepts ont été bien assimilés",
                "- Prêt pour le niveau suivant",
                ""
            ])
        elif effectiveness >= 0.6:
            report_lines.extend([
                "⚠️ **Bonne session avec quelques difficultés**",
                "- La plupart des analyses ont réussi", 
                "- Réviser les concepts d'agents en échec",
                "- Refaire l'exercice pour consolider",
                ""
            ])
        else:
            report_lines.extend([
                "❌ **Session difficile - aide nécessaire**",
                "- Plusieurs agents ont échoué",
                "- Revoir les concepts fondamentaux",
                "- Demander assistance au professeur",
                ""
            ])
        
        # Prochaines étapes
        next_level_mapping = {
            "L1": "L2 - Logique propositionnelle",
            "L2": "L3 - Logique modale et orchestration",
            "L3": "M1 - Synthèse et recherche", 
            "M1": "M2 - Recherche avancée",
            "M2": "Doctorat - Recherche indépendante"
        }
        
        next_level = next_level_mapping.get(self.config.student_level, "Niveau suivant")
        report_lines.extend([
            "## 🚀 Prochaines Étapes",
            "",
            f"- **Objectif suivant:** {next_level}",
            "- **Concepts à maîtriser:** Selon les résultats de cette session",
            "- **Pratique recommandée:** Refaire l'analyse avec d'autres textes",
            ""
        ])
        
        # Pied de page
        report_lines.extend([
            "---",
            "",
            "*Rapport généré automatiquement par le Système de Démonstration Éducatif EPITA*",
            f"*Version 1.0.0 - {datetime.now().strftime('%Y-%m-%d')}*"
        ])
        
        return "\n".join(report_lines)
    
    async def save_educational_session(self, results: Dict[str, Any]) -> str:
        """Sauvegarde la session éducative avec tous les éléments."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Rapport markdown
        report_file = REPORTS_DIR / f"educational_report_{self.config.student_level}_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(results.get("educational_report", ""))
        
        # Données JSON complètes
        data_file = LOGS_DIR / f"educational_session_{self.config.student_level}_{timestamp}.json"
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        # Conversations séparées pour analyse
        conversations_file = LOGS_DIR / f"conversations_{self.config.student_level}_{timestamp}.json"
        with open(conversations_file, 'w', encoding='utf-8') as f:
            json.dump(results.get("conversations", []), f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Session éducative sauvegardée:")
        logger.info(f"  - Rapport: {report_file}")
        logger.info(f"  - Données: {data_file}") 
        logger.info(f"  - Conversations: {conversations_file}")
        
        return str(report_file)

async def demonstrate_educational_modes():
    """Démonstration des différents modes éducatifs."""
    print("🎓 DÉMONSTRATION DES MODES ÉDUCATIFS")
    print("=" * 50)
    
    # Démonstration mode débutant L1
    print("\n1️⃣ MODE DÉBUTANT (L1) - Détection de sophismes basiques")
    config_l1 = EducationalConfiguration(
        mode=EducationalMode.DEBUTANT,
        student_level="L1",
        enable_advanced_metrics=False,
        explanation_detail_level="detailed"
    )
    
    system_l1 = EducationalShowcaseSystem(config_l1)
    if await system_l1.initialize_system():
        results_l1 = await system_l1.run_educational_demo()
        report_file_l1 = await system_l1.save_educational_session(results_l1)
        print(f"✓ Rapport L1 généré: {report_file_l1}")
    
    print("\n" + "─" * 50)
    
    # Démonstration mode intermédiaire L3
    print("\n2️⃣ MODE INTERMÉDIAIRE (L3) - Logique modale et orchestration")
    config_l3 = EducationalConfiguration(
        mode=EducationalMode.INTERMEDIAIRE,
        student_level="L3", 
        enable_advanced_metrics=True,
        explanation_detail_level="medium"
    )
    
    system_l3 = EducationalShowcaseSystem(config_l3)
    if await system_l3.initialize_system():
        results_l3 = await system_l3.run_educational_demo()
        report_file_l3 = await system_l3.save_educational_session(results_l3)
        print(f"✓ Rapport L3 généré: {report_file_l3}")
    
    print("\n" + "─" * 50)
    
    # Démonstration mode expert M1
    print("\n3️⃣ MODE EXPERT (M1) - Orchestration complète multi-agents")
    config_m1 = EducationalConfiguration(
        mode=EducationalMode.EXPERT,
        student_level="M1",
        enable_advanced_metrics=True,
        enable_conversation_capture=True,
        explanation_detail_level="basic"
    )
    
    system_m1 = EducationalShowcaseSystem(config_m1)
    if await system_m1.initialize_system():
        results_m1 = await system_m1.run_educational_demo()
        report_file_m1 = await system_m1.save_educational_session(results_m1)
        print(f"✓ Rapport M1 généré: {report_file_m1}")
    
    print("\n🎯 DÉMONSTRATION TERMINÉE")
    print("Tous les rapports éducatifs ont été générés avec succès !")

def setup_demo_environment():
    """Configure l'environnement pour les démonstrations."""
    # Variables d'environnement pour forcer l'exécution authentique
    env_vars = {
        "FORCE_AUTHENTIC_EXECUTION": "true",
        "DISABLE_MOCKS_EDUCATIONAL": "true", 
        "ENABLE_EDUCATIONAL_MODE": "true",
        "EPITA_PEDAGOGICAL_SYSTEM": "true",
        "EDUCATIONAL_LANGUAGE": "fr",
        "EDUCATIONAL_VERBOSE": "true"
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    # Charger les variables d'environnement depuis .env si disponible
    try:
        from dotenv import load_dotenv, find_dotenv
        env_path = find_dotenv(filename=".env", usecwd=True, raise_error_if_not_found=False)
        if env_path:
            load_dotenv(env_path, override=True)
            print(f"✓ Configuration .env chargée depuis: {env_path}")
        else:
            print("⚠ Fichier .env non trouvé - utilisation configuration par défaut")
    except ImportError:
        print("⚠ python-dotenv non disponible - utilisation variables d'environnement")

def main():
    """Point d'entrée principal du système éducatif."""
    parser = argparse.ArgumentParser(
        description="Système de Démonstration Éducatif EPITA - Intelligence Symbolique",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  python educational_showcase_system.py --level L1 --mode debutant
  python educational_showcase_system.py --level L3 --mode intermediaire --lang fr
  python educational_showcase_system.py --level M1 --mode expert --demo-all
  python educational_showcase_system.py --demo-modes
        """
    )
    
    parser.add_argument("--level", choices=["L1", "L2", "L3", "M1", "M2"], 
                       default="L3", help="Niveau étudiant (défaut: L3)")
    parser.add_argument("--mode", choices=[mode.value for mode in EducationalMode],
                       default="intermediaire", help="Mode d'apprentissage (défaut: intermediaire)")
    parser.add_argument("--lang", choices=["fr", "en", "es"], default="fr", 
                       help="Langue de l'interface (défaut: fr)")
    parser.add_argument("--text", type=str, help="Texte personnalisé à analyser")
    parser.add_argument("--demo-modes", action="store_true", 
                       help="Démonstration de tous les modes éducatifs")
    parser.add_argument("--no-llm", action="store_true",
                       help="Désactiver les services LLM (mode dégradé)")
    parser.add_argument("--verbose", action="store_true",
                       help="Logging détaillé")
    
    args = parser.parse_args()
    
    # Configuration du logging selon la verbosité
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        os.environ["EDUCATIONAL_VERBOSE"] = "true"
    
    # Configuration de l'environnement
    setup_demo_environment()
    
    # Exécution selon les arguments
    if args.demo_modes:
        print("🚀 Lancement de la démonstration complète des modes éducatifs...")
        asyncio.run(demonstrate_educational_modes())
    else:
        # Session éducative personnalisée
        config = EducationalConfiguration(
            mode=EducationalMode(args.mode),
            language=EducationalLanguage(args.lang),
            student_level=args.level,
            enable_real_llm=not args.no_llm,
            enable_conversation_capture=True,
            enable_step_by_step=True,
            enable_interactive_feedback=True,
            enable_advanced_metrics=(args.level in ["M1", "M2"])
        )
        
        async def run_custom_session():
            system = EducationalShowcaseSystem(config)
            
            if await system.initialize_system():
                results = await system.run_educational_demo(args.text)
                report_file = await system.save_educational_session(results)
                
                print(f"\n🎉 Session éducative terminée avec succès !")
                print(f"📄 Rapport généré: {report_file}")
                print(f"📊 Efficacité: {results['session_metrics']['educational_effectiveness']:.0%}")
                print(f"⏱️ Durée: {results['session_metrics']['total_duration_seconds']:.1f}s")
            else:
                print("❌ Échec de l'initialisation du système éducatif")
                sys.exit(1)
        
        print(f"🎓 Lancement session éducative {args.level} - Mode {args.mode}")
        asyncio.run(run_custom_session())

if __name__ == "__main__":
    main()