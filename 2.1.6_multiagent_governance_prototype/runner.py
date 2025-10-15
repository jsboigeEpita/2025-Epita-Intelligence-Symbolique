import pandas as pd
from agents.agent_factory import AgentFactory
from governance.methods import GOVERNANCE_METHODS
from scenarios.loader import load_scenario
from metrics.metrics import summarize_results
import numpy as np
import json


def run_simulation(agents, scenario_data, method):
    # Placeholder: import actual simulation logic
    from governance.simulation import simulate_governance

    return simulate_governance(agents, scenario_data, method)


def batch_run(config_path, n_runs=100, method=None, output_csv="results.csv"):
    with open(config_path) as f:
        scenario_data = json.load(f)
    all_results = []
    for i in range(n_runs):
        agents = AgentFactory.create_agents(scenario_data["agents"], seed=i)
        m = method or scenario_data.get("default_method", "majority")
        results = run_simulation(agents, scenario_data, m)
        summary = summarize_results(results)
        summary["run"] = i
        summary["method"] = m
        all_results.append(summary)
    df = pd.DataFrame(all_results)
    df.to_csv(output_csv, index=False)
    print(f"Batch results saved to {output_csv}")
    print(df.groupby("method").mean(numeric_only=True))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Batch experiment runner")
    parser.add_argument("--config", required=True, help="Scenario config JSON")
    parser.add_argument("--n_runs", type=int, default=100, help="Number of runs")
    parser.add_argument("--method", default=None, help="Governance method")
    parser.add_argument("--output_csv", default="results.csv", help="CSV output file")
    args = parser.parse_args()
    batch_run(args.config, args.n_runs, args.method, args.output_csv)
