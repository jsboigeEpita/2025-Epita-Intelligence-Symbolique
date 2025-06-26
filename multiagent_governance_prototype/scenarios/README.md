# Scenarios for Multiagent Governance Prototype

This directory contains example scenarios for benchmarking and comparing governance methods. Each scenario is a JSON file specifying agents, their personalities and preferences, available options, and optional context fields for advanced features.

## How to Add a Scenario
- Create a new JSON file in this directory.
- Specify the list of agents, their personalities, preferences, and the available options.
- Optionally, add a `context` field to describe the scenario, add extra parameters, or enable advanced features.
- Add a short description to this README.

## Advanced Scenario Features

### 1. **Adjacency Matrix (Networked Simulation)**
- Add an `adjacency` field in `context` to specify the agent communication network.
- Example (3 agents, A can talk to B and C, B can talk to A, C can talk to A):
  ```json
  "context": {
    "adjacency": [[0,1,1],[1,0,0],[1,0,0]]
  }
  ```
- If present, distributed consensus (gossip protocol) is used.

### 2. **Coalitions**
- Agents can form coalitions dynamically based on trust, but you can also predefine coalitions by setting the `coalition` field for each agent (optional, for custom experiments).

### 3. **Manipulability/Noise**
- You can design scenarios to test manipulability by setting up polarized groups, bribery targets, or agents with random personalities.
- Use the CLI's `manipulability-analysis` command to run systematic tests.

### 4. **Context Field**
- The `context` field can include any extra parameters needed for your experiment (e.g., `quadratic_budget`, `byzantine_ratio`, etc).

## Scenario Validation and Best Practices
- Ensure all agents have unique names.
- All options referenced in agent preferences must be present in the scenario's `options` list.
- If using an adjacency matrix, it must be square and match the number of agents.
- Use the scenario generator CLI for quick, valid scenario creation.
- Add a clear `description` in the `context` for documentation.

## Included Scenarios

| File | Description | Network | Coalition | Manipulability/Noise | Custom Context |
|------|-------------|---------|-----------|----------------------|---------------|
| `example_scenario.json` | 5 agents, 3 options, mixed personalities. Resource allocation. Now includes BDI and Reactive agent types. |   |   |   |   |
| `polarized_two_groups.json` | 8 agents, 2 polarized groups, 2 options. Simulates a political vote. |   |   |   |   |
| `all_stubborn.json` | 6 agents, all stubborn, 3 options. Deadlock likely. |   |   |   |   |
| `all_flexible.json` | 6 agents, all flexible, 3 options. Rapid consensus. |   |   |   |   |
| `random_personalities.json` | 10 agents, random personalities, 4 options. High diversity. |   |   |   |   |
| `large_committee.json` | 20 agents, 5 options, mixed personalities. Simulates a large committee. |   |   |   |   |
| `coalition_scenario.json` | 9 agents, 3 natural coalitions, 3 options. Coalition dynamics. |   | ✔ |   |   |
| `project_funding.json` | 7 agents, 4 options, preferences based on project impact. Real-world funding. |   |   |   |   |
| `single_dissenter.json` | 5 agents, 4 agree, 1 stubborn dissenter. Tests consensus robustness. |   |   |   |   |
| `resource_division.json` | 12 agents, 3 options, preferences based on resource needs. Fairness test. |   |   |   |   |
| `strategic_majority.json` | 7 agents, majority are strategic, 3 options. Tests tactical voting. |   |   |   |   |
| `network_ring.json` | 6 agents in a ring network, mixed personalities, 3 options. | ✔ |   |   |   |
| `coalition_explicit.json` | 8 agents, 2 explicit coalitions, 3 options. |   | ✔ |   |   |
| `manipulability_test.json` | 10 agents, polarized, random personalities, 3 options. |   |   | ✔ |   |
| `custom_context.json` | 7 agents, 3 options, custom quadratic voting budget. |   |   |   | ✔ |

See each scenario's JSON file for full details. 