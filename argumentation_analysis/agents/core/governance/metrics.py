"""
Governance simulation metrics — consensus, fairness, efficiency, satisfaction, stability.

Adapted from 2.1.6_multiagent_governance_prototype/metrics/metrics.py.
"""

from typing import Any, Dict, List, Optional, Union

import numpy as np


def consensus_rate(results):
    """Fraction of agents voting for the winner.

    Handles three ``votes`` shapes the governance plugin's LLM-generated
    JSON can take (#1273): a sequential list (``["A", "A", "B"]``), a
    per-option tally map (``{"A": 2, "B": 1}``), or a per-agent vote map
    (``{"agent_1": "A", "agent_2": "B"}``). The plugin calls this without a
    try/except wrapper, so a dict must not raise ``AttributeError`` on
    ``.count()``. Dicts are disambiguated by whether ``winner`` is a key
    (tally map) or a value (per-agent map). Returns 0.0 on missing/empty.
    """
    if not results or "votes" not in results or "winner" not in results:
        return 0.0
    votes = results["votes"]
    winner = results["winner"]
    if not votes or winner is None:
        return 0.0

    def _tally(value: Any) -> float:
        # Normalize a tally entry to a scalar vote count: a number stays,
        # a (pos, neg)/list sums its numeric items, anything else is 0.
        if isinstance(value, (list, tuple)):
            return float(sum(v for v in value if isinstance(v, (int, float))))
        return float(value) if isinstance(value, (int, float)) else 0.0

    if isinstance(votes, dict):
        if winner in votes:
            # Per-option tally map {option: count}: winner's share of total.
            total = sum(_tally(v) for v in votes.values())
            return _tally(votes.get(winner, 0)) / total if total else 0.0
        # Per-agent vote map {agent: choice}: fraction of agents who picked
        # the winner.
        return sum(1 for v in votes.values() if v == winner) / len(votes)
    return votes.count(winner) / len(votes)


def gini(array):
    """Calculate the Gini coefficient of an array."""
    array = np.array(array, dtype=float)
    if array.size == 0:
        return 0.0
    if np.amin(array) < 0:
        array -= np.amin(array)
    array += 1e-8
    array = np.sort(array)
    n = array.shape[0]
    index = np.arange(1, n + 1)
    return float((np.sum((2 * index - n - 1) * array)) / (n * np.sum(array)))


def fairness_index(results):
    """1 - Gini coefficient of satisfaction (higher is fairer)."""
    if not results or "satisfaction" not in results:
        return 0.0
    return 1 - gini(np.array(results["satisfaction"]))


def efficiency(results, max_rounds=3):
    """Normalized efficiency: 1 - (rounds-1)/(max_rounds-1)."""
    if not results:
        return 0
    rounds = results.get("rounds", 1)
    if max_rounds <= 1:
        return 1.0
    value = 1 - (rounds - 1) / (max_rounds - 1)
    return max(0.0, min(1.0, value))


def satisfaction(results):
    """Mean agent satisfaction."""
    if not results or "satisfaction" not in results:
        return 0.0
    return float(np.mean(results["satisfaction"]))


def stability(results_list):
    """Fraction of runs with the same winner (1=stable, 0=unstable)."""
    if not results_list:
        return 0.0
    winners = [r["winner"] for r in results_list if "winner" in r]
    return int(len(set(winners)) == 1) if winners else 0.0


# per_agent_satisfaction was withdrawn (#2137): zero callers in the repo.


def summarize_results(results):
    """Summarize results for a single run or batch (list of runs)."""
    if isinstance(results, list):
        return {
            "consensus_rate": float(np.mean([consensus_rate(r) for r in results])),
            "fairness": float(np.mean([fairness_index(r) for r in results])),
            "efficiency": float(np.mean([efficiency(r) for r in results])),
            "satisfaction": float(np.mean([satisfaction(r) for r in results])),
            "stability": stability(results),
        }
    else:
        return {
            "consensus_rate": consensus_rate(results),
            "fairness": fairness_index(results),
            "efficiency": efficiency(results),
            "satisfaction": satisfaction(results),
        }


# validate_scenario was withdrawn (#2137): zero callers in the repo — its only
# consumers were simulation.py (withdrawn with it) and its own tests.
