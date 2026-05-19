"""Re-prompt trace extraction for the SCDA growth validation hook.

Captures structured traces from the conversational orchestrator's growth
validation re-prompt loop, enabling analysis of when and why agents were
re-prompted during analysis phases.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

_FINGERPRINT_KEYS = (
    "arguments",
    "fallacies",
    "counter_arguments",
    "jtms_beliefs",
    "dung_frameworks",
    "aspic_results",
    "belief_revision_results",
    "nl_to_logic_translations",
    "fol_analysis",
    "propositional_analysis",
    "modal_analysis",
)


@dataclass
class RepromptTrace:
    """Single re-prompt event captured during growth validation."""

    phase_name: str
    turn: int
    attempt_idx: int
    fingerprint_before: List[int]
    fingerprint_after: List[int]
    delta: List[int]
    outcome: str  # "ok" (growth achieved) | "reran" (re-prompted again) | "gave_up" (limit reached)
    agent_name: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def total_delta(self) -> int:
        return sum(abs(d) for d in self.delta)

    @property
    def grew(self) -> bool:
        return any(d != 0 for d in self.delta)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        lines = [
            f"### Re-prompt #{self.attempt_idx} — {self.phase_name} (turn {self.turn})",
            f"- **Agent:** {self.agent_name or 'unknown'}",
            f"- **Outcome:** {self.outcome}",
            f"- **Total delta:** {self.total_delta}",
            f"- **Fingerprint before:** {self.fingerprint_before}",
            f"- **Fingerprint after:** {self.fingerprint_after}",
            f"- **Delta:** {self.delta}",
            f"- **Timestamp:** {self.timestamp}",
        ]
        return "\n".join(lines)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class RepromptTraceExtractor:
    """Accumulates and analyzes re-prompt traces from an SCDA run.

    Usage:
        extractor = RepromptTraceExtractor()
        # ... pass extractor to orchestrator via enable_reprompt_tracing=True ...
        traces = extractor.traces
        extractor.to_json()
        extractor.to_markdown()
    """

    def __init__(self) -> None:
        self._traces: List[RepromptTrace] = []

    @property
    def traces(self) -> List[RepromptTrace]:
        return list(self._traces)

    def record(
        self,
        phase_name: str,
        turn: int,
        attempt_idx: int,
        fingerprint_before: tuple[int, ...],
        fingerprint_after: tuple[int, ...],
        outcome: str,
        agent_name: str = "",
    ) -> RepromptTrace:
        delta = [aft - bef for bef, aft in zip(fingerprint_before, fingerprint_after)]
        trace = RepromptTrace(
            phase_name=phase_name,
            turn=turn,
            attempt_idx=attempt_idx,
            fingerprint_before=list(fingerprint_before),
            fingerprint_after=list(fingerprint_after),
            delta=delta,
            outcome=outcome,
            agent_name=agent_name,
        )
        self._traces.append(trace)
        logger.debug(
            "Re-prompt trace recorded: phase=%s turn=%d attempt=%d outcome=%s delta=%s",
            phase_name, turn, attempt_idx, outcome, delta,
        )
        return trace

    def to_json(self) -> str:
        return json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_traces": len(self._traces),
                "phases_affected": list({t.phase_name for t in self._traces}),
                "outcomes": {
                    o: sum(1 for t in self._traces if t.outcome == o)
                    for o in ("ok", "reran", "gave_up")
                },
                "traces": [t.to_dict() for t in self._traces],
            },
            indent=2,
            ensure_ascii=False,
        )

    def to_markdown(self) -> str:
        lines = [
            "# Re-Prompt Trace Report",
            "",
            f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Total re-prompts:** {len(self._traces)}",
            "",
        ]
        if not self._traces:
            lines.append("*No re-prompt events recorded.*")
            return "\n".join(lines)

        phases = {}
        for t in self._traces:
            phases.setdefault(t.phase_name, []).append(t)

        lines.append("## Summary by Phase")
        lines.append("")
        lines.append("| Phase | Re-prompts | OK | Reran | Gave up |")
        lines.append("|-------|-----------|-----|-------|---------|")
        for phase, phase_traces in phases.items():
            ok = sum(1 for t in phase_traces if t.outcome == "ok")
            reran = sum(1 for t in phase_traces if t.outcome == "reran")
            gave_up = sum(1 for t in phase_traces if t.outcome == "gave_up")
            lines.append(f"| {phase} | {len(phase_traces)} | {ok} | {reran} | {gave_up} |")
        lines.append("")

        lines.append("## Detailed Traces")
        lines.append("")
        for t in self._traces:
            lines.append(t.to_markdown())
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_traces": len(self._traces),
            "traces": [t.to_dict() for t in self._traces],
        }

    @classmethod
    def from_phase_log(
        cls,
        phase_log: List[Dict[str, Any]],
        fingerprints: Optional[Dict[str, List[tuple[int, ...]]]] = None,
    ) -> "RepromptTraceExtractor":
        """Reconstruct traces from a phase_log returned by ``_run_phase``.

        ``phase_log`` entries with a ``"re_prompt"`` key are re-prompt events.
        ``fingerprints`` maps ``"phase_name:turn"`` to ``[before, after]`` tuples.
        """
        extractor = cls()
        for entry in phase_log:
            rp_idx = entry.get("re_prompt")
            if rp_idx is None:
                continue
            phase = entry.get("phase", "unknown")
            turn = entry.get("turn", 0)
            agent = entry.get("agent", "")
            fp_key = f"{phase}:{turn}"
            fp_before = (0,)
            fp_after = (0,)
            if fingerprints and fp_key in fingerprints:
                fps = fingerprints[fp_key]
                if len(fps) >= 2:
                    fp_before = fps[0]
                    fp_after = fps[-1]
            outcome = "ok" if rp_idx == 1 else "reran"
            extractor.record(
                phase_name=phase,
                turn=turn,
                attempt_idx=rp_idx,
                fingerprint_before=fp_before,
                fingerprint_after=fp_after,
                outcome=outcome,
                agent_name=agent,
            )
        return extractor
