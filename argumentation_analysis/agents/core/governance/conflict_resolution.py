"""
Conflict detection and mediation strategies for governance simulation.

Adapted from 2.1.6_multiagent_governance_prototype/governance/conflict_resolution.py.
"""


def detect_conflicts(agent_positions):
    """Detect conflicts between agent positions.

    Returns list of conflict dicts with 'agents' and 'conflict_level'.
    """
    conflicts = []
    agents = list(agent_positions.keys())
    for i in range(len(agents)):
        for j in range(i + 1, len(agents)):
            a1, a2 = agents[i], agents[j]
            pos1, pos2 = agent_positions[a1], agent_positions[a2]
            conflict_level = 1.0 if pos1 != pos2 else 0.0
            if conflict_level > 0.0:
                conflicts.append({"agents": [a1, a2], "conflict_level": conflict_level})
    return conflicts


def resolve_conflict(conflict, strategy="collaborative"):
    """Resolve a conflict using the specified mediation strategy."""
    if strategy == "collaborative":
        return collaborative_mediation(conflict)
    elif strategy == "competitive":
        return competitive_mediation(conflict)
    elif strategy == "compromise":
        return compromise_mediation(conflict)
    else:
        return collaborative_mediation(conflict)


def collaborative_mediation(conflict):
    return {
        "resolution_type": "collaborative",
        "success_probability": 0.8,
        "agents": conflict["agents"],
        "details": "Agents seek common ground.",
    }


def competitive_mediation(conflict):
    return {
        "resolution_type": "competitive",
        "success_probability": 0.5,
        "agents": conflict["agents"],
        "details": "Agents compete for their preferred outcome.",
    }


def compromise_mediation(conflict):
    return {
        "resolution_type": "compromise",
        "success_probability": 0.7,
        "agents": conflict["agents"],
        "details": "Agents agree to a middle ground.",
    }
