import click
from rich.console import Console
from rich.table import Table
from agents.agent_factory import AgentFactory
from governance.methods import GOVERNANCE_METHODS
from scenarios.loader import load_scenario, list_scenarios
from runner import run_simulation
from metrics.metrics import summarize_results, per_agent_satisfaction, validate_scenario
from reporting.visualize import (
    plot_results,
    plot_method_comparison,
    plot_manipulability_impact,
)
from governance.simulation import manipulability_analysis
import json
import os
import numpy as np
import pandas as pd

console = Console()


@click.group()
def cli():
    """Multiagent Governance Prototype CLI"""
    pass


@cli.command("list-methods")
def list_methods():
    """List available governance methods."""
    console.print("[bold cyan]Available governance methods:[/bold cyan]")
    for method in GOVERNANCE_METHODS:
        console.print(f"- [green]{method}[/green]")


@cli.command("list-scenarios-cmd")
def list_scenarios_cmd():
    """List available scenarios."""
    scenarios = list_scenarios()
    console.print("[bold cyan]Available scenarios:[/bold cyan]")
    for s in scenarios:
        console.print(f"- [yellow]{s}[/yellow]")


@cli.command("run")
@click.option("--scenario", default=None, help="Path to scenario JSON file")
@click.option("--method", default=None, help="Governance method to use")
def run(scenario, method):
    """Run a simulation with selected scenario and governance method."""
    try:
        if not scenario:
            scenarios = list_scenarios()
            console.print("[bold cyan]Select a scenario:[/bold cyan]")
            for i, s in enumerate(scenarios):
                console.print(f"{i+1}. [yellow]{s}[/yellow]")
            idx = int(console.input("Enter scenario number: ")) - 1
            scenario = f"scenarios/{scenarios[idx]}"
        scenario_data = load_scenario(scenario)
        if not method:
            console.print("[bold cyan]Select a governance method:[/bold cyan]")
            for i, m in enumerate(GOVERNANCE_METHODS):
                console.print(f"{i+1}. [green]{m}[/green]")
            idx = int(console.input("Enter method number: ")) - 1
            method = list(GOVERNANCE_METHODS.keys())[idx]
        agents = AgentFactory.create_agents(scenario_data["agents"])
        results = run_simulation(agents, scenario_data, method)
        summary = summarize_results(results)
        table = Table(title="Simulation Results", show_lines=True)
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")
        for k, v in summary.items():
            table.add_row(k, f"{v:.3f}" if isinstance(v, float) else str(v))
        console.print(table)
        agent_sat = per_agent_satisfaction(results)
        table2 = Table(title="Per-Agent Satisfaction")
        table2.add_column("Agent", style="yellow")
        table2.add_column("Satisfaction", style="green")
        for agent, sat in agent_sat.items():
            table2.add_row(agent, f"{sat:.2f}")
        console.print(table2)
        plot_results(results)
    except Exception as e:
        console.print(f"[red]Error running simulation: {e}[/red]")


@cli.command("generate-scenario")
@click.option("--n_agents", prompt="Number of agents", type=int)
@click.option("--n_options", prompt="Number of options", type=int)
@click.option(
    "--personalities",
    prompt="Comma-separated personalities (stubborn,flexible,strategic,random)",
    default="stubborn,flexible,strategic,random",
)
@click.option("--seed", default=None, type=int, help="Random seed for reproducibility")
@click.option("--output", prompt="Output filename (in scenarios/)", default=None)
def generate_scenario(n_agents, n_options, personalities, seed, output):
    """Interactively or programmatically generate a scenario and save as JSON."""
    try:
        np.random.seed(seed)
        personalities = [p.strip() for p in personalities.split(",") if p.strip()]
        options = [chr(65 + i) for i in range(n_options)]
        agents = []
        for i in range(n_agents):
            name = f"Agent{i+1}"
            personality = np.random.choice(personalities)
            preferences = list(np.random.permutation(options))
            agents.append(
                {
                    "name": name,
                    "personality": personality,
                    "preferences": preferences,
                    "options": options,
                }
            )
        scenario = {
            "agents": agents,
            "options": options,
            "context": {
                "description": f"Generated scenario: {n_agents} agents, {n_options} options, personalities: {personalities}"
            },
        }
        if not output:
            output = f"generated_{n_agents}a_{n_options}o.json"
        out_path = (
            os.path.join(os.path.dirname(__file__), "scenarios", output)
            if not output.startswith("scenarios/")
            else output
        )
        with open(out_path, "w") as f:
            json.dump(scenario, f, indent=2)
        console.print(f"[green]Scenario saved to {out_path}[/green]")
    except Exception as e:
        console.print(f"[red]Error generating scenario: {e}[/red]")


@cli.command("compare-all")
def compare_all():
    """Run all governance methods on all scenarios, output summary table and plots."""
    try:
        scenarios = list_scenarios()
        results = []
        for scenario_file in scenarios:
            scenario_path = (
                f"scenarios/{scenario_file}"
                if not scenario_file.startswith("scenarios/")
                else scenario_file
            )
            scenario_data = load_scenario(scenario_path)
            agents_config = scenario_data["agents"]
            for method in GOVERNANCE_METHODS:
                agents = AgentFactory.create_agents(agents_config)
                res = run_simulation(agents, scenario_data, method)
                summary = summarize_results(res)
                summary["scenario"] = scenario_file
                summary["method"] = method
                results.append(summary)
        df = pd.DataFrame(results)
        df.to_csv("comparison_results.csv", index=False)
        df.to_markdown("comparison_results.md", index=False)
        table = Table(title="Batch Comparison Results", show_lines=True)
        for col in df.columns:
            table.add_column(col, style="cyan")
        for _, row in df.iterrows():
            table.add_row(*[str(x) for x in row.values])
        console.print(table)
        plot_method_comparison(df)
        console.print(
            "[green]Results saved to comparison_results.csv and comparison_results.md[/green]"
        )
    except Exception as e:
        console.print(f"[red]Error in batch comparison: {e}[/red]")


@cli.command("manipulability-analysis")
@click.option("--scenario", required=True, help="Path to scenario JSON file")
@click.option("--method", required=True, help="Governance method to use")
def manipulability_analysis_cmd(scenario, method):
    """Run manipulability analysis for a scenario and method, and visualize the impact."""
    try:
        scenario_data = load_scenario(scenario)
        agents = AgentFactory.create_agents(scenario_data["agents"])
        results_list = manipulability_analysis(agents, scenario_data, method)
        if not results_list:
            console.print("[red]No results from manipulability analysis.[/red]")
            return
        table = Table(title="Manipulability Analysis Results", show_lines=True)
        metrics = ["manipulation_type", "consensus_rate", "fairness", "satisfaction"]
        for m in metrics:
            table.add_column(m, style="cyan")
        for r in results_list:
            table.add_row(*(str(r.get(m, "")) for m in metrics))
        console.print(table)
        plot_manipulability_impact(results_list)
    except Exception as e:
        console.print(f"[red]Error in manipulability analysis: {e}[/red]")


@cli.command("validate-scenarios")
def validate_scenarios_cmd():
    """Validate all scenario files in the scenarios/ directory."""
    import os
    import json

    scenario_dir = os.path.join(os.path.dirname(__file__), "scenarios")
    scenario_files = [f for f in os.listdir(scenario_dir) if f.endswith(".json")]
    all_valid = True
    for fname in scenario_files:
        with open(os.path.join(scenario_dir, fname)) as f:
            scenario = json.load(f)
        valid, msg = validate_scenario(scenario)
        if valid:
            console.print(f"[green][OK] {fname}[/green]")
        else:
            console.print(f"[red][ERROR] {fname}: {msg}[/red]")
            all_valid = False
    if not all_valid:
        console.print("[red]Some scenarios are invalid.[/red]")
        exit(1)
    else:
        console.print("[green]All scenarios are valid.[/green]")


if __name__ == "__main__":
    cli()
