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
    """Configuration unifiée pour l'analyse textuelle."""
    
    def __init__(self,
                 analysis_modes: List[str] = None,
                 orchestration_mode: str = "pipeline",
                 logic_type: str = "fol",
                 use_mocks: bool = False,
                 use_advanced_tools: bool = True,
                 output_format: str = "detailed",
                 enable_conversation_logging: bool = True):
        """
        Initialise la configuration unifiée.
        
        Args:
            analysis_modes: Modes d'analyse ["informal", "formal", "unified"]
            orchestration_mode: Mode orchestrateur ["pipeline", "real", "conversation"]
            logic_type: Type de logique ["fol", "modal", "propositional"]
            use_mocks: Utilisation de mocks pour les tests
            use_advanced_tools: Activation des outils avancés
            output_format: Format de sortie ["summary", "detailed", "json"]
            enable_conversation_logging: Log des conversations
        """
        self.analysis_modes = analysis_modes or ["informal", "formal"]
        self.orchestration_mode = orchestration_mode
        self.logic_type = logic_type
        self.use_mocks = use_mocks
        self.use_advanced_tools = use_advanced_tools
        self.output_format = output_format
        self.enable_conversation_logging = enable_conversation_logging
        
        # Validation des modes
        valid_modes = {"informal", "formal", "unified"}
        self.analysis_modes = [mode for mode in self.analysis_modes if mode in valid_modes]
        
        if not self.analysis_modes:
            self.analysis_modes = ["informal"]


class UnifiedTextAnalysisPipeline:
    """Pipeline unifié d'analyse textuelle consolidant les fonctionnalités de analyze_text.py."""
    
    def __init__(self, config: UnifiedAnalysisConfig):
        """Initialise le pipeline unifié."""
        self.config = config
        self.llm_service = None
        self.orchestrator = None
        self.analysis_tools = {}
        self.jvm_ready = False
        self.conversation_logger = None
        
        # État interne
        self.initialized = False
        self.start_time = None
        
    async def initialize(self) -> bool:
        """Initialise tous les composants du pipeline."""
        logger.info("[INIT] Initialisation du pipeline unifie...")
        self.start_time = time.time()
        
        # Configuration du logger conversationnel
        if self.config.enable_conversation_logging:
            self.conversation_logger = RealConversationLogger()
            logger.info("[INIT] Logger conversationnel active")
        
        # 1. Initialisation JVM si nécessaire
        if "formal" in self.config.analysis_modes or "unified" in self.config.analysis_modes:
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
        
        # PHASE 2: Mocks éliminés - utilisation exclusive des outils réels
        if self.config.use_mocks:
            logger.warning("use_mocks=True demandé mais les mocks ont été éliminés en Phase 2")
            logger.info("Forçage de l'utilisation des outils réels")
        
        logger.info("[TOOLS] Utilisation des outils d'analyse réels uniquement")
        
        # Pas de try/except - on laisse les vraies erreurs apparaître
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
        
        logger.info("[TOOLS] Outils d'analyse réels initialisés avec succès")
    
    async def analyze_text_unified(self, 
                                   text: str, 
                                   source_info: Optional[str] = None) -> Dict[str, Any]:
        """
        Lance l'analyse unifiée d'un texte selon la configuration.
        
        Args:
            text: Texte à analyser
            source_info: Information sur la source (optionnel)
            
        Returns:
            Dictionnaire des résultats d'analyse
        """
        logger.info(f"[ANALYZE] Debut analyse unifiee (modes: {self.config.analysis_modes})")
        analysis_start = time.time()
        
        # Structure de résultats unifiée
        results = {
            "metadata": {
                "analysis_timestamp": datetime.now().isoformat(),
                "pipeline_version": "unified_2.0",
                "analysis_modes": self.config.analysis_modes.copy(),
                "orchestration_mode": self.config.orchestration_mode,
                "text_length": len(text),
                "source_info": source_info or "Non spécifié"
            },
            "informal_analysis": {},
            "formal_analysis": {},
            "unified_analysis": {},
            "orchestration_analysis": {},
            "recommendations": [],
            "conversation_log": {},
            "execution_time": 0
        }
        
        try:
            # Analyse informelle
            if "informal" in self.config.analysis_modes:
                logger.info("[ANALYZE] Execution analyse informelle...")
                if self.config.orchestration_mode in ["real", "conversation"] and self.orchestrator:
                    results["informal_analysis"] = await self._perform_informal_analysis_orchestrated(text)
                else:
                    results["informal_analysis"] = await self._perform_informal_analysis(text)
            
            # Analyse formelle
            if "formal" in self.config.analysis_modes:
                logger.info("[ANALYZE] Execution analyse formelle...")
                results["formal_analysis"] = await self._perform_formal_analysis(text)
            
            # Analyse unifiée (combinaison sophistiquée)
            if "unified" in self.config.analysis_modes:
                logger.info("[ANALYZE] Execution analyse unifiee...")
                results["unified_analysis"] = await self._perform_unified_analysis(text)
            
            # Orchestration si activée
            if self.orchestrator and self.config.orchestration_mode != "pipeline":
                logger.info("[ANALYZE] Execution orchestration avancee...")
                results["orchestration_analysis"] = await self._perform_orchestration_analysis(text)
            
            # Génération des recommandations
            results["recommendations"] = self._generate_recommendations(results)
            
            # Log conversationnel
            if self.conversation_logger:
                results["conversation_log"] = self.get_conversation_log()
            
        except Exception as e:
            logger.error(f"[ANALYZE] Erreur durant l'analyse: {e}")
            results["error"] = str(e)
        
        # Calcul du temps d'exécution
        results["execution_time"] = time.time() - analysis_start
        
        logger.info(f"[ANALYZE] Analyse unifiee terminee en {results['execution_time']:.2f}s")
        return results
    
    async def _perform_informal_analysis(self, text: str) -> Dict[str, Any]:
        """Effectue l'analyse informelle avec les outils classiques."""
        informal_results = {
            "status": "Unknown",
            "fallacies": [],
            "summary": {}
        }
        
        try:
            # Utilisation des analyseurs contextuels et complexes
            contextual_analyzer = self.analysis_tools.get("contextual_analyzer")
            severity_evaluator = self.analysis_tools.get("severity_evaluator")
            
            if contextual_analyzer:
                # Analyse contextuelle des sophismes
                context_text = text[:500] + "..." if len(text) > 500 else text
                sample_context = {"text": context_text, "context_type": "sample_for_analysis"}
                
                contextual_fallacies = contextual_analyzer.detect_fallacies_with_context(
                    text,
                    sample_context,
                    include_confidence=True
                )
                
                # Format des sophismes détectés
                informal_results["fallacies"] = [
                    {
                        "type": f.get("type", "Type inconnu"),
                        "text_fragment": f.get("text_fragment", "Fragment non disponible"),
                        "explanation": f.get("explanation", "Explication non disponible"),
                        "severity": f.get("severity", "Moyen"),
                        "confidence": f.get("confidence", 0.0)
                    }
                    for f in contextual_fallacies
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
            "combined_insights": [],
            "meta_analysis": {}
        }
        
        synthesis_agent = self.analysis_tools.get("synthesis_agent")
        if not synthesis_agent:
            unified_results["status"] = "Skipped"
            unified_results["reason"] = "SynthesisAgent non disponible"
            return unified_results
        
        try:
            # Analyse unifiée avec le SynthesisAgent
            synthesis_result = await synthesis_agent.synthesize_analysis(
                text_input=text,
                context={"source": "unified_pipeline", "timestamp": datetime.now().isoformat()}
            )
            
            if synthesis_result and synthesis_result.get("status") == "success":
                unified_results.update({
                    "status": "Success",
                    "synthesis_report": synthesis_result.get("synthesis", ""),
                    "combined_insights": synthesis_result.get("insights", []),
                    "meta_analysis": synthesis_result.get("meta_analysis", {})
                })
            else:
                unified_results["status"] = "Failed"
                unified_results["reason"] = synthesis_result.get("error", "Erreur inconnue")
                
        except Exception as e:
            logger.error(f"Erreur analyse unifiée: {e}")
            unified_results["status"] = "Error"
            unified_results["reason"] = str(e)
        
        return unified_results
    
    async def _perform_orchestration_analysis(self, text: str) -> Dict[str, Any]:
        """Effectue l'analyse orchestrée."""
        orchestration_results = {
            "status": "Unknown",
            "orchestrator_type": self.config.orchestration_mode,
            "agents_used": [],
            "conversation_summary": {}
        }
        
        if not self.orchestrator:
            orchestration_results["status"] = "Skipped"
            orchestration_results["reason"] = "Orchestrateur non disponible"
            return orchestration_results
        
        try:
            if hasattr(self.orchestrator, 'analyze_text_comprehensive'):
                # Pour RealLLMOrchestrator
                orch_result = await self.orchestrator.analyze_text_comprehensive(
                    text, 
                    context={"source": "unified_pipeline"}
                )
                
                orchestration_results.update({
                    "status": "success",
                    "agents_used": orch_result.get("agents_used", []),
                    "conversation_summary": orch_result.get("conversation_summary", {}),
                    "analysis_results": orch_result.get("results", {})
                })
                
            elif hasattr(self.orchestrator, 'run_conversation'):
                # Pour ConversationOrchestrator
                conv_result = await self.orchestrator.run_conversation(text)
                
                orchestration_results.update({
                    "status": "success",
                    "conversation_summary": conv_result,
                    "agents_used": ["ConversationOrchestrator"]
                })
            else:
                orchestration_results["status"] = "Failed"
                orchestration_results["reason"] = "Méthode d'orchestration non reconnue"
                
        except Exception as e:
            logger.error(f"Erreur orchestration: {e}")
            orchestration_results["status"] = "Error"
            orchestration_results["reason"] = str(e)
        
        return orchestration_results
    
    async def _perform_informal_analysis_orchestrated(self, text: str) -> Dict[str, Any]:
        """Effectue l'analyse informelle via l'orchestrateur."""
        informal_results = {
            "status": "Unknown",
            "fallacies": [],
            "summary": {},
            "extraction_method": "orchestrated"
        }
        
        if not self.orchestrator:
            logger.warning("Orchestrateur non disponible pour analyse informelle")
            return await self._perform_informal_analysis(text)
        
        try:
            # Exécution de l'analyse via l'orchestrateur
            if hasattr(self.orchestrator, 'analyze_text_comprehensive'):
                orch_result = await self.orchestrator.analyze_text_comprehensive(
                    text, 
                    context={"analysis_focus": "informal", "extract_fallacies": True}
                )
                conversation_log = orch_result.get("conversation_log", {})
                
            elif hasattr(self.orchestrator, 'run_conversation'):
                conversation_log = await self.orchestrator.run_conversation(text)
            else:
                logger.warning("Méthode d'orchestration non reconnue, fallback vers analyse standard")
                return await self._perform_informal_analysis(text)
            
            # EXTRACTION DES SOPHISMES DEPUIS LE LOG CONVERSATIONNEL
            logger.info("🔍 Extraction des sophismes depuis le log conversationnel...")
            
            # PRIORITÉ 1: Chercher dans les tool_calls
            if isinstance(conversation_log, dict) and "tool_calls" in conversation_log:
                for i, tool_call in enumerate(conversation_log["tool_calls"]):
                    if isinstance(tool_call, dict):
                        result = tool_call.get("result", {})
                        
                        # Chercher les résultats d'InformalAnalysisAgent ou les fallacies
                        if isinstance(result, dict):
                            # Essayer plusieurs clés possibles pour les sophismes
                            sophismes_data = (
                                result.get("fallacies") or 
                                result.get("sophismes") or 
                                result.get("detected_fallacies") or
                                result.get("fallacy_analysis", {}).get("fallacies", [])
                            )
                            
                            # Fallback: chercher dans informal_analysis
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
                                logger.warning(f"Erreur lors du parsing JSON des sophismes: {e}")
                        
            # PRIORITÉ 2: Chercher dans les messages (fallback pour autre format d'orchestrateur)
            if not informal_results["fallacies"] and isinstance(conversation_log, list):
                for msg in conversation_log:
                    if isinstance(msg, dict) and "sophismes" in str(msg):
                        try:
                            # Chercher des sophismes dans les messages
                            content = str(msg.get("content", ""))
                            if "sophismes" in content.lower():
                                # Essayer d'extraire le JSON depuis le contenu
                                import json
                                json_start = content.find('{"sophismes"')
                                if json_start != -1:
                                    # Chercher la fin du JSON
                                    bracket_count = 0
                                    json_end = json_start
                                    for j, char in enumerate(content[json_start:], json_start):
                                        if char == '{':
                                            bracket_count += 1
                                        elif char == '}':
                                            bracket_count -= 1
                                            if bracket_count == 0:
                                                json_end = j + 1
                                                break
                                    
                                    json_text = content[json_start:json_end]
                                    sophismes_json = json.loads(json_text)
                                    
                                    for sophisme_data in sophismes_json.get("sophismes", []):
                                        sophisme = {
                                            "type": sophisme_data.get("nom", "Type inconnu"),
                                            "text_fragment": sophisme_data.get("citation", "Fragment non disponible"),
                                            "explanation": sophisme_data.get("explication", "Explication non disponible"),
                                            "severity": "Moyen",
                                            "confidence": 0.0,
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
    
    def _calculate_severity_distribution(self, fallacies: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calcule la distribution des niveaux de sévérité."""
        distribution = {"Faible": 0, "Moyen": 0, "Élevé": 0, "Critique": 0}
        for fallacy in fallacies:
            severity = fallacy.get("severity", "Moyen")
            if severity in distribution:
                distribution[severity] += 1
        return distribution


# ==========================================
# FONCTIONS D'ENTRÉE PUBLIQUES DU PIPELINE
# ==========================================

async def run_unified_text_analysis_pipeline(
    text: str,
    config: Optional[UnifiedAnalysisConfig] = None,
    source_info: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fonction d'entrée principale pour le pipeline unifié d'analyse textuelle.
    
    Args:
        text: Texte à analyser
        config: Configuration d'analyse (optionnel, valeurs par défaut utilisées)
        source_info: Information sur la source du texte (optionnel)
    
    Returns:
        Dictionnaire complet des résultats d'analyse
    """
    # Configuration par défaut si non fournie
    if config is None:
        config = UnifiedAnalysisConfig(
            analysis_modes=["informal", "formal"],
            orchestration_mode="pipeline",
            use_mocks=False
        )
    
    # Création et initialisation du pipeline
    pipeline = UnifiedTextAnalysisPipeline(config)
    
    try:
        # Initialisation
        init_success = await pipeline.initialize()
        if not init_success:
            return {
                "error": "Échec de l'initialisation du pipeline",
                "status": "failed"
            }
        
        # Analyse
        results = await pipeline.analyze_text_unified(text, source_info)
        results["status"] = "success"
        
        return results
        
    except Exception as e:
        logger.error(f"Erreur pipeline unifié: {e}")
        return {
            "error": str(e),
            "status": "failed",
            "metadata": {
                "analysis_timestamp": datetime.now().isoformat(),
                "pipeline_version": "unified_2.0",
                "text_length": len(text) if text else 0
            }
        }


def create_unified_config_from_legacy(
    mode: str = "formal",
    use_mocks: bool = False,
    orchestration_mode: str = "pipeline",
    **kwargs
) -> UnifiedAnalysisConfig:
    """
    Crée une configuration unifiée depuis les paramètres legacy.
    
    Args:
        mode: Mode d'analyse principal ("formal", "informal", "unified")
        use_mocks: Utilisation des mocks pour les tests
        orchestration_mode: Mode d'orchestrateur
        **kwargs: Paramètres additionnels
    
    Returns:
        Configuration unifiée
    """
    # Mapping des modes legacy vers les nouveaux modes
    mode_mapping = {
        "formal": ["formal"],
        "informal": ["informal"],
        "unified": ["informal", "formal", "unified"],
        "all": ["informal", "formal", "unified"]
    }
    
    analysis_modes = mode_mapping.get(mode, ["informal"])
    
    return UnifiedAnalysisConfig(
        analysis_modes=analysis_modes,
        orchestration_mode=orchestration_mode,
        logic_type=kwargs.get("logic_type", "fol"),
        use_mocks=use_mocks,
        use_advanced_tools=kwargs.get("use_advanced_tools", True),
        output_format=kwargs.get("output_format", "detailed"),
        enable_conversation_logging=kwargs.get("enable_conversation_logging", True)
    )
