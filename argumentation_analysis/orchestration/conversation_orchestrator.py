#!/usr/bin/env python3
"""
Conversation Orchestrator - Composant réutilisable pour orchestration conversationnelle
================================================================================

Composant unifié pour orchestration conversationnelle avec support de 4 modes :
- micro : Orchestration ultra-légère
- demo : Démonstration complète avec agents simulés
- trace : Test du système de traçage conversationnel
- enhanced : Test des composants PM améliorés

S'intègre harmonieusement avec l'architecture Semantic Kernel existante.
"""

import time
import json
import logging
import warnings
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

# Imports Semantic Kernel et architecture
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.llm_service import create_llm_service

logger = logging.getLogger("ConversationOrchestrator")


class ConversationLogger:
    """Logger conversationnel unifié compatible avec l'architecture existante."""

    def __init__(self, mode: str = "demo"):
        self.mode = mode
        self.start_time = time.time()
        self.messages = []
        self.tool_calls = []
        self.state_snapshots = []
        self.logger = logging.getLogger(f"{__name__}.ConversationLogger")

        # Limites selon le mode pour éviter surcharge
        self._set_mode_limits()

    def _set_mode_limits(self):
        """Configure les limites selon le mode."""
        if self.mode == "micro":
            self.max_messages = 8
            self.max_tools = 6
            self.max_states = 3
            self.max_message_len = 150
        else:
            self.max_messages = 20
            self.max_tools = 15
            self.max_states = 8
            self.max_message_len = 300

    def log_agent_message(self, agent: str, message: str, phase: str = "analysis"):
        """Enregistre un message conversationnel d'agent."""
        if len(self.messages) >= self.max_messages:
            return

        # Troncature intelligente pour éviter surcharge
        if len(message) > self.max_message_len:
            message = message[: self.max_message_len - 3] + "..."

        timestamp_ms = (time.time() - self.start_time) * 1000
        entry = {
            "type": "message",
            "agent": agent,
            "message": message,
            "phase": phase,
            "timestamp": time.time() - self.start_time,
            "time_ms": timestamp_ms,
        }
        self.messages.append(entry)

        # Log dans le système principal
        self.logger.info(f"[{agent}] {message}")

        # Affichage console selon mode
        if self.mode != "trace":
            print(f"[CONVERSATION] {agent}: {message}")

    def log_tool_call(
        self,
        agent: str,
        tool: str,
        args: Dict[str, Any],
        result: Any,
        success: bool = True,
    ):
        """Enregistre un appel d'outil."""
        if len(self.tool_calls) >= self.max_tools:
            return

        # Sérialisation et troncature des données volumineuses
        args_str = str(args)
        if len(args_str) > 100:
            args_str = args_str[:97] + "..."

        result_str = str(result)
        if len(result_str) > 150:
            result_str = result_str[:147] + "..."

        timestamp_ms = (time.time() - self.start_time) * 1000
        entry = {
            "type": "tool_call",
            "agent": agent,
            "tool": tool,
            "arguments": args_str,
            "result": result_str,
            "success": success,
            "timestamp": time.time() - self.start_time,
            "time_ms": timestamp_ms,
        }
        self.tool_calls.append(entry)

        # Log dans le système principal
        self.logger.info(f"[TOOL] {agent} -> {tool}: {success}")

        # Affichage console selon mode
        if self.mode != "trace":
            print(f"[TOOL] {agent} -> {tool}: {args_str} = {result_str}")

    def log_state_snapshot(self, phase: str, state_data: Dict[str, Any]):
        """Enregistre un snapshot d'état."""
        if len(self.state_snapshots) >= self.max_states:
            return

        entry = {
            "type": "state",
            "phase": phase,
            "data": state_data,
            "timestamp": time.time() - self.start_time,
        }
        self.state_snapshots.append(entry)

        # Log dans le système principal
        self.logger.info(f"[STATE] Phase {phase}: {len(state_data)} metrics")

        # Affichage console selon mode
        if self.mode != "trace":
            print(f"[STATE] Phase {phase}: {state_data}")


class AnalysisState:
    """État d'analyse unifié compatible avec RhetoricalAnalysisState."""

    def __init__(self):
        self.score = 0.0
        self.agents_active = 0
        self.fallacies_detected = 0
        self.propositions_found = 0
        self.consistency_score = 0.0
        self.phase = "initialization"
        self.completed = False

        # Métriques additionnelles pour compatibilité
        self.processing_time = 0.0
        self.agent_results = {}

    def update_from_informal(self, result: Dict[str, Any]):
        """Met à jour l'état avec résultats d'analyse informelle."""
        self.fallacies_detected += result.get("fallacies_count", 0)
        self.score += result.get("sophistication_score", 0.0) * 0.4
        self.agent_results["informal"] = result

    def update_from_modal(self, result: Dict[str, Any]):
        """Met à jour l'état avec résultats de logique modale."""
        self.propositions_found += result.get("propositions_count", 0)
        self.consistency_score = result.get("consistency", 0.0)
        self.score += result.get("logical_score", 0.0) * 0.3
        self.agent_results["modal"] = result

    def update_from_synthesis(self, result: Dict[str, Any]):
        """Met à jour l'état avec résultats de synthèse."""
        self.score += result.get("unified_score", 0.0) * 0.3
        self.completed = True
        self.agent_results["synthesis"] = result

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'état en dictionnaire."""
        return {
            "score": round(self.score, 2),
            "agents_active": self.agents_active,
            "fallacies_detected": self.fallacies_detected,
            "propositions_found": self.propositions_found,
            "consistency_score": round(self.consistency_score, 2),
            "phase": self.phase,
            "completed": self.completed,
            "processing_time": round(self.processing_time, 3),
        }

    def to_rhetorical_state(self) -> "RhetoricalAnalysisState":
        """Convertit vers RhetoricalAnalysisState pour compatibilité."""
        state = RhetoricalAnalysisState(initial_text="")
        if self.completed:
            state.final_conclusion = f"Analysis completed with score {self.score:.2f}"
        return state


class SimulatedAgent:
    """Agent simulé pour démonstrations - Compatible avec l'architecture."""

    def __init__(self, name: str, agent_type: str):
        self.name = name
        self.agent_type = agent_type
        self.logger = logging.getLogger(f"{__name__}.{name}")

    def analyze(
        self, text: str, conv_logger: ConversationLogger, state: AnalysisState
    ) -> Dict[str, Any]:
        """Simule une analyse selon le type d'agent."""

        self.logger.info(f"Début analyse {self.agent_type} pour {self.name}")

        if self.agent_type == "informal":
            return self._analyze_informal(text, conv_logger, state)
        elif self.agent_type == "fol_logic":
            return self._analyze_fol_logic(text, conv_logger, state)
        elif self.agent_type == "synthesis":
            return self._analyze_synthesis(text, conv_logger, state)
        else:
            self.logger.error(f"Type d'agent inconnu: {self.agent_type}")
            return {"error": "Unknown agent type"}

    def _analyze_informal(
        self, text: str, conv_logger: ConversationLogger, state: AnalysisState
    ) -> Dict[str, Any]:
        """Analyse informelle simulée avec patterns réalistes."""

        conv_logger.log_agent_message(
            self.name,
            "Je vais analyser ce texte pour détecter les sophismes et manipulations rhétoriques.",
            "informal_analysis",
        )

        # Délai réaliste pour simulation
        time.sleep(0.002)

        # Simulation de détection de sophismes
        sophisms_result = [
            {"type": "Historical Rewriting", "confidence": 0.85},
            {"type": "False Cause", "confidence": 0.78},
        ]

        conv_logger.log_tool_call(
            self.name,
            "detect_sophisms_from_taxonomy",
            {
                "text": text[:50] + "...",
                "branches": ["logical", "emotional", "rhetorical"],
                "severity_threshold": 0.3,
            },
            sophisms_result,
        )

        conv_logger.log_agent_message(
            self.name,
            f"Sophismes détectés: '{sophisms_result[0]['type']}' (confiance: {sophisms_result[0]['confidence']}) et '{sophisms_result[1]['type']}' (confiance: {sophisms_result[1]['confidence']}). Analyse des motifs rhétoriques en cours...",
            "informal_analysis",
        )

        time.sleep(0.002)

        # Simulation d'analyse des patterns
        patterns_result = {"patterns_found": 3, "nationalist_appeals": 2}

        conv_logger.log_tool_call(
            self.name,
            "analyze_rhetorical_patterns",
            {
                "text_segments": ["key phrases..."],
                "pattern_types": ["nationalism", "victimization"],
            },
            patterns_result,
        )

        result = {
            "fallacies_count": 2,
            "sophistication_score": 0.8,
            "main_issues": ["historical_distortion", "emotional_manipulation"],
        }

        conv_logger.log_agent_message(
            self.name,
            f"Analyse terminée. {result['fallacies_count']} sophismes détectés, {patterns_result['patterns_found']} motifs rhétoriques identifiés. Score de sophistication : {result['sophistication_score']}/1.0",
            "informal_analysis",
        )

        state.update_from_informal(result)
        state.agents_active += 1

        return result

    def _analyze_modal(
        self, text: str, conv_logger: ConversationLogger, state: AnalysisState
    ) -> Dict[str, Any]:
        """Analyse modale simulée avec logique formelle."""

        conv_logger.log_agent_message(
            self.name,
            "Je vais transformer ce texte en propositions logiques modales pour analyser sa cohérence.",
            "modal_analysis",
        )

        time.sleep(0.003)

        # Simulation d'extraction de propositions modales
        belief_set_result = {
            "propositions": [
                "BOX(Created(Ukraine, Russia))",
                "DIAMOND(Harsh(actions))",
                "NECESSITY(FirmActions))",
            ],
            "modal_operators": ["necessity", "possibility", "necessity"],
            "consistency_status": "potentially_inconsistent",
        }

        conv_logger.log_tool_call(
            self.name,
            "text_to_belief_set",
            {
                "text": text[:50] + "...",
                "logic_type": "modal",
                "extract_propositions": True,
            },
            belief_set_result,
        )

        propositions_str = "', '".join(belief_set_result["propositions"])
        conv_logger.log_agent_message(
            self.name,
            f"Propositions modales extraites: '{propositions_str}'. Vérification de la cohérence logique...",
            "modal_analysis",
        )

        time.sleep(0.002)

        # Simulation de vérification de cohérence
        consistency_result = {"consistency": 0.65, "contradictions": 1}

        conv_logger.log_tool_call(
            self.name,
            "check_logical_consistency",
            {"propositions": belief_set_result["propositions"]},
            consistency_result,
        )

        result = {
            "propositions_count": len(belief_set_result["propositions"]),
            "consistency": consistency_result["consistency"],
            "logical_score": 0.7,
            "contradictions": consistency_result["contradictions"],
        }

        conv_logger.log_agent_message(
            self.name,
            f"Analyse modale terminée. {result['propositions_count']} propositions extraites, cohérence logique: {result['consistency']:.2f}, {result['contradictions']} contradiction détectée.",
            "modal_analysis",
        )

        state.update_from_modal(result)
        state.agents_active += 1

        return result

    def _analyze_fol_logic(
        self, text: str, conv_logger: ConversationLogger, state: AnalysisState
    ) -> Dict[str, Any]:
        """Analyse FOL simulée avec logique du premier ordre."""

        conv_logger.log_agent_message(
            self.name,
            "Je vais transformer ce texte en formules de logique du premier ordre (FOL) pour analyser sa cohérence.",
            "fol_analysis",
        )

        time.sleep(0.003)

        # Simulation d'extraction de formules FOL
        belief_set_result = {
            "formulas": [
                "∀x(Created(x) → ResponsibleAction(x))",
                "∃y(HarshAction(y) ∧ Necessary(y))",
                "∀z(FirmAction(z) → Justified(z))",
            ],
            "predicates": [
                "Created",
                "ResponsibleAction",
                "HarshAction",
                "Necessary",
                "FirmAction",
                "Justified",
            ],
            "quantifiers": ["universal", "existential", "universal"],
            "consistency_status": "potentially_consistent",
        }

        conv_logger.log_tool_call(
            self.name,
            "convert_to_fol",
            {"text": text[:50] + "...", "logic_type": "fol", "extract_formulas": True},
            belief_set_result,
        )

        formulas_str = "', '".join(belief_set_result["formulas"])
        conv_logger.log_agent_message(
            self.name,
            f"Formules FOL extraites: '{formulas_str}'. Vérification de la cohérence logique avec Tweety...",
            "fol_analysis",
        )

        time.sleep(0.002)

        # Simulation de vérification de cohérence FOL
        consistency_result = {
            "consistency": 0.85,
            "contradictions": 0,
            "satisfiable": True,
        }

        conv_logger.log_tool_call(
            self.name,
            "analyze_fol",
            {"formulas": belief_set_result["formulas"]},
            consistency_result,
        )

        result = {
            "formulas_count": len(belief_set_result["formulas"]),
            "consistency": consistency_result["consistency"],
            "logical_score": 0.85,
            "contradictions": consistency_result["contradictions"],
            "satisfiable": consistency_result["satisfiable"],
        }

        conv_logger.log_agent_message(
            self.name,
            f"Analyse FOL terminée. {result['formulas_count']} formules extraites, cohérence logique: {result['consistency']:.2f}, satisfiable: {result['satisfiable']}.",
            "fol_analysis",
        )

        state.update_from_modal(result)  # Réutilise la méthode pour l'instant
        state.agents_active += 1

        return result

    def _analyze_synthesis(
        self, text: str, conv_logger: ConversationLogger, state: AnalysisState
    ) -> Dict[str, Any]:
        """Analyse de synthèse simulée unifiée."""

        conv_logger.log_agent_message(
            self.name,
            "Je vais synthétiser les analyses informelle et modale pour produire une évaluation unifiée.",
            "synthesis",
        )

        # Simulation d'unification des résultats
        conv_logger.log_tool_call(
            self.name,
            "unify_analysis_results",
            {
                "informal_results": {"fallacies": state.fallacies_detected},
                "formal_results": {"consistency": state.consistency_score},
                "synthesis_strategy": "comprehensive",
            },
            {
                "unified_score": 0.73,
                "overall_validity": "questionable",
                "main_issues": ["historical_distortion", "logical_inconsistency"],
            },
        )

        result = {
            "unified_score": 0.73,
            "overall_validity": "questionable",
            "recommendation": "Critical analysis required",
        }

        conv_logger.log_agent_message(
            self.name,
            f"Synthèse terminée. Score unifié : {result['unified_score']}. Le texte présente des faiblesses argumentatives significatives.",
            "synthesis",
        )

        state.update_from_synthesis(result)
        state.agents_active += 1

        return result


class ConversationOrchestrator:
    """Orchestrateur conversationnel unifié compatible avec l'architecture Semantic Kernel."""

    def __init__(self, mode: str = "demo", kernel=None):
        self.mode = mode
        self.kernel = kernel
        self.conv_logger = ConversationLogger(mode)
        self.state = AnalysisState()
        self.logger = logging.getLogger(f"{__name__}.ConversationOrchestrator")
        self._real_agents = {}  # Cache for real agent instances

        # Configuration des agents selon le mode
        self._setup_agents()

        # Pour stockage du texte analysé
        self.current_text = ""

    def _kernel_has_llm(self) -> bool:
        """Check if the kernel has at least one LLM service registered."""
        try:
            return bool(self.kernel and self.kernel.services)
        except Exception:
            return False

    def _setup_agents(self):
        """Configure les agents selon le mode."""
        if self.mode == "real":
            if self.kernel and self._kernel_has_llm():
                self._setup_real_agents()
            else:
                self.logger.warning(
                    "Mode 'real' requested but no kernel/LLM available. "
                    "Falling back to 'demo' mode."
                )
                self.mode = "demo"
                self._setup_simulated_agents()
        elif self.mode == "micro":
            self.agents = [
                SimulatedAgent("InformalAgent", "informal"),
                SimulatedAgent("ModalLogicAgent", "modal"),
            ]
        else:
            self._setup_simulated_agents()

        self.logger.info(f"Mode {self.mode}: {len(self.agents)} agents configurés")

    def _setup_simulated_agents(self):
        """Setup simulated agents for demo/trace/enhanced modes."""
        self.agents = [
            SimulatedAgent("InformalAnalysisAgent", "informal"),
            SimulatedAgent("FOLLogicAgent", "fol_logic"),
            SimulatedAgent("SynthesisAgent", "synthesis"),
        ]

    def _setup_real_agents(self):
        """Create real LLM-backed agents. Falls back per-agent on failure."""
        self.agents = []  # Not used in real mode

        # 1. InformalAnalysisAgent
        try:
            from argumentation_analysis.agents.core.informal.informal_agent import (
                InformalAnalysisAgent,
            )

            informal = InformalAnalysisAgent(
                kernel=self.kernel,
                agent_name="InformalAnalysisAgent",
            )
            self._real_agents["informal"] = informal
            self.logger.info("Real InformalAnalysisAgent created")
        except Exception as e:
            self.logger.warning(f"Cannot create real InformalAnalysisAgent: {e}")

        # 2. SynthesisAgent
        try:
            from argumentation_analysis.agents.core.synthesis.synthesis_agent import (
                SynthesisAgent as RealSynthesisAgent,
            )

            synth = RealSynthesisAgent(
                kernel=self.kernel,
                agent_name="SynthesisAgent",
            )
            self._real_agents["synthesis"] = synth
            self.logger.info("Real SynthesisAgent created")
        except Exception as e:
            self.logger.warning(f"Cannot create real SynthesisAgent: {e}")

        if not self._real_agents:
            self.logger.error("No real agents could be created. Falling back to demo.")
            self.mode = "demo"
            self._setup_simulated_agents()

    def _adapt_real_result(self, agent_key: str, raw_result) -> Dict[str, Any]:
        """Adapt real agent output to AnalysisState-compatible dict format."""
        if isinstance(raw_result, dict):
            result = raw_result
        elif hasattr(raw_result, "model_dump"):
            result = raw_result.model_dump()
        else:
            result = {"raw": str(raw_result)}

        if agent_key == "informal":
            fallacies = result.get("fallacies", [])
            return {
                "fallacies_count": len(fallacies),
                "sophistication_score": min(len(fallacies) * 0.2 + 0.3, 1.0),
                "main_issues": [
                    f.get("type", f.get("fallacy_type", "unknown"))
                    for f in fallacies[:5]
                ],
                "raw_result": result,
            }
        elif agent_key == "fol_logic":
            return {
                "formulas_count": len(result.get("formulas", [])),
                "propositions_count": len(result.get("formulas", [])),
                "consistency": 1.0 if result.get("consistency_check", False) else 0.5,
                "logical_score": result.get("confidence_score", 0.5),
                "contradictions": len(result.get("validation_errors", [])),
                "satisfiable": result.get("consistency_check", True),
                "raw_result": result,
            }
        elif agent_key == "synthesis":
            return {
                "unified_score": result.get("confidence_level", 0.5) or 0.5,
                "overall_validity": str(result.get("overall_validity", "unknown")),
                "recommendation": result.get("executive_summary", "N/A"),
                "raw_result": result,
            }
        return result

    async def _invoke_real_agent(self, agent_key: str, agent, text: str):
        """Invoke the appropriate method on a real agent."""
        if agent_key == "informal":
            if hasattr(agent, "perform_complete_analysis"):
                return await agent.perform_complete_analysis(text)
            elif hasattr(agent, "analyze_text"):
                return await agent.analyze_text(text, analysis_type="fallacies")
            else:
                raise AttributeError(
                    "InformalAnalysisAgent has no suitable analysis method"
                )
        elif agent_key == "fol_logic":
            if hasattr(agent, "analyze_text"):
                return await agent.analyze_text(text)
            else:
                raise AttributeError("FOLLogicAgent has no suitable analysis method")
        elif agent_key == "synthesis":
            report = await agent.synthesize_analysis(text)
            if hasattr(report, "model_dump"):
                return report.model_dump()
            return vars(report) if hasattr(report, "__dict__") else {"raw": str(report)}
        else:
            raise ValueError(f"Unknown agent key: {agent_key}")

    async def _run_real_agent(
        self, agent_key: str, agent, text: str, timeout: float = 60.0
    ) -> Dict[str, Any]:
        """Run a real agent with logging and timeout."""
        import asyncio

        agent_name = getattr(agent, "name", agent_key)

        self.conv_logger.log_agent_message(
            agent_name,
            f"Starting real analysis ({agent_key})...",
            f"{agent_key}_analysis",
        )

        try:
            raw_result = await asyncio.wait_for(
                self._invoke_real_agent(agent_key, agent, text),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            self.conv_logger.log_agent_message(
                agent_name, f"Agent timed out after {timeout}s", "error"
            )
            return {"error": f"Timeout after {timeout}s"}
        except Exception as e:
            self.conv_logger.log_agent_message(
                agent_name, f"Agent error: {str(e)[:200]}", "error"
            )
            return {"error": str(e)}

        adapted = self._adapt_real_result(agent_key, raw_result)

        self.conv_logger.log_tool_call(
            agent_name,
            f"real_{agent_key}_analysis",
            {"text_length": len(text)},
            adapted,
        )

        # Update state
        if agent_key == "informal":
            self.state.update_from_informal(adapted)
        elif agent_key == "fol_logic":
            self.state.update_from_modal(adapted)
        elif agent_key == "synthesis":
            self.state.update_from_synthesis(adapted)
        self.state.agents_active += 1

        self.conv_logger.log_agent_message(
            agent_name,
            f"Analysis complete. Result keys: {list(adapted.keys())}",
            f"{agent_key}_analysis",
        )

        return adapted

    async def run_orchestration_async(self, text: str) -> str:
        """Execute orchestration with real LLM-backed agents (async)."""
        if self.mode != "real":
            return self.run_orchestration(text)

        self.current_text = text
        start_time = time.time()

        self.logger.info(
            f"Starting async orchestration mode 'real' for {len(text)} chars"
        )

        self.conv_logger.log_agent_message(
            "ProjectManager",
            f"Starting real LLM rhetorical analysis. "
            f"Available agents: {list(self._real_agents.keys())}.",
            "coordination",
        )

        self.state.phase = "active"
        self.conv_logger.log_state_snapshot("initialization", self.state.to_dict())

        agent_order = ["informal", "fol_logic", "synthesis"]

        for agent_key in agent_order:
            if agent_key not in self._real_agents:
                self.logger.info(f"Agent '{agent_key}' not available, skipping")
                continue

            try:
                await self._run_real_agent(
                    agent_key, self._real_agents[agent_key], text
                )
                self.state.phase = f"post_{agent_key}"
                self.conv_logger.log_state_snapshot(
                    f"after_{agent_key}", self.state.to_dict()
                )
            except Exception as e:
                self.logger.error(f"Agent '{agent_key}' failed: {e}")
                self.conv_logger.log_agent_message(
                    agent_key,
                    f"Agent failed with error: {str(e)[:200]}",
                    "error",
                )

        self.conv_logger.log_tool_call(
            "ProjectManager",
            "coordinate_final_synthesis",
            {
                "agents_results": len(self._real_agents),
                "final_score": self.state.score,
            },
            {"coordination": "success", "status": "completed"},
        )

        self.conv_logger.log_agent_message(
            "ProjectManager",
            f"Real orchestration complete. Score: {self.state.score}.",
            "conclusion",
        )

        self.state.phase = "completed"
        self.state.completed = True
        self.state.processing_time = time.time() - start_time
        self.conv_logger.log_state_snapshot("final", self.state.to_dict())

        self.logger.info(
            f"Async orchestration completed in {self.state.processing_time:.3f}s"
        )

        return self.generate_report()

    def run_orchestration(self, text: str) -> str:
        """Exécute l'orchestration conversationnelle selon le mode."""

        self.current_text = text
        start_time = time.time()

        self.logger.info(
            f"Démarrage orchestration mode '{self.mode}' pour {len(text)} caractères"
        )

        # Message d'introduction du Project Manager
        self.conv_logger.log_agent_message(
            "ProjectManager",
            f"Démarrage de l'orchestration d'analyse rhétorique en mode {self.mode}. Coordination des agents spécialisés.",
            "coordination",
        )

        # État initial
        self.state.phase = "active"
        self.conv_logger.log_state_snapshot("initialization", self.state.to_dict())

        # Coordination des agents
        agents_list = ", ".join([a.name for a in self.agents])
        self.conv_logger.log_agent_message(
            "ProjectManager",
            f"Agents disponibles : {agents_list}. Démarrage séquentiel des analyses.",
            "coordination",
        )

        # Exécution séquentielle des analyses
        for agent in self.agents:
            # Limitation pour mode micro
            if self.mode == "micro" and len(self.conv_logger.tool_calls) >= 4:
                self.logger.info("Mode micro: limite d'outils atteinte")
                break

            try:
                result = agent.analyze(text, self.conv_logger, self.state)

                # Snapshot intermédiaire
                self.state.phase = f"post_{agent.agent_type}"
                self.conv_logger.log_state_snapshot(
                    f"after_{agent.name}", self.state.to_dict()
                )

                self.logger.info(f"Agent {agent.name} terminé avec succès")

            except Exception as e:
                self.logger.error(f"Erreur agent {agent.name}: {e}")
                # Continue avec les autres agents

        # Coordination finale par le PM
        self.conv_logger.log_tool_call(
            "ProjectManager",
            "coordinate_final_synthesis",
            {"agents_results": len(self.agents), "final_score": self.state.score},
            {
                "coordination": "success",
                "status": "completed",
                "recommendation": "analysis_complete",
            },
        )

        # Message de conclusion
        self.conv_logger.log_agent_message(
            "ProjectManager",
            f"Orchestration terminée avec succès. Score final : {self.state.score}. Tous les agents ont contribué à l'analyse.",
            "conclusion",
        )

        # État final
        self.state.phase = "completed"
        self.state.completed = True
        self.state.processing_time = time.time() - start_time
        self.conv_logger.log_state_snapshot("final", self.state.to_dict())
        self.logger.info(f"Orchestration terminée en {self.state.processing_time:.3f}s")

        warnings.warn(
            "`ConversationOrchestrator` is deprecated and will be removed in a future version. "
            "Please use `analysis_runner` for new implementations. "
            "This class is maintained for backward compatibility only.",
            DeprecationWarning,
            stacklevel=2,
        )

        return self.generate_report()

    def generate_report(self) -> str:
        """Génère le rapport conversationnel unifié avec chronologie intégrée."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_time = (time.time() - self.conv_logger.start_time) * 1000

        # Informations sur l'extrait analysé
        text_size = len(self.current_text) if self.current_text else 0
        text_words = len(self.current_text.split()) if self.current_text else 0

        report = f"""# TRACE ANALYTIQUE - LOGIQUE MODALE INTEGREE
===

## 📄 EXTRAIT ANALYSE
- **Source:** Texte libre (analyse modale)
- **Taille:** {text_size} caractères, {text_words} mots
- **Type:** Argumentation juridico-politique avec modalités logiques
- **Extrait:** "{self.current_text[:100]}{'...' if text_size > 100 else ''}"

## ⏱️ METADONNEES D'EXECUTION
- **Timestamp:** {timestamp}
- **Mode:** {self.mode} (capture conversationnelle)
- **Durée totale:** {total_time:.1f}ms
- **Agents orchestrés:** {self.state.agents_active}

## 🎭 TRACE CONVERSATIONNELLE CHRONOLOGIQUE
"""

        # Fusionner et trier les événements par timestamp
        all_events = []

        # Ajouter les messages
        for msg in self.conv_logger.messages:
            all_events.append(
                {"type": "message", "timestamp": msg["time_ms"], "data": msg}
            )

        # Ajouter les appels d'outils
        for tool in self.conv_logger.tool_calls:
            all_events.append(
                {"type": "tool", "timestamp": tool["time_ms"], "data": tool}
            )

        # Tri chronologique
        all_events.sort(key=lambda x: x["timestamp"])

        # Génération de la trace chronologique
        for event in all_events:
            if event["type"] == "message":
                msg = event["data"]
                report += f"""
### [{msg['time_ms']:.1f}ms] 💬 **{msg['agent']}**
**Phase:** {msg['phase']}
**Message:** *"{msg['message']}"*
"""
            elif event["type"] == "tool":
                tool = event["data"]
                status = "✅" if tool["success"] else "❌"
                report += f"""
### [{tool['time_ms']:.1f}ms] 🔧 **APPEL OUTIL** {status}
**Agent:** {tool['agent']}
**Outil:** `{tool['tool']}`
**Arguments:** {tool['arguments']}
**Résultat:** {tool['result']}
"""

        # États significatifs uniquement
        significant_states = [
            s
            for s in self.conv_logger.state_snapshots
            if s["phase"] in ["after_ModalLogicAgent", "final"]
        ]

        if significant_states:
            report += "\n## 📊 EVOLUTION DES METRIQUES CLES\n"
            for state in significant_states:
                report += f"""
**Phase {state['phase']} [{state['timestamp']*1000:.1f}ms]:**
"""
                key_metrics = [
                    "score",
                    "fallacies_detected",
                    "propositions_found",
                    "consistency_score",
                ]
                for key in key_metrics:
                    if key in state["data"]:
                        report += f"- {key}: {state['data'][key]}  "
                report += "\n"

        # Résumé final enrichi
        report += f"""
## 🎯 BILAN D'ANALYSE MODALE
- **Score global:** {self.state.score:.3f}/1.0
- **Modalités extraites:** {self.state.propositions_found} (nécessité/possibilité)
- **Cohérence logique:** {self.state.consistency_score:.2f}/1.0
- **Sophismes détectés:** {self.state.fallacies_detected}
- **Statut:** {"✅ Analyse complète" if self.state.completed else "⏳ En cours"}

## 🔍 DIAGNOSTIC TECHNIQUE
- **Performance:** {total_time:.1f}ms (mode {self.mode})
- **Messages capturés:** {len(self.conv_logger.messages)} échanges
- **Outils utilisés:** {len(self.conv_logger.tool_calls)} appels
- **Pipeline modal:** {"✅ Opérationnel" if self.state.completed else "❌ Interrompu"}

---
*Trace générée par Enhanced PM Orchestration v2.0 - Mode chronologique intégré*
"""

        return report

    def get_conversation_state(self) -> Dict[str, Any]:
        """Retourne l'état de la conversation pour intégration externe."""
        return {
            "mode": self.mode,
            "state": self.state.to_dict(),
            "messages_count": len(self.conv_logger.messages),
            "tools_count": len(self.conv_logger.tool_calls),
            "processing_time": self.state.processing_time,
            "completed": self.state.completed,
        }

    async def run_demo_conversation(self, text: str) -> Dict[str, Any]:
        """
        Interface asynchrone pour le pipeline unifié.

        Args:
            text: Texte à analyser

        Returns:
            Dict contenant les résultats de l'orchestration
        """
        if self.mode == "real":
            report = await self.run_orchestration_async(text)
        else:
            report = self.run_orchestration(text)

        return {
            "status": "success",
            "report": report,
            "conversation_state": self.get_conversation_state(),
            "text_analyzed": text,
            "mode": self.mode,
        }

    async def run_conversation(self, text: str) -> Dict[str, Any]:
        """Alias for run_demo_conversation (expected by MainOrchestrator)."""
        return await self.run_demo_conversation(text)


def create_conversation_orchestrator(
    mode: str = "demo", kernel=None
) -> ConversationOrchestrator:
    """Factory pour créer un orchestrateur conversationnel."""
    logger.info(f"Création orchestrateur conversationnel mode {mode}")
    return ConversationOrchestrator(mode=mode, kernel=kernel)


# Fonctions de mode pour compatibilité avec l'interface existante
def run_mode_micro(text: str) -> str:
    """Mode micro : orchestration ultra-légère."""
    orchestrator = create_conversation_orchestrator("micro")
    return orchestrator.run_orchestration(text)


def run_mode_demo(text: str) -> str:
    """Mode demo : démonstration complète."""
    orchestrator = create_conversation_orchestrator("demo")
    return orchestrator.run_orchestration(text)


def run_mode_trace(text: str) -> str:
    """Mode trace : test du système de traçage."""
    orchestrator = create_conversation_orchestrator("trace")
    return orchestrator.run_orchestration(text)


def run_mode_enhanced(text: str) -> str:
    """Mode enhanced : test des composants PM améliorés."""
    orchestrator = create_conversation_orchestrator("enhanced")
    return orchestrator.run_orchestration(text)
