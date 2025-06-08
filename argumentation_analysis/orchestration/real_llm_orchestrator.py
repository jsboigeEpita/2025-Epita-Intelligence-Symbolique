<<<<<<< MAIN
#!/usr/bin/env python3
"""
Real LLM Orchestrator - Composant réutilisable pour orchestration avec vrais agents LLM
========================================================================================

Composant d'orchestration utilisant de véritables appels à GPT-4o-mini au lieu de simulations.
S'intègre harmonieusement avec l'architecture existante du projet.
"""

import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

# Imports Semantic Kernel
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, AzureChatCompletion

# Imports de l'architecture existante
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.llm_service import create_llm_service
from argumentation_analysis.core.jvm_setup import initialize_jvm

# Imports des agents réels
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent
from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent
from argumentation_analysis.agents.core.synthesis.synthesis_agent import SynthesisAgent

# Import du système de correction intelligente des erreurs Tweety
from argumentation_analysis.utils.tweety_error_analyzer import TweetyErrorAnalyzer, create_bnf_feedback_for_error

logger = logging.getLogger("RealLLMOrchestrator")


class RealConversationLogger:
    """Logger pour conversations avec vrais agents LLM - Compatible avec l'architecture existante."""
    
    def __init__(self):
        self.start_time = time.time()
        self.messages = []
        self.tool_calls = []
        self.state_snapshots = []
        self.logger = logging.getLogger(f"{__name__}.ConversationLogger")
        
    def log_agent_message(self, agent: str, message: str, phase: str):
        """Enregistre un message d'agent."""
        timestamp_ms = (time.time() - self.start_time) * 1000
        self.messages.append({
            'timestamp': timestamp_ms,
            'time_ms': timestamp_ms,
            'agent': agent,
            'message': message,
            'phase': phase
        })
        self.logger.info(f"[{timestamp_ms:.1f}ms] MESSAGE {agent}: {message}")
        
    def log_tool_call(self, agent: str, tool: str, arguments: Any, result: Any, success: bool = True):
        """Enregistre un appel d'outil."""
        timestamp_ms = (time.time() - self.start_time) * 1000
        self.tool_calls.append({
            'timestamp': timestamp_ms,
            'time_ms': timestamp_ms,
            'agent': agent,
            'tool': tool,
            'arguments': arguments,
            'result': result,
            'success': success
        })
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"[{timestamp_ms:.1f}ms] TOOL {agent} -> {tool} {status}")
        
    def log_state_snapshot(self, phase: str, state_data: Dict[str, Any]):
        """Enregistre un snapshot d'état."""
        timestamp = time.time() - self.start_time
        self.state_snapshots.append({
            'timestamp': timestamp,
            'phase': phase,
            'data': state_data
        })


class RealLLMOrchestrator:
    """
    Orchestrateur utilisant de vrais agents LLM - Intégré avec l'architecture existante.
    
    Ce composant réutilisable encapsule la logique d'orchestration avec de véritables
    appels LLM tout en respectant les patterns de l'architecture du projet.
    """
    
    def __init__(self, mode: str = "real", llm_service: Optional[Union[OpenAIChatCompletion, AzureChatCompletion]] = None):
        """
        Initialise l'orchestrateur.
        
        Args:
            mode: Mode d'opération ("real" par défaut)
            llm_service: Service LLM optionnel (créé automatiquement si None)
        """
        self.mode = mode
        self.logger = RealConversationLogger()
        self.state = None  # Sera initialisé avec RhetoricalAnalysisState
        self.llm_service = llm_service
        self.kernel = None
        self.agents = {}
        self.current_text = ""
        self.orchestration_logger = logging.getLogger(f"{__name__}.Orchestrator")
        
    async def initialize(self) -> bool:
        """
        Initialise complètement l'orchestrateur.
        
        Cette méthode est appelée par le pipeline unifié.
        """
        try:
            self.orchestration_logger.info("Initialisation complète de l'orchestrateur LLM réel...")
            
            # 1. Initialiser les services LLM
            llm_success = await self.initialize_llm_services()
            if not llm_success:
                return False
                
            # 2. Initialiser les agents réels
            agents_success = await self.initialize_real_agents()
            if not agents_success:
                return False
                
            self.orchestration_logger.info("Orchestrateur LLM réel initialisé avec succès")
            return True
            
        except Exception as e:
            self.orchestration_logger.error(f"Erreur lors de l'initialisation complète: {e}")
            return False
        
    async def initialize_llm_services(self) -> bool:
        """Initialise les services LLM réels."""
        try:
            self.logger.log_agent_message(
                "ProjectManager",
                "Initialisation des services LLM réels (GPT-4o-mini)...",
                "initialization"
            )
            
            # Service LLM - utiliser celui fourni ou en créer un
            if self.llm_service is None:
                self.llm_service = create_llm_service()
                
            if not self.llm_service:
                raise Exception("Impossible de créer le service LLM")
                
            # Kernel Semantic Kernel
            self.kernel = sk.Kernel()
            self.kernel.add_service(self.llm_service)
            
            self.logger.log_tool_call(
                "ProjectManager",
                "initialize_llm_service",
                {"service_type": "GPT-4o-mini", "kernel": "semantic_kernel"},
                {"service_id": self.llm_service.service_id, "status": "ready"},
                True
            )
            
            self.orchestration_logger.info(f"Services LLM initialisés avec succès: {self.llm_service.service_id}")
            return True
            
        except Exception as e:
            self.logger.log_tool_call(
                "ProjectManager", 
                "initialize_llm_service",
                {"service_type": "GPT-4o-mini"},
                {"error": str(e)},
                False
            )
            self.orchestration_logger.error(f"Erreur initialisation services LLM: {e}")
            return False
            
    async def initialize_real_agents(self) -> bool:
        """Initialise les vrais agents LLM."""
        try:
            self.logger.log_agent_message(
                "ProjectManager",
                "Création des agents d'analyse réels...",
                "initialization"
            )
            
            # Agent d'analyse informelle
            informal_agent = InformalAnalysisAgent(kernel=self.kernel)
            informal_agent.setup_agent_components(self.llm_service.service_id)
            self.agents["informal"] = informal_agent
            
            # Agent de logique modale 
            modal_agent = ModalLogicAgent(kernel=self.kernel, service_id=self.llm_service.service_id)
            modal_agent.setup_agent_components(self.llm_service.service_id)
            self.agents["modal"] = modal_agent
            
            # Agent de synthèse
            synthesis_agent = SynthesisAgent(kernel=self.kernel)
            synthesis_agent.setup_agent_components(self.llm_service.service_id)
            self.agents["synthesis"] = synthesis_agent
            
            self.logger.log_tool_call(
                "ProjectManager",
                "initialize_real_agents",
                {"agents": ["InformalAnalysisAgent", "ModalLogicAgent", "SynthesisAgent"]},
                {"agents_created": len(self.agents), "all_ready": True},
                True
            )
            
            self.logger.log_agent_message(
                "ProjectManager",
                f"Agents réels créés avec succès: {', '.join(self.agents.keys())}",
                "initialization"
            )
            
            self.orchestration_logger.info(f"Agents réels initialisés: {list(self.agents.keys())}")
            return True
            
        except Exception as e:
            self.logger.log_tool_call(
                "ProjectManager",
                "initialize_real_agents", 
                {"agents": ["InformalAnalysisAgent", "ModalLogicAgent", "SynthesisAgent"]},
                {"error": str(e)},
                False
            )
            self.orchestration_logger.error(f"Erreur initialisation agents: {e}")
            return False
            
    async def run_real_informal_analysis(self, text: str) -> Dict[str, Any]:
        """Exécute l'analyse informelle avec le vrai agent."""
        self.logger.log_agent_message(
            "InformalAnalysisAgent",
            "Démarrage de l'analyse rhétorique informelle avec GPT-4o-mini...",
            "informal_analysis"
        )
        
        try:
            agent = self.agents["informal"]
            
            # Appel réel de l'agent
            result = await agent.perform_complete_analysis(text)
            
            self.logger.log_tool_call(
                "InformalAnalysisAgent",
                "perform_complete_analysis",
                {"text_length": len(text), "analysis_type": "rhetorical"},
                result,
                True
            )
            
            # Mise à jour de l'état partagé
            if self.state:
                sophisms_count = len(result.get('fallacies', []))
                self.state.fallacies_detected = sophisms_count
                self.state.agents_results['informal'] = result
                
                sophisms_details = [f"{f.get('nom', 'Unknown')} (confiance: {f.get('confidence', 0):.2f})"
                                  for f in result.get('fallacies', [])]
                
                self.logger.log_agent_message(
                    "InformalAnalysisAgent",
                    f"Analyse terminée. {sophisms_count} sophismes détectés: {', '.join(sophisms_details)}. Score de qualité rhétorique calculé.",
                    "informal_analysis"
                )
                
                self.state.agents_active += 1
                self.state.overall_score += 0.3
            
            return result
            
        except Exception as e:
            self.logger.log_tool_call(
                "InformalAnalysisAgent",
                "perform_complete_analysis",
                {"text_length": len(text)},
                {"error": str(e)},
                False
            )
            self.orchestration_logger.error(f"Erreur analyse informelle: {e}")
            raise
            
    async def run_real_modal_analysis(self, text: str) -> Dict[str, Any]:
        """Exécute l'analyse modale avec correction intelligente des erreurs Tweety via feedback BNF."""
        self.logger.log_agent_message(
            "ModalLogicAgent",
            "Démarrage de l'analyse de logique modale avec correction intelligente des erreurs...",
            "modal_analysis"
        )
        
        try:
            agent = self.agents["modal"]
            
            # Initialiser l'analyseur d'erreurs Tweety
            error_analyzer = TweetyErrorAnalyzer()
            
            # Système de correction intelligente avec feedback BNF progressif
            max_retries = 3
            last_error = ""
            bnf_feedback_history = []
            
            for attempt in range(max_retries):
                attempt_num = attempt + 1
                
                # Logger le début de chaque tentative avec contexte de progression
                attempt_context = f"avec feedback BNF progressif (erreurs précédentes analysées)" if attempt > 0 else "première tentative"
                self.logger.log_agent_message(
                    "ModalLogicAgent",
                    f"Tentative de conversion {attempt_num}/3 {attempt_context}...",
                    "sk_retry_intelligent"
                )
                
                try:
                    # Construire un prompt enrichi avec le feedback BNF des tentatives précédentes
                    enhanced_input = self._build_enhanced_prompt_with_bnf_feedback(text, bnf_feedback_history)
                    
                    # Appel de la fonction sémantique avec le prompt enrichi
                    result = await agent.sk_kernel.plugins[agent.name]["TextToModalBeliefSet"].invoke(
                        agent.sk_kernel, input=enhanced_input
                    )
                    
                    # Extraire et parser le JSON
                    import json
                    json_str = agent._extract_json_block(str(result))
                    kb_json = json.loads(json_str)
                    
                    # Valider la cohérence du JSON
                    is_valid, validation_msg = agent._validate_modal_kb_json(kb_json)
                    if not is_valid:
                        raise ValueError(f"JSON invalide: {validation_msg}")
                    
                    # Construire la base de connaissances modale
                    belief_set_content = agent._construct_modal_kb_from_json(kb_json)
                    
                    if not belief_set_content:
                        raise ValueError("La conversion a produit une base de connaissances vide.")

                    # Valider avec Tweety
                    is_valid, validation_msg = agent.tweety_bridge.validate_modal_belief_set(belief_set_content)
                    if not is_valid:
                        raise ValueError(f"Ensemble de croyances invalide selon Tweety: {validation_msg}")
                    
                    # Si on arrive ici, la tentative a réussi grâce au feedback BNF
                    from argumentation_analysis.agents.core.belief_sets.modal_belief_set import ModalBeliefSet
                    belief_set_obj = ModalBeliefSet(belief_set_content)
                    
                    correction_success_msg = f"SUCCÈS après {attempt_num} tentative(s)" if attempt_num == 1 else f"CORRECTION INTELLIGENTE RÉUSSIE après {attempt_num} tentatives (feedback BNF efficace)"
                    
                    self.logger.log_tool_call(
                        "ModalLogicAgent",
                        f"text_to_belief_set_intelligent_attempt_{attempt_num}",
                        {
                            "text_length": len(text),
                            "attempt": attempt_num,
                            "bnf_feedback_used": len(bnf_feedback_history) > 0,
                            "correction_method": "intelligent_bnf_feedback"
                        },
                        {
                            "success": True,
                            "belief_set_size": len(belief_set_content),
                            "correction_success": correction_success_msg
                        },
                        True
                    )
                    
                    self.logger.log_agent_message(
                        "ModalLogicAgent",
                        correction_success_msg + f". Analyse modale valide générée.",
                        "intelligent_correction_success"
                    )
                    
                    return {"belief_set": belief_set_obj, "success": True, "corrected_attempt": attempt_num}
                    
                except Exception as e:
                    # Analyser l'erreur avec le système BNF intelligent
                    error_msg = str(e)
                    
                    # Générer le feedback BNF constructif
                    bnf_feedback = error_analyzer.analyze_error(error_msg, {
                        "attempt": attempt_num,
                        "agent": "ModalLogicAgent",
                        "text_context": text[:100]
                    })
                    
                    # Créer le message de feedback formaté
                    feedback_message = error_analyzer.generate_bnf_feedback_message(bnf_feedback, attempt_num)
                    
                    # Stocker le feedback pour les prochaines tentatives
                    bnf_feedback_history.append({
                        "attempt": attempt_num,
                        "error": error_msg,
                        "feedback": bnf_feedback,
                        "feedback_message": feedback_message
                    })
                    
                    last_error = f"Tentative {attempt_num}: {error_msg}"
                    
                    # Logger l'échec avec le feedback BNF généré
                    self.logger.log_tool_call(
                        "ModalLogicAgent",
                        f"text_to_belief_set_intelligent_attempt_{attempt_num}",
                        {
                            "text_length": len(text),
                            "attempt": attempt_num,
                            "error_type": bnf_feedback.error_type,
                            "bnf_confidence": bnf_feedback.confidence
                        },
                        {
                            "error": error_msg,
                            "bnf_feedback_generated": True,
                            "error_type": bnf_feedback.error_type,
                            "bnf_rules_count": len(bnf_feedback.bnf_rules),
                            "corrections_provided": len(bnf_feedback.corrections)
                        },
                        False
                    )
                    
                    # Logger le message de feedback constructif
                    self.logger.log_agent_message(
                        "ModalLogicAgent",
                        f"Tentative {attempt_num}/{max_retries} - Erreur analysée: {bnf_feedback.error_type}. Feedback BNF généré pour correction intelligente.",
                        "intelligent_error_analysis"
                    )
                    
                    # Log detaillé du feedback BNF (pour débogage et traces)
                    self.orchestration_logger.info(f"Feedback BNF Tentative {attempt_num}:\n{feedback_message}")
                    
                    if attempt_num == max_retries:
                        break
            
            # Toutes les tentatives ont échoué malgré le feedback BNF
            final_error = f"Échec de la correction intelligente après {max_retries} tentatives avec feedback BNF. Dernière erreur: {last_error}"
            
            # Analyser l'échec global pour des recommandations d'amélioration système
            failure_analysis = self._analyze_correction_failure(bnf_feedback_history)
            
            self.logger.log_tool_call(
                "ModalLogicAgent",
                "intelligent_modal_conversion",
                {
                    "text_length": len(text),
                    "logic_type": "modal",
                    "max_retries": max_retries,
                    "correction_method": "intelligent_bnf_feedback",
                    "bnf_feedbacks_generated": len(bnf_feedback_history)
                },
                {
                    "error": final_error,
                    "sk_retry_attempts": max_retries,
                    "bnf_correction_attempted": True,
                    "failure_analysis": failure_analysis
                },
                False
            )
            
            self.logger.log_agent_message(
                "ModalLogicAgent",
                f"Correction intelligente échouée après {max_retries} tentatives avec feedback BNF. {failure_analysis}. Poursuite de l'orchestration sans analyse modale.",
                "intelligent_correction_failure"
            )
            
            # Mise à jour de l'état avec l'erreur et les tentatives de correction
            if self.state:
                self.state.agents_results['modal'] = {
                    "error": final_error,
                    "intelligent_correction_attempted": True,
                    "bnf_feedback_history": bnf_feedback_history,
                    "failure_analysis": failure_analysis
                }
                self.state.agents_active += 1
                
            return {"error": final_error, "correction_attempted": True, "bnf_feedback_history": bnf_feedback_history}
            
        except Exception as e:
            self.logger.log_tool_call(
                "ModalLogicAgent",
                "intelligent_modal_conversion",
                {"text_length": len(text)},
                {"error": str(e), "correction_system_error": True},
                False
            )
            self.orchestration_logger.error(f"Erreur système de correction intelligente: {e}")
            raise
            
    async def run_real_synthesis(self, text: str) -> Any:
        """Exécute la synthèse avec le vrai agent."""
        self.logger.log_agent_message(
            "SynthesisAgent",
            "Démarrage de la synthèse unifiée avec GPT-4o-mini...",
            "synthesis"
        )
        
        try:
            agent = self.agents["synthesis"]
            
            # Synthèse des résultats
            synthesis_result = await agent.synthesize_analysis(text)
            
            self.logger.log_tool_call(
                "SynthesisAgent",
                "perform_complete_analysis",
                {
                    "informal_results": self.state.agents_results.get('informal', {}) if self.state else {},
                    "modal_results": self.state.agents_results.get('modal', {}) if self.state else {},
                    "synthesis_strategy": "unified_analysis"
                },
                synthesis_result,
                True
            )
            
            # Extraction des résultats depuis UnifiedReport
            if hasattr(synthesis_result, 'overall_score'):
                unified_score = synthesis_result.overall_score
            else:
                unified_score = 0.0
                
            if hasattr(synthesis_result, 'main_issues'):
                main_issues = synthesis_result.main_issues or []
            else:
                main_issues = []
            
            self.logger.log_agent_message(
                "SynthesisAgent",
                f"Synthèse terminée. Score unifié: {unified_score:.3f}, problèmes identifiés: {', '.join(main_issues)}",
                "synthesis"
            )
            
            # Mise à jour de l'état partagé
            if self.state:
                self.state.agents_results['synthesis'] = synthesis_result
                self.state.agents_active += 1
                self.state.overall_score = unified_score
                self.state.analysis_completed = True
            
            return synthesis_result
            
        except Exception as e:
            self.logger.log_tool_call(
                "SynthesisAgent",
                "perform_complete_analysis",
                {"text_length": len(text)},
                {"error": str(e)},
                False
            )
            self.orchestration_logger.error(f"Erreur synthèse: {e}")
            raise
            
    async def orchestrate_analysis(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        Interface standardisée pour le pipeline unifié.
        
        Cette méthode fait le wrapper vers run_orchestration() en adaptant
        les paramètres et le format de retour pour l'interface unifiée.
        """
        try:
            self.orchestration_logger.info("Démarrage orchestration unifiée via interface standardisée...")
            
            # Exécuter l'orchestration complète
            markdown_report = await self.run_orchestration(text, kwargs.get('state'))
            
            # Adapter le résultat pour l'interface unifiée
            result = {
                "orchestration": {
                    "mode": self.mode,
                    "agents_used": list(self.agents.keys()),
                    "success": True,
                    "report": markdown_report
                },
                "conversation_log": {
                    "messages": self.logger.messages,
                    "tool_calls": self.logger.tool_calls,
                    "state_snapshots": self.logger.state_snapshots
                },
                "metadata": {
                    "llm_service_id": self.llm_service.service_id if self.llm_service else None,
                    "agents_count": len(self.agents),
                    "total_runtime_ms": (time.time() - self.logger.start_time) * 1000 if self.logger.start_time else 0
                }
            }
            
            # Ajouter les résultats détaillés si disponibles
            if self.state:
                result["analysis_results"] = {
                    "overall_score": self.state.overall_score,
                    "agents_results": dict(self.state.agents_results),
                    "analysis_completed": self.state.analysis_completed
                }
            
            self.orchestration_logger.info("Orchestration unifiée terminée avec succès")
            return result
            
        except Exception as e:
            self.orchestration_logger.error(f"Erreur orchestration unifiée: {e}")
            return {
                "orchestration": {
                    "mode": self.mode,
                    "success": False,
                    "error": str(e)
                },
                "conversation_log": {
                    "messages": self.logger.messages,
                    "tool_calls": self.logger.tool_calls
                }
            }
            
    async def run_orchestration(self, text: str, state: Optional[RhetoricalAnalysisState] = None) -> str:
        """
        Exécute l'orchestration complète avec vrais agents LLM.
        
        Args:
            text: Texte à analyser
            state: État partagé optionnel (créé automatiquement si None)
            
        Returns:
            Rapport d'analyse au format markdown
        """
        self.current_text = text
        
        # Initialiser l'état si non fourni
        if state is None:
            self.state = RhetoricalAnalysisState(initial_text=text)
        else:
            self.state = state
            
        try:
            # Initialisation
            if not await self.initialize_llm_services():
                raise Exception("Impossible d'initialiser les services LLM")
                
            if not await self.initialize_real_agents():
                raise Exception("Impossible d'initialiser les agents")
                
            self.logger.log_state_snapshot("initialization", self._state_to_dict())
            
            # Coordination du ProjectManager
            self.logger.log_agent_message(
                "ProjectManager",
                "Orchestration démarrée. Lancement séquentiel des analyses avec agents LLM réels.",
                "coordination"
            )
            
            # Analyses séquentielles
            await self.run_real_informal_analysis(text)
            self.logger.log_state_snapshot("after_informal", self._state_to_dict())
            
            await self.run_real_modal_analysis(text)
            self.logger.log_state_snapshot("after_modal", self._state_to_dict())
            
            await self.run_real_synthesis(text)
            self.logger.log_state_snapshot("final", self._state_to_dict())
            
            # Coordination finale
            self.logger.log_tool_call(
                "ProjectManager",
                "coordinate_final_synthesis",
                {"agents_results": len(self.agents), "final_score": self.state.overall_score},
                {"coordination": "success", "status": "completed", "real_llm_calls": True},
                True
            )
            
            self.logger.log_agent_message(
                "ProjectManager",
                f"Orchestration terminée avec succès. Score final: {self.state.overall_score:.3f}. Tous les agents LLM ont contribué à l'analyse.",
                "conclusion"
            )
            
            return self.generate_report()
            
        except Exception as e:
            self.logger.log_agent_message(
                "ProjectManager",
                f"Erreur lors de l'orchestration: {str(e)}",
                "error"
            )
            self.orchestration_logger.error(f"Erreur orchestration: {e}")
            raise
            
    def _state_to_dict(self) -> Dict[str, Any]:
        """Convertit l'état en dictionnaire pour les snapshots."""
        if not self.state:
            return {}
            
        return {
            "overall_score": round(self.state.overall_score, 3),
            "agents_active": self.state.agents_active,
            "fallacies_detected": self.state.fallacies_detected,
            "propositions_found": self.state.propositions_found,
            "consistency_score": round(self.state.consistency_score, 3),
            "analysis_completed": self.state.analysis_completed,
            "agents_results_keys": list(self.state.agents_results.keys())
        }
            
    def _build_enhanced_prompt_with_bnf_feedback(self, original_text: str, bnf_feedback_history: List[Dict[str, Any]]) -> str:
        """
        Construit un prompt enrichi avec le feedback BNF des tentatives précédentes.
        
        Args:
            original_text: Texte original à analyser
            bnf_feedback_history: Historique des feedbacks BNF des tentatives précédentes
            
        Returns:
            Prompt enrichi avec les corrections BNF
        """
        if not bnf_feedback_history:
            return original_text
        
        # Construire le prompt enrichi
        enhanced_prompt = f"""TEXTE À ANALYSER: {original_text}

⚠️ CORRECTIONS BNF BASÉES SUR LES ERREURS PRÉCÉDENTES:

"""
        
        for feedback_entry in bnf_feedback_history:
            attempt = feedback_entry["attempt"]
            feedback = feedback_entry["feedback"]
            
            enhanced_prompt += f"""
TENTATIVE {attempt} - ERREUR ANALYSÉE: {feedback.error_type}
RÈGLES BNF À RESPECTER:
"""
            for rule in feedback.bnf_rules:
                enhanced_prompt += f"• {rule}\n"
            
            enhanced_prompt += f"""
CORRECTIONS SPÉCIFIQUES:
"""
            for correction in feedback.corrections:
                enhanced_prompt += f"• {correction}\n"
            
            enhanced_prompt += f"""
EXEMPLE DE CORRECTION:
{feedback.example_fix}

"""
        
        enhanced_prompt += f"""
🎯 INSTRUCTIONS STRICTES POUR CETTE TENTATIVE:
1. Appliquer TOUTES les corrections BNF mentionnées ci-dessus
2. Éviter les erreurs identifiées dans les tentatives précédentes
3. Respecter strictement la syntaxe Tweety Modal Logic
4. Déclarer tous les prédicats avant usage dans les formules modales
5. Ne JAMAIS utiliser "constant" dans les formules, seulement dans les déclarations

Générez le JSON corrigé en tenant compte de ce feedback constructif.
"""
        
        return enhanced_prompt
    
    def _analyze_correction_failure(self, bnf_feedback_history: List[Dict[str, Any]]) -> str:
        """
        Analyse l'échec global du système de correction pour des recommandations d'amélioration.
        
        Args:
            bnf_feedback_history: Historique complet des tentatives et feedbacks
            
        Returns:
            Analyse de l'échec avec recommandations
        """
        if not bnf_feedback_history:
            return "Aucune tentative de correction documentée."
        
        # Analyser les patterns d'erreurs
        error_types = [entry["feedback"].error_type for entry in bnf_feedback_history]
        recurring_errors = {}
        for error_type in error_types:
            recurring_errors[error_type] = recurring_errors.get(error_type, 0) + 1
        
        # Analyser la progression (ou régression)
        if len(bnf_feedback_history) > 1:
            first_error = bnf_feedback_history[0]["feedback"].error_type
            last_error = bnf_feedback_history[-1]["feedback"].error_type
            progression = "Même type d'erreur persistant" if first_error == last_error else "Types d'erreurs différents"
        else:
            progression = "Une seule tentative"
        
        # Calculer l'efficacité du feedback
        confidence_scores = [entry["feedback"].confidence for entry in bnf_feedback_history]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        analysis = f"""Erreurs récurrentes: {dict(recurring_errors)}.
Progression: {progression}.
Confiance moyenne feedback: {avg_confidence:.2f}.
Recommandation: {"Améliorer le prompt système de l'agent modal" if avg_confidence > 0.8 else "Améliorer l'analyseur d'erreurs BNF"}"""
        
        return analysis

    def generate_report(self) -> str:
        """Génère le rapport final avec résultats LLM réels."""
        total_time = (time.time() - self.logger.start_time) * 1000
        text_size = len(self.current_text)
        text_words = len(self.current_text.split())
        
        report = f"""# TRACE ANALYTIQUE - AGENTS LLM RÉELS (GPT-4o-mini)
===========================================================

## 📄 EXTRAIT ANALYSE
- **Source:** Texte libre (analyse LLM réelle)
- **Taille:** {text_size} caractères, {text_words} mots
- **Type:** Argumentation avec analyses LLM complètes
- **Extrait:** "{self.current_text[:100]}{'...' if text_size > 100 else ''}"

## ⏱️ METADONNEES D'EXECUTION
- **Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Mode:** {self.mode} (agents LLM réels)
- **Durée totale:** {total_time:.1f}ms
- **Service LLM:** {self.llm_service.service_id if self.llm_service else 'N/A'}
- **Agents orchestrés:** {self.state.agents_active if self.state else 0}

## 🎭 TRACE CONVERSATIONNELLE CHRONOLOGIQUE (VRAIS APPELS LLM)
"""
        
        # Fusionner messages et outils chronologiquement
        all_events = []
        
        for msg in self.logger.messages:
            all_events.append({
                'type': 'message',
                'timestamp': msg['time_ms'],
                'data': msg
            })
            
        for tool in self.logger.tool_calls:
            all_events.append({
                'type': 'tool',
                'timestamp': tool['time_ms'], 
                'data': tool
            })
            
        all_events.sort(key=lambda x: x['timestamp'])
        
        for event in all_events:
            if event['type'] == 'message':
                msg = event['data']
                report += f"""
### [{msg['time_ms']:.1f}ms] 💬 **{msg['agent']}**
**Phase:** {msg['phase']}  
**Message:** *"{msg['message']}"*
"""
            elif event['type'] == 'tool':
                tool = event['data']
                status = "✅" if tool['success'] else "❌"
                report += f"""
### [{tool['time_ms']:.1f}ms] 🔧 **APPEL LLM RÉEL** {status}
**Agent:** {tool['agent']}  
**Outil:** `{tool['tool']}`  
**Arguments:** {str(tool['arguments'])[:200]}{'...' if len(str(tool['arguments'])) > 200 else ''}  
**Résultat:** {str(tool['result'])[:200]}{'...' if len(str(tool['result'])) > 200 else ''}
"""
        
        # États finaux
        significant_states = [s for s in self.logger.state_snapshots 
                            if s['phase'] in ['after_modal', 'final']]
        
        if significant_states:
            report += "\n## 📊 EVOLUTION DES METRIQUES RÉELLES\n"
            for state in significant_states:
                report += f"""
**Phase {state['phase']} [{state['timestamp']*1000:.1f}ms]:**  
"""
                for key, value in state['data'].items():
                    if key != 'agents_results_keys':
                        report += f"- {key}: {value}  "
                report += "\n"
        
        # Bilan final
        if self.state:
            report += f"""
## 🎯 BILAN D'ANALYSE LLM RÉELLE
- **Score global:** {self.state.overall_score:.3f}/1.0 (calculé par GPT-4o-mini)
- **Sophismes détectés:** {self.state.fallacies_detected} (analyse LLM réelle)
- **Propositions modales:** {self.state.propositions_found} (extraction LLM)
- **Cohérence logique:** {self.state.consistency_score:.3f}/1.0 (vérification LLM)
- **Statut:** {"✅ Analyse LLM complète" if self.state.analysis_completed else "⏳ En cours"}
"""
        
        report += f"""
## 🔍 DIAGNOSTIC TECHNIQUE
- **Performance:** {total_time:.1f}ms (vrais appels LLM)
- **Messages capturés:** {len(self.logger.messages)} échanges
- **Appels LLM:** {len(self.logger.tool_calls)} (GPT-4o-mini)
- **Pipeline:** ✅ Agents LLM réels opérationnels

---
*Trace générée par Enhanced PM Orchestration v2.0 - Agents LLM réels (GPT-4o-mini)*
"""
        
        return report


# Fonction de compatibilité pour l'interface existante
async def run_real_llm_analysis(text: str, llm_service: Optional[Union[OpenAIChatCompletion, AzureChatCompletion]] = None) -> str:
    """
    Interface de compatibilité pour exécuter une analyse avec vrais agents LLM.
    
    Args:
        text: Texte à analyser
        llm_service: Service LLM optionnel
        
    Returns:
        Rapport d'analyse au format markdown
    """
    orchestrator = RealLLMOrchestrator(mode="real", llm_service=llm_service)
    return await orchestrator.run_orchestration(text)


# Logger du module
module_logger = logging.getLogger(__name__)
module_logger.debug("Module real_llm_orchestrator chargé.")

=======
#!/usr/bin/env python3
"""
Real LLM Orchestrator - Composant réutilisable pour orchestration avec vrais agents LLM
========================================================================================

Composant d'orchestration utilisant de véritables appels à GPT-4o-mini au lieu de simulations.
S'intègre harmonieusement avec l'architecture existante du projet.
"""

import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

# Imports Semantic Kernel
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, AzureChatCompletion

# Imports de l'architecture existante
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.llm_service import create_llm_service
from argumentation_analysis.core.jvm_setup import initialize_jvm

# Imports des agents réels
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent
from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent
from argumentation_analysis.agents.core.synthesis.synthesis_agent import SynthesisAgent

# Import du système de correction intelligente des erreurs Tweety
from argumentation_analysis.utils.tweety_error_analyzer import TweetyErrorAnalyzer, create_bnf_feedback_for_error

logger = logging.getLogger("RealLLMOrchestrator")


class RealConversationLogger:
    """Logger pour conversations avec vrais agents LLM - Compatible avec l'architecture existante."""
    
    def __init__(self):
        self.start_time = time.time()
        self.messages = []
        self.tool_calls = []
        self.state_snapshots = []
        self.logger = logging.getLogger(f"{__name__}.ConversationLogger")
        
    def log_agent_message(self, agent: str, message: str, phase: str):
        """Enregistre un message d'agent."""
        timestamp_ms = (time.time() - self.start_time) * 1000
        self.messages.append({
            'timestamp': timestamp_ms,
            'time_ms': timestamp_ms,
            'agent': agent,
            'message': message,
            'phase': phase
        })
        self.logger.info(f"[{timestamp_ms:.1f}ms] MESSAGE {agent}: {message}")
        
    def log_tool_call(self, agent: str, tool: str, arguments: Any, result: Any, success: bool = True):
        """Enregistre un appel d'outil."""
        timestamp_ms = (time.time() - self.start_time) * 1000
        self.tool_calls.append({
            'timestamp': timestamp_ms,
            'time_ms': timestamp_ms,
            'agent': agent,
            'tool': tool,
            'arguments': arguments,
            'result': result,
            'success': success
        })
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"[{timestamp_ms:.1f}ms] TOOL {agent} -> {tool} {status}")
        
    def log_state_snapshot(self, phase: str, state_data: Dict[str, Any]):
        """Enregistre un snapshot d'état."""
        timestamp = time.time() - self.start_time
        self.state_snapshots.append({
            'timestamp': timestamp,
            'phase': phase,
            'data': state_data
        })


class RealLLMOrchestrator:
    """
    Orchestrateur utilisant de vrais agents LLM - Intégré avec l'architecture existante.
    
    Ce composant réutilisable encapsule la logique d'orchestration avec de véritables
    appels LLM tout en respectant les patterns de l'architecture du projet.
    """
    
    def __init__(self, mode: str = "real", llm_service: Optional[Union[OpenAIChatCompletion, AzureChatCompletion]] = None):
        """
        Initialise l'orchestrateur.
        
        Args:
            mode: Mode d'opération ("real" par défaut)
            llm_service: Service LLM optionnel (créé automatiquement si None)
        """
        self.mode = mode
        self.logger = RealConversationLogger()
        self.state = None  # Sera initialisé avec RhetoricalAnalysisState
        self.llm_service = llm_service
        self.kernel = None
        self.agents = {}
        self.current_text = ""
        self.orchestration_logger = logging.getLogger(f"{__name__}.Orchestrator")
        
    async def initialize(self) -> bool:
        """
        Initialise complètement l'orchestrateur.
        
        Cette méthode est appelée par le pipeline unifié.
        """
        try:
            self.orchestration_logger.info("Initialisation complète de l'orchestrateur LLM réel...")
            
            # 1. Initialiser les services LLM
            llm_success = await self.initialize_llm_services()
            if not llm_success:
                return False
                
            # 2. Initialiser les agents réels
            agents_success = await self.initialize_real_agents()
            if not agents_success:
                return False
                
            self.orchestration_logger.info("Orchestrateur LLM réel initialisé avec succès")
            return True
            
        except Exception as e:
            self.orchestration_logger.error(f"Erreur lors de l'initialisation complète: {e}")
            return False
        
    async def initialize_llm_services(self) -> bool:
        """Initialise les services LLM réels."""
        try:
            self.logger.log_agent_message(
                "ProjectManager",
                "Initialisation des services LLM réels (GPT-4o-mini)...",
                "initialization"
            )
            
            # Service LLM - utiliser celui fourni ou en créer un
            if self.llm_service is None:
                self.llm_service = create_llm_service()
                
            if not self.llm_service:
                raise Exception("Impossible de créer le service LLM")
                
            # Kernel Semantic Kernel
            self.kernel = sk.Kernel()
            self.kernel.add_service(self.llm_service)
            
            self.logger.log_tool_call(
                "ProjectManager",
                "initialize_llm_service",
                {"service_type": "GPT-4o-mini", "kernel": "semantic_kernel"},
                {"service_id": self.llm_service.service_id, "status": "ready"},
                True
            )
            
            self.orchestration_logger.info(f"Services LLM initialisés avec succès: {self.llm_service.service_id}")
            return True
            
        except Exception as e:
            self.logger.log_tool_call(
                "ProjectManager", 
                "initialize_llm_service",
                {"service_type": "GPT-4o-mini"},
                {"error": str(e)},
                False
            )
            self.orchestration_logger.error(f"Erreur initialisation services LLM: {e}")
            return False
            
    async def initialize_real_agents(self) -> bool:
        """Initialise les vrais agents LLM."""
        try:
            self.logger.log_agent_message(
                "ProjectManager",
                "Création des agents d'analyse réels...",
                "initialization"
            )
            
            # Agent d'analyse informelle
            informal_agent = InformalAnalysisAgent(kernel=self.kernel)
            informal_agent.setup_agent_components(self.llm_service.service_id)
            self.agents["informal"] = informal_agent
            
            # Agent de logique modale 
            modal_agent = ModalLogicAgent(kernel=self.kernel, service_id=self.llm_service.service_id)
            modal_agent.setup_agent_components(self.llm_service.service_id)
            self.agents["modal"] = modal_agent
            
            # Agent de synthèse
            synthesis_agent = SynthesisAgent(kernel=self.kernel)
            synthesis_agent.setup_agent_components(self.llm_service.service_id)
            self.agents["synthesis"] = synthesis_agent
            
            self.logger.log_tool_call(
                "ProjectManager",
                "initialize_real_agents",
                {"agents": ["InformalAnalysisAgent", "ModalLogicAgent", "SynthesisAgent"]},
                {"agents_created": len(self.agents), "all_ready": True},
                True
            )
            
            self.logger.log_agent_message(
                "ProjectManager",
                f"Agents réels créés avec succès: {', '.join(self.agents.keys())}",
                "initialization"
            )
            
            self.orchestration_logger.info(f"Agents réels initialisés: {list(self.agents.keys())}")
            return True
            
        except Exception as e:
            self.logger.log_tool_call(
                "ProjectManager",
                "initialize_real_agents", 
                {"agents": ["InformalAnalysisAgent", "ModalLogicAgent", "SynthesisAgent"]},
                {"error": str(e)},
                False
            )
            self.orchestration_logger.error(f"Erreur initialisation agents: {e}")
            return False
            
    async def run_real_informal_analysis(self, text: str) -> Dict[str, Any]:
        """Exécute l'analyse informelle avec le vrai agent."""
        self.logger.log_agent_message(
            "InformalAnalysisAgent",
            "Démarrage de l'analyse rhétorique informelle avec GPT-4o-mini...",
            "informal_analysis"
        )
        
        try:
            agent = self.agents["informal"]
            
            # Appel réel de l'agent
            result = await agent.perform_complete_analysis(text)
            
            self.logger.log_tool_call(
                "InformalAnalysisAgent",
                "perform_complete_analysis",
                {"text_length": len(text), "analysis_type": "rhetorical"},
                result,
                True
            )
            
            # Mise à jour de l'état partagé
            if self.state:
                sophisms_count = len(result.get('fallacies', []))
                self.state.fallacies_detected = sophisms_count
                self.state.agents_results['informal'] = result
                
                sophisms_details = [f"{f.get('nom', 'Unknown')} (confiance: {f.get('confidence', 0):.2f})"
                                  for f in result.get('fallacies', [])]
                
                self.logger.log_agent_message(
                    "InformalAnalysisAgent",
                    f"Analyse terminée. {sophisms_count} sophismes détectés: {', '.join(sophisms_details)}. Score de qualité rhétorique calculé.",
                    "informal_analysis"
                )
                
                self.state.agents_active += 1
                self.state.overall_score += 0.3
            
            return result
            
        except Exception as e:
            self.logger.log_tool_call(
                "InformalAnalysisAgent",
                "perform_complete_analysis",
                {"text_length": len(text)},
                {"error": str(e)},
                False
            )
            self.orchestration_logger.error(f"Erreur analyse informelle: {e}")
            raise
            
    async def run_real_modal_analysis(self, text: str) -> Dict[str, Any]:
        """Exécute l'analyse modale avec correction intelligente des erreurs Tweety via feedback BNF."""
        self.logger.log_agent_message(
            "ModalLogicAgent",
            "Démarrage de l'analyse de logique modale avec correction intelligente des erreurs...",
            "modal_analysis"
        )
        
        try:
            agent = self.agents["modal"]
            
            # Initialiser l'analyseur d'erreurs Tweety
            error_analyzer = TweetyErrorAnalyzer()
            
            # Système de correction intelligente avec feedback BNF progressif
            max_retries = 3
            last_error = ""
            bnf_feedback_history = []
            
            for attempt in range(max_retries):
                attempt_num = attempt + 1
                
                # Logger le début de chaque tentative avec contexte de progression
                attempt_context = f"avec feedback BNF progressif (erreurs précédentes analysées)" if attempt > 0 else "première tentative"
                self.logger.log_agent_message(
                    "ModalLogicAgent",
                    f"Tentative de conversion {attempt_num}/3 {attempt_context}...",
                    "sk_retry_intelligent"
                )
                
                try:
                    # Construire un prompt enrichi avec le feedback BNF des tentatives précédentes
                    enhanced_input = self._build_enhanced_prompt_with_bnf_feedback(text, bnf_feedback_history)
                    
                    # Appel de la fonction sémantique avec le prompt enrichi
                    result = await agent.sk_kernel.plugins[agent.name]["TextToModalBeliefSet"].invoke(
                        agent.sk_kernel, input=enhanced_input
                    )
                    
                    # Extraire et parser le JSON
                    import json
                    json_str = agent._extract_json_block(str(result))
                    kb_json = json.loads(json_str)
                    
                    # Valider la cohérence du JSON
                    is_valid, validation_msg = agent._validate_modal_kb_json(kb_json)
                    if not is_valid:
                        raise ValueError(f"JSON invalide: {validation_msg}")
                    
                    # Construire la base de connaissances modale
                    belief_set_content = agent._construct_modal_kb_from_json(kb_json)
                    
                    if not belief_set_content:
                        raise ValueError("La conversion a produit une base de connaissances vide.")

                    # Valider avec Tweety
                    is_valid, validation_msg = agent.tweety_bridge.validate_modal_belief_set(belief_set_content)
                    if not is_valid:
                        raise ValueError(f"Ensemble de croyances invalide selon Tweety: {validation_msg}")
                    
                    # Si on arrive ici, la tentative a réussi grâce au feedback BNF
                    from argumentation_analysis.agents.core.belief_sets.modal_belief_set import ModalBeliefSet
                    belief_set_obj = ModalBeliefSet(belief_set_content)
                    
                    correction_success_msg = f"SUCCÈS après {attempt_num} tentative(s)" if attempt_num == 1 else f"CORRECTION INTELLIGENTE RÉUSSIE après {attempt_num} tentatives (feedback BNF efficace)"
                    
                    self.logger.log_tool_call(
                        "ModalLogicAgent",
                        f"text_to_belief_set_intelligent_attempt_{attempt_num}",
                        {
                            "text_length": len(text),
                            "attempt": attempt_num,
                            "bnf_feedback_used": len(bnf_feedback_history) > 0,
                            "correction_method": "intelligent_bnf_feedback"
                        },
                        {
                            "success": True,
                            "belief_set_size": len(belief_set_content),
                            "correction_success": correction_success_msg
                        },
                        True
                    )
                    
                    self.logger.log_agent_message(
                        "ModalLogicAgent",
                        correction_success_msg + f". Analyse modale valide générée.",
                        "intelligent_correction_success"
                    )
                    
                    return {"belief_set": belief_set_obj, "success": True, "corrected_attempt": attempt_num}
                    
                except Exception as e:
                    # Analyser l'erreur avec le système BNF intelligent
                    error_msg = str(e)
                    
                    # Générer le feedback BNF constructif
                    bnf_feedback = error_analyzer.analyze_error(error_msg, {
                        "attempt": attempt_num,
                        "agent": "ModalLogicAgent",
                        "text_context": text[:100]
                    })
                    
                    # Créer le message de feedback formaté
                    feedback_message = error_analyzer.generate_bnf_feedback_message(bnf_feedback, attempt_num)
                    
                    # Stocker le feedback pour les prochaines tentatives
                    bnf_feedback_history.append({
                        "attempt": attempt_num,
                        "error": error_msg,
                        "feedback": bnf_feedback,
                        "feedback_message": feedback_message
                    })
                    
                    last_error = f"Tentative {attempt_num}: {error_msg}"
                    
                    # Logger l'échec avec le feedback BNF généré
                    self.logger.log_tool_call(
                        "ModalLogicAgent",
                        f"text_to_belief_set_intelligent_attempt_{attempt_num}",
                        {
                            "text_length": len(text),
                            "attempt": attempt_num,
                            "error_type": bnf_feedback.error_type,
                            "bnf_confidence": bnf_feedback.confidence
                        },
                        {
                            "error": error_msg,
                            "bnf_feedback_generated": True,
                            "error_type": bnf_feedback.error_type,
                            "bnf_rules_count": len(bnf_feedback.bnf_rules),
                            "corrections_provided": len(bnf_feedback.corrections)
                        },
                        False
                    )
                    
                    # Logger le message de feedback constructif
                    self.logger.log_agent_message(
                        "ModalLogicAgent",
                        f"Tentative {attempt_num}/{max_retries} - Erreur analysée: {bnf_feedback.error_type}. Feedback BNF généré pour correction intelligente.",
                        "intelligent_error_analysis"
                    )
                    
                    # Log detaillé du feedback BNF (pour débogage et traces)
                    self.orchestration_logger.info(f"Feedback BNF Tentative {attempt_num}:\n{feedback_message}")
                    
                    if attempt_num == max_retries:
                        break
            
            # Toutes les tentatives ont échoué malgré le feedback BNF
            final_error = f"Échec de la correction intelligente après {max_retries} tentatives avec feedback BNF. Dernière erreur: {last_error}"
            
            # Analyser l'échec global pour des recommandations d'amélioration système
            failure_analysis = self._analyze_correction_failure(bnf_feedback_history)
            
            self.logger.log_tool_call(
                "ModalLogicAgent",
                "intelligent_modal_conversion",
                {
                    "text_length": len(text),
                    "logic_type": "modal",
                    "max_retries": max_retries,
                    "correction_method": "intelligent_bnf_feedback",
                    "bnf_feedbacks_generated": len(bnf_feedback_history)
                },
                {
                    "error": final_error,
                    "sk_retry_attempts": max_retries,
                    "bnf_correction_attempted": True,
                    "failure_analysis": failure_analysis
                },
                False
            )
            
            self.logger.log_agent_message(
                "ModalLogicAgent",
                f"Correction intelligente échouée après {max_retries} tentatives avec feedback BNF. {failure_analysis}. Poursuite de l'orchestration sans analyse modale.",
                "intelligent_correction_failure"
            )
            
            # Mise à jour de l'état avec l'erreur et les tentatives de correction
            if self.state:
                self.state.agents_results['modal'] = {
                    "error": final_error,
                    "intelligent_correction_attempted": True,
                    "bnf_feedback_history": bnf_feedback_history,
                    "failure_analysis": failure_analysis
                }
                self.state.agents_active += 1
                
            return {"error": final_error, "correction_attempted": True, "bnf_feedback_history": bnf_feedback_history}
            
        except Exception as e:
            self.logger.log_tool_call(
                "ModalLogicAgent",
                "intelligent_modal_conversion",
                {"text_length": len(text)},
                {"error": str(e), "correction_system_error": True},
                False
            )
            self.orchestration_logger.error(f"Erreur système de correction intelligente: {e}")
            raise
            
    async def run_real_synthesis(self, text: str) -> Any:
        """Exécute la synthèse avec le vrai agent."""
        self.logger.log_agent_message(
            "SynthesisAgent",
            "Démarrage de la synthèse unifiée avec GPT-4o-mini...",
            "synthesis"
        )
        
        try:
            agent = self.agents["synthesis"]
            
            # Synthèse des résultats
            synthesis_result = await agent.synthesize_analysis(text)
            
            self.logger.log_tool_call(
                "SynthesisAgent",
                "perform_complete_analysis",
                {
                    "informal_results": self.state.agents_results.get('informal', {}) if self.state else {},
                    "modal_results": self.state.agents_results.get('modal', {}) if self.state else {},
                    "synthesis_strategy": "unified_analysis"
                },
                synthesis_result,
                True
            )
            
            # Extraction des résultats depuis UnifiedReport
            if hasattr(synthesis_result, 'overall_score'):
                unified_score = synthesis_result.overall_score
            else:
                unified_score = 0.0
                
            if hasattr(synthesis_result, 'main_issues'):
                main_issues = synthesis_result.main_issues or []
            else:
                main_issues = []
            
            self.logger.log_agent_message(
                "SynthesisAgent",
                f"Synthèse terminée. Score unifié: {unified_score:.3f}, problèmes identifiés: {', '.join(main_issues)}",
                "synthesis"
            )
            
            # Mise à jour de l'état partagé
            if self.state:
                self.state.agents_results['synthesis'] = synthesis_result
                self.state.agents_active += 1
                self.state.overall_score = unified_score
                self.state.analysis_completed = True
            
            return synthesis_result
            
        except Exception as e:
            self.logger.log_tool_call(
                "SynthesisAgent",
                "perform_complete_analysis",
                {"text_length": len(text)},
                {"error": str(e)},
                False
            )
            self.orchestration_logger.error(f"Erreur synthèse: {e}")
            raise
            
    async def orchestrate_analysis(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        Interface standardisée pour le pipeline unifié.
        
        Cette méthode fait le wrapper vers run_orchestration() en adaptant
        les paramètres et le format de retour pour l'interface unifiée.
        """
        try:
            self.orchestration_logger.info("Démarrage orchestration unifiée via interface standardisée...")
            
            # Exécuter l'orchestration complète
            markdown_report = await self.run_orchestration(text, kwargs.get('state'))
            
            # Adapter le résultat pour l'interface unifiée
            result = {
                "orchestration": {
                    "mode": self.mode,
                    "agents_used": list(self.agents.keys()),
                    "success": True,
                    "report": markdown_report
                },
                "conversation_log": {
                    "messages": self.logger.messages,
                    "tool_calls": self.logger.tool_calls,
                    "state_snapshots": self.logger.state_snapshots
                },
                "metadata": {
                    "llm_service_id": self.llm_service.service_id if self.llm_service else None,
                    "agents_count": len(self.agents),
                    "total_runtime_ms": (time.time() - self.logger.start_time) * 1000 if self.logger.start_time else 0
                }
            }
            
            # Ajouter les résultats détaillés si disponibles
            if self.state:
                result["analysis_results"] = {
                    "overall_score": self.state.overall_score,
                    "agents_results": dict(self.state.agents_results),
                    "analysis_completed": self.state.analysis_completed
                }
            
            self.orchestration_logger.info("Orchestration unifiée terminée avec succès")
            return result
            
        except Exception as e:
            self.orchestration_logger.error(f"Erreur orchestration unifiée: {e}")
            return {
                "orchestration": {
                    "mode": self.mode,
                    "success": False,
                    "error": str(e)
                },
                "conversation_log": {
                    "messages": self.logger.messages,
                    "tool_calls": self.logger.tool_calls
                }
            }
            
    async def run_orchestration(self, text: str, state: Optional[RhetoricalAnalysisState] = None) -> str:
        """
        Exécute l'orchestration complète avec vrais agents LLM.
        
        Args:
            text: Texte à analyser
            state: État partagé optionnel (créé automatiquement si None)
            
        Returns:
            Rapport d'analyse au format markdown
        """
        self.current_text = text
        
        # Initialiser l'état si non fourni
        if state is None:
            self.state = RhetoricalAnalysisState(initial_text=text)
        else:
            self.state = state
            
        try:
            # Initialisation
            if not await self.initialize_llm_services():
                raise Exception("Impossible d'initialiser les services LLM")
                
            if not await self.initialize_real_agents():
                raise Exception("Impossible d'initialiser les agents")
                
            self.logger.log_state_snapshot("initialization", self._state_to_dict())
            
            # Coordination du ProjectManager
            self.logger.log_agent_message(
                "ProjectManager",
                "Orchestration démarrée. Lancement séquentiel des analyses avec agents LLM réels.",
                "coordination"
            )
            
            # Analyses séquentielles
            await self.run_real_informal_analysis(text)
            self.logger.log_state_snapshot("after_informal", self._state_to_dict())
            
            await self.run_real_modal_analysis(text)
            self.logger.log_state_snapshot("after_modal", self._state_to_dict())
            
            await self.run_real_synthesis(text)
            self.logger.log_state_snapshot("final", self._state_to_dict())
            
            # Coordination finale
            self.logger.log_tool_call(
                "ProjectManager",
                "coordinate_final_synthesis",
                {"agents_results": len(self.agents), "final_score": self.state.overall_score},
                {"coordination": "success", "status": "completed", "real_llm_calls": True},
                True
            )
            
            self.logger.log_agent_message(
                "ProjectManager",
                f"Orchestration terminée avec succès. Score final: {self.state.overall_score:.3f}. Tous les agents LLM ont contribué à l'analyse.",
                "conclusion"
            )
            
            return self.generate_report()
            
        except Exception as e:
            self.logger.log_agent_message(
                "ProjectManager",
                f"Erreur lors de l'orchestration: {str(e)}",
                "error"
            )
            self.orchestration_logger.error(f"Erreur orchestration: {e}")
            raise
            
    def _state_to_dict(self) -> Dict[str, Any]:
        """Convertit l'état en dictionnaire pour les snapshots."""
        if not self.state:
            return {}
            
        return {
            "overall_score": round(self.state.overall_score, 3),
            "agents_active": self.state.agents_active,
            "fallacies_detected": self.state.fallacies_detected,
            "propositions_found": self.state.propositions_found,
            "consistency_score": round(self.state.consistency_score, 3),
            "analysis_completed": self.state.analysis_completed,
            "agents_results_keys": list(self.state.agents_results.keys())
        }
            
    def _build_enhanced_prompt_with_bnf_feedback(self, original_text: str, bnf_feedback_history: List[Dict[str, Any]]) -> str:
        """
        Construit un prompt enrichi avec le feedback BNF des tentatives précédentes.
        
        Args:
            original_text: Texte original à analyser
            bnf_feedback_history: Historique des feedbacks BNF des tentatives précédentes
            
        Returns:
            Prompt enrichi avec les corrections BNF
        """
        if not bnf_feedback_history:
            return original_text
        
        # Construire le prompt enrichi
        enhanced_prompt = f"""TEXTE À ANALYSER: {original_text}

⚠️ CORRECTIONS BNF BASÉES SUR LES ERREURS PRÉCÉDENTES:

"""
        
        for feedback_entry in bnf_feedback_history:
            attempt = feedback_entry["attempt"]
            feedback = feedback_entry["feedback"]
            
            enhanced_prompt += f"""
TENTATIVE {attempt} - ERREUR ANALYSÉE: {feedback.error_type}
RÈGLES BNF À RESPECTER:
"""
            for rule in feedback.bnf_rules:
                enhanced_prompt += f"• {rule}\n"
            
            enhanced_prompt += f"""
CORRECTIONS SPÉCIFIQUES:
"""
            for correction in feedback.corrections:
                enhanced_prompt += f"• {correction}\n"
            
            enhanced_prompt += f"""
EXEMPLE DE CORRECTION:
{feedback.example_fix}

"""
        
        enhanced_prompt += f"""
🎯 INSTRUCTIONS STRICTES POUR CETTE TENTATIVE:
1. Appliquer TOUTES les corrections BNF mentionnées ci-dessus
2. Éviter les erreurs identifiées dans les tentatives précédentes
3. Respecter strictement la syntaxe Tweety Modal Logic
4. Déclarer tous les prédicats avant usage dans les formules modales
5. Ne JAMAIS utiliser "constant" dans les formules, seulement dans les déclarations

Générez le JSON corrigé en tenant compte de ce feedback constructif.
"""
        
        return enhanced_prompt
    
    def _analyze_correction_failure(self, bnf_feedback_history: List[Dict[str, Any]]) -> str:
        """
        Analyse l'échec global du système de correction pour des recommandations d'amélioration.
        
        Args:
            bnf_feedback_history: Historique complet des tentatives et feedbacks
            
        Returns:
            Analyse de l'échec avec recommandations
        """
        if not bnf_feedback_history:
            return "Aucune tentative de correction documentée."
        
        # Analyser les patterns d'erreurs
        error_types = [entry["feedback"].error_type for entry in bnf_feedback_history]
        recurring_errors = {}
        for error_type in error_types:
            recurring_errors[error_type] = recurring_errors.get(error_type, 0) + 1
        
        # Analyser la progression (ou régression)
        if len(bnf_feedback_history) > 1:
            first_error = bnf_feedback_history[0]["feedback"].error_type
            last_error = bnf_feedback_history[-1]["feedback"].error_type
            progression = "Même type d'erreur persistant" if first_error == last_error else "Types d'erreurs différents"
        else:
            progression = "Une seule tentative"
        
        # Calculer l'efficacité du feedback
        confidence_scores = [entry["feedback"].confidence for entry in bnf_feedback_history]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        analysis = f"""Erreurs récurrentes: {dict(recurring_errors)}.
Progression: {progression}.
Confiance moyenne feedback: {avg_confidence:.2f}.
Recommandation: {"Améliorer le prompt système de l'agent modal" if avg_confidence > 0.8 else "Améliorer l'analyseur d'erreurs BNF"}"""
        
        return analysis

    def generate_report(self) -> str:
        """Génère le rapport final avec résultats LLM réels."""
        total_time = (time.time() - self.logger.start_time) * 1000
        text_size = len(self.current_text)
        text_words = len(self.current_text.split())
        
        report = f"""# TRACE ANALYTIQUE - AGENTS LLM RÉELS (GPT-4o-mini)
===========================================================

## 📄 EXTRAIT ANALYSE
- **Source:** Texte libre (analyse LLM réelle)
- **Taille:** {text_size} caractères, {text_words} mots
- **Type:** Argumentation avec analyses LLM complètes
- **Extrait:** "{self.current_text[:100]}{'...' if text_size > 100 else ''}"

## ⏱️ METADONNEES D'EXECUTION
- **Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Mode:** {self.mode} (agents LLM réels)
- **Durée totale:** {total_time:.1f}ms
- **Service LLM:** {self.llm_service.service_id if self.llm_service else 'N/A'}
- **Agents orchestrés:** {self.state.agents_active if self.state else 0}

## 🎭 TRACE CONVERSATIONNELLE CHRONOLOGIQUE (VRAIS APPELS LLM)
"""
        
        # Fusionner messages et outils chronologiquement
        all_events = []
        
        for msg in self.logger.messages:
            all_events.append({
                'type': 'message',
                'timestamp': msg['time_ms'],
                'data': msg
            })
            
        for tool in self.logger.tool_calls:
            all_events.append({
                'type': 'tool',
                'timestamp': tool['time_ms'], 
                'data': tool
            })
            
        all_events.sort(key=lambda x: x['timestamp'])
        
        for event in all_events:
            if event['type'] == 'message':
                msg = event['data']
                report += f"""
### [{msg['time_ms']:.1f}ms] 💬 **{msg['agent']}**
**Phase:** {msg['phase']}  
**Message:** *"{msg['message']}"*
"""
            elif event['type'] == 'tool':
                tool = event['data']
                status = "✅" if tool['success'] else "❌"
                report += f"""
### [{tool['time_ms']:.1f}ms] 🔧 **APPEL LLM RÉEL** {status}
**Agent:** {tool['agent']}  
**Outil:** `{tool['tool']}`  
**Arguments:** {str(tool['arguments'])[:200]}{'...' if len(str(tool['arguments'])) > 200 else ''}  
**Résultat:** {str(tool['result'])[:200]}{'...' if len(str(tool['result'])) > 200 else ''}
"""
        
        # États finaux
        significant_states = [s for s in self.logger.state_snapshots 
                            if s['phase'] in ['after_modal', 'final']]
        
        if significant_states:
            report += "\n## 📊 EVOLUTION DES METRIQUES RÉELLES\n"
            for state in significant_states:
                report += f"""
**Phase {state['phase']} [{state['timestamp']*1000:.1f}ms]:**  
"""
                for key, value in state['data'].items():
                    if key != 'agents_results_keys':
                        report += f"- {key}: {value}  "
                report += "\n"
        
        # Bilan final
        if self.state:
            report += f"""
## 🎯 BILAN D'ANALYSE LLM RÉELLE
- **Score global:** {self.state.overall_score:.3f}/1.0 (calculé par GPT-4o-mini)
- **Sophismes détectés:** {self.state.fallacies_detected} (analyse LLM réelle)
- **Propositions modales:** {self.state.propositions_found} (extraction LLM)
- **Cohérence logique:** {self.state.consistency_score:.3f}/1.0 (vérification LLM)
- **Statut:** {"✅ Analyse LLM complète" if self.state.analysis_completed else "⏳ En cours"}
"""
        
        report += f"""
## 🔍 DIAGNOSTIC TECHNIQUE
- **Performance:** {total_time:.1f}ms (vrais appels LLM)
- **Messages capturés:** {len(self.logger.messages)} échanges
- **Appels LLM:** {len(self.logger.tool_calls)} (GPT-4o-mini)
- **Pipeline:** ✅ Agents LLM réels opérationnels

---
*Trace générée par Enhanced PM Orchestration v2.0 - Agents LLM réels (GPT-4o-mini)*
"""
        
        return report


# Fonction de compatibilité pour l'interface existante
async def run_real_llm_analysis(text: str, llm_service: Optional[Union[OpenAIChatCompletion, AzureChatCompletion]] = None) -> str:
    """
    Interface de compatibilité pour exécuter une analyse avec vrais agents LLM.
    
    Args:
        text: Texte à analyser
        llm_service: Service LLM optionnel
        
    Returns:
        Rapport d'analyse au format markdown
    """
    orchestrator = RealLLMOrchestrator(mode="real", llm_service=llm_service)
    return await orchestrator.run_orchestration(text)


# Logger du module
module_logger = logging.getLogger(__name__)
module_logger.debug("Module real_llm_orchestrator chargé.")
>>>>>>> BACKUP
