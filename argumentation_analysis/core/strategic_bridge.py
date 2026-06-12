"""
RA-4 #1049 — Bridge between StrategicState and UnifiedAnalysisState.

Copies strategic objectives and decisions from the hierarchical strategic layer
into the core UnifiedAnalysisState so operational agents can access them.
Follows the hierarchy_bridge.py pattern (adapter between paradigms).

Privacy enforcement: strips raw_text, source_name, author from all copied data.
"""

import copy
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Keys that must be stripped from objective/decision dicts for privacy.
# These match the dataset privacy discipline (CLAUDE.md §Dataset Privacy).
_PRIVACY_STRIP_KEYS = frozenset({"raw_text", "source_name", "author", "full_text"})

# Patterns that indicate identifying content — replaced with opaque markers.
_PRIVACY_REPLACEMENTS = {
    # Named individuals → opaque speaker IDs
    # (handled by scrubbing the keys above; no regex heuristics per anti-pendule)
}


def _privacy_scrub_objectives(objectives: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deep-copy objectives and strip privacy-sensitive keys.

    Walks all nested dicts recursively. Any key in _PRIVACY_STRIP_KEYS
    is removed from every dict encountered.
    """
    scrubbed = []
    for obj in objectives:
        scrubbed.append(_scrub_dict(copy.deepcopy(obj)))
    return scrubbed


def _scrub_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively strip privacy-sensitive keys from a dict."""
    keys_to_remove = [k for k in d if k in _PRIVACY_STRIP_KEYS]
    for k in keys_to_remove:
        del d[k]
    # Recurse into nested dicts and lists of dicts
    for key, value in d.items():
        if isinstance(value, dict):
            d[key] = _scrub_dict(value)
        elif isinstance(value, list):
            d[key] = [
                _scrub_dict(item) if isinstance(item, dict) else item
                for item in value
            ]
    return d


def sync_strategic_to_unified(
    strategic_state: Any,
    unified_state: Any,
) -> int:
    """Copy objectives + decisions from StrategicState to UnifiedAnalysisState.

    Args:
        strategic_state: A StrategicState instance with global_objectives
            and strategic_decisions_log attributes.
        unified_state: A UnifiedAnalysisState instance with strategic_objectives
            and strategic_decisions_log attributes.

    Returns:
        Number of objectives synced.
    """
    objectives = getattr(strategic_state, "global_objectives", [])
    decisions = getattr(strategic_state, "strategic_decisions_log", [])

    # Deep-copy objectives with privacy scrub
    scrubbed_objectives = _privacy_scrub_objectives(objectives)
    unified_state.strategic_objectives = scrubbed_objectives

    # Deep-copy decisions log (also scrubbed — decisions may contain text refs)
    unified_state.strategic_decisions_log = _privacy_scrub_objectives(decisions)

    count = len(unified_state.strategic_objectives)
    logger.info(
        "Synced %d strategic objectives and %d decisions to UnifiedAnalysisState",
        count,
        len(unified_state.strategic_decisions_log),
    )
    return count
