"""
Conflict Resolution for JTMS multi-agent scenarios.

Extracted from agents/jtms_communication_hub.py for standalone use.
Works with belief dictionaries — no direct agent dependency.

5 resolution strategies:
- confidence_based: highest confidence wins
- evidence_based: evidence quality + justification count
- consensus: placeholder for N-agent voting
- agent_expertise: domain-specific expertise mapping
- temporal: most recent belief wins
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ConflictResolver")


class ConflictResolver:
    """Resolve conflicts between competing beliefs from multiple agents.

    Operates on belief dictionaries, not agent objects — usable in both
    pipeline and conversational modes.

    Usage:
        resolver = ConflictResolver()
        conflict = {
            "belief_name": "hypothesis_X",
            "beliefs": {
                "agent_1": {"belief_name": "hypothesis_X", "confidence": 0.8, "valid": True},
                "agent_2": {"belief_name": "hypothesis_X", "confidence": 0.3, "valid": False},
            },
            "context": {"type": "hypothesis"},
        }
        result = resolver.resolve(conflict, strategy="confidence_based")
    """

    STRATEGIES = [
        "confidence_based",
        "evidence_based",
        "consensus",
        "agent_expertise",
        "temporal",
    ]

    # Domain expertise mapping: context type → preferred agent role
    EXPERTISE_MAP = {
        "hypothesis": "sherlock",
        "evidence": "sherlock",
        "deduction": "sherlock",
        "validation": "watson",
        "logical_proof": "watson",
        "consistency": "watson",
        "quality": "quality",
        "fallacy": "informal",
        "counter_argument": "counter",
    }

    def __init__(self):
        self.resolution_history: List[Dict[str, Any]] = []

    def resolve(
        self,
        conflict: Dict[str, Any],
        strategy: str = "confidence_based",
    ) -> Dict[str, Any]:
        """Resolve a conflict synchronously. Returns resolution dict."""
        if strategy not in self.STRATEGIES:
            strategy = "confidence_based"

        result = {
            "conflict_id": conflict.get(
                "conflict_id", f"conflict_{len(self.resolution_history)}"
            ),
            "strategy_used": strategy,
            "resolved": False,
            "chosen_belief": None,
            "chosen_agent": None,
            "reasoning": "",
            "timestamp": datetime.now().isoformat(),
        }

        try:
            resolver_fn = getattr(self, f"_resolve_by_{strategy.replace('_based', '')}")
            resolution = resolver_fn(conflict)
            result.update(resolution)
        except Exception as e:
            result["error"] = str(e)
            result["reasoning"] = f"Resolution error: {e}"

        self.resolution_history.append(result)
        return result

    def _resolve_by_confidence(self, conflict: Dict) -> Dict:
        """Pick the belief with highest confidence."""
        beliefs = conflict.get("beliefs", {})
        best_belief = None
        best_confidence = -1.0
        best_agent = None

        for agent_name, data in beliefs.items():
            confidence = data.get("confidence", 0.0)
            if confidence > best_confidence:
                best_confidence = confidence
                best_belief = data.get("belief_name")
                best_agent = agent_name

        return {
            "resolved": best_belief is not None,
            "chosen_belief": best_belief,
            "chosen_agent": best_agent,
            "reasoning": f"Highest confidence: {best_confidence:.2f} by {best_agent}",
            "confidence_score": best_confidence,
        }

    def _resolve_by_evidence(self, conflict: Dict) -> Dict:
        """Pick the belief with best evidence score (justification count * confidence)."""
        beliefs = conflict.get("beliefs", {})
        best_belief = None
        best_score = -1.0
        best_agent = None

        for agent_name, data in beliefs.items():
            justification_count = data.get("justification_count", 1)
            confidence = data.get("confidence", 0.0)
            score = justification_count * confidence

            if score > best_score:
                best_score = score
                best_belief = data.get("belief_name")
                best_agent = agent_name

        return {
            "resolved": best_belief is not None,
            "chosen_belief": best_belief,
            "chosen_agent": best_agent,
            "reasoning": f"Best evidence score: {best_score:.2f} by {best_agent}",
            "evidence_score": best_score,
        }

    def _resolve_by_consensus(self, conflict: Dict) -> Dict:
        """Majority vote among agents. Requires 3+ agents for meaningful result."""
        beliefs = conflict.get("beliefs", {})
        if len(beliefs) < 3:
            return {
                "resolved": False,
                "reasoning": "Consensus requires 3+ agents",
            }

        # Count votes for each truth value
        votes_true = sum(1 for d in beliefs.values() if d.get("valid") is True)
        votes_false = sum(1 for d in beliefs.values() if d.get("valid") is False)

        if votes_true > votes_false:
            winner = next(
                (a for a, d in beliefs.items() if d.get("valid") is True), None
            )
            return {
                "resolved": True,
                "chosen_agent": winner,
                "chosen_belief": beliefs[winner]["belief_name"] if winner else None,
                "reasoning": f"Consensus: {votes_true} for vs {votes_false} against",
            }
        elif votes_false > votes_true:
            winner = next(
                (a for a, d in beliefs.items() if d.get("valid") is False), None
            )
            return {
                "resolved": True,
                "chosen_agent": winner,
                "chosen_belief": beliefs[winner]["belief_name"] if winner else None,
                "reasoning": f"Consensus: {votes_false} against vs {votes_true} for",
            }
        return {"resolved": False, "reasoning": "Consensus tie"}

    def _resolve_by_agent_expertise(self, conflict: Dict) -> Dict:
        """Pick the belief from the agent with domain expertise."""
        beliefs = conflict.get("beliefs", {})
        context_type = conflict.get("context", {}).get("type", "unknown")
        expert_role = self.EXPERTISE_MAP.get(context_type, "sherlock")

        for agent_name, data in beliefs.items():
            if expert_role.lower() in agent_name.lower():
                return {
                    "resolved": True,
                    "chosen_belief": data.get("belief_name"),
                    "chosen_agent": agent_name,
                    "reasoning": f"Expert {expert_role} for domain {context_type}",
                    "expertise_domain": context_type,
                }

        # Fallback to confidence if no expert found
        return self._resolve_by_confidence(conflict)

    def _resolve_by_temporal(self, conflict: Dict) -> Dict:
        """Pick the most recently updated belief."""
        beliefs = conflict.get("beliefs", {})
        latest_agent = None
        latest_ts = None

        for agent_name, data in beliefs.items():
            ts = data.get("timestamp")
            if ts and (latest_ts is None or ts > latest_ts):
                latest_ts = ts
                latest_agent = agent_name

        if latest_agent:
            return {
                "resolved": True,
                "chosen_belief": beliefs[latest_agent].get("belief_name"),
                "chosen_agent": latest_agent,
                "reasoning": f"Most recent: {latest_agent} at {latest_ts}",
            }

        # Fallback to confidence
        return self._resolve_by_confidence(conflict)

    def get_history(self) -> List[Dict[str, Any]]:
        """Get resolution history."""
        return self.resolution_history

    def get_stats(self) -> Dict[str, Any]:
        """Get resolution statistics."""
        resolved = sum(1 for r in self.resolution_history if r.get("resolved"))
        by_strategy = {}
        for r in self.resolution_history:
            s = r.get("strategy_used", "unknown")
            by_strategy[s] = by_strategy.get(s, 0) + 1

        return {
            "total_conflicts": len(self.resolution_history),
            "resolved": resolved,
            "unresolved": len(self.resolution_history) - resolved,
            "by_strategy": by_strategy,
        }
