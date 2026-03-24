"""
Trace analyzer for conversational orchestration (#208-S).

Lightweight adapter that wraps the enhanced trace analyzer from
reporting/ to provide per-turn convergence measurement, state
evolution tracking, and quality reports for conversational mode.

Extracted from enhanced_pm_analysis_runner.py (deprecated) patterns.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("TraceAnalyzer")


@dataclass
class TurnTrace:
    """Trace of a single conversational turn."""

    phase: str
    turn: int
    agent: str
    content_length: int
    tool_calls: int = 0
    state_fields_changed: int = 0
    timestamp: float = 0.0


@dataclass
class PhaseTrace:
    """Trace of a complete conversational phase."""

    name: str
    turns: List[TurnTrace] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    state_before: Dict[str, int] = field(default_factory=dict)
    state_after: Dict[str, int] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time if self.end_time else 0.0

    @property
    def total_content(self) -> int:
        return sum(t.content_length for t in self.turns)

    @property
    def agents_active(self) -> List[str]:
        return list({t.agent for t in self.turns})


@dataclass
class ConvergenceMetrics:
    """Metrics measuring convergence of the conversational analysis."""

    state_fields_populated: int = 0
    total_state_fields: int = 0
    arguments_found: int = 0
    fallacies_found: int = 0
    quality_scores_count: int = 0
    counter_arguments_count: int = 0
    formal_results_count: int = 0

    @property
    def coverage_ratio(self) -> float:
        """Ratio of populated state fields (0.0-1.0)."""
        return (
            self.state_fields_populated / self.total_state_fields
            if self.total_state_fields
            else 0.0
        )

    @property
    def is_converged(self) -> bool:
        """Analysis has converged when all key dimensions are populated."""
        return (
            self.arguments_found > 0
            and self.fallacies_found >= 0  # 0 is valid (no fallacies)
            and self.quality_scores_count > 0
        )


class ConversationalTraceAnalyzer:
    """Trace analyzer for conversational orchestration.

    Tracks per-turn state evolution, measures convergence, and produces
    quality reports after each analysis run.

    Usage:
        analyzer = ConversationalTraceAnalyzer()
        analyzer.start()
        analyzer.begin_phase("Extraction")
        analyzer.record_turn(phase="Extraction", turn=1, agent="PM", content="...")
        analyzer.end_phase("Extraction", state_snapshot)
        analyzer.stop()
        report = analyzer.generate_report()
    """

    def __init__(self):
        self.phases: List[PhaseTrace] = []
        self._current_phase: Optional[PhaseTrace] = None
        self._start_time: float = 0.0
        self._end_time: float = 0.0
        self._state_snapshots: List[Dict[str, Any]] = []

    def start(self) -> None:
        """Start trace capture."""
        self.phases = []
        self._current_phase = None
        self._start_time = time.time()
        self._state_snapshots = []
        logger.info("[TRACE] Capture started")

    def stop(self) -> None:
        """Stop trace capture."""
        self._end_time = time.time()
        if self._current_phase and not self._current_phase.end_time:
            self._current_phase.end_time = time.time()
        logger.info(
            f"[TRACE] Capture stopped — {len(self.phases)} phases, "
            f"{sum(len(p.turns) for p in self.phases)} turns"
        )

    def begin_phase(self, phase_name: str, state_snapshot: Optional[Dict] = None) -> None:
        """Begin tracking a new conversational phase."""
        if self._current_phase and not self._current_phase.end_time:
            self._current_phase.end_time = time.time()

        phase = PhaseTrace(
            name=phase_name,
            start_time=time.time(),
        )
        if state_snapshot:
            phase.state_before = _count_state_fields(state_snapshot)

        self._current_phase = phase
        self.phases.append(phase)

    def end_phase(self, phase_name: str, state_snapshot: Optional[Dict] = None) -> None:
        """End tracking the current phase."""
        if self._current_phase and self._current_phase.name == phase_name:
            self._current_phase.end_time = time.time()
            if state_snapshot:
                self._current_phase.state_after = _count_state_fields(state_snapshot)
                self._state_snapshots.append(state_snapshot)

    def record_turn(
        self,
        phase: str,
        turn: int,
        agent: str,
        content: str,
        tool_calls: int = 0,
    ) -> None:
        """Record a single conversational turn."""
        trace = TurnTrace(
            phase=phase,
            turn=turn,
            agent=agent,
            content_length=len(content) if content else 0,
            tool_calls=tool_calls,
            timestamp=time.time(),
        )
        if self._current_phase and self._current_phase.name == phase:
            self._current_phase.turns.append(trace)

    def compute_convergence(self, state_snapshot: Dict[str, Any]) -> ConvergenceMetrics:
        """Compute convergence metrics from state snapshot."""
        metrics = ConvergenceMetrics()

        # Count non-empty fields
        for key, value in state_snapshot.items():
            metrics.total_state_fields += 1
            if value and value not in ([], {}, "", None, 0, False):
                metrics.state_fields_populated += 1

        # Count specific dimensions
        if isinstance(state_snapshot.get("identified_arguments"), list):
            metrics.arguments_found = len(state_snapshot["identified_arguments"])
        if isinstance(state_snapshot.get("identified_fallacies"), list):
            metrics.fallacies_found = len(state_snapshot["identified_fallacies"])
        if isinstance(state_snapshot.get("argument_quality_scores"), dict):
            metrics.quality_scores_count = len(state_snapshot["argument_quality_scores"])
        if isinstance(state_snapshot.get("counter_arguments"), list):
            metrics.counter_arguments_count = len(state_snapshot["counter_arguments"])

        # Count formal results
        for key in ["fol_analysis_results", "propositional_analysis_results"]:
            results = state_snapshot.get(key, [])
            if isinstance(results, list):
                metrics.formal_results_count += len(results)

        return metrics

    def generate_report(self) -> Dict[str, Any]:
        """Generate a structured trace report."""
        total_turns = sum(len(p.turns) for p in self.phases)
        total_duration = self._end_time - self._start_time if self._end_time else 0.0

        # Compute final convergence if we have snapshots
        final_convergence = None
        if self._state_snapshots:
            final_convergence = self.compute_convergence(self._state_snapshots[-1])

        phase_summaries = []
        for phase in self.phases:
            phase_summaries.append({
                "name": phase.name,
                "turns": len(phase.turns),
                "duration_seconds": round(phase.duration, 1),
                "agents": phase.agents_active,
                "total_content_chars": phase.total_content,
                "state_before": phase.state_before,
                "state_after": phase.state_after,
            })

        report = {
            "total_phases": len(self.phases),
            "total_turns": total_turns,
            "total_duration_seconds": round(total_duration, 1),
            "phases": phase_summaries,
        }

        if final_convergence:
            report["convergence"] = {
                "coverage_ratio": round(final_convergence.coverage_ratio, 3),
                "is_converged": final_convergence.is_converged,
                "arguments_found": final_convergence.arguments_found,
                "fallacies_found": final_convergence.fallacies_found,
                "quality_scores": final_convergence.quality_scores_count,
                "counter_arguments": final_convergence.counter_arguments_count,
                "formal_results": final_convergence.formal_results_count,
            }

        return report

    def generate_markdown_report(self) -> str:
        """Generate a human-readable markdown trace report."""
        data = self.generate_report()
        lines = [
            "# Conversational Analysis Trace Report",
            "",
            f"**Duration:** {data['total_duration_seconds']}s | "
            f"**Phases:** {data['total_phases']} | "
            f"**Turns:** {data['total_turns']}",
            "",
        ]

        for phase in data.get("phases", []):
            lines.append(f"## Phase: {phase['name']}")
            lines.append(
                f"- Turns: {phase['turns']} | Duration: {phase['duration_seconds']}s"
            )
            lines.append(f"- Agents: {', '.join(phase['agents'])}")
            lines.append(f"- Content: {phase['total_content_chars']} chars")
            lines.append("")

        conv = data.get("convergence")
        if conv:
            lines.append("## Convergence")
            lines.append(f"- Coverage: {conv['coverage_ratio']:.1%}")
            lines.append(f"- Converged: {'Yes' if conv['is_converged'] else 'No'}")
            lines.append(f"- Arguments: {conv['arguments_found']}")
            lines.append(f"- Fallacies: {conv['fallacies_found']}")
            lines.append(f"- Quality scores: {conv['quality_scores']}")
            lines.append(f"- Counter-arguments: {conv['counter_arguments']}")
            lines.append("")

        return "\n".join(lines)


def _count_state_fields(snapshot: Dict[str, Any]) -> Dict[str, int]:
    """Count non-empty fields in a state snapshot by category."""
    counts = {"total": 0, "populated": 0}
    for key, value in snapshot.items():
        counts["total"] += 1
        if value and value not in ([], {}, "", None, 0, False):
            counts["populated"] += 1
    return counts
