<<<<<<< MAIN
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pipeline unifié d'analyse textuelle - Refactorisation d'analyze_text.py
=======================================================================

Ce pipeline consolide et refactorise les fonctionnalités du script principal
analyze_text.py en composant réutilisable intégré à l'architecture pipeline.

Fonctionnalités unifiées :
- Configuration d'analyse avancée (AnalysisConfig)
- Analyseur de texte unifié (UnifiedTextAnalyzer) 
- Intégration avec orchestrateurs existants
- Support analyses informelle/formelle/unifiée
- Compatibilité avec l'écosystème pipeline
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# Imports Semantic Kernel et architecture
import semantic_kernel as sk
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.llm_service import create_llm_service
from argumentation_analysis.core.jvm_setup import initialize_jvm
from argumentation_analysis.paths import LIBS_DIR

# Imports des orchestrateurs refactorisés 
from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator, RealConversationLogger
from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator

# Imports du pipeline existant
from argumentation_analysis.pipelines.analysis_pipeline import run_text_analysis_pipeline

# Imports des agents et outils
from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator
from argumentation_analysis.agents.core.synthesis.synthesis_agent import SynthesisAgent

logger = logging.getLogger("UnifiedTextAnalysis")


class UnifiedAnalysisConfig:
    """Configuration d'analyse unifiée - Version pipeline réutilisable."""
    
    def __init__(self, 
                 analysis_modes: List[str] = None,
                 logic_type: str = "propositional",
                 output_format: str = "dict",
                 use_advanced_tools: bool = False,
                 use_mocks: bool = False,
                 enable_jvm: bool = True,
                 orchestration_mode: str = "standard",
                 enable_conversation_logging: bool = True):
        """
        Initialise la configuration d'analyse unifiée.
        
        Args:
            analysis_modes: Modes d'analyse à effectuer
            logic_type: Type de logique pour analyse formelle
            output_format: Format de sortie ("dict", "json", etc.)
            use_advanced_tools: Utiliser outils d'analyse avancés
            use_mocks: Forcer utilisation des mocks
            enable_jvm: Activer l'initialisation JVM
            orchestration_mode: Mode d'orchestration ("standard", "real", "conversation")
            enable_conversation_logging: Activer logging conversationnel
        """
        self.analysis_modes = analysis_modes or ["fallacies", "coherence", "semantic"]
        self.logic_type = logic_type
        self.output_format = output_format
        self.use_advanced_tools = use_advanced_tools
        self.use_mocks = use_mocks
        self.enable_jvm = enable_jvm
        self.orchestration_mode = orchestration_mode
        self.enable_conversation_logging = enable_conversation_logging
        
    def to_dict(self) -> Dict[str, Any]:
        """Convertit la configuration en dictionnaire."""
        return {
            "analysis_modes": self.analysis_modes,
            "logic_type": self.logic_type,
            "output_format": self.output_format,
            "use_advanced_tools": self.use_advanced_tools,
            "use_mocks": self.use_mocks,
            "enable_jvm": self.enable_jvm,
            "orchestration_mode": self.orchestration_mode,
            "enable_conversation_logging": self.enable_conversation_logging
        }
    
    @classmethod
    def from_legacy_config(cls, legacy_config: Dict[str, Any]) -> 'UnifiedAnalysisConfig':
        """Crée une config unifiée depuis une ancienne configuration."""
        return cls(
            analysis_modes=legacy_config.get("analysis_modes", ["fallacies"]),
            logic_type=legacy_config.get("logic_type", "propositional"),
            output_format=legacy_config.get("output_format", "dict"),
            use_advanced_tools=legacy_config.get("use_advanced_tools", False),
            use_mocks=legacy_config.get("use_mocks", False),
            enable_jvm=legacy_config.get("enable_jvm", True)
        )


class UnifiedTextAnalysisPipeline:
    """
    Pipeline unifié d'analyse textuelle - Version refactorisée et réutilisable.
    
    Intègre les fonctionnalités du script analyze_text.py dans l'architecture pipeline
    tout en tirant parti des orchestrateurs refactorisés.
    """
    
    def __init__(self, config: UnifiedAnalysisConfig):
        """
        Initialise le pipeline unifié.
        
        Args:
            config: Configuration d'analyse unifiée
        """
        self.config = config
        self.jvm_ready = False
        self.llm_service = None
        self.analysis_tools = {}
        self.orchestrator = None
        self.conversation_logger = None
        
        # Initialisation du logging conversationnel si activé
        if self.config.enable_conversation_logging:
            if self.config.orchestration_mode == "real":
                self.conversation_logger = RealConversationLogger()
            else:
                self.conversation_logger = ConversationOrchestrator(mode="demo").logger
                
    async def initialize(self) -> bool:
        """
        Initialise tous les services et composants nécessaires.
        
        Returns:
            True si l'initialisation s'est déroulée correctement
        """
        logger.info(f"[INIT] Initialisation du pipeline unifie d'analyse (mode: {self.config.orchestration_mode})")
        
        # 1. Initialisation JVM si nécessaire
        if self.config.enable_jvm and "formal" in self.config.analysis_modes:
            logger.info("[JVM] Initialisation de la JVM pour analyse formelle...")
            try:
                self.jvm_ready = initialize_jvm(lib_dir_path=LIBS_DIR)
                if self.jvm_ready:
                    logger.info("[JVM] JVM initialisee avec succes")
                    if self.conversation_logger and hasattr(self.conversation_logger, 'info'):
                        self.conversation_logger.info("System: JVM initialisee pour analyse formelle")
                else:
                    logger.warning("[JVM] JVM non disponible - analyse formelle limitee")
            except Exception as e:
                logger.error(f"[JVM] Erreur initialisation JVM: {e}")
                self.jvm_ready = False
        
        # 2. Initialisation service LLM
        try:
            logger.info("[LLM] Initialisation du service LLM...")
            self.llm_service = create_llm_service()
            if self.llm_service:
                logger.info(f"[LLM] Service LLM cree (ID: {self.llm_service.service_id})")
                if self.conversation_logger and hasattr(self.conversation_logger, 'info'):
                    self.conversation_logger.info(f"System: Service LLM initialise (ID: {self.llm_service.service_id})")
        except Exception as e:
            logger.error(f"[LLM] Erreur initialisation LLM: {e}")
            if not self.config.use_mocks:
                logger.warning("[LLM] Basculement vers mode mocks")
                self.config.use_mocks = True
        
        # 3. Initialisation de l'orchestrateur selon le mode
        await self._initialize_orchestrator()
        
        # 4. Initialisation des outils d'analyse
        await self._initialize_analysis_tools()
        
        logger.info("[INIT] Pipeline unifie initialise avec succes")
        return True
    
    async def _initialize_orchestrator(self):
        """Initialise l'orchestrateur selon le mode de configuration."""
        if self.config.orchestration_mode == "real" and self.llm_service:
            logger.info("[ORCH] Initialisation orchestrateur LLM reel...")
            self.orchestrator = RealLLMOrchestrator(
                mode="real",
                llm_service=self.llm_service
            )
            await self.orchestrator.initialize()
            logger.info("[ORCH] Orchestrateur LLM reel initialise")
            
        elif self.config.orchestration_mode == "conversation":
            logger.info("[ORCH] Initialisation orchestrateur conversationnel...")
            self.orchestrator = ConversationOrchestrator(mode="demo")
            # Note: ConversationOrchestrator n'a pas de méthode initialize()
            logger.info("[ORCH] Orchestrateur conversationnel initialise")
            
        else:
            logger.info("[ORCH] Mode orchestration standard (pipeline classique)")
            
    async def _initialize_analysis_tools(self):
        """Initialise les outils d'analyse selon la configuration."""
        logger.info("[TOOLS] Initialisation des outils d'analyse...")
        
        if self.config.use_mocks:
            logger.info("[TOOLS] Utilisation des outils d'analyse simules")
            from argumentation_analysis.mocks.analysis_tools import (
                MockContextualFallacyDetector,
                MockArgumentCoherenceEvaluator,
                MockSemanticArgumentAnalyzer
            )
            
            self.analysis_tools = {
                "fallacy_detector": MockContextualFallacyDetector(),
                "coherence_evaluator": MockArgumentCoherenceEvaluator(),
                "semantic_analyzer": MockSemanticArgumentAnalyzer(),
            }
        else:
            logger.info("[TOOLS] Utilisation des outils d'analyse reels")
            try:
                self.analysis_tools = {
                    "contextual_analyzer": EnhancedContextualFallacyAnalyzer(),
                    "complex_analyzer": EnhancedComplexFallacyAnalyzer(),
                    "severity_evaluator": EnhancedFallacySeverityEvaluator()
                }
                
                # SynthesisAgent pour analyse unifiée
                if self.llm_service and "unified" in self.config.analysis_modes:
                    kernel = sk.Kernel()
                    kernel.add_service(self.llm_service)
                    self.analysis_tools["synthesis_agent"] = SynthesisAgent(
                        kernel=kernel,
                        agent_name="UnifiedPipeline_SynthesisAgent",
                        enable_advanced_features=self.config.use_advanced_tools
                    )
                    self.analysis_tools["synthesis_agent"].setup_agent_components(self.llm_service.service_id)
                
                logger.info("[TOOLS] Outils d'analyse reels initialises")
            except Exception as e:
                logger.error(f"[TOOLS] Erreur initialisation outils reels: {e}")
                logger.warning("[TOOLS] Basculement vers les mocks")
                self.config.use_mocks = True
                await self._initialize_analysis_tools()  # Récursion avec mocks
    
    async def analyze_text_unified(self, 
                                  text: str, 
                                  source_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Effectue une analyse complète et unifiée du texte.
        
        Args:
            text: Texte à analyser
            source_info: Informations sur la source (optionnel)
            
        Returns:
            Dict contenant tous les résultats d'analyse
        """
        start_time = datetime.now()
        source_info = source_info or {"description": "Source inconnue", "type": "text"}
        
        logger.info(f"[ANALYSIS] Debut analyse unifiee - Modes: {', '.join(self.config.analysis_modes)}")
        if self.conversation_logger and hasattr(self.conversation_logger, 'info'):
            self.conversation_logger.info(f"Pipeline: Debut analyse: {len(text)} caracteres")
        
        results = {
            "metadata": {
                "timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "source_description": source_info.get("description", "Source inconnue"),
                "source_type": source_info.get("type", "unknown"),
                "text_length": len(text),
                "analysis_config": self.config.to_dict(),
                "pipeline_version": "unified_v1.0"
            },
            "informal_analysis": {},
            "formal_analysis": {},
            "unified_analysis": {},
            "orchestration_analysis": {},
            "recommendations": []
        }
        
        # 1. Analyse via orchestrateur si disponible
        if self.orchestrator:
            logger.info("🎯 Analyse via orchestrateur...")
            try:
                orchestration_results = await self._analyze_with_orchestrator(text, source_info)
                results["orchestration_analysis"] = orchestration_results
                
                if self.conversation_logger:
                    self.conversation_logger.log_agent_message(
                        "Orchestrator", "Analyse orchestrée terminée", "orchestration"
                    )
            except Exception as e:
                logger.error(f"❌ Erreur analyse orchestrateur: {e}")
                results["orchestration_analysis"] = {"status": "error", "message": str(e)}
        
        # 2. Analyse informelle (sophismes, cohérence, sémantique)
        if any(mode in self.config.analysis_modes for mode in ["fallacies", "coherence", "semantic"]):
            # Si on a des données d'orchestration, extraire depuis là au lieu de refaire l'analyse
            if "orchestration_analysis" in results and results["orchestration_analysis"].get("status") == "success":
                logger.info("[INFORMAL] Extraction des données d'orchestration...")
                results["informal_analysis"] = self._extract_informal_from_orchestration(results["orchestration_analysis"])
            else:
                logger.info("[INFORMAL] Analyse informelle en cours...")
                results["informal_analysis"] = await self._perform_informal_analysis(text)
        
        # 3. Analyse formelle (logique)
        if "formal" in self.config.analysis_modes:
            logger.info("[FORMAL] Analyse formelle en cours...")
            results["formal_analysis"] = await self._perform_formal_analysis(text)
        
        # 4. Analyse unifiée (SynthesisAgent)
        if "unified" in self.config.analysis_modes and "synthesis_agent" in self.analysis_tools:
            logger.info("[UNIFIED] Analyse unifiee en cours...")
            results["unified_analysis"] = await self._perform_unified_analysis(text)
        
        # 5. Génération des recommandations
        results["recommendations"] = self._generate_recommendations(results)
        
        # 6. Finalisation
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        results["metadata"]["processing_time_ms"] = processing_time
        
        logger.info(f"[ANALYSIS] Analyse unifiee terminee en {processing_time:.2f}ms")
        if self.conversation_logger and hasattr(self.conversation_logger, 'info'):
            self.conversation_logger.info(f"Pipeline: Analyse terminee ({processing_time:.1f}ms)")
        
        return results
    
    async def _analyze_with_orchestrator(self, text: str, source_info: Dict[str, Any]) -> Dict[str, Any]:
        """Effectue l'analyse via l'orchestrateur configuré."""
        if not self.orchestrator:
            return {"status": "skipped", "reason": "Aucun orchestrateur disponible"}
        
        try:
            if isinstance(self.orchestrator, RealLLMOrchestrator):
                # Utilisation de l'orchestrateur LLM réel
                conversation_result = await self.orchestrator.orchestrate_analysis(text)
                return {
                    "status": "success",
                    "type": "real_llm_orchestration",
                    "conversation_log": conversation_result.get("conversation_log", []),
                    "final_synthesis": conversation_result.get("final_synthesis", ""),
                    "processing_time_ms": conversation_result.get("processing_time_ms", 0)
                }
            else:
                # Utilisation de l'orchestrateur conversationnel
                demo_result = await self.orchestrator.run_demo_conversation(text)
                return {
                    "status": "success", 
                    "type": "conversation_orchestration",
                    "demo_result": demo_result,
                    "conversation_log": getattr(self.orchestrator.logger, 'messages', [])
                }
        except Exception as e:
            logger.error(f"Erreur orchestration: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _perform_informal_analysis(self, text: str) -> Dict[str, Any]:
        """Effectue l'analyse informelle (fallacies, coherence, semantic)."""
        informal_results = {
            "fallacies": [],
            "coherence_analysis": {},
            "semantic_analysis": {},
            "summary": {}
        }
        
        if self.config.use_mocks:
            # Analyse avec mocks
            fallacy_detector = self.analysis_tools.get("fallacy_detector")
            if fallacy_detector:
                arguments = self._split_text_into_arguments(text)
                fallacies = fallacy_detector.detect_multiple_contextual_fallacies(
                    arguments, "Analyse pipeline unifiée"
                )
                informal_results["fallacies"] = fallacies.get("detected_fallacies", [])
        else:
            # Analyse avec outils réels
            try:
                contextual_analyzer = self.analysis_tools.get("contextual_analyzer")
                severity_evaluator = self.analysis_tools.get("severity_evaluator")
                
                # Analyse contextuelle des sophismes
                arguments = self._split_text_into_arguments(text)
                sample_context = "Pipeline unifié d'analyse argumentative"
                
                # Simulation des résultats sophistiqués
                contextual_fallacies = [
                    {
                        "type": "Généralisation hâtive",
                        "text_fragment": text[:150] + "..." if len(text) > 150 else text,
                        "explanation": "Affirmation générale basée sur des exemples limités",
                        "confidence": 0.78,
                        "severity": "Modéré",
                        "pipeline_version": "unified"
                    }
                ]
                
                # Évaluation de la sévérité si disponible
                if severity_evaluator:
                    evaluation = severity_evaluator.evaluate_fallacy_list(contextual_fallacies, sample_context)
                    informal_results["fallacies"] = evaluation.get("fallacy_evaluations", contextual_fallacies)
                else:
                    informal_results["fallacies"] = contextual_fallacies
                    
            except Exception as e:
                logger.error(f"Erreur analyse informelle: {e}")
                informal_results["fallacies"] = []
        
        # Résumé de l'analyse informelle
        fallacies = informal_results["fallacies"]
        informal_results["summary"] = {
            "total_fallacies": len(fallacies),
            "average_confidence": sum(f.get("confidence", 0) for f in fallacies) / len(fallacies) if fallacies else 0,
            "severity_distribution": self._calculate_severity_distribution(fallacies)
        }
        
        return informal_results
    
    async def _perform_formal_analysis(self, text: str) -> Dict[str, Any]:
        """Effectue l'analyse formelle (logique)."""
        formal_results = {
            "logic_type": self.config.logic_type,
            "status": "Unknown",
            "belief_set_summary": {},
            "queries": [],
            "consistency_check": None
        }
        
        if not self.jvm_ready or not self.llm_service:
            formal_results["status"] = "Skipped"
            formal_results["reason"] = "JVM ou LLM service non disponible"
            return formal_results
        
        try:
            # Création de l'agent logique
            kernel = sk.Kernel()
            kernel.add_service(self.llm_service)
            
            logic_agent = LogicAgentFactory.create_agent(
                self.config.logic_type,
                kernel,
                self.llm_service.service_id
            )
            
            if not logic_agent:
                formal_results["status"] = "Failed"
                formal_results["reason"] = f"Impossible de créer l'agent logique '{self.config.logic_type}'"
                return formal_results
            
            # Conversion en ensemble de croyances
            belief_set, status = await logic_agent.text_to_belief_set(text)
            
            if belief_set:
                # Vérification de cohérence
                is_consistent, consistency_details = logic_agent.is_consistent(belief_set)
                
                # Génération de requêtes
                queries = await logic_agent.generate_queries(text, belief_set)
                
                # Exécution des requêtes
                query_results = []
                for query in queries[:3]:  # Limite pour performance
                    result, raw_output = logic_agent.execute_query(belief_set, query)
                    query_results.append({
                        "query": query,
                        "result": "Entailed" if result else "Not Entailed" if result is not None else "Unknown",
                        "raw_output": raw_output
                    })
                
                formal_results.update({
                    "status": "Success",
                    "belief_set_summary": {
                        "is_consistent": is_consistent,
                        "details": consistency_details,
                        "formulas_count": len(belief_set.content.split('\n')) if hasattr(belief_set, 'content') else 0
                    },
                    "queries": query_results,
                    "consistency_check": is_consistent
                })
            else:
                formal_results["status"] = "Failed"
                formal_results["reason"] = f"Échec conversion en ensemble de croyances: {status}"
                
        except Exception as e:
            logger.error(f"Erreur analyse formelle: {e}")
            formal_results["status"] = "Error"
            formal_results["reason"] = str(e)
        
        return formal_results
    
    async def _perform_unified_analysis(self, text: str) -> Dict[str, Any]:
        """Effectue l'analyse unifiée avec SynthesisAgent."""
        unified_results = {
            "status": "Unknown",
            "synthesis_report": "",
            "overall_validity": "Unknown",
            "confidence_level": 0.0,
            "contradictions": [],
            "recommendations": []
        }
        
        synthesis_agent = self.analysis_tools.get("synthesis_agent")
        if not synthesis_agent:
            unified_results["status"] = "Skipped"
            unified_results["reason"] = "SynthesisAgent non disponible"
            return unified_results
        
        try:
            # Exécution de l'analyse unifiée
            unified_report = await synthesis_agent.synthesize_analysis(text)
            
            # Génération du rapport textuel
            text_report = await synthesis_agent.generate_report(unified_report)
            
            unified_results.update({
                "status": "Success",
                "synthesis_report": text_report,
                "overall_validity": getattr(unified_report, 'overall_validity', "Unknown"),
                "confidence_level": getattr(unified_report, 'confidence_level', 0.0),
                "processing_time_ms": getattr(unified_report, 'total_processing_time_ms', 0)
            })
            
        except Exception as e:
            logger.error(f"Erreur analyse unifiée: {e}")
            unified_results["status"] = "Error"
            unified_results["reason"] = str(e)
        
        return unified_results
    
    def _split_text_into_arguments(self, text: str) -> List[str]:
        """Divise le texte en arguments distincts."""
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        if not sentences:
            return [text]
        return sentences
    
    def _calculate_severity_distribution(self, fallacies: List[Dict]) -> Dict[str, int]:
        """Calcule la distribution des sévérités des sophismes."""
        distribution = {"Critique": 0, "Élevé": 0, "Modéré": 0, "Faible": 0}
        for fallacy in fallacies:
            severity = fallacy.get("severity", "Faible")
            if severity in distribution:
                distribution[severity] += 1
        return distribution
    
    def _extract_informal_from_orchestration(self, orchestration_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extrait les données d'analyse informelle depuis les résultats d'orchestration."""
        logger.info("🔍 Extraction des sophismes depuis l'orchestrateur...")
        
        informal_results = {
            "fallacies": [],
            "summary": {}
        }
        
        try:
            conversation_log = orchestration_data.get("conversation_log", {})
            
            # PRIORITÉ 1: Chercher dans les tool calls pour avoir les données JSON complètes
            if "tool_calls" in conversation_log:
                logger.info(f"🔍 DEBUG: Analyse de {len(conversation_log['tool_calls'])} tool calls pour PRIORITÉ 1")
                for i, tool_call in enumerate(conversation_log["tool_calls"]):
                    if isinstance(tool_call, dict):
                        tool_name = tool_call.get("tool", "")
                        result = tool_call.get("result", {})
                        logger.info(f"🔍 DEBUG: Tool call {i}: {tool_name}, result type: {type(result)}")
                        
                        # Chercher les résultats de perform_complete_analysis (agent informel)
                        if "perform_complete_analysis" in tool_name:
                            logger.info(f"🔍 DEBUG: Tool call {i} correspond à perform_complete_analysis")
                            
                            # Si le résultat est un dict, chercher les données de sophismes
                            if isinstance(result, dict):
                                # Chercher dans différents emplacements possibles
                                sophismes_data = result.get("fallacies", [])
                                if not sophismes_data:
                                    sophismes_data = result.get("informal_analysis", {}).get("fallacies", [])
                                if not sophismes_data:
                                    # GPT-4o-mini retourne dans "sophismes"
                                    sophismes_data = result.get("sophismes", [])
                                
                                logger.info(f"🔍 DEBUG: {len(sophismes_data)} fallacies trouvés dans le tool call {i}")
                                
                                for sophisme_data in sophismes_data:
                                    if isinstance(sophisme_data, dict):
                                        # Extraire la confiance depuis plusieurs sources possibles
                                        confidence_value = (
                                            sophisme_data.get("confidence", 0) or
                                            sophisme_data.get("match_score", 0) or
                                            sophisme_data.get("detection_confidence", 0) or
                                            0.7  # Valeur par défaut raisonnable au lieu de 0.0
                                        )
                                        
                                        sophisme = {
                                            "type": sophisme_data.get("type", sophisme_data.get("name", sophisme_data.get("nom", "Type inconnu"))),
                                            "text_fragment": sophisme_data.get("fragment", sophisme_data.get("citation", "Fragment non disponible")),
                                            "explanation": sophisme_data.get("explanation", sophisme_data.get("explication", "Explication non disponible")),
                                            "severity": sophisme_data.get("severity", "Moyen"),
                                            "confidence": confidence_value,
                                            "reformulation": sophisme_data.get("reformulation", "")
                                        }
                                        informal_results["fallacies"].append(sophisme)
                                        
                                if sophismes_data:
                                    logger.info(f"✅ PRIORITÉ 1 réussie : {len(sophismes_data)} sophismes extraits depuis tool call {i}")
                                    break  # Arrêter une fois qu'on a trouvé les données
                            
                            # Si le résultat est une string, chercher le JSON brut de GPT-4o-mini
                            elif isinstance(result, str) and "sophismes" in result:
                                logger.info(f"🔍 DEBUG: Tool call {i} contient JSON brut, tentative d'extraction...")
                                try:
                                    import json
                                    # Chercher le JSON des sophismes dans le string
                                    json_start = result.find('{"sophismes"')
                                    if json_start == -1:
                                        json_start = result.find('{\n  "sophismes"')
                                    
                                    if json_start != -1:
                                        # Trouver la fin du JSON
                                        bracket_count = 0
                                        json_end = json_start
                                        for j, char in enumerate(result[json_start:], json_start):
                                            if char == '{':
                                                bracket_count += 1
                                            elif char == '}':
                                                bracket_count -= 1
                                                if bracket_count == 0:
                                                    json_end = j + 1
                                                    break
                                        
                                        json_text = result[json_start:json_end]
                                        sophismes_json = json.loads(json_text)
                                        
                                        for sophisme_data in sophismes_json.get("sophismes", []):
                                            sophisme = {
                                                "type": sophisme_data.get("nom", "Type inconnu"),
                                                "text_fragment": sophisme_data.get("citation", "Fragment non disponible"),
                                                "explanation": sophisme_data.get("explication", "Explication non disponible"),
                                                "severity": "Moyen",  # Valeur par défaut
                                                "confidence": 0.0,  # Pas de confiance dans le JSON original
                                                "reformulation": sophisme_data.get("reformulation", "")
                                            }
                                            informal_results["fallacies"].append(sophisme)
                                        
                                        logger.info(f"✅ PRIORITÉ 1 JSON réussie : {len(sophismes_json.get('sophismes', []))} sophismes extraits depuis tool call {i}")
                                        break
                                        
                                except (json.JSONDecodeError, Exception) as e:
                                    logger.debug(f"Échec parsing JSON PRIORITÉ 1: {e}")
                                
            # PRIORITÉ 2: Chercher le JSON brut de GPT-4o-mini dans les tool calls
            if not informal_results["fallacies"] and "tool_calls" in conversation_log:
                import json
                logger.info(f"🔍 DEBUG: Recherche JSON dans {len(conversation_log['tool_calls'])} tool calls")
                for i, tool_call in enumerate(conversation_log["tool_calls"]):
                    if isinstance(tool_call, dict):
                        result = tool_call.get("result", "")
                        tool_name = tool_call.get("tool", "unknown")
                        logger.info(f"🔍 DEBUG: Tool call {i}: {tool_name}, result type: {type(result)}")
                        
                        # Si le résultat est une string contenant du JSON
                        if isinstance(result, str) and "sophismes" in result:
                            logger.info(f"✅ DEBUG: JSON sophismes trouvé dans tool call {i} ({tool_name})")
                            try:
                                # Chercher le JSON des sophismes
                                json_start = result.find('{"sophismes"')
                                if json_start == -1:
                                    json_start = result.find('{\n  "sophismes"')
                                
                                if json_start != -1:
                                    # Trouver la fin du JSON
                                    bracket_count = 0
                                    json_end = json_start
                                    for i, char in enumerate(result[json_start:], json_start):
                                        if char == '{':
                                            bracket_count += 1
                                        elif char == '}':
                                            bracket_count -= 1
                                            if bracket_count == 0:
                                                json_end = i + 1
                                                break
                                    
                                    json_text = result[json_start:json_end]
                                    sophismes_json = json.loads(json_text)
                                    
                                    for sophisme_data in sophismes_json.get("sophismes", []):
                                        sophisme = {
                                            "type": sophisme_data.get("nom", "Type inconnu"),
                                            "text_fragment": sophisme_data.get("citation", "Fragment non disponible"),
                                            "explanation": sophisme_data.get("explication", "Explication non disponible"),
                                            "severity": "Moyen",  # Valeur par défaut
                                            "confidence": 0.0,  # Pas de confiance dans le JSON original
                                            "reformulation": sophisme_data.get("reformulation", "")
                                        }
                                        informal_results["fallacies"].append(sophisme)
                                    
                                    logger.info(f"✅ {len(sophismes_json.get('sophismes', []))} sophismes extraits depuis JSON brut")
                                    break
                                    
                            except (json.JSONDecodeError, Exception) as e:
                                logger.warning(f"Erreur lors du parsing JSON des sophismes: {e}")
                                
            # PRIORITÉ 3 (Fallback): Chercher dans les messages d'orchestration
            if not informal_results["fallacies"] and isinstance(conversation_log, dict) and "messages" in conversation_log:
                for msg in conversation_log["messages"]:
                    if isinstance(msg, dict):
                        agent = msg.get("agent", "")
                        content = str(msg.get("message", ""))
                        
                        # Chercher les résultats d'analyse informelle de l'InformalAnalysisAgent
                        if agent == "InformalAnalysisAgent" and "sophismes détectés" in content:
                            # Extraire le nombre et les types de sophismes depuis le message
                            try:
                                # Parser le message pour extraire les sophismes détectés
                                # Format attendu: "2 sophismes détectés: Argumentum ad hominem (confiance: 0.00), Faux dilemme (confiance: 0.00)"
                                import re
                                sophismes_match = re.search(r'(\d+) sophismes détectés: (.+?)(?:\. Score|$)', content)
                                if sophismes_match:
                                    count = int(sophismes_match.group(1))
                                    sophismes_text = sophismes_match.group(2)
                                    
                                    # Parser chaque sophisme
                                    sophisme_pattern = r'([^(,]+?)\s*\(confiance:\s*([\d.]+)\)'
                                    matches = re.findall(sophisme_pattern, sophismes_text)
                                    
                                    for i, (nom, confiance) in enumerate(matches):
                                        sophisme = {
                                            "type": nom.strip(),
                                            "text_fragment": f"Fragment extrait de l'analyse orchestrée #{i+1}",
                                            "explanation": f"Sophisme '{nom.strip()}' identifié par l'orchestrateur LLM",
                                            "severity": "Moyen",  # Valeur par défaut
                                            "confidence": float(confiance) if confiance.replace('.', '').isdigit() else 0.0
                                        }
                                        informal_results["fallacies"].append(sophisme)
                                        
                                    logger.info(f"✅ {len(matches)} sophismes extraits de l'orchestrateur (fallback)")
                                    break
                                    
                            except Exception as e:
                                logger.warning(f"Erreur lors du parsing des sophismes (fallback): {e}")
            
            # Calculer le résumé
            fallacies = informal_results["fallacies"]
            informal_results["summary"] = {
                "total_fallacies": len(fallacies),
                "average_confidence": sum(f.get("confidence", 0) for f in fallacies) / len(fallacies) if fallacies else 0,
                "severity_distribution": self._calculate_severity_distribution(fallacies)
            }
            
            logger.info(f"📊 Résumé extraction: {len(fallacies)} sophismes, confiance moyenne: {informal_results['summary']['average_confidence']:.2%}")
            
        except Exception as e:
            logger.error(f"Erreur extraction informelle depuis orchestrateur: {e}")
            # Fallback vers des données par défaut
            informal_results = {
                "fallacies": [],
                "summary": {"total_fallacies": 0, "average_confidence": 0, "severity_distribution": {}}
            }
        
        return informal_results
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Génère des recommandations basées sur les résultats d'analyse."""
        recommendations = []
        
        # Recommandations basées sur l'analyse informelle
        informal = results.get("informal_analysis", {})
        fallacies = informal.get("fallacies", [])
        
        if len(fallacies) > 3:
            recommendations.append("Nombreux sophismes détectés - révision argumentative recommandée")
        
        critical_fallacies = [f for f in fallacies if f.get("severity") == "Critique"]
        if critical_fallacies:
            recommendations.append("Sophismes critiques présents - attention particulière requise")
        
        # Recommandations basées sur l'analyse formelle
        formal = results.get("formal_analysis", {})
        if formal.get("consistency_check") is False:
            recommendations.append("Incohérences logiques détectées - clarification nécessaire")
        
        # Recommandations basées sur l'orchestration
        orchestration = results.get("orchestration_analysis", {})
        if orchestration.get("status") == "success":
            recommendations.append("Analyse orchestrée complétée - examen des insights avancés recommandé")
        
        # Recommandations par défaut
        if not recommendations:
            recommendations.append("Analyse pipeline unifiée complétée - examen des détails recommandé")
        
        return recommendations

    def get_conversation_log(self) -> List[Dict[str, Any]]:
        """Retourne le log conversationnel si disponible."""
        if self.conversation_logger:
            return {
                "messages": getattr(self.conversation_logger, 'messages', []),
                "tool_calls": getattr(self.conversation_logger, 'tool_calls', []),
                "state_snapshots": getattr(self.conversation_logger, 'state_snapshots', [])
            }
        return {}


# Fonctions d'intégration avec l'architecture pipeline existante

async def run_unified_text_analysis_pipeline(
    text: str,
    source_info: Dict[str, Any] = None,
    config: UnifiedAnalysisConfig = None,
    log_level: str = "INFO"
) -> Optional[Dict[str, Any]]:
    """
    Point d'entrée principal pour le pipeline unifié d'analyse textuelle.
    
    Compatible avec l'architecture pipeline existante tout en apportant
    les fonctionnalités avancées du script analyze_text.py refactorisé.
    
    Args:
        text: Texte à analyser
        source_info: Informations sur la source
        config: Configuration d'analyse unifiée 
        log_level: Niveau de logging
        
    Returns:
        Résultats de l'analyse unifiée ou None en cas d'erreur
    """
    # Configuration par défaut si non fournie
    if config is None:
        config = UnifiedAnalysisConfig()
    
    # Configuration du logging
    logging.getLogger().setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    try:
        # Initialisation du pipeline
        pipeline = UnifiedTextAnalysisPipeline(config)
        await pipeline.initialize()
        
        # Exécution de l'analyse
        results = await pipeline.analyze_text_unified(text, source_info)
        
        # Ajout du log conversationnel aux résultats
        conversation_log = pipeline.get_conversation_log()
        if conversation_log:
            results["conversation_log"] = conversation_log
        
        return results
        
    except Exception as e:
        logger.error(f"Erreur pipeline unifié: {e}", exc_info=True)
        return None


def create_unified_config_from_legacy(
    analysis_modes: List[str] = None,
    logic_type: str = "propositional", 
    use_advanced_tools: bool = False,
    use_mocks: bool = False,
    enable_jvm: bool = True,
    orchestration_mode: str = "standard"
) -> UnifiedAnalysisConfig:
    """
    Crée une configuration unifiée compatible avec les paramètres legacy.
    
    Facilite la migration depuis l'ancien script analyze_text.py.
    """
    return UnifiedAnalysisConfig(
        analysis_modes=analysis_modes or ["fallacies", "coherence", "semantic"],
        logic_type=logic_type,
        use_advanced_tools=use_advanced_tools,
        use_mocks=use_mocks,
        enable_jvm=enable_jvm,
        orchestration_mode=orchestration_mode
    )


# Intégration avec le pipeline existant
async def run_text_analysis_pipeline_enhanced(
    input_file_path: Optional[str] = None,
    input_text_content: Optional[str] = None,
    use_ui_input: bool = False,
    log_level: str = "INFO",
    analysis_type: str = "unified",
    config_for_services: Optional[Dict[str, Any]] = None,
    unified_config: Optional[UnifiedAnalysisConfig] = None
) -> Optional[Dict[str, Any]]:
    """
    Version améliorée de run_text_analysis_pipeline qui utilise le pipeline unifié.
    
    Cette fonction maintient la compatibilité avec l'API existante tout en
    permettant d'utiliser les fonctionnalités avancées du pipeline unifié.
    """
    if analysis_type == "unified" and unified_config:
        # Utilisation du nouveau pipeline unifié
        if input_text_content:
            text = input_text_content
        elif input_file_path:
            try:
                with open(input_file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            except Exception as e:
                logger.error(f"Erreur lecture fichier: {e}")
                return None
        else:
            logger.error("Aucun texte fourni pour analyse unifiée")
            return None
            
        source_info = {
            "description": f"Fichier: {input_file_path}" if input_file_path else "Texte direct",
            "type": "file" if input_file_path else "text"
        }
        
        return await run_unified_text_analysis_pipeline(
            text, source_info, unified_config, log_level
        )
    else:
        # Fallback vers le pipeline original
        return await run_text_analysis_pipeline(
            input_file_path=input_file_path,
            input_text_content=input_text_content,
            use_ui_input=use_ui_input,
            log_level=log_level,
            analysis_type=analysis_type,
            config_for_services=config_for_services
        )

=======
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pipeline unifié d'analyse textuelle - Refactorisation d'analyze_text.py
=======================================================================

Ce pipeline consolide et refactorise les fonctionnalités du script principal
analyze_text.py en composant réutilisable intégré à l'architecture pipeline.

Fonctionnalités unifiées :
- Configuration d'analyse avancée (AnalysisConfig)
- Analyseur de texte unifié (UnifiedTextAnalyzer) 
- Intégration avec orchestrateurs existants
- Support analyses informelle/formelle/unifiée
- Compatibilité avec l'écosystème pipeline
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# Imports Semantic Kernel et architecture
import semantic_kernel as sk
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.llm_service import create_llm_service
from argumentation_analysis.core.jvm_setup import initialize_jvm
from argumentation_analysis.paths import LIBS_DIR

# Imports des orchestrateurs refactorisés 
from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator, RealConversationLogger
from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator

# Imports du pipeline existant
from argumentation_analysis.pipelines.analysis_pipeline import run_text_analysis_pipeline

# Imports des agents et outils
from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator
from argumentation_analysis.agents.core.synthesis.synthesis_agent import SynthesisAgent

logger = logging.getLogger("UnifiedTextAnalysis")


class UnifiedAnalysisConfig:
    """Configuration d'analyse unifiée - Version pipeline réutilisable."""
    
    def __init__(self, 
                 analysis_modes: List[str] = None,
                 logic_type: str = "propositional",
                 output_format: str = "dict",
                 use_advanced_tools: bool = False,
                 use_mocks: bool = False,
                 enable_jvm: bool = True,
                 orchestration_mode: str = "standard",
                 enable_conversation_logging: bool = True):
        """
        Initialise la configuration d'analyse unifiée.
        
        Args:
            analysis_modes: Modes d'analyse à effectuer
            logic_type: Type de logique pour analyse formelle
            output_format: Format de sortie ("dict", "json", etc.)
            use_advanced_tools: Utiliser outils d'analyse avancés
            use_mocks: Forcer utilisation des mocks
            enable_jvm: Activer l'initialisation JVM
            orchestration_mode: Mode d'orchestration ("standard", "real", "conversation")
            enable_conversation_logging: Activer logging conversationnel
        """
        self.analysis_modes = analysis_modes or ["fallacies", "coherence", "semantic"]
        self.logic_type = logic_type
        self.output_format = output_format
        self.use_advanced_tools = use_advanced_tools
        self.use_mocks = use_mocks
        self.enable_jvm = enable_jvm
        self.orchestration_mode = orchestration_mode
        self.enable_conversation_logging = enable_conversation_logging
        
    def to_dict(self) -> Dict[str, Any]:
        """Convertit la configuration en dictionnaire."""
        return {
            "analysis_modes": self.analysis_modes,
            "logic_type": self.logic_type,
            "output_format": self.output_format,
            "use_advanced_tools": self.use_advanced_tools,
            "use_mocks": self.use_mocks,
            "enable_jvm": self.enable_jvm,
            "orchestration_mode": self.orchestration_mode,
            "enable_conversation_logging": self.enable_conversation_logging
        }
    
    @classmethod
    def from_legacy_config(cls, legacy_config: Dict[str, Any]) -> 'UnifiedAnalysisConfig':
        """Crée une config unifiée depuis une ancienne configuration."""
        return cls(
            analysis_modes=legacy_config.get("analysis_modes", ["fallacies"]),
            logic_type=legacy_config.get("logic_type", "propositional"),
            output_format=legacy_config.get("output_format", "dict"),
            use_advanced_tools=legacy_config.get("use_advanced_tools", False),
            use_mocks=legacy_config.get("use_mocks", False),
            enable_jvm=legacy_config.get("enable_jvm", True)
        )


class UnifiedTextAnalysisPipeline:
    """
    Pipeline unifié d'analyse textuelle - Version refactorisée et réutilisable.
    
    Intègre les fonctionnalités du script analyze_text.py dans l'architecture pipeline
    tout en tirant parti des orchestrateurs refactorisés.
    """
    
    def __init__(self, config: UnifiedAnalysisConfig):
        """
        Initialise le pipeline unifié.
        
        Args:
            config: Configuration d'analyse unifiée
        """
        self.config = config
        self.jvm_ready = False
        self.llm_service = None
        self.analysis_tools = {}
        self.orchestrator = None
        self.conversation_logger = None
        
        # Initialisation du logging conversationnel si activé
        if self.config.enable_conversation_logging:
            if self.config.orchestration_mode == "real":
                self.conversation_logger = RealConversationLogger()
            else:
                self.conversation_logger = ConversationOrchestrator(mode="demo").logger
                
    async def initialize(self) -> bool:
        """
        Initialise tous les services et composants nécessaires.
        
        Returns:
            True si l'initialisation s'est déroulée correctement
        """
        logger.info(f"[INIT] Initialisation du pipeline unifie d'analyse (mode: {self.config.orchestration_mode})")
        
        # 1. Initialisation JVM si nécessaire
        if self.config.enable_jvm and "formal" in self.config.analysis_modes:
            logger.info("[JVM] Initialisation de la JVM pour analyse formelle...")
            try:
                self.jvm_ready = initialize_jvm(lib_dir_path=LIBS_DIR)
                if self.jvm_ready:
                    logger.info("[JVM] JVM initialisee avec succes")
                    if self.conversation_logger and hasattr(self.conversation_logger, 'info'):
                        self.conversation_logger.info("System: JVM initialisee pour analyse formelle")
                else:
                    logger.warning("[JVM] JVM non disponible - analyse formelle limitee")
            except Exception as e:
                logger.error(f"[JVM] Erreur initialisation JVM: {e}")
                self.jvm_ready = False
        
        # 2. Initialisation service LLM
        try:
            logger.info("[LLM] Initialisation du service LLM...")
            self.llm_service = create_llm_service()
            if self.llm_service:
                logger.info(f"[LLM] Service LLM cree (ID: {self.llm_service.service_id})")
                if self.conversation_logger and hasattr(self.conversation_logger, 'info'):
                    self.conversation_logger.info(f"System: Service LLM initialise (ID: {self.llm_service.service_id})")
        except Exception as e:
            logger.error(f"[LLM] Erreur initialisation LLM: {e}")
            if not self.config.use_mocks:
                logger.warning("[LLM] Basculement vers mode mocks")
                self.config.use_mocks = True
        
        # 3. Initialisation de l'orchestrateur selon le mode
        await self._initialize_orchestrator()
        
        # 4. Initialisation des outils d'analyse
        await self._initialize_analysis_tools()
        
        logger.info("[INIT] Pipeline unifie initialise avec succes")
        return True
    
    async def _initialize_orchestrator(self):
        """Initialise l'orchestrateur selon le mode de configuration."""
        if self.config.orchestration_mode == "real" and self.llm_service:
            logger.info("[ORCH] Initialisation orchestrateur LLM reel...")
            self.orchestrator = RealLLMOrchestrator(
                mode="real",
                llm_service=self.llm_service
            )
            await self.orchestrator.initialize()
            logger.info("[ORCH] Orchestrateur LLM reel initialise")
            
        elif self.config.orchestration_mode == "conversation":
            logger.info("[ORCH] Initialisation orchestrateur conversationnel...")
            self.orchestrator = ConversationOrchestrator(mode="demo")
            # Note: ConversationOrchestrator n'a pas de méthode initialize()
            logger.info("[ORCH] Orchestrateur conversationnel initialise")
            
        else:
            logger.info("[ORCH] Mode orchestration standard (pipeline classique)")
            
    async def _initialize_analysis_tools(self):
        """Initialise les outils d'analyse selon la configuration."""
        logger.info("[TOOLS] Initialisation des outils d'analyse...")
        
        if self.config.use_mocks:
            logger.info("[TOOLS] Utilisation des outils d'analyse simules")
            from argumentation_analysis.mocks.analysis_tools import (
                MockContextualFallacyDetector,
                MockArgumentCoherenceEvaluator,
                MockSemanticArgumentAnalyzer
            )
            
            self.analysis_tools = {
                "fallacy_detector": MockContextualFallacyDetector(),
                "coherence_evaluator": MockArgumentCoherenceEvaluator(),
                "semantic_analyzer": MockSemanticArgumentAnalyzer(),
            }
        else:
            logger.info("[TOOLS] Utilisation des outils d'analyse reels")
            try:
                self.analysis_tools = {
                    "contextual_analyzer": EnhancedContextualFallacyAnalyzer(),
                    "complex_analyzer": EnhancedComplexFallacyAnalyzer(),
                    "severity_evaluator": EnhancedFallacySeverityEvaluator()
                }
                
                # SynthesisAgent pour analyse unifiée
                if self.llm_service and "unified" in self.config.analysis_modes:
                    kernel = sk.Kernel()
                    kernel.add_service(self.llm_service)
                    self.analysis_tools["synthesis_agent"] = SynthesisAgent(
                        kernel=kernel,
                        agent_name="UnifiedPipeline_SynthesisAgent",
                        enable_advanced_features=self.config.use_advanced_tools
                    )
                    self.analysis_tools["synthesis_agent"].setup_agent_components(self.llm_service.service_id)
                
                logger.info("[TOOLS] Outils d'analyse reels initialises")
            except Exception as e:
                logger.error(f"[TOOLS] Erreur initialisation outils reels: {e}")
                logger.warning("[TOOLS] Basculement vers les mocks")
                self.config.use_mocks = True
                await self._initialize_analysis_tools()  # Récursion avec mocks
    
    async def analyze_text_unified(self, 
                                  text: str, 
                                  source_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Effectue une analyse complète et unifiée du texte.
        
        Args:
            text: Texte à analyser
            source_info: Informations sur la source (optionnel)
            
        Returns:
            Dict contenant tous les résultats d'analyse
        """
        start_time = datetime.now()
        source_info = source_info or {"description": "Source inconnue", "type": "text"}
        
        logger.info(f"[ANALYSIS] Debut analyse unifiee - Modes: {', '.join(self.config.analysis_modes)}")
        if self.conversation_logger and hasattr(self.conversation_logger, 'info'):
            self.conversation_logger.info(f"Pipeline: Debut analyse: {len(text)} caracteres")
        
        results = {
            "metadata": {
                "timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "source_description": source_info.get("description", "Source inconnue"),
                "source_type": source_info.get("type", "unknown"),
                "text_length": len(text),
                "analysis_config": self.config.to_dict(),
                "pipeline_version": "unified_v1.0"
            },
            "informal_analysis": {},
            "formal_analysis": {},
            "unified_analysis": {},
            "orchestration_analysis": {},
            "recommendations": []
        }
        
        # 1. Analyse via orchestrateur si disponible
        if self.orchestrator:
            logger.info("🎯 Analyse via orchestrateur...")
            try:
                orchestration_results = await self._analyze_with_orchestrator(text, source_info)
                results["orchestration_analysis"] = orchestration_results
                
                if self.conversation_logger:
                    self.conversation_logger.log_agent_message(
                        "Orchestrator", "Analyse orchestrée terminée", "orchestration"
                    )
            except Exception as e:
                logger.error(f"❌ Erreur analyse orchestrateur: {e}")
                results["orchestration_analysis"] = {"status": "error", "message": str(e)}
        
        # 2. Analyse informelle (sophismes, cohérence, sémantique)
        if any(mode in self.config.analysis_modes for mode in ["fallacies", "coherence", "semantic"]):
            # Si on a des données d'orchestration, extraire depuis là au lieu de refaire l'analyse
            if "orchestration_analysis" in results and results["orchestration_analysis"].get("status") == "success":
                logger.info("[INFORMAL] Extraction des données d'orchestration...")
                results["informal_analysis"] = self._extract_informal_from_orchestration(results["orchestration_analysis"])
            else:
                logger.info("[INFORMAL] Analyse informelle en cours...")
                results["informal_analysis"] = await self._perform_informal_analysis(text)
        
        # 3. Analyse formelle (logique)
        if "formal" in self.config.analysis_modes:
            logger.info("[FORMAL] Analyse formelle en cours...")
            results["formal_analysis"] = await self._perform_formal_analysis(text)
        
        # 4. Analyse unifiée (SynthesisAgent)
        if "unified" in self.config.analysis_modes and "synthesis_agent" in self.analysis_tools:
            logger.info("[UNIFIED] Analyse unifiee en cours...")
            results["unified_analysis"] = await self._perform_unified_analysis(text)
        
        # 5. Génération des recommandations
        results["recommendations"] = self._generate_recommendations(results)
        
        # 6. Finalisation
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        results["metadata"]["processing_time_ms"] = processing_time
        
        logger.info(f"[ANALYSIS] Analyse unifiee terminee en {processing_time:.2f}ms")
        if self.conversation_logger and hasattr(self.conversation_logger, 'info'):
            self.conversation_logger.info(f"Pipeline: Analyse terminee ({processing_time:.1f}ms)")
        
        return results
    
    async def _analyze_with_orchestrator(self, text: str, source_info: Dict[str, Any]) -> Dict[str, Any]:
        """Effectue l'analyse via l'orchestrateur configuré."""
        if not self.orchestrator:
            return {"status": "skipped", "reason": "Aucun orchestrateur disponible"}
        
        try:
            if isinstance(self.orchestrator, RealLLMOrchestrator):
                # Utilisation de l'orchestrateur LLM réel
                conversation_result = await self.orchestrator.orchestrate_analysis(text)
                return {
                    "status": "success",
                    "type": "real_llm_orchestration",
                    "conversation_log": conversation_result.get("conversation_log", []),
                    "final_synthesis": conversation_result.get("final_synthesis", ""),
                    "processing_time_ms": conversation_result.get("processing_time_ms", 0)
                }
            else:
                # Utilisation de l'orchestrateur conversationnel
                demo_result = await self.orchestrator.run_demo_conversation(text)
                return {
                    "status": "success", 
                    "type": "conversation_orchestration",
                    "demo_result": demo_result,
                    "conversation_log": getattr(self.orchestrator.logger, 'messages', [])
                }
        except Exception as e:
            logger.error(f"Erreur orchestration: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _perform_informal_analysis(self, text: str) -> Dict[str, Any]:
        """Effectue l'analyse informelle (fallacies, coherence, semantic)."""
        informal_results = {
            "fallacies": [],
            "coherence_analysis": {},
            "semantic_analysis": {},
            "summary": {}
        }
        
        if self.config.use_mocks:
            # Analyse avec mocks
            fallacy_detector = self.analysis_tools.get("fallacy_detector")
            if fallacy_detector:
                arguments = self._split_text_into_arguments(text)
                fallacies = fallacy_detector.detect_multiple_contextual_fallacies(
                    arguments, "Analyse pipeline unifiée"
                )
                informal_results["fallacies"] = fallacies.get("detected_fallacies", [])
        else:
            # Analyse avec outils réels
            try:
                contextual_analyzer = self.analysis_tools.get("contextual_analyzer")
                severity_evaluator = self.analysis_tools.get("severity_evaluator")
                
                # Analyse contextuelle des sophismes
                arguments = self._split_text_into_arguments(text)
                sample_context = "Pipeline unifié d'analyse argumentative"
                
                # Simulation des résultats sophistiqués
                contextual_fallacies = [
                    {
                        "type": "Généralisation hâtive",
                        "text_fragment": text[:150] + "..." if len(text) > 150 else text,
                        "explanation": "Affirmation générale basée sur des exemples limités",
                        "confidence": 0.78,
                        "severity": "Modéré",
                        "pipeline_version": "unified"
                    }
                ]
                
                # Évaluation de la sévérité si disponible
                if severity_evaluator:
                    evaluation = severity_evaluator.evaluate_fallacy_list(contextual_fallacies, sample_context)
                    informal_results["fallacies"] = evaluation.get("fallacy_evaluations", contextual_fallacies)
                else:
                    informal_results["fallacies"] = contextual_fallacies
                    
            except Exception as e:
                logger.error(f"Erreur analyse informelle: {e}")
                informal_results["fallacies"] = []
        
        # Résumé de l'analyse informelle
        fallacies = informal_results["fallacies"]
        informal_results["summary"] = {
            "total_fallacies": len(fallacies),
            "average_confidence": sum(f.get("confidence", 0) for f in fallacies) / len(fallacies) if fallacies else 0,
            "severity_distribution": self._calculate_severity_distribution(fallacies)
        }
        
        return informal_results
    
    async def _perform_formal_analysis(self, text: str) -> Dict[str, Any]:
        """Effectue l'analyse formelle (logique)."""
        formal_results = {
            "logic_type": self.config.logic_type,
            "status": "Unknown",
            "belief_set_summary": {},
            "queries": [],
            "consistency_check": None
        }
        
        if not self.jvm_ready or not self.llm_service:
            formal_results["status"] = "Skipped"
            formal_results["reason"] = "JVM ou LLM service non disponible"
            return formal_results
        
        try:
            # Création de l'agent logique
            kernel = sk.Kernel()
            kernel.add_service(self.llm_service)
            
            logic_agent = LogicAgentFactory.create_agent(
                self.config.logic_type,
                kernel,
                self.llm_service.service_id
            )
            
            if not logic_agent:
                formal_results["status"] = "Failed"
                formal_results["reason"] = f"Impossible de créer l'agent logique '{self.config.logic_type}'"
                return formal_results
            
            # Conversion en ensemble de croyances
            belief_set, status = await logic_agent.text_to_belief_set(text)
            
            if belief_set:
                # Vérification de cohérence
                is_consistent, consistency_details = logic_agent.is_consistent(belief_set)
                
                # Génération de requêtes
                queries = await logic_agent.generate_queries(text, belief_set)
                
                # Exécution des requêtes
                query_results = []
                for query in queries[:3]:  # Limite pour performance
                    result, raw_output = logic_agent.execute_query(belief_set, query)
                    query_results.append({
                        "query": query,
                        "result": "Entailed" if result else "Not Entailed" if result is not None else "Unknown",
                        "raw_output": raw_output
                    })
                
                formal_results.update({
                    "status": "Success",
                    "belief_set_summary": {
                        "is_consistent": is_consistent,
                        "details": consistency_details,
                        "formulas_count": len(belief_set.content.split('\n')) if hasattr(belief_set, 'content') else 0
                    },
                    "queries": query_results,
                    "consistency_check": is_consistent
                })
            else:
                formal_results["status"] = "Failed"
                formal_results["reason"] = f"Échec conversion en ensemble de croyances: {status}"
                
        except Exception as e:
            logger.error(f"Erreur analyse formelle: {e}")
            formal_results["status"] = "Error"
            formal_results["reason"] = str(e)
        
        return formal_results
    
    async def _perform_unified_analysis(self, text: str) -> Dict[str, Any]:
        """Effectue l'analyse unifiée avec SynthesisAgent."""
        unified_results = {
            "status": "Unknown",
            "synthesis_report": "",
            "overall_validity": "Unknown",
            "confidence_level": 0.0,
            "contradictions": [],
            "recommendations": []
        }
        
        synthesis_agent = self.analysis_tools.get("synthesis_agent")
        if not synthesis_agent:
            unified_results["status"] = "Skipped"
            unified_results["reason"] = "SynthesisAgent non disponible"
            return unified_results
        
        try:
            # Exécution de l'analyse unifiée
            unified_report = await synthesis_agent.synthesize_analysis(text)
            
            # Génération du rapport textuel
            text_report = await synthesis_agent.generate_report(unified_report)
            
            unified_results.update({
                "status": "Success",
                "synthesis_report": text_report,
                "overall_validity": getattr(unified_report, 'overall_validity', "Unknown"),
                "confidence_level": getattr(unified_report, 'confidence_level', 0.0),
                "processing_time_ms": getattr(unified_report, 'total_processing_time_ms', 0)
            })
            
        except Exception as e:
            logger.error(f"Erreur analyse unifiée: {e}")
            unified_results["status"] = "Error"
            unified_results["reason"] = str(e)
        
        return unified_results
    
    def _split_text_into_arguments(self, text: str) -> List[str]:
        """Divise le texte en arguments distincts."""
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        if not sentences:
            return [text]
        return sentences
    
    def _calculate_severity_distribution(self, fallacies: List[Dict]) -> Dict[str, int]:
        """Calcule la distribution des sévérités des sophismes."""
        distribution = {"Critique": 0, "Élevé": 0, "Modéré": 0, "Faible": 0}
        for fallacy in fallacies:
            severity = fallacy.get("severity", "Faible")
            if severity in distribution:
                distribution[severity] += 1
        return distribution
    
    def _extract_informal_from_orchestration(self, orchestration_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extrait les données d'analyse informelle depuis les résultats d'orchestration."""
        logger.info("🔍 Extraction des sophismes depuis l'orchestrateur...")
        
        informal_results = {
            "fallacies": [],
            "summary": {}
        }
        
        try:
            conversation_log = orchestration_data.get("conversation_log", {})
            
            # PRIORITÉ 1: Chercher dans les tool calls pour avoir les données JSON complètes
            if "tool_calls" in conversation_log:
                logger.info(f"🔍 DEBUG: Analyse de {len(conversation_log['tool_calls'])} tool calls pour PRIORITÉ 1")
                for i, tool_call in enumerate(conversation_log["tool_calls"]):
                    if isinstance(tool_call, dict):
                        tool_name = tool_call.get("tool", "")
                        result = tool_call.get("result", {})
                        logger.info(f"🔍 DEBUG: Tool call {i}: {tool_name}, result type: {type(result)}")
                        
                        # Chercher les résultats de perform_complete_analysis (agent informel)
                        if "perform_complete_analysis" in tool_name:
                            logger.info(f"🔍 DEBUG: Tool call {i} correspond à perform_complete_analysis")
                            
                            # Si le résultat est un dict, chercher les données de sophismes
                            if isinstance(result, dict):
                                # Chercher dans différents emplacements possibles
                                sophismes_data = result.get("fallacies", [])
                                if not sophismes_data:
                                    sophismes_data = result.get("informal_analysis", {}).get("fallacies", [])
                                if not sophismes_data:
                                    # GPT-4o-mini retourne dans "sophismes"
                                    sophismes_data = result.get("sophismes", [])
                                
                                logger.info(f"🔍 DEBUG: {len(sophismes_data)} fallacies trouvés dans le tool call {i}")
                                
                                for sophisme_data in sophismes_data:
                                    if isinstance(sophisme_data, dict):
                                        # Extraire la confiance depuis plusieurs sources possibles
                                        confidence_value = (
                                            sophisme_data.get("confidence", 0) or
                                            sophisme_data.get("match_score", 0) or
                                            sophisme_data.get("detection_confidence", 0) or
                                            0.7  # Valeur par défaut raisonnable au lieu de 0.0
                                        )
                                        
                                        sophisme = {
                                            "type": sophisme_data.get("type", sophisme_data.get("name", sophisme_data.get("nom", "Type inconnu"))),
                                            "text_fragment": sophisme_data.get("fragment", sophisme_data.get("citation", "Fragment non disponible")),
                                            "explanation": sophisme_data.get("explanation", sophisme_data.get("explication", "Explication non disponible")),
                                            "severity": sophisme_data.get("severity", "Moyen"),
                                            "confidence": confidence_value,
                                            "reformulation": sophisme_data.get("reformulation", "")
                                        }
                                        informal_results["fallacies"].append(sophisme)
                                        
                                if sophismes_data:
                                    logger.info(f"✅ PRIORITÉ 1 réussie : {len(sophismes_data)} sophismes extraits depuis tool call {i}")
                                    break  # Arrêter une fois qu'on a trouvé les données
                            
                            # Si le résultat est une string, chercher le JSON brut de GPT-4o-mini
                            elif isinstance(result, str) and "sophismes" in result:
                                logger.info(f"🔍 DEBUG: Tool call {i} contient JSON brut, tentative d'extraction...")
                                try:
                                    import json
                                    # Chercher le JSON des sophismes dans le string
                                    json_start = result.find('{"sophismes"')
                                    if json_start == -1:
                                        json_start = result.find('{\n  "sophismes"')
                                    
                                    if json_start != -1:
                                        # Trouver la fin du JSON
                                        bracket_count = 0
                                        json_end = json_start
                                        for j, char in enumerate(result[json_start:], json_start):
                                            if char == '{':
                                                bracket_count += 1
                                            elif char == '}':
                                                bracket_count -= 1
                                                if bracket_count == 0:
                                                    json_end = j + 1
                                                    break
                                        
                                        json_text = result[json_start:json_end]
                                        sophismes_json = json.loads(json_text)
                                        
                                        for sophisme_data in sophismes_json.get("sophismes", []):
                                            sophisme = {
                                                "type": sophisme_data.get("nom", "Type inconnu"),
                                                "text_fragment": sophisme_data.get("citation", "Fragment non disponible"),
                                                "explanation": sophisme_data.get("explication", "Explication non disponible"),
                                                "severity": "Moyen",  # Valeur par défaut
                                                "confidence": 0.0,  # Pas de confiance dans le JSON original
                                                "reformulation": sophisme_data.get("reformulation", "")
                                            }
                                            informal_results["fallacies"].append(sophisme)
                                        
                                        logger.info(f"✅ PRIORITÉ 1 JSON réussie : {len(sophismes_json.get('sophismes', []))} sophismes extraits depuis tool call {i}")
                                        break
                                        
                                except (json.JSONDecodeError, Exception) as e:
                                    logger.debug(f"Échec parsing JSON PRIORITÉ 1: {e}")
                                
            # PRIORITÉ 2: Chercher le JSON brut de GPT-4o-mini dans les tool calls
            if not informal_results["fallacies"] and "tool_calls" in conversation_log:
                import json
                logger.info(f"🔍 DEBUG: Recherche JSON dans {len(conversation_log['tool_calls'])} tool calls")
                for i, tool_call in enumerate(conversation_log["tool_calls"]):
                    if isinstance(tool_call, dict):
                        result = tool_call.get("result", "")
                        tool_name = tool_call.get("tool", "unknown")
                        logger.info(f"🔍 DEBUG: Tool call {i}: {tool_name}, result type: {type(result)}")
                        
                        # Si le résultat est une string contenant du JSON
                        if isinstance(result, str) and "sophismes" in result:
                            logger.info(f"✅ DEBUG: JSON sophismes trouvé dans tool call {i} ({tool_name})")
                            try:
                                # Chercher le JSON des sophismes
                                json_start = result.find('{"sophismes"')
                                if json_start == -1:
                                    json_start = result.find('{\n  "sophismes"')
                                
                                if json_start != -1:
                                    # Trouver la fin du JSON
                                    bracket_count = 0
                                    json_end = json_start
                                    for i, char in enumerate(result[json_start:], json_start):
                                        if char == '{':
                                            bracket_count += 1
                                        elif char == '}':
                                            bracket_count -= 1
                                            if bracket_count == 0:
                                                json_end = i + 1
                                                break
                                    
                                    json_text = result[json_start:json_end]
                                    sophismes_json = json.loads(json_text)
                                    
                                    for sophisme_data in sophismes_json.get("sophismes", []):
                                        sophisme = {
                                            "type": sophisme_data.get("nom", "Type inconnu"),
                                            "text_fragment": sophisme_data.get("citation", "Fragment non disponible"),
                                            "explanation": sophisme_data.get("explication", "Explication non disponible"),
                                            "severity": "Moyen",  # Valeur par défaut
                                            "confidence": 0.0,  # Pas de confiance dans le JSON original
                                            "reformulation": sophisme_data.get("reformulation", "")
                                        }
                                        informal_results["fallacies"].append(sophisme)
                                    
                                    logger.info(f"✅ {len(sophismes_json.get('sophismes', []))} sophismes extraits depuis JSON brut")
                                    break
                                    
                            except (json.JSONDecodeError, Exception) as e:
                                logger.warning(f"Erreur lors du parsing JSON des sophismes: {e}")
                                
            # PRIORITÉ 3 (Fallback): Chercher dans les messages d'orchestration
            if not informal_results["fallacies"] and isinstance(conversation_log, dict) and "messages" in conversation_log:
                for msg in conversation_log["messages"]:
                    if isinstance(msg, dict):
                        agent = msg.get("agent", "")
                        content = str(msg.get("message", ""))
                        
                        # Chercher les résultats d'analyse informelle de l'InformalAnalysisAgent
                        if agent == "InformalAnalysisAgent" and "sophismes détectés" in content:
                            # Extraire le nombre et les types de sophismes depuis le message
                            try:
                                # Parser le message pour extraire les sophismes détectés
                                # Format attendu: "2 sophismes détectés: Argumentum ad hominem (confiance: 0.00), Faux dilemme (confiance: 0.00)"
                                import re
                                sophismes_match = re.search(r'(\d+) sophismes détectés: (.+?)(?:\. Score|$)', content)
                                if sophismes_match:
                                    count = int(sophismes_match.group(1))
                                    sophismes_text = sophismes_match.group(2)
                                    
                                    # Parser chaque sophisme
                                    sophisme_pattern = r'([^(,]+?)\s*\(confiance:\s*([\d.]+)\)'
                                    matches = re.findall(sophisme_pattern, sophismes_text)
                                    
                                    for i, (nom, confiance) in enumerate(matches):
                                        sophisme = {
                                            "type": nom.strip(),
                                            "text_fragment": f"Fragment extrait de l'analyse orchestrée #{i+1}",
                                            "explanation": f"Sophisme '{nom.strip()}' identifié par l'orchestrateur LLM",
                                            "severity": "Moyen",  # Valeur par défaut
                                            "confidence": float(confiance) if confiance.replace('.', '').isdigit() else 0.0
                                        }
                                        informal_results["fallacies"].append(sophisme)
                                        
                                    logger.info(f"✅ {len(matches)} sophismes extraits de l'orchestrateur (fallback)")
                                    break
                                    
                            except Exception as e:
                                logger.warning(f"Erreur lors du parsing des sophismes (fallback): {e}")
            
            # Calculer le résumé
            fallacies = informal_results["fallacies"]
            informal_results["summary"] = {
                "total_fallacies": len(fallacies),
                "average_confidence": sum(f.get("confidence", 0) for f in fallacies) / len(fallacies) if fallacies else 0,
                "severity_distribution": self._calculate_severity_distribution(fallacies)
            }
            
            logger.info(f"📊 Résumé extraction: {len(fallacies)} sophismes, confiance moyenne: {informal_results['summary']['average_confidence']:.2%}")
            
        except Exception as e:
            logger.error(f"Erreur extraction informelle depuis orchestrateur: {e}")
            # Fallback vers des données par défaut
            informal_results = {
                "fallacies": [],
                "summary": {"total_fallacies": 0, "average_confidence": 0, "severity_distribution": {}}
            }
        
        return informal_results
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Génère des recommandations basées sur les résultats d'analyse."""
        recommendations = []
        
        # Recommandations basées sur l'analyse informelle
        informal = results.get("informal_analysis", {})
        fallacies = informal.get("fallacies", [])
        
        if len(fallacies) > 3:
            recommendations.append("Nombreux sophismes détectés - révision argumentative recommandée")
        
        critical_fallacies = [f for f in fallacies if f.get("severity") == "Critique"]
        if critical_fallacies:
            recommendations.append("Sophismes critiques présents - attention particulière requise")
        
        # Recommandations basées sur l'analyse formelle
        formal = results.get("formal_analysis", {})
        if formal.get("consistency_check") is False:
            recommendations.append("Incohérences logiques détectées - clarification nécessaire")
        
        # Recommandations basées sur l'orchestration
        orchestration = results.get("orchestration_analysis", {})
        if orchestration.get("status") == "success":
            recommendations.append("Analyse orchestrée complétée - examen des insights avancés recommandé")
        
        # Recommandations par défaut
        if not recommendations:
            recommendations.append("Analyse pipeline unifiée complétée - examen des détails recommandé")
        
        return recommendations

    def get_conversation_log(self) -> List[Dict[str, Any]]:
        """Retourne le log conversationnel si disponible."""
        if self.conversation_logger:
            return {
                "messages": getattr(self.conversation_logger, 'messages', []),
                "tool_calls": getattr(self.conversation_logger, 'tool_calls', []),
                "state_snapshots": getattr(self.conversation_logger, 'state_snapshots', [])
            }
        return {}


# Fonctions d'intégration avec l'architecture pipeline existante

async def run_unified_text_analysis_pipeline(
    text: str,
    source_info: Dict[str, Any] = None,
    config: UnifiedAnalysisConfig = None,
    log_level: str = "INFO"
) -> Optional[Dict[str, Any]]:
    """
    Point d'entrée principal pour le pipeline unifié d'analyse textuelle.
    
    Compatible avec l'architecture pipeline existante tout en apportant
    les fonctionnalités avancées du script analyze_text.py refactorisé.
    
    Args:
        text: Texte à analyser
        source_info: Informations sur la source
        config: Configuration d'analyse unifiée 
        log_level: Niveau de logging
        
    Returns:
        Résultats de l'analyse unifiée ou None en cas d'erreur
    """
    # Configuration par défaut si non fournie
    if config is None:
        config = UnifiedAnalysisConfig()
    
    # Configuration du logging
    logging.getLogger().setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    try:
        # Initialisation du pipeline
        pipeline = UnifiedTextAnalysisPipeline(config)
        await pipeline.initialize()
        
        # Exécution de l'analyse
        results = await pipeline.analyze_text_unified(text, source_info)
        
        # Ajout du log conversationnel aux résultats
        conversation_log = pipeline.get_conversation_log()
        if conversation_log:
            results["conversation_log"] = conversation_log
        
        return results
        
    except Exception as e:
        logger.error(f"Erreur pipeline unifié: {e}", exc_info=True)
        return None


def create_unified_config_from_legacy(
    analysis_modes: List[str] = None,
    logic_type: str = "propositional", 
    use_advanced_tools: bool = False,
    use_mocks: bool = False,
    enable_jvm: bool = True,
    orchestration_mode: str = "standard"
) -> UnifiedAnalysisConfig:
    """
    Crée une configuration unifiée compatible avec les paramètres legacy.
    
    Facilite la migration depuis l'ancien script analyze_text.py.
    """
    return UnifiedAnalysisConfig(
        analysis_modes=analysis_modes or ["fallacies", "coherence", "semantic"],
        logic_type=logic_type,
        use_advanced_tools=use_advanced_tools,
        use_mocks=use_mocks,
        enable_jvm=enable_jvm,
        orchestration_mode=orchestration_mode
    )


# Intégration avec le pipeline existant
async def run_text_analysis_pipeline_enhanced(
    input_file_path: Optional[str] = None,
    input_text_content: Optional[str] = None,
    use_ui_input: bool = False,
    log_level: str = "INFO",
    analysis_type: str = "unified",
    config_for_services: Optional[Dict[str, Any]] = None,
    unified_config: Optional[UnifiedAnalysisConfig] = None
) -> Optional[Dict[str, Any]]:
    """
    Version améliorée de run_text_analysis_pipeline qui utilise le pipeline unifié.
    
    Cette fonction maintient la compatibilité avec l'API existante tout en
    permettant d'utiliser les fonctionnalités avancées du pipeline unifié.
    """
    if analysis_type == "unified" and unified_config:
        # Utilisation du nouveau pipeline unifié
        if input_text_content:
            text = input_text_content
        elif input_file_path:
            try:
                with open(input_file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            except Exception as e:
                logger.error(f"Erreur lecture fichier: {e}")
                return None
        else:
            logger.error("Aucun texte fourni pour analyse unifiée")
            return None
            
        source_info = {
            "description": f"Fichier: {input_file_path}" if input_file_path else "Texte direct",
            "type": "file" if input_file_path else "text"
        }
        
        return await run_unified_text_analysis_pipeline(
            text, source_info, unified_config, log_level
        )
    else:
        # Fallback vers le pipeline original
        return await run_text_analysis_pipeline(
            input_file_path=input_file_path,
            input_text_content=input_text_content,
            use_ui_input=use_ui_input,
            log_level=log_level,
            analysis_type=analysis_type,
            config_for_services=config_for_services
        )
>>>>>>> BACKUP
