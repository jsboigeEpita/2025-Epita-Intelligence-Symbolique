"""
Governance voting methods — 7 algorithms for collective decision-making.

Methods: majority, plurality, borda, condorcet, quadratic, byzantine, raft.
All functions share the signature ``(agents, options, context) -> winner``.

Adapted from 2.1.6_multiagent_governance_prototype/governance/methods.py.
"""

from collections import Counter

import numpy as np


def majority_voting(agents, options, context):
    """Each agent votes for top choice; most voted option wins."""
    votes = [a.decide(options, context) for a in agents]
    tally = Counter(votes)
    winner, _ = tally.most_common(1)[0]
    return winner


def plurality_voting(agents, options, context):
    """Alias for majority voting (single-winner)."""
    return majority_voting(agents, options, context)


def borda_count(agents, options, context):
    """Preference-based scoring: n-1 for top, n-2 for second, etc."""
    scores = {o: 0 for o in options}
    n = len(options)
    for a in agents:
        for i, o in enumerate(a.preferences):
            if o in scores:
                scores[o] += n - i - 1
    winner = max(scores, key=scores.get)
    return winner


def condorcet_method(agents, options, context):
    """Pairwise comparison; Condorcet winner or Borda fallback."""
    n = len(options)
    pairwise_wins = {o: 0 for o in options}
    for o1 in options:
        for o2 in options:
            if o1 == o2:
                continue
            o1_wins = sum(
                a.preferences.index(o1) < a.preferences.index(o2)
                for a in agents
                if o1 in a.preferences and o2 in a.preferences
            )
            o2_wins = len(agents) - o1_wins
            if o1_wins > o2_wins:
                pairwise_wins[o1] += 1
    for o in options:
        if pairwise_wins[o] == n - 1:
            return o
    return borda_count(agents, options, context)


def quadratic_voting(agents, options, context):
    """Budget-based quadratic voting with rational allocation."""
    budget = context.get("quadratic_budget", 9) if context else 9
    votes = {o: 0 for o in options}
    for a in agents:
        allocation = [0] * len(options)
        top_pref = a.preferences[0] if a.preferences else options[0]
        if a.personality == "flexible" and len(options) > 1:
            top_idx = options.index(top_pref) if top_pref in options else 0
            second_pref = a.preferences[1] if len(a.preferences) > 1 else options[0]
            second_idx = options.index(second_pref) if second_pref in options else 0
            allocation[top_idx] = budget // 2
            allocation[second_idx] = budget - (budget // 2)
        else:
            top_idx = options.index(top_pref) if top_pref in options else 0
            allocation[top_idx] = budget
        for i, o in enumerate(options):
            votes[o] += allocation[i]
    winner = max(votes, key=votes.get)
    return winner


def byzantine_consensus(agents, options, context):
    """Simulates faulty agents (random votes) + honest majority."""
    byzantine_ratio = context.get("byzantine_ratio", 0.2) if context else 0.2
    n_byzantine = int(len(agents) * byzantine_ratio)
    honest_agents = agents[n_byzantine:]
    votes = [a.decide(options, context) for a in honest_agents]
    votes += [np.random.choice(options) for _ in range(n_byzantine)]
    tally = Counter(votes)
    winner, _ = tally.most_common(1)[0]
    return winner


def raft_consensus(agents, options, context):
    """Leader election + proposal; majority acceptance or fallback."""
    leader = np.random.choice(agents)
    proposal = leader.decide(options, context)
    acceptances = 1
    for a in agents:
        if a is leader:
            continue
        if proposal in a.preferences[:2]:
            acceptances += 1
    if acceptances > len(agents) // 2:
        return proposal
    else:
        return majority_voting(agents, options, context)


GOVERNANCE_METHODS = {
    "majority": majority_voting,
    "plurality": plurality_voting,
    "borda": borda_count,
    "condorcet": condorcet_method,
    "quadratic": quadratic_voting,
    "byzantine": byzantine_consensus,
    "raft": raft_consensus,
}
