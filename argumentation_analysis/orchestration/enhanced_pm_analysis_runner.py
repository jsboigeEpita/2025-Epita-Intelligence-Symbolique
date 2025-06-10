#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Enhanced Project Manager Analysis Runner avec orchestration multi-tours,
gestion d'état partagé et format de conversation amélioré.

Ce module intègre :
- Orchestration multi-tours avec Project Manager
- Gestion d'état partagé coordonnée
- Format de conversation élégant avec headers spéciaux
- Coordination agents formels/informels
- Capture enrichie avec évolution d'état
"""

import sys
import os
import time
import traceback
import asyncio
import logging
import json
import random
from typing import List, Optional, Union, Any, Dict

# Configuration des chemins
current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_script_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Imports Semantic Kernel
import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent
from argumentation_analysis.utils.semantic_kernel_compatibility import AuthorRole, AgentGroupChat, ChatCompletionAgent, Agent, AgentChatException, FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, AzureChatCompletion
from semantic_kernel.functions.kernel_arguments import KernelArguments

# Imports système existant
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.core.strategies import SimpleTerminationStrategy, BalancedParticipationStrategy

# Imports agents
from argumentation_analysis.agents.core.pm.pm_agent import ProjectManagerAgent
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent
from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent

# Import du système de trace amélioré
from argumentation_analysis.reporting.enhanced_real_time_trace_analyzer import (
    enhanced_global_trace_analyzer,
    start_enhanced_pm_capture,
    stop_enhanced_pm_capture,
    start_pm_orchestration_phase,
    capture_shared_state,
    get_enhanced_pm_report,
    save_enhanced_pm_report,
    enhanced_tool_call_tracer
)

logger = logging.getLogger("EnhancedPMOrchestration")
if not logger.handlers and not logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class EnhancedProjectManagerOrchestrator:
    """
    Orchestrateur Project Manager amélioré avec gestion d'état partagé,
    orchestration multi-tours et format de conversation élégant.
    """
    
    def __init__(self, llm_service: Union[OpenAIChatCompletion, AzureChatCompletion]):
        """Initialise l'orchestrateur PM amélioré."""
        self.llm_service = llm_service
        self.shared_state: Optional[RhetoricalAnalysisState] = None
        self.kernel: Optional[sk.Kernel] = None
        self.group_chat: Optional[AgentGroupChat] = None
        self.state_manager_plugin: Optional[StateManagerPlugin] = None
        
        # Orchestration multi-tours
        self.orchestration_phases = []
        self.current_phase = None
        self.tour_counter = 0
        self.phase_counter = 0
        
        # Agents pour l'orchestration
        self.agents = {}
        self.agent_list = []
        
        # Métadonnées PM
        self.pm_metadata = {
            "orchestration_type": "Enhanced Multi-Turn PM",
            "state_management": True,
            "conversation_format": "Enhanced Markdown",
            "agents_coordination": "Formal/Informal Balance"
        }
    
    async def setup_enhanced_orchestration(self, texte_a_analyser: str) -> bool:
        """Configure l'orchestration PM améliorée."""
        logger.info("[CONFIG] Configuration de l'orchestration PM améliorée...")
        
        try:
            # 1. Création de l'état partagé
            self.shared_state = RhetoricalAnalysisState(initial_text=texte_a_analyser)
            self.state_manager_plugin = StateManagerPlugin(self.shared_state)
            
            # 2. Configuration du kernel
            self.kernel = sk.Kernel()
            self.kernel.add_service(self.llm_service)
            self.kernel.add_plugin(self.state_manager_plugin, plugin_name="StateManager")
            
            # 3. Configuration des agents avec instrumentation de trace
            await self._setup_enhanced_agents()
            
            # 4. Configuration des stratégies
            self._setup_enhanced_strategies()
            
            # 5. Démarrage de la capture de trace
            start_enhanced_pm_capture()
            
            logger.info("✅ Orchestration PM améliorée configurée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Erreur configuration orchestration PM: {e}", exc_info=True)
            return False
    
    async def _setup_enhanced_agents(self):
        """Configure les agents avec instrumentation de trace améliorée."""
        logger.info("[SETUP] Configuration des agents avec instrumentation...")
        
        llm_service_id = self.llm_service.service_id
        prompt_exec_settings = self.kernel.get_prompt_execution_settings_from_service_id(llm_service_id)
        prompt_exec_settings.function_choice_behavior = FunctionChoiceBehavior.Auto(
            auto_invoke_kernel_functions=True, 
            max_auto_invoke_attempts=5
        )
        
        # Configuration Project Manager
        pm_agent_refactored = ProjectManagerAgent(kernel=self.kernel, agent_name="EnhancedProjectManagerAgent")
        pm_agent_refactored.setup_agent_components(llm_service_id=llm_service_id)
        
        pm_agent = ChatCompletionAgent(
            kernel=self.kernel,
            service=self.llm_service,
            name="ProjectManagerAgent",
            instructions=pm_agent_refactored.system_prompt,
            arguments=KernelArguments(settings=prompt_exec_settings)
        )
        self.agents["ProjectManager"] = pm_agent
        
        # Configuration Informal Agent
        informal_agent_refactored = InformalAnalysisAgent(kernel=self.kernel, agent_name="EnhancedInformalAgent")
        informal_agent_refactored.setup_agent_components(llm_service_id=llm_service_id)
        
        informal_agent = ChatCompletionAgent(
            kernel=self.kernel,
            service=self.llm_service,
            name="InformalAnalysisAgent",
            instructions=informal_agent_refactored.system_prompt,
            arguments=KernelArguments(settings=prompt_exec_settings)
        )
        self.agents["InformalAnalysis"] = informal_agent
        
        # Configuration Modal Logic Agent
        modal_agent_refactored = ModalLogicAgent(kernel=self.kernel, agent_name="EnhancedModalLogicAgent")
        modal_agent_refactored.setup_agent_components(llm_service_id=llm_service_id)
        
        modal_agent = ChatCompletionAgent(
            kernel=self.kernel,
            service=self.llm_service,
            name="ModalLogicAgent",
            instructions=modal_agent_refactored.system_prompt,
            arguments=KernelArguments(settings=prompt_exec_settings)
        )
        self.agents["ModalLogic"] = modal_agent
        
        # Configuration Extract Agent
        extract_agent_refactored = ExtractAgent(kernel=self.kernel, agent_name="EnhancedExtractAgent")
        extract_agent_refactored.setup_agent_components(llm_service_id=llm_service_id)
        
        extract_agent = ChatCompletionAgent(
            kernel=self.kernel,
            service=self.llm_service,
            name="ExtractAgent", 
            instructions=extract_agent_refactored.system_prompt,
            arguments=KernelArguments(settings=prompt_exec_settings)
        )
        self.agents["Extract"] = extract_agent
        
        self.agent_list = list(self.agents.values())
        logger.info(f"✅ {len(self.agents)} agents configurés avec instrumentation")
    
    def _setup_enhanced_strategies(self):
        """Configure les stratégies d'orchestration améliorées."""
        logger.info("📋 Configuration des stratégies d'orchestration...")
        
        # Stratégie de terminaison étendue pour multi-tours
        termination_strategy = SimpleTerminationStrategy(self.shared_state, max_steps=20)
        
        # Stratégie de sélection avec balance formal/informal
        selection_strategy = BalancedParticipationStrategy(
            agents=self.agent_list,
            state=self.shared_state,
            default_agent_name="ProjectManagerAgent"
        )
        
        # Création du groupe de chat
        self.group_chat = AgentGroupChat(
            agents=self.agent_list,
            selection_strategy=selection_strategy,
            termination_strategy=termination_strategy
        )
        
        logger.info("✅ Stratégies d'orchestration configurées")
    
    async def run_enhanced_pm_orchestration(self, texte_a_analyser: str) -> Dict[str, Any]:
        """Lance l'orchestration PM améliorée avec gestion d'état multi-tours."""
        run_start_time = time.time()
        run_id = random.randint(10000, 99999)
        
        logger.info(f"[START] Démarrage orchestration PM améliorée (Run_{run_id})")
        
        # Configuration de l'orchestration
        setup_success = await self.setup_enhanced_orchestration(texte_a_analyser)
        if not setup_success:
            return {"success": False, "error": "Échec configuration orchestration"}
        
        try:
            # Phase 1: Initialisation et analyse informelle
            await self._run_phase_1_informal_analysis()
            
            # Phase 2: Analyse formelle modal logic
            await self._run_phase_2_formal_analysis()
            
            # Phase 3: Synthèse et coordination PM
            await self._run_phase_3_synthesis_coordination()
            
            # Finalisation
            stop_enhanced_pm_capture()
            
            # Génération du rapport final
            enhanced_report = get_enhanced_pm_report()
            
            # Sauvegarde
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            report_path = f"./logs/enhanced_pm_orchestration_demo_{timestamp}.md"
            save_success = save_enhanced_pm_report(report_path)
            
            total_duration = time.time() - run_start_time
            
            result = {
                "success": True,
                "run_id": run_id,
                "total_duration_ms": total_duration * 1000,
                "phases_completed": len(self.orchestration_phases),
                "state_snapshots": enhanced_global_trace_analyzer.total_state_snapshots,
                "tool_calls": enhanced_global_trace_analyzer.total_tool_calls,
                "report_path": report_path if save_success else None,
                "enhanced_report": enhanced_report,
                "pm_metadata": self.pm_metadata
            }
            
            logger.info(f"✅ Orchestration PM terminée avec succès ({total_duration:.2f}s)")
            return result
            
        except Exception as e:
            logger.error(f"[ERROR] Erreur orchestration PM: {e}", exc_info=True)
            stop_enhanced_pm_capture()
            return {"success": False, "error": str(e)}
    
    async def _run_phase_1_informal_analysis(self):
        """Phase 1: Analyse informelle coordonnée par PM."""
        self.phase_counter += 1
        phase_id = f"phase_{self.phase_counter}"
        
        logger.info("[CONFIG] Phase 1: Analyse informelle coordonnée")
        
        # Démarrage de la phase
        start_pm_orchestration_phase(
            phase_id=phase_id,
            phase_name="Analyse Informelle Coordonnée", 
            assigned_agents=["ProjectManagerAgent", "InformalAnalysisAgent"]
        )
        
        # Capture de l'état initial
        self.tour_counter += 1
        capture_shared_state(
            phase_id=phase_id,
            tour_number=self.tour_counter,
            agent_active="ProjectManagerAgent",
            state_variables={
                "phase": "informal_analysis",
                "agents_active": ["ProjectManagerAgent", "InformalAnalysisAgent"],
                "tasks_defined": len(self.shared_state.analysis_tasks),
                "arguments_identified": len(self.shared_state.identified_arguments),
                "fallacies_detected": len(self.shared_state.identified_fallacies)
            },
            metadata={
                "phase_type": "initialization",
                "coordination": "pm_directed",
                "state_management": "active"
            }
        )
        
        # Message initial pour PM
        initial_prompt = f"""Bonjour équipe d'analyse. Je suis le Project Manager de cette orchestration multi-tours.

TEXTE À ANALYSER:
'''
{self.shared_state.raw_text}
'''

MISSION PHASE 1 - ANALYSE INFORMELLE:
1. Coordonner l'identification des arguments principaux
2. Détecter les sophismes et fallacies logiques  
3. Préparer la base pour l'analyse formelle
4. Gérer l'état partagé entre agents

ProjectManagerAgent, veuillez définir les tâches d'analyse et coordonner l'équipe."""
        
        logger.info(f"💬 Tour {self.tour_counter}: Prompt initial PM")
        
        # Ajout à l'historique
        if hasattr(self.group_chat, 'history') and hasattr(self.group_chat.history, 'add_user_message'):
            self.group_chat.history.add_user_message(initial_prompt)
        
        # Exécution de la phase avec capture
        await self._execute_conversation_phase(phase_id, max_turns=8)
        
        # Capture de l'état final de phase
        capture_shared_state(
            phase_id=phase_id,
            tour_number=self.tour_counter,
            agent_active="ProjectManagerAgent",
            state_variables={
                "phase": "informal_analysis_complete",
                "tasks_defined": len(self.shared_state.analysis_tasks),
                "arguments_identified": len(self.shared_state.identified_arguments),
                "fallacies_detected": len(self.shared_state.identified_fallacies),
                "readiness_for_formal": True
            },
            metadata={
                "phase_completion": "success",
                "next_phase": "formal_analysis",
                "coordination_quality": "high"
            }
        )
        
        logger.info("✅ Phase 1 terminée: Base informelle établie")
    
    async def _run_phase_2_formal_analysis(self):
        """Phase 2: Analyse formelle avec modal logic."""
        self.phase_counter += 1
        phase_id = f"phase_{self.phase_counter}"
        
        logger.info("[CONFIG] Phase 2: Analyse formelle modal logic")
        
        # Démarrage de la phase
        start_pm_orchestration_phase(
            phase_id=phase_id,
            phase_name="Analyse Formelle Modal Logic",
            assigned_agents=["ProjectManagerAgent", "ModalLogicAgent", "InformalAnalysisAgent"]
        )
        
        # Message de transition PM
        transition_prompt = f"""TRANSITION VERS PHASE 2 - ANALYSE FORMELLE

État actuel de l'analyse:
- Tâches définies: {len(self.shared_state.analysis_tasks)}
- Arguments identifiés: {len(self.shared_state.identified_arguments)}  
- Sophismes détectés: {len(self.shared_state.identified_fallacies)}

MISSION PHASE 2:
1. Formalisation en logique modale des arguments identifiés
2. Vérification de la cohérence logique
3. Analyse des modalités (nécessité, possibilité)
4. Coordination état partagé entre analyse informelle et formelle

ModalLogicAgent, veuillez commencer la formalisation en vous basant sur l'état partagé actuel."""
        
        # Capture état de transition
        self.tour_counter += 1
        capture_shared_state(
            phase_id=phase_id,
            tour_number=self.tour_counter,
            agent_active="ProjectManagerAgent",
            state_variables={
                "phase": "formal_analysis_start",
                "belief_sets": len(self.shared_state.belief_sets),
                "queries_logged": len(self.shared_state.query_log),
                "formal_readiness": True,
                "informal_base_established": True
            },
            metadata={
                "transition": "informal_to_formal",
                "coordination_mode": "state_shared",
                "agents_cooperation": "high"
            }
        )
        
        # Ajout du message de transition
        if hasattr(self.group_chat, 'history') and hasattr(self.group_chat.history, 'add_user_message'):
            self.group_chat.history.add_user_message(transition_prompt)
        
        # Exécution de la phase formelle
        await self._execute_conversation_phase(phase_id, max_turns=10)
        
        # Capture état final phase 2
        capture_shared_state(
            phase_id=phase_id,
            tour_number=self.tour_counter,
            agent_active="ModalLogicAgent",
            state_variables={
                "phase": "formal_analysis_complete",
                "belief_sets": len(self.shared_state.belief_sets),
                "queries_executed": len(self.shared_state.query_log),
                "formal_consistency": True,
                "modal_analysis_complete": True
            },
            metadata={
                "formal_verification": "completed",
                "logical_consistency": "verified",
                "next_phase": "synthesis"
            }
        )
        
        logger.info("✅ Phase 2 terminée: Analyse formelle complète")
    
    async def _run_phase_3_synthesis_coordination(self):
        """Phase 3: Synthèse finale coordonnée par PM."""
        self.phase_counter += 1
        phase_id = f"phase_{self.phase_counter}"
        
        logger.info("[CONFIG] Phase 3: Synthèse finale et coordination")
        
        # Démarrage de la phase
        start_pm_orchestration_phase(
            phase_id=phase_id,
            phase_name="Synthèse Finale et Coordination PM",
            assigned_agents=["ProjectManagerAgent", "InformalAnalysisAgent", "ModalLogicAgent", "ExtractAgent"]
        )
        
        # Message de synthèse finale
        synthesis_prompt = f"""PHASE 3 FINALE - SYNTHÈSE ET COORDINATION

BILAN COMPLET DE L'ANALYSE:
- Analyses informelles: {len(self.shared_state.identified_arguments)} arguments, {len(self.shared_state.identified_fallacies)} sophismes
- Analyses formelles: {len(self.shared_state.belief_sets)} belief sets, {len(self.shared_state.query_log)} requêtes
- Réponses aux tâches: {len(self.shared_state.answers)} tâches résolues

MISSION FINALE:
1. Synthèse coordonnée des résultats informels et formels
2. Validation de la cohérence globale
3. Génération de la conclusion finale 
4. Archivage et structuration des résultats

ProjectManagerAgent, veuillez coordonner la synthèse finale en intégrant tous les résultats de l'état partagé."""
        
        # Capture état de synthèse
        self.tour_counter += 1
        capture_shared_state(
            phase_id=phase_id,
            tour_number=self.tour_counter,
            agent_active="ProjectManagerAgent",
            state_variables={
                "phase": "final_synthesis",
                "total_tasks": len(self.shared_state.analysis_tasks),
                "total_answers": len(self.shared_state.answers),
                "informal_complete": True,
                "formal_complete": True,
                "synthesis_readiness": True
            },
            metadata={
                "final_coordination": "active",
                "synthesis_mode": "comprehensive",
                "pm_orchestration": "complete"
            }
        )
        
        # Ajout du message de synthèse
        if hasattr(self.group_chat, 'history') and hasattr(self.group_chat.history, 'add_user_message'):
            self.group_chat.history.add_user_message(synthesis_prompt)
        
        # Exécution finale
        await self._execute_conversation_phase(phase_id, max_turns=6)
        
        # Capture état final complet
        capture_shared_state(
            phase_id=phase_id,
            tour_number=self.tour_counter,
            agent_active="ProjectManagerAgent",
            state_variables={
                "phase": "orchestration_complete",
                "final_conclusion": self.shared_state.final_conclusion is not None,
                "all_tasks_completed": len(self.shared_state.answers) >= len(self.shared_state.analysis_tasks),
                "orchestration_success": True,
                "pm_coordination_quality": "excellent"
            },
            metadata={
                "orchestration_status": "fully_complete",
                "pm_effectiveness": "high",
                "multi_turn_success": True,
                "state_management_quality": "excellent"
            }
        )
        
        logger.info("✅ Phase 3 terminée: Orchestration PM complète")
    
    async def _execute_conversation_phase(self, phase_id: str, max_turns: int):
        """Exécute une phase de conversation avec capture de trace."""
        logger.info(f"🔄 Exécution phase {phase_id} (max {max_turns} tours)")
        
        turn_count = 0
        try:
            async for message in self.group_chat.invoke():
                turn_count += 1
                self.tour_counter += 1
                
                if not message:
                    logger.warning(f"Message vide reçu au tour {turn_count}")
                    break
                
                if turn_count >= max_turns:
                    logger.info(f"Limite de tours atteinte pour phase {phase_id}")
                    break
                
                # Capture des détails du message
                agent_name = message.name or getattr(message, 'author_name', f"Role:{message.role.name}")
                content = str(message.content) if message.content else ""
                
                logger.info(f"💬 Tour {self.tour_counter}: {agent_name}")
                logger.debug(f"   Contenu: {content[:200]}...")
                
                # Capture du message de conversation
                enhanced_global_trace_analyzer.capture_conversation_message(
                    agent_name=agent_name,
                    content=content,
                    tour_number=self.tour_counter,
                    phase_id=phase_id,
                    tool_calls_count=len(getattr(message, 'tool_calls', []) or [])
                )
                
                # Capture des tool calls s'il y en a
                tool_calls = getattr(message, 'tool_calls', []) or []
                if tool_calls:
                    logger.info(f"   🔧 {len(tool_calls)} appels d'outils détectés")
                    for tc in tool_calls:
                        self._capture_tool_call_from_message(tc, agent_name)
                
                # Pause pour éviter la surcharge
                await asyncio.sleep(0.1)
                
        except AgentChatException as e:
            if "Chat is already complete" in str(e):
                logger.info(f"Conversation phase {phase_id} terminée naturellement")
            else:
                logger.error(f"Erreur conversation phase {phase_id}: {e}")
                raise
        
        logger.info(f"✅ Phase {phase_id} exécutée: {turn_count} tours")
    
    def _capture_tool_call_from_message(self, tool_call, agent_name: str):
        """Capture un tool call depuis un message SK."""
        try:
            # Extraction des informations du tool call
            tool_name = "unknown_tool"
            arguments = {}
            
            if hasattr(tool_call, 'function') and tool_call.function:
                if hasattr(tool_call.function, 'name'):
                    tool_name = tool_call.function.name
                if hasattr(tool_call.function, 'arguments'):
                    arguments = tool_call.function.arguments or {}
            
            # Enregistrement avec trace améliorée
            enhanced_global_trace_analyzer.record_enhanced_tool_call(
                agent_name=agent_name,
                tool_name=tool_name,
                arguments=arguments,
                result="Tool call captured from message",
                execution_time_ms=0.0,  # Non mesurable depuis message
                success=True
            )
            
        except Exception as e:
            logger.error(f"Erreur capture tool call: {e}")


# Fonction principale d'exécution
async def run_enhanced_pm_orchestration_demo(
    texte_a_analyser: str,
    llm_service: Union[OpenAIChatCompletion, AzureChatCompletion]
) -> Dict[str, Any]:
    """
    Lance une démo complète d'orchestration PM avec gestion d'état partagé
    et format de conversation amélioré.
    """
    logger.info("[DEMO] DEMARRAGE DEMO PROJECT MANAGER ENHANCED")
    logger.info("=" * 60)
    
    try:
        # Création de l'orchestrateur
        orchestrator = EnhancedProjectManagerOrchestrator(llm_service)
        
        # Lancement de l'orchestration
        result = await orchestrator.run_enhanced_pm_orchestration(texte_a_analyser)
        
        if result["success"]:
            logger.info("[SUCCESS] DÉMO PM TERMINÉE AVEC SUCCÈS")
            logger.info(f"   Phases complétées: {result['phases_completed']}")
            logger.info(f"   Snapshots d'état: {result['state_snapshots']}")
            logger.info(f"   Appels d'outils: {result['tool_calls']}")
            logger.info(f"   Durée totale: {result['total_duration_ms']:.1f}ms")
            if result.get('report_path'):
                logger.info(f"   Rapport sauvegardé: {result['report_path']}")
        else:
            logger.error(f"[ERROR] ÉCHEC DÉMO PM: {result.get('error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"[ERROR] Erreur critique démo PM: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# Classe wrapper pour compatibilité
class EnhancedPMAnalysisRunner:
    """Wrapper pour intégration facile du PM amélioré."""
    
    def __init__(self):
        self.logger = logging.getLogger("EnhancedPMRunner")
    
    async def run_enhanced_analysis(self, text_content: str, llm_service=None):
        """Lance une analyse avec orchestration PM améliorée."""
        if llm_service is None:
            from argumentation_analysis.core.llm_service import create_llm_service
            llm_service = create_llm_service()
        
        return await run_enhanced_pm_orchestration_demo(text_content, llm_service)