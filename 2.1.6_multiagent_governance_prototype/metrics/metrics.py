import numpy as np

def consensus_rate(results):
    """
    Fraction of agents voting for the winner.
    """
    if not results or 'votes' not in results or 'winner' not in results:
        return 0.0
    votes = results['votes']
    winner = results['winner']
    if not votes or winner is None:
        return 0.0
    return votes.count(winner) / len(votes)

def gini(array):
    """
    Calculate the Gini coefficient of a numpy array.
    """
    array = np.array(array)
    if array.size == 0:
        return 0.0
    if np.amin(array) < 0:
        array -= np.amin(array)
    array += 1e-8  # Avoid division by zero
    array = np.sort(array)
    n = array.shape[0]
    index = np.arange(1, n+1)
    return (np.sum((2 * index - n - 1) * array)) / (n * np.sum(array))

def fairness_index(results):
    """
    1 - Gini coefficient of satisfaction (higher is fairer).
    """
    if not results or 'satisfaction' not in results:
        return 0.0
    return 1 - gini(np.array(results['satisfaction']))

def efficiency(results, max_rounds=3):
    """
    Efficiency normalized: 1 - (rounds-1)/(max_rounds-1), always in [0, 1].
    """
    if not results:
        return 0
    rounds = results.get('rounds', 1)
    if max_rounds <= 1:
        return 1.0
    value = 1 - (rounds - 1) / (max_rounds - 1)
    return max(0.0, min(1.0, value))

def satisfaction(results):
    """
    Mean agent satisfaction (how close outcome is to each agent's top preference).
    """
    if not results or 'satisfaction' not in results:
        return 0.0
    return float(np.mean(results['satisfaction']))

def stability(results_list):
    """
    Fraction of runs with the same winner (1=stable, 0=unstable).
    """
    if not results_list:
        return 0.0
    winners = [r['winner'] for r in results_list if 'winner' in r]
    return int(len(set(winners)) == 1) if winners else 0.0

def per_agent_satisfaction(results):
    """
    Returns a dict of agent_name: satisfaction for the run.
    """
    if not results or 'agent_names' not in results or 'satisfaction' not in results:
        return {}
    return dict(zip(results['agent_names'], results['satisfaction']))

def summarize_results(results):
    """
    Summarize results for a single run or a batch (list of runs).
    """
    if isinstance(results, list):
        return {
            'consensus_rate': np.mean([consensus_rate(r) for r in results]),
            'fairness': np.mean([fairness_index(r) for r in results]),
            'efficiency': np.mean([efficiency(r) for r in results]),
            'satisfaction': np.mean([satisfaction(r) for r in results]),
            'stability': stability(results),
        }
    else:
        return {
            'consensus_rate': consensus_rate(results),
            'fairness': fairness_index(results),
            'efficiency': efficiency(results),
            'satisfaction': satisfaction(results),
        }

def validate_scenario(scenario):
    """
    Validate a scenario dict for completeness and correctness.
    Returns (is_valid, error_message)
    """
    if not scenario or 'agents' not in scenario or 'options' not in scenario:
        return False, 'Missing agents or options.'
    agent_names = set()
    for agent in scenario['agents']:
        if 'name' not in agent or 'preferences' not in agent or 'options' not in agent:
            return False, f"Agent missing required fields: {agent}"
        if agent['name'] in agent_names:
            return False, f"Duplicate agent name: {agent['name']}"
        agent_names.add(agent['name'])
        for opt in agent['preferences']:
            if opt not in scenario['options']:
                return False, f"Agent {agent['name']} has invalid preference: {opt}"
    context = scenario.get('context', {})
    if 'adjacency' in context:
        adj = context['adjacency']
        n = len(scenario['agents'])
        if not (isinstance(adj, list) and all(isinstance(row, list) and len(row) == n for row in adj) and len(adj) == n):
            return False, 'Adjacency matrix must be square and match number of agents.'
    return True, '' 