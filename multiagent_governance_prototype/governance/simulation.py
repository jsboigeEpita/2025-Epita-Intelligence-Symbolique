from .methods import GOVERNANCE_METHODS
import numpy as np
from collections import defaultdict
import math

def shapley_value(coalition, all_agents, payoff_func):
    """
    Compute Shapley value for each agent in a coalition.
    payoff_func: function that takes a set of agent names and returns the coalition's value.
    """
    from itertools import permutations
    n = len(coalition)
    if n == 0:
        return {}
    values = {a.name: 0.0 for a in coalition}
    agents_list = list(coalition)
    for perm in permutations(agents_list):
        prev = set()
        for i, agent in enumerate(perm):
            prev_set = set(a.name for a in prev)
            with_agent = prev_set | {agent.name}
            without_agent = prev_set
            marginal = payoff_func(with_agent) - payoff_func(without_agent)
            values[agent.name] += marginal / math.factorial(n)
            prev.add(agent)
    return values

def get_neighbors(agent, agents, adjacency):
    idx = [a.name for a in agents].index(agent.name)
    return [agents[j] for j, connected in enumerate(adjacency[idx]) if connected and j != idx]

def distributed_gossip_consensus(agents, options, adjacency, rounds=5):
    """
    Distributed consensus using gossip: each agent shares its vote with neighbors, updates to local majority.
    """
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
    """
    Run the governance method with support for networked/distributed simulation.
    If scenario context includes 'adjacency', use distributed consensus (gossip protocol).
    Otherwise, use coalition logic as before.
    """
    options = scenario_data['options']
    context = scenario_data.get('context', {})
    method_fn = GOVERNANCE_METHODS[method]
    adjacency = context.get('adjacency', None)
    if adjacency:
        winner, agent_votes = distributed_gossip_consensus(agents, options, adjacency)
        votes = [agent_votes[a.name] for a in agents]
        satisfaction = [1.0 - a.preferences.index(winner)/max(1, len(a.preferences)-1) if winner in a.preferences else 0 for a in agents]
        for a, v, s in zip(agents, votes, satisfaction):
            a.update_memory(v, winner, context)
        result = {
            'votes': votes,
            'winner': winner,
            'satisfaction': satisfaction,
            'options': options,
            'agent_names': [a.name for a in agents],
            'networked': True,
            'adjacency': adjacency,
            'rounds': 5,
            'history': []
        }
        return result
    max_rounds = 3 if method in ('condorcet', 'raft') else 1
    winner = None
    round_num = 0
    results_per_round = []
    coalitions = []
    unassigned = set(agents)
    while unassigned:
        agent = unassigned.pop()
        partners = [a for a in unassigned if agent.trust.get(a.name, 0) > 0.8]
        if partners:
            coalition = [agent] + partners
            for p in partners:
                unassigned.remove(p)
            for a in coalition:
                a.coalition = f"coalition_{len(coalitions)+1}"
            coalitions.append(coalition)
        else:
            agent.coalition = f"coalition_{len(coalitions)+1}"
            coalitions.append([agent])
    coalition_votes = {}
    for coalition in coalitions:
        leader = coalition[0]
        internal_votes = [a.decide(options, {'coalition_leader': leader.preferences[0]}) for a in coalition]
        coalition_votes[coalition[0].coalition] = leader.preferences[0]
    bloc_votes = list(coalition_votes.values())
    tally = defaultdict(int)
    for v in bloc_votes:
        tally[v] += 1
    winner = max(tally, key=tally.get)
    def payoff_func(agent_names):
        return sum(1.0 for a in agents if a.name in agent_names and winner == a.preferences[0])
    coalition_payoffs = {}
    for coalition in coalitions:
        sv = shapley_value(coalition, agents, payoff_func)
        for a in coalition:
            coalition_payoffs[a.name] = sv[a.name]
    votes = [a.decide(options, context) for a in agents]
    satisfaction = [1.0 - a.preferences.index(winner)/max(1, len(a.preferences)-1) if winner in a.preferences else 0 for a in agents]
    for a, v, s in zip(agents, votes, satisfaction):
        a.update_memory(v, winner, context)
    result = {
        'votes': votes,
        'winner': winner,
        'satisfaction': satisfaction,
        'options': options,
        'agent_names': [a.name for a in agents],
        'coalitions': [[a.name for a in c] for c in coalitions],
        'coalition_payoffs': coalition_payoffs,
        'rounds': 1,
        'history': []
    }
    return result

def simulate_manipulation(agents, scenario_data, method, manipulation_type='strategic', noise_level=0.0, bribery_budget=0):
    """
    Simulate governance with manipulation/noise:
    - manipulation_type: 'strategic', 'false_coalition', 'bribery', 'noise'
    - noise_level: probability of randomizing an agent's vote
    - bribery_budget: number of agents that can be bribed to vote for a target
    Returns: result dict as in simulate_governance, plus manipulation info.
    """
    options = scenario_data['options']
    context = scenario_data.get('context', {}).copy()
    agents_copy = [a for a in agents]
    # Strategic manipulation: agents vote for 2nd or 3rd preference if it blocks a disliked option
    if manipulation_type == 'strategic':
        for a in agents_copy:
            if len(a.preferences) > 1:
                # If top preference is unlikely to win, vote for 2nd to block rival
                a.decide = lambda opts, ctx=None, a=a: a.preferences[1]
    # False coalition: agents form a coalition to block a target option
    if manipulation_type == 'false_coalition':
        target = options[0]
        for a in agents_copy[:len(agents_copy)//2]:
            a.coalition = 'false_coalition'
            a.decide = lambda opts, ctx=None, a=a: target
    # Bribery: bribe a subset of agents to vote for a target
    if manipulation_type == 'bribery' and bribery_budget > 0:
        target = options[-1]
        bribed = np.random.choice(agents_copy, bribery_budget, replace=False)
        for a in bribed:
            a.decide = lambda opts, ctx=None, a=a: target
    # Noise: with probability noise_level, randomize agent's vote
    if manipulation_type == 'noise' and noise_level > 0.0:
        for a in agents_copy:
            orig_decide = a.decide
            a.decide = lambda opts, ctx=None, orig_decide=orig_decide: orig_decide(opts, ctx) if np.random.rand() > noise_level else np.random.choice(opts)
    # Run normal simulation
    result = simulate_governance(agents_copy, scenario_data, method)
    result['manipulation_type'] = manipulation_type
    result['noise_level'] = noise_level
    result['bribery_budget'] = bribery_budget
    return result

# CLI-accessible entry point for manipulability analysis

def manipulability_analysis(agents, scenario_data, method):
    """
    Run a suite of manipulation/noise scenarios and report impact on metrics.
    Returns: list of result dicts for each manipulation type/level.
    """
    results = []
    # Baseline
    baseline = simulate_governance(agents, scenario_data, method)
    baseline['manipulation_type'] = 'none'
    results.append(baseline)
    # Strategic manipulation
    results.append(simulate_manipulation(agents, scenario_data, method, 'strategic'))
    # False coalition
    results.append(simulate_manipulation(agents, scenario_data, method, 'false_coalition'))
    # Bribery (bribe 1 and 2 agents)
    results.append(simulate_manipulation(agents, scenario_data, method, 'bribery', bribery_budget=1))
    results.append(simulate_manipulation(agents, scenario_data, method, 'bribery', bribery_budget=2))
    # Noise (10% and 30%)
    results.append(simulate_manipulation(agents, scenario_data, method, 'noise', noise_level=0.1))
    results.append(simulate_manipulation(agents, scenario_data, method, 'noise', noise_level=0.3))
    return results 