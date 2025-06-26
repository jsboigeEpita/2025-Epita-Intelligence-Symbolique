# Multiagent Governance Prototype

## Overview

This project is a showcaseable, interactive, and extensible prototype for benchmarking and comparing different multiagent governance methods. It supports advanced features such as negotiation, learning, coalition formation, networked/distributed simulation, manipulability analysis, and advanced visualization. The platform is designed for research, teaching, and experimentation in multiagent systems and social choice.

## Features
- **Multiple Governance Methods:** Plurality, Borda, Condorcet, Quadratic Voting, Majority, Byzantine Consensus, Raft, and more.
- **Agent Diversity:** Agents have different personalities (stubborn, flexible, strategic, random), trust, learning (Q-learning), negotiation, and coalition logic.
- **Dynamic Scenarios:** Randomized or user-defined decision problems, agent populations, and communication networks.
- **Coalition Formation:** Agents can form, join, or leave coalitions based on trust and negotiation.
- **Networked/Distributed Simulation:** Agents communicate and reach consensus only with their neighbors in a user-specified network (adjacency matrix).
- **Manipulability Analysis:** Systematic testing of strategic voting, false coalitions, bribery, and noise/misinformation robustness.
- **Interactive CLI:** Configure experiments, generate scenarios, run batch comparisons, analyze manipulability, and visualize results step-by-step.
- **Advanced Visualization:** Bar charts, satisfaction histograms, consensus evolution, network/coalition graphs, and manipulability impact plots.
- **Extensible:** Easily add new governance methods, agent types, metrics, or scenario features.
- **Batch Testing:** Run many simulations for robust benchmarking, with CSV/Markdown export.

## Architecture
- `agents/` — Agent models, personalities, and strategies
- `governance/` — Governance protocols and consensus mechanisms
- `metrics/` — Evaluation metrics and reporting tools
- `scenarios/` — Scenario definitions and generators
- `cli.py` — Interactive command-line interface
- `runner.py` — Batch experiment runner
- `reporting/` — Automated report and visualization generation

## Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   # For advanced visualization (network/coalition graphs):
   pip install networkx
   ```

## Usage

### 1. **List Available Methods and Scenarios**
```bash
python cli.py list-methods
python cli.py list-scenarios-cmd
```

### 2. **Run a Simulation**
```bash
python cli.py run --scenario scenarios/example_scenario.json --method majority
# Or interactively (no arguments)
python cli.py run
```

### 3. **Generate a Scenario**
```bash
python cli.py generate-scenario
# Follow prompts for number of agents, options, personalities, etc.
```

### 4. **Batch Comparison (All Methods, All Scenarios)**
```bash
python cli.py compare-all
# Results saved to comparison_results.csv and comparison_results.md
```

### 5. **Manipulability Analysis**
```bash
python cli.py manipulability-analysis --scenario scenarios/example_scenario.json --method majority
# See impact of manipulation/noise on consensus, fairness, satisfaction
```

### 6. **Visualize Results**
- Plots are shown automatically after each run.
- For network/coalition graphs or manipulability impact, use:
```python
from reporting.visualize import plot_network, plot_coalitions, plot_manipulability_impact
# See reporting/visualize.py for usage
```

## Scenario Format

Each scenario is a JSON file with the following structure:
```json
{
  "agents": [
    {"name": "Alice", "personality": "stubborn", "preferences": ["A", "B", "C"], "options": ["A", "B", "C"]},
    ...
  ],
  "options": ["A", "B", "C"],
  "context": {
    "description": "Resource allocation among three projects.",
    "adjacency": [[0,1,1],[1,0,0],[1,0,0]]  // Optional: communication network
  }
}
```
- **adjacency**: (optional) adjacency matrix for agent communication network. If present, distributed consensus is used.
- **context**: (optional) can include any extra parameters for advanced features.

## How to Extend
- **Add new agent types:** Implement in `agents/base_agent.py` and update `agent_factory.py`.
- **Add new governance methods:** Implement in `governance/methods.py` and register in `GOVERNANCE_METHODS`.
- **Add new metrics:** Implement in `metrics/metrics.py`.
- **Add new scenario features:** Update scenario JSON and loader as needed.
- **Add new CLI commands:** Extend `cli.py`.

## Dependencies
- numpy
- scipy
- pandas
- matplotlib
- seaborn
- rich
- click
- networkx (optional, for advanced visualization)

## Example Output

**Simulation Table:**
```
+----------------+---------+
| Metric         | Value   |
+----------------+---------+
| consensus_rate | 0.800   |
| fairness       | 0.950   |
| efficiency     | 1       |
| satisfaction   | 0.750   |
+----------------+---------+
```

**Example Plot:**
![Example Plot](example_plot.png)

**Network Graph:**
![Network Graph](network_graph.png)

## License
MIT 

## New Agent Types
- **BDI Agent:** Implements Belief-Desire-Intention logic. Maintains beliefs, desires, intentions, and can update them. Supports protocol stubs for message passing.
- **Reactive Agent:** Implements rule-based responses to context. Supports protocol stubs for message passing.

## Protocol Layer
- Agents (including BDI and Reactive) have stubs for FIPA-ACL-like message passing (send_message, receive_message).

## Conflict Resolution System
- Integrated collaborative, competitive, and compromise mediation strategies. Conflicts are detected and resolved during simulation, and results are logged.

## Feature Mapping to Subject
| Subject Requirement | Implementation |
|---------------------|----------------|
| BDI/Reactive Agents | `BDIAgent`, `ReactiveAgent` classes, selectable in scenarios |
| Protocol Layer      | `send_message`, `receive_message` stubs in all agent types |
| Conflict Resolution | `conflict_resolution.py` with mediation strategies, integrated in simulation |
| End-to-End Pipeline | CLI and simulation pipeline: agent creation, scenario, conflict detection/resolution, consensus, metrics |
| Metrics             | `metrics/metrics.py` and CLI reporting |
| Scenario Diversity  | Rich scenarios in `scenarios/` |
| Extensibility       | Modular design, easy to add new methods, agents, metrics | 