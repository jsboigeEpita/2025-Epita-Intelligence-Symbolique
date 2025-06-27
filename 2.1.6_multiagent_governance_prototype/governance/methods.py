from collections import Counter, defaultdict
import numpy as np

# --- Majority Voting ---
def majority_voting(agents, options, context):
    """
    Each agent votes for their top choice. Option with most votes wins.
    """
    votes = [a.decide(options, context) for a in agents]
    tally = Counter(votes)
    winner, _ = tally.most_common(1)[0]
    return winner

# --- Plurality Voting (same as majority for single-winner) ---
def plurality_voting(agents, options, context):
    return majority_voting(agents, options, context)

# --- Borda Count ---
def borda_count(agents, options, context):
    """
    Each agent ranks options. Points assigned: n-1 for top, n-2 for second, ...
    Option with highest total points wins.
    """
    scores = {o: 0 for o in options}
    n = len(options)
    for a in agents:
        for i, o in enumerate(a.preferences):
            if o in scores:
                scores[o] += n - i - 1
    winner = max(scores, key=scores.get)
    return winner

# --- Condorcet Method ---
def condorcet_method(agents, options, context):
    """
    Pairwise compare all options. Option that beats all others in head-to-head is the Condorcet winner.
    If no Condorcet winner, fallback to Borda.
    """
    n = len(options)
    pairwise_wins = {o: 0 for o in options}
    for i, o1 in enumerate(options):
        for o2 in options:
            if o1 == o2:
                continue
            o1_wins = sum(a.preferences.index(o1) < a.preferences.index(o2) for a in agents)
            o2_wins = len(agents) - o1_wins
            if o1_wins > o2_wins:
                pairwise_wins[o1] += 1
    # Condorcet winner must win against all others
    for o in options:
        if pairwise_wins[o] == n - 1:
            return o
    # No Condorcet winner, fallback to Borda
    return borda_count(agents, options, context)

# --- Quadratic Voting ---
def quadratic_voting(agents, options, context):
    """
    Each agent has a fixed budget (e.g., 9 credits). They allocate votes to options.
    Cost per option: sum of squares of votes per option. Winner is option with most votes.
    Agents allocate votes to maximize their satisfaction (simulate rational allocation).
    """
    budget = context.get('quadratic_budget', 9) if context else 9
    votes = {o: 0 for o in options}
    for a in agents:
        # Rational: allocate all to top preference, or split if two top
        allocation = [0] * len(options)
        if a.personality == 'flexible' and len(options) > 1:
            # Split between top 2
            allocation[a.preferences.index(options[0])] = budget // 2
            allocation[a.preferences.index(options[1])] = budget - (budget // 2)
        else:
            allocation[a.preferences.index(a.preferences[0])] = budget
        for i, o in enumerate(options):
            votes[o] += allocation[i]
    winner = max(votes, key=votes.get)
    return winner

# --- Byzantine Consensus ---
def byzantine_consensus(agents, options, context):
    """
    Simulate a fraction of agents as faulty (random votes), rest use majority.
    """
    byzantine_ratio = context.get('byzantine_ratio', 0.2) if context else 0.2
    n_byzantine = int(len(agents) * byzantine_ratio)
    honest_agents = agents[n_byzantine:]
    byzantine_agents = agents[:n_byzantine]
    votes = [a.decide(options, context) for a in honest_agents]
    votes += [np.random.choice(options) for _ in byzantine_agents]
    tally = Counter(votes)
    winner, _ = tally.most_common(1)[0]
    return winner

# --- Raft Consensus ---
def raft_consensus(agents, options, context):
    """
    Simulate leader election (random leader). Leader proposes, others accept/reject. Majority acceptance required.
    """
    leader = np.random.choice(agents)
    proposal = leader.decide(options, context)
    acceptances = 1  # leader always accepts own proposal
    for a in agents:
        if a is leader:
            continue
        # Accept if proposal is in top 2 preferences
        if proposal in a.preferences[:2]:
            acceptances += 1
    if acceptances > len(agents) // 2:
        return proposal
    else:
        # If not accepted, fallback to majority
        return majority_voting(agents, options, context)

GOVERNANCE_METHODS = {
    'majority': majority_voting,
    'plurality': plurality_voting,
    'borda': borda_count,
    'condorcet': condorcet_method,
    'quadratic': quadratic_voting,
    'byzantine': byzantine_consensus,
    'raft': raft_consensus,
} 