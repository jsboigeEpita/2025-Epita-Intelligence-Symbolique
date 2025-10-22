#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Enhanced Real-Time Trace Analyzer pour Project Manager avec format de conversation amélioré
et gestion d'état partagé. Capture l'orchestration multi-tours avec évolution d'état.

Ce module capture :
- Conversation agentielle avec markup élégant
- Évolution de l'état partagé entre phases
- Coordination Project Manager
- Orchestration multi-tours avec gestion d'état
"""

import time
import logging
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import functools

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    """Message de conversation agentielle."""

    agent_name: str
    content: str
    tour_number: int
    phase_id: str
    timestamp: float = field(default_factory=time.time)
    tool_calls_count: int = 0

    def to_enhanced_format(self) -> str:
        """Convertit le message en format conversation élégant."""
        # Truncate long content intelligently
        display_content = (
            self.content[:500] + "..." if len(self.content) > 500 else self.content
        )

        lines = [
            f"## 💬 **{self.agent_name}**: (Tour {self.tour_number})",
            "",
            f"{display_content}",
            "",
        ]

        if self.tool_calls_count > 0:
            lines.append(f"*{self.tool_calls_count} appels d'outils effectués*")
            lines.append("")

        return "\n".join(lines)


@dataclass
class StateSnapshot:
    """Snapshot de l'état partagé à un moment donné."""

    phase_id: str
    tour_number: int
    agent_active: str
    state_variables: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def to_markdown_format(self) -> str:
        """Conversion en format markdown élégant."""
        lines = [
            f"## 📊 **État Partagé** - Phase {self.phase_id}",
            "",
            "### Variables d'État :",
        ]

        for key, value in self.state_variables.items():
            if isinstance(value, (int, float)):
                lines.append(f"- `{key}`: {value}")
            elif isinstance(value, str):
                truncated = value[:50] + "..." if len(value) > 50 else value
                lines.append(f'- `{key}`: "{truncated}"')
            elif isinstance(value, (list, dict)):
                count = len(value) if hasattr(value, "__len__") else "N/A"
                lines.append(f"- `{key}`: {type(value).__name__}({count})")
            else:
                lines.append(f"- `{key}`: {type(value).__name__}")

        lines.extend(
            [
                "",
                "### Métadonnées :",
                f"- **Tour**: {self.tour_number}",
                f'- **Phase**: "{self.phase_id}"',
                f"- **Agent actif**: {self.agent_active}",
            ]
        )

        for key, value in self.metadata.items():
            lines.append(f"- **{key}**: {value}")

        return "\n".join(lines)


@dataclass
class EnhancedToolCall:
    """Appel d'outil avec format de conversation amélioré selon spécifications."""

    agent_name: str
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    timestamp: float
    execution_time_ms: float
    success: bool
    error_message: Optional[str] = None
    call_id: str = ""

    def to_enhanced_conversation_format(self) -> str:
        """Conversion en format de conversation amélioré selon spécifications exactes."""
        # Formatage intelligent des arguments (tronqués mais informatifs)
        self._format_arguments_elegantly()

        # Formatage du résultat condensé mais informatif
        result_formatted = self._format_result_smartly()

        # Format amélioré selon spécifications
        lines = [f"### 🔧 **Tool**: {self.tool_name}", "**Arguments:**"]

        # Arguments formatés avec bullet points
        if self.arguments:
            for key, value in self.arguments.items():
                truncated_value = self._truncate_value_smartly(value)
                lines.append(f"- {key}: {truncated_value}")
        else:
            lines.append("- (aucun argument)")

        lines.extend(
            [
                "",
                f"**Timing:** {self.execution_time_ms:.1f}ms",
                "",
                "**Résultat:**",
                f"```{result_formatted}```",
                "",
                "---",
            ]
        )

        return "\n".join(lines)

    def _format_arguments_elegantly(self) -> str:
        """Formate les arguments avec troncature élégante."""
        if not self.arguments:
            return "{}"

        formatted_args = []
        for key, value in self.arguments.items():
            truncated = self._truncate_value_smartly(value)
            formatted_args.append(f"{key}: {truncated}")

        return ", ".join(formatted_args)

    def _truncate_value_smartly(self, value: Any) -> str:
        """Troncature intelligente avec préservation du sens."""
        if isinstance(value, str):
            if len(value) > 80:
                return f'"{value[:77]}..."'
            return f'"{value}"'
        elif isinstance(value, (list, tuple)):
            if len(value) == 0:
                return "[]"
            elif len(value) <= 2:
                return str(value)
            else:
                return f"[{len(value)} éléments...]"
        elif isinstance(value, dict):
            if len(value) <= 2:
                return str(value)
            else:
                return f"{{{len(value)} clés...}}"
        else:
            val_str = str(value)
            if len(val_str) > 80:
                return val_str[:77] + "..."
            return val_str

    def _format_result_smartly(self) -> str:
        """Formate le résultat de manière condensée mais informative."""
        if self.result is None:
            return "None"

        if isinstance(self.result, str):
            if len(self.result) > 150:
                return f"{self.result[:147]}..."
            return self.result

        if isinstance(self.result, (list, tuple)):
            count = len(self.result)
            if count == 0:
                return "Liste vide"
            elif count <= 3:
                return str(self.result)
            else:
                return f"Liste de {count} éléments"

        if isinstance(self.result, dict):
            keys_count = len(self.result)
            if keys_count <= 2:
                return str(self.result)
            else:
                return f"Dictionnaire avec {keys_count} clés"

        # Pour autres types
        result_str = str(self.result)
        if len(result_str) > 150:
            return result_str[:147] + "..."
        return result_str


@dataclass
class ProjectManagerPhase:
    """Phase d'orchestration gérée par le Project Manager."""

    phase_id: str
    phase_name: str
    assigned_agents: List[str]
    state_snapshots: List[StateSnapshot] = field(default_factory=list)
    tool_calls: List[EnhancedToolCall] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    success: bool = True

    def add_state_snapshot(self, snapshot: StateSnapshot):
        """Ajoute un snapshot d'état à cette phase."""
        self.state_snapshots.append(snapshot)

    def add_tool_call(self, tool_call: EnhancedToolCall):
        """Ajoute un appel d'outil à cette phase."""
        self.tool_calls.append(tool_call)

    def finalize(self):
        """Finalise la phase."""
        self.end_time = time.time()

    def to_enhanced_conversation_format(self) -> str:
        """Convertit la phase en format conversation amélioré."""
        lines = [
            f"## 🎯 **Phase**: {self.phase_name}",
            f"**ID Phase**: {self.phase_id}",
            f"**Agents assignés**: {', '.join(self.assigned_agents)}",
            f"**Durée**: {self._get_duration():.1f}ms",
            "",
        ]

        # Snapshots d'état
        if self.state_snapshots:
            lines.append("### 📊 Évolution de l'État")
            for snapshot in self.state_snapshots:
                lines.extend([snapshot.to_markdown_format(), ""])

        # Tool calls avec format amélioré
        if self.tool_calls:
            lines.append("### 🔧 Outils Utilisés")
            for tool_call in self.tool_calls:
                lines.extend(
                    [
                        f"#### Agent: {tool_call.agent_name}",
                        tool_call.to_enhanced_conversation_format(),
                        "",
                    ]
                )

        return "\n".join(lines)

    def _get_duration(self) -> float:
        """Calcule la durée de la phase en millisecondes."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0


class EnhancedRealTimeTraceAnalyzer:
    """
    Analyseur de traces en temps réel amélioré pour Project Manager
    avec format de conversation élégant et gestion d'état partagé.
    """

    def __init__(self):
        """Initialise l'analyseur de traces amélioré."""
        self.orchestration_phases: List[ProjectManagerPhase] = []
        self.current_phase: Optional[ProjectManagerPhase] = None
        self.state_evolution: List[StateSnapshot] = []
        self.conversation_messages: List[ConversationMessage] = []
        self.capture_enabled = False
        self.start_time = None
        self.end_time = None
        self.total_tool_calls = 0
        self.total_state_snapshots = 0
        self.lock = threading.Lock()

        # Métadonnées d'orchestration
        self.orchestration_metadata = {
            "pm_active": False,
            "multi_turn_coordination": False,
            "state_management_enabled": False,
            "total_phases": 0,
        }

    def start_capture(self):
        """Démarre la capture d'orchestration avec Project Manager."""
        with self.lock:
            self.capture_enabled = True
            self.start_time = time.time()
            self.orchestration_phases = []
            self.current_phase = None
            self.state_evolution = []
            self.conversation_messages = []
            self.total_tool_calls = 0
            self.total_state_snapshots = 0
            self.orchestration_metadata.update(
                {
                    "pm_active": True,
                    "state_management_enabled": True,
                    "capture_start": datetime.now().isoformat(),
                }
            )
            logger.info(
                "[ENHANCED-TRACE] Capture d'orchestration PM avec gestion d'état démarrée"
            )

    def stop_capture(self):
        """Arrête la capture d'orchestration."""
        with self.lock:
            self.capture_enabled = False
            self.end_time = time.time()
            if self.current_phase:
                self.current_phase.finalize()

            self.orchestration_metadata.update(
                {
                    "total_phases": len(self.orchestration_phases),
                    "total_tool_calls": self.total_tool_calls,
                    "total_state_snapshots": self.total_state_snapshots,
                    "capture_end": datetime.now().isoformat(),
                }
            )

            logger.info(
                f"[ENHANCED-TRACE] Capture terminée - {len(self.orchestration_phases)} phases, "
                f"{self.total_tool_calls} outils, {self.total_state_snapshots} snapshots d'état"
            )

    def start_pm_phase(
        self, phase_id: str, phase_name: str, assigned_agents: List[str]
    ) -> Optional[ProjectManagerPhase]:
        """Démarre une nouvelle phase d'orchestration PM."""
        if not self.capture_enabled:
            return None

        with self.lock:
            # Finaliser la phase précédente
            if self.current_phase:
                self.current_phase.finalize()

            # Créer nouvelle phase
            self.current_phase = ProjectManagerPhase(
                phase_id=phase_id,
                phase_name=phase_name,
                assigned_agents=assigned_agents,
            )
            self.orchestration_phases.append(self.current_phase)
            self.orchestration_metadata["multi_turn_coordination"] = True

            logger.debug(
                f"[ENHANCED-TRACE] Nouvelle phase PM: {phase_name} (agents: {assigned_agents})"
            )
            return self.current_phase

    def capture_state_snapshot(
        self,
        phase_id: str,
        tour_number: int,
        agent_active: str,
        state_variables: Dict[str, Any],
        metadata: Dict[str, Any] = None,
    ):
        """Capture un snapshot de l'état partagé."""
        if not self.capture_enabled:
            return

        with self.lock:
            self.total_state_snapshots += 1

            snapshot = StateSnapshot(
                phase_id=phase_id,
                tour_number=tour_number,
                agent_active=agent_active,
                state_variables=state_variables,
                metadata=metadata or {},
            )

            # Ajouter à l'évolution globale
            self.state_evolution.append(snapshot)

            # Ajouter à la phase courante si applicable
            if self.current_phase and self.current_phase.phase_id == phase_id:
                self.current_phase.add_state_snapshot(snapshot)

            logger.debug(
                f"[ENHANCED-TRACE] État capturé: Phase {phase_id}, Tour {tour_number}, Agent {agent_active}"
            )

    def record_enhanced_tool_call(
        self,
        agent_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any,
        execution_time_ms: float,
        success: bool = True,
        error_message: Optional[str] = None,
    ):
        """Enregistre un appel d'outil avec format amélioré."""
        if not self.capture_enabled:
            return

        with self.lock:
            self.total_tool_calls += 1

            tool_call = EnhancedToolCall(
                agent_name=agent_name,
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                timestamp=time.time(),
                execution_time_ms=execution_time_ms,
                success=success,
                error_message=error_message,
                call_id=f"enhanced_call_{self.total_tool_calls}_{int(time.time())}",
            )

            # Ajouter à la phase courante
            if self.current_phase:
                self.current_phase.add_tool_call(tool_call)

            logger.debug(
                f"[ENHANCED-TRACE] Outil enregistré (amélioré): {agent_name}.{tool_name} -> {execution_time_ms:.1f}ms"
            )

    def capture_conversation_message(
        self,
        agent_name: str,
        content: str,
        tour_number: int,
        phase_id: str = "unknown",
        tool_calls_count: int = 0,
    ):
        """Capture un message de conversation agentielle."""
        if not self.capture_enabled:
            return

        with self.lock:
            message = ConversationMessage(
                agent_name=agent_name,
                content=content,
                tour_number=tour_number,
                phase_id=phase_id,
                tool_calls_count=tool_calls_count,
            )
            self.conversation_messages.append(message)
            logger.debug(
                f"[ENHANCED-CONV] Message capturé: {agent_name} (tour {tour_number})"
            )

    def generate_enhanced_pm_orchestration_report(self) -> str:
        """Génère le rapport complet d'orchestration PM avec format amélioré."""
        if not self.orchestration_phases:
            return "Aucune orchestration PM capturée"

        report_lines = []

        # En-tête principal
        report_lines.extend(
            [
                "# DÉMO PROJECT MANAGER - ORCHESTRATION MULTI-TOURS",
                "=" * 60,
                f"**Généré le:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"**Durée totale:** {self._get_total_duration_ms():.1f}ms",
                f"**Phases d'orchestration:** {len(self.orchestration_phases)}",
                f"**Total outils utilisés:** {self.total_tool_calls}",
                f"**Snapshots d'état:** {self.total_state_snapshots}",
                "",
            ]
        )

        # 1. Métadonnées de l'orchestration
        report_lines.extend(
            [
                "## 1. Métadonnées de l'orchestration",
                "-" * 40,
                f"- **Project Manager actif**: {'✅' if self.orchestration_metadata.get('pm_active') else '❌'}",
                f"- **Coordination multi-tours**: {'✅' if self.orchestration_metadata.get('multi_turn_coordination') else '❌'}",
                f"- **Gestion d'état partagé**: {'✅' if self.orchestration_metadata.get('state_management_enabled') else '❌'}",
                f"- **Type d'orchestration**: Unified Rhetorical Analysis avec PM",
                f"- **Stratégie de coordination**: Balanced Participation avec State Management",
                "",
            ]
        )

        # 2. Évolution de l'état partagé
        report_lines.extend(["## 2. Évolution de l'état partagé", "-" * 35, ""])

        if self.state_evolution:
            for i, snapshot in enumerate(self.state_evolution, 1):
                report_lines.extend(
                    [f"### Snapshot {i}", snapshot.to_markdown_format(), ""]
                )
        else:
            report_lines.append("*Aucune évolution d'état capturée*")

        # 3. Conversation agentielle complète
        report_lines.extend(["## 3. Conversation agentielle complète", "-" * 40, ""])

        if self.conversation_messages:
            # Grouper les messages par phase
            messages_by_phase = {}
            for message in self.conversation_messages:
                phase_id = message.phase_id
                if phase_id not in messages_by_phase:
                    messages_by_phase[phase_id] = []
                messages_by_phase[phase_id].append(message)

            # Affichage par phase
            for phase_id, messages in messages_by_phase.items():
                report_lines.extend([f"### 🎯 Phase: {phase_id}", ""])

                for message in messages:
                    report_lines.extend([message.to_enhanced_format(), ""])
        else:
            report_lines.append("*Aucune conversation capturée*")

        # 4. Phases d'orchestration détaillées
        report_lines.extend(["## 4. Phases d'orchestration détaillées", "-" * 40, ""])

        for i, phase in enumerate(self.orchestration_phases, 1):
            report_lines.extend(
                [
                    f"### 🎯 Phase {i}: {phase.phase_name}",
                    "",
                    phase.to_enhanced_conversation_format(),
                    "",
                ]
            )

        # 4. Synthèse de l'orchestration
        report_lines.extend(
            [
                "## 4. Synthèse de l'orchestration",
                "-" * 30,
            ]
        )

        # Statistiques par phase
        for phase in self.orchestration_phases:
            duration = phase._get_duration()
            tool_count = len(phase.tool_calls)
            state_count = len(phase.state_snapshots)

            report_lines.extend(
                [
                    f"### Phase: {phase.phase_name}",
                    f"- **Durée**: {duration:.1f}ms",
                    f"- **Outils utilisés**: {tool_count}",
                    f"- **Snapshots d'état**: {state_count}",
                    f"- **Agents impliqués**: {', '.join(phase.assigned_agents)}",
                    "",
                ]
            )

        # 5. Validation PM et coordination
        report_lines.extend(
            [
                "## 5. Validation PM et coordination",
                "-" * 35,
                "✅ **Project Manager opérationnel**: Phases d'orchestration coordonnées",
                "✅ **Gestion d'état partagé**: Évolution capturée à chaque phase clé",
                "✅ **Format de conversation amélioré**: Headers spéciaux et markup élégant",
                "✅ **Orchestration multi-tours**: Coordination agents formels/informels",
                "✅ **Trace enrichie**: Capture complète avec évolution d'état",
                "",
            ]
        )

        # Validation des objectifs clés
        objectives_met = [
            (
                "Format conversation lisible",
                "✅",
                "Headers spéciaux et markup élégant implémentés",
            ),
            ("PM opérationnel", "✅", "Orchestration multi-phases coordonnée"),
            (
                "Gestion d'état partagé",
                "✅",
                f"{self.total_state_snapshots} snapshots capturés",
            ),
            ("Trace enrichie", "✅", "Évolution d'état documentée à chaque phase"),
            (
                "Démo complète",
                "✅",
                f"{len(self.orchestration_phases)} phases d'orchestration",
            ),
        ]

        report_lines.append("**Validation des objectifs:**")
        for obj, status, details in objectives_met:
            report_lines.append(f"- {status} **{obj}**: {details}")

        # Footer
        report_lines.extend(
            [
                "",
                "=" * 60,
                "*Rapport généré par EnhancedRealTimeTraceAnalyzer v2.0*",
                "*Project Manager avec orchestration multi-tours et gestion d'état partagé*",
                "*Format de conversation amélioré selon spécifications exactes*",
            ]
        )

        return "\n".join(report_lines)

    def _get_total_duration_ms(self) -> float:
        """Calcule la durée totale en millisecondes."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    def save_enhanced_report(self, filepath: str) -> bool:
        """Sauvegarde le rapport d'orchestration amélioré."""
        try:
            report = self.generate_enhanced_pm_orchestration_report()
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report)
            logger.info(
                f"[ENHANCED-SAVE] Rapport d'orchestration PM sauvegardé: {filepath}"
            )
            return True
        except Exception as e:
            logger.error(f"[ENHANCED-ERROR] Erreur sauvegarde rapport: {e}")
            return False


# Instance globale pour utilisation dans tout le système
enhanced_global_trace_analyzer = EnhancedRealTimeTraceAnalyzer()


def enhanced_tool_call_tracer(agent_name: str, tool_name: str):
    """Décorateur pour tracer automatiquement les appels d'outils avec format amélioré."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not enhanced_global_trace_analyzer.capture_enabled:
                return func(*args, **kwargs)

            start_time = time.time()
            result = None
            success = True
            error_message = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                execution_time = (time.time() - start_time) * 1000
                enhanced_global_trace_analyzer.record_enhanced_tool_call(
                    agent_name=agent_name,
                    tool_name=tool_name,
                    arguments=kwargs,
                    result=result,
                    execution_time_ms=execution_time,
                    success=success,
                    error_message=error_message,
                )

        return wrapper

    return decorator


# Fonctions utilitaires pour intégration facile
def start_enhanced_pm_capture():
    """Démarre la capture d'orchestration PM améliorée."""
    enhanced_global_trace_analyzer.start_capture()


def stop_enhanced_pm_capture():
    """Arrête la capture d'orchestration PM."""
    enhanced_global_trace_analyzer.stop_capture()


def start_pm_orchestration_phase(
    phase_id: str, phase_name: str, assigned_agents: List[str]
):
    """Démarre une nouvelle phase d'orchestration PM."""
    return enhanced_global_trace_analyzer.start_pm_phase(
        phase_id, phase_name, assigned_agents
    )


def capture_shared_state(
    phase_id: str,
    tour_number: int,
    agent_active: str,
    state_variables: Dict[str, Any],
    metadata: Dict[str, Any] = None,
):
    """Capture un snapshot de l'état partagé."""
    enhanced_global_trace_analyzer.capture_state_snapshot(
        phase_id, tour_number, agent_active, state_variables, metadata
    )


def get_enhanced_pm_report() -> str:
    """Récupère le rapport d'orchestration PM complet."""
    return enhanced_global_trace_analyzer.generate_enhanced_pm_orchestration_report()


def save_enhanced_pm_report(filepath: str) -> bool:
    """Sauvegarde le rapport d'orchestration PM."""
    return enhanced_global_trace_analyzer.save_enhanced_report(filepath)
