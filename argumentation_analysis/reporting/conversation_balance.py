#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Conversation balance analyzer — entropy-based participation scoring.

Analyzes multi-agent conversation logs to produce a balance score in [0, 1],
per-agent turn/token distributions, and dominance alerts. Designed for the
SCDA conversational pipeline (see conversational_orchestrator.py).

Balance score uses Shannon entropy normalized by the maximum entropy for the
number of active agents: ``H / H_max`` where ``H = -sum(p_i * log2(p_i))``.
A score of 1.0 means perfectly balanced participation; 0.0 means a single
agent dominated the entire conversation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class AgentStats:
    """Per-agent participation statistics."""

    name: str
    turn_count: int = 0
    total_chars: int = 0
    turns_per_phase: Dict[str, int] = field(default_factory=dict)


@dataclass
class BalanceReport:
    """Full conversation balance report."""

    balance_score: float
    active_agents: int
    total_turns: int
    agent_stats: Dict[str, AgentStats]
    dominance_alerts: List[str]

    def to_markdown(self) -> str:
        lines = [
            "## Conversation Balance Report",
            "",
            f"- **Balance score**: {self.balance_score:.3f}",
            f"- **Active agents**: {self.active_agents}",
            f"- **Total turns**: {self.total_turns}",
            "",
            "### Per-Agent Statistics",
            "",
            "| Agent | Turns | Chars | Turns/phase |",
            "|-------|-------|-------|-------------|",
        ]
        for name, stats in sorted(self.agent_stats.items()):
            phase_str = ", ".join(
                f"{p}:{c}" for p, c in sorted(stats.turns_per_phase.items())
            )
            lines.append(f"| {name} | {stats.turn_count} | {stats.total_chars:,} | {phase_str} |")
        if self.dominance_alerts:
            lines.append("")
            lines.append("### Dominance Alerts")
            for alert in self.dominance_alerts:
                lines.append(f"- {alert}")
        lines.append("")
        return "\n".join(lines)


class ConversationBalanceAnalyzer:
    """Analyze multi-agent conversation balance from SCDA conversation logs.

    The input ``conversation_log`` is the list produced by
    ``run_conversational_analysis`` — each entry is a dict with at least
    ``"agent"`` and ``"content"`` keys (or ``"type"`` for structural entries
    which are skipped).
    """

    def __init__(self, dominance_threshold: float = 0.5) -> None:
        self.dominance_threshold = dominance_threshold

    def analyze(self, conversation_log: Sequence[Dict[str, Any]]) -> BalanceReport:
        agent_data: Dict[str, AgentStats] = {}
        total_turns = 0

        for entry in conversation_log:
            # Skip structural entries (conflict_resolution, etc.)
            entry_type = entry.get("type")
            if entry_type and entry_type not in ("agent_turn", "turn"):
                continue

            agent_name = entry.get("agent")
            if not agent_name:
                continue

            content = entry.get("content", "")
            phase = entry.get("phase", "unknown")

            if agent_name not in agent_data:
                agent_data[agent_name] = AgentStats(name=agent_name)

            stats = agent_data[agent_name]
            stats.turn_count += 1
            stats.total_chars += len(content)
            stats.turns_per_phase[phase] = stats.turns_per_phase.get(phase, 0) + 1
            total_turns += 1

        active_agents = len(agent_data)
        balance_score = self._compute_entropy(agent_data, total_turns)
        alerts = self._detect_dominance(agent_data, total_turns)

        return BalanceReport(
            balance_score=balance_score,
            active_agents=active_agents,
            total_turns=total_turns,
            agent_stats=agent_data,
            dominance_alerts=alerts,
        )

    def _compute_entropy(
        self, agent_data: Dict[str, AgentStats], total_turns: int
    ) -> float:
        if total_turns == 0 or len(agent_data) <= 1:
            return 0.0

        entropy = 0.0
        for stats in agent_data.values():
            p = stats.turn_count / total_turns
            if p > 0:
                entropy -= p * math.log2(p)

        max_entropy = math.log2(len(agent_data))
        return entropy / max_entropy if max_entropy > 0 else 0.0

    def _detect_dominance(
        self, agent_data: Dict[str, AgentStats], total_turns: int
    ) -> List[str]:
        alerts: List[str] = []
        if total_turns == 0:
            return alerts

        for name, stats in agent_data.items():
            ratio = stats.turn_count / total_turns
            if ratio > self.dominance_threshold:
                alerts.append(
                    f"{name} dominates with {stats.turn_count}/{total_turns} "
                    f"turns ({ratio:.0%})"
                )

        # Check for silent agents (0 turns in multi-agent setup)
        for name, stats in agent_data.items():
            if stats.turn_count == 0 and len(agent_data) > 1:
                alerts.append(f"{name} has 0 turns (silent agent)")

        return alerts

    def analyze_from_state(
        self,
        state: Any,
        conversation_log: Sequence[Dict[str, Any]],
    ) -> BalanceReport:
        """Analyze balance enriched with UnifiedAnalysisState dimensions.

        Adds phase-level annotations from the state (e.g. number of arguments
        extracted per phase) to the balance report.
        """
        report = self.analyze(conversation_log)

        if state is not None and hasattr(state, "identified_arguments"):
            args = state.identified_arguments
            fallacies = state.identified_fallacies
            n_args = len(args) if args else 0
            n_fall = len(fallacies) if fallacies else 0
            report.agent_stats["__state__"] = AgentStats(
                name="__state__",
                turn_count=0,
                total_chars=0,
                turns_per_phase={
                    "arguments_extracted": n_args,
                    "fallacies_detected": n_fall,
                },
            )
        return report
