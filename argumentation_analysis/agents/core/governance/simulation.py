"""
Governance simulation — coalition formation, Shapley values, gossip consensus,
and manipulability analysis.

Adapted from 2.1.6_multiagent_governance_prototype/governance/simulation.py.
"""

import math
from collections import defaultdict
from itertools import permutations

import numpy as np

from . import conflict_resolution
from .governance_methods import GOVERNANCE_METHODS


def shapley_value(coalition, all_agents, payoff_func):
    """Compute Shapley value for each agent in a coalition."""
    n = len(coalition)
    if n == 0:
        return {}
    values = {a.name: 0.0 for a in coalition}
    agents_list = list(coalition)
    for perm in permutations(agents_list):
        prev = set()
        for agent in perm:
            prev_set = set(a.name for a in prev)
            with_agent = prev_set | {agent.name}
            without_agent = prev_set
            marginal = payoff_func(with_agent) - payoff_func(without_agent)
            values[agent.name] += marginal / math.factorial(n)
            prev.add(agent)
    return values


def get_neighbors(agent, agents, adjacency):
    """Get neighbors of an agent based on adjacency matrix."""
    idx = [a.name for a in agents].index(agent.name)
    return [
        agents[j]
        for j, connected in enumerate(adjacency[idx])
        if connected and j != idx
    ]


def distributed_gossip_consensus(agents, options, adjacency, rounds=5):
    """Distributed consensus using gossip: share votes with neighbors,
    update to local majority over multiple rounds."""
    votes = {a.name: a.decide(options) for a in agents}
    for _ in range(rounds):
        new_votes = votes.copy()
        for a in agents:
            neighbors = get_neighbors(a, agents, adjacency)
            neighbor_votes = [votes[n.name] for n in neighbors]
            all_votes = neighbor_votes + [votes[a.name]]
            counts = defaultdict(int)
            for v in all_votes:
                counts[v] += 1
            new_votes[a.name] = max(counts, key=counts.get)
        votes = new_votes
    final_counts = defaultdict(int)
    for v in votes.values():
        final_counts[v] += 1
    winner = max(final_counts, key=final_counts.get)
    return winner, votes


def simulate_governance(agents, scenario_data, method):
    """Run governance method with optional distributed gossip consensus.

    If scenario context includes 'adjacency', uses distributed gossip.
    Otherwise, uses coalition-based simulation with Shapley values.
    """
    options = scenario_data["options"]
    context = scenario_data.get("context", {})
    adjacency = context.get("adjacency", None)

    if adjacency:
        winner, agent_votes = distributed_gossip_consensus(agents, options, adjacency)
        votes = [agent_votes[a.name] for a in agents]
        satisfaction = [
            (
                1.0 - a.preferences.index(winner) / max(1, len(a.preferences) - 1)
                if winner in a.preferences
                else 0
            )
            for a in agents
        ]
        for a, v in zip(agents, votes):
            a.update_memory(v, winner, context)
        return {
            "votes": votes,
            "winner": winner,
            "satisfaction": satisfaction,
            "options": options,
            "agent_names": [a.name for a in agents],
            "networked": True,
            "adjacency": adjacency,
            "rounds": 5,
            "history": [],
            "conflicts": [],
            "resolved_conflicts": [],
        }

    # Coalition-based simulation
    coalitions = []
    unassigned = set(range(len(agents)))
    while unassigned:
        idx = unassigned.pop()
        agent = agents[idx]
        partner_idxs = [
            i for i in unassigned if agent.trust.get(agents[i].name, 0) > 0.8
        ]
        if partner_idxs:
            coalition = [agents[idx]] + [agents[i] for i in partner_idxs]
            for i in partner_idxs:
                unassigned.discard(i)
            for a in coalition:
                a.coalition = f"coalition_{len(coalitions)+1}"
            coalitions.append(coalition)
        else:
            agent.coalition = f"coalition_{len(coalitions)+1}"
            coalitions.append([agent])

    # Coalition voting
    coalition_votes = {}
    for coalition in coalitions:
        leader = coalition[0]
        coalition_votes[leader.coalition] = leader.preferences[0]

    bloc_votes = list(coalition_votes.values())
    tally = defaultdict(int)
    for v in bloc_votes:
        tally[v] += 1
    winner = max(tally, key=tally.get)

    def payoff_func(agent_names):
        return sum(
            1.0 for a in agents if a.name in agent_names and winner == a.preferences[0]
        )

    coalition_payoffs = {}
    for coalition in coalitions:
        sv = shapley_value(coalition, agents, payoff_func)
        for a in coalition:
            coalition_payoffs[a.name] = sv[a.name]

    votes = [a.decide(options, context) for a in agents]
    satisfaction = [
        (
            1.0 - a.preferences.index(winner) / max(1, len(a.preferences) - 1)
            if winner in a.preferences
            else 0
        )
        for a in agents
    ]
    for a, v in zip(agents, votes):
        a.update_memory(v, winner, context)

    positions = {a.name: a.decide(options, context) for a in agents}
    conflicts = conflict_resolution.detect_conflicts(positions)
    resolved_conflicts = []
    if conflicts:
        for conflict in conflicts:
            resolution = conflict_resolution.resolve_conflict(
                conflict,
                strategy=context.get("mediation_strategy", "collaborative"),
            )
            resolved_conflicts.append(resolution)

    return {
        "votes": votes,
        "winner": winner,
        "satisfaction": satisfaction,
        "options": options,
        "agent_names": [a.name for a in agents],
        "coalitions": [[a.name for a in c] for c in coalitions],
        "coalition_payoffs": coalition_payoffs,
        "rounds": 1,
        "history": [],
        "conflicts": conflicts,
        "resolved_conflicts": resolved_conflicts,
    }


def simulate_manipulation(
    agents,
    scenario_data,
    method,
    manipulation_type="strategic",
    noise_level=0.0,
    bribery_budget=0,
):
    """Simulate governance under manipulation (strategic, coalition, bribery, noise)."""
    options = scenario_data["options"]
    agents_copy = list(agents)

    if manipulation_type == "strategic":
        for a in agents_copy:
            if len(a.preferences) > 1:
                a.decide = lambda opts, ctx=None, a=a: a.preferences[1]
    if manipulation_type == "false_coalition":
        target = options[0]
        for a in agents_copy[: len(agents_copy) // 2]:
            a.coalition = "false_coalition"
            a.decide = lambda opts, ctx=None, t=target: t
    if manipulation_type == "bribery" and bribery_budget > 0:
        target = options[-1]
        bribed = np.random.choice(
            agents_copy, min(bribery_budget, len(agents_copy)), replace=False
        )
        for a in bribed:
            a.decide = lambda opts, ctx=None, t=target: t
    if manipulation_type == "noise" and noise_level > 0.0:
        for a in agents_copy:
            orig_decide = a.decide
            a.decide = lambda opts, ctx=None, od=orig_decide: (
                od(opts, ctx)
                if np.random.rand() > noise_level
                else np.random.choice(opts)
            )

    result = simulate_governance(agents_copy, scenario_data, method)
    result["manipulation_type"] = manipulation_type
    result["noise_level"] = noise_level
    result["bribery_budget"] = bribery_budget
    return result


def manipulability_analysis(agents, scenario_data, method):
    """Run a suite of manipulation scenarios and report impact."""
    results = []
    baseline = simulate_governance(agents, scenario_data, method)
    baseline["manipulation_type"] = "none"
    results.append(baseline)
    results.append(simulate_manipulation(agents, scenario_data, method, "strategic"))
    results.append(
        simulate_manipulation(agents, scenario_data, method, "false_coalition")
    )
    results.append(
        simulate_manipulation(
            agents, scenario_data, method, "bribery", bribery_budget=1
        )
    )
    results.append(
        simulate_manipulation(
            agents, scenario_data, method, "bribery", bribery_budget=2
        )
    )
    results.append(
        simulate_manipulation(agents, scenario_data, method, "noise", noise_level=0.1)
    )
    results.append(
        simulate_manipulation(agents, scenario_data, method, "noise", noise_level=0.3)
    )
    return results
