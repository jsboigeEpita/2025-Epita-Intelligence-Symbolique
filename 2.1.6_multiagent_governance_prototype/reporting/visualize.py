import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

try:
    import networkx as nx

    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False


def plot_results(results, save_path=None):
    """
    Plot votes, satisfaction, per-agent satisfaction, and consensus evolution (if multi-round).
    Optionally save the plot to a file.
    """
    if not results or "votes" not in results or "satisfaction" not in results:
        print("[plot_results] Invalid or empty results.")
        return
    votes = results["votes"]
    winner = results.get("winner", None)
    satisfaction = results["satisfaction"]
    options = results.get("options", [])
    agent_names = results.get("agent_names", [str(i) for i in range(len(votes))])
    rounds = results.get("rounds", 1)
    history = results.get("history", None)

    plt.figure(figsize=(14, 4))
    plt.subplot(1, 3, 1)
    if options:
        sns.countplot(x=votes, order=options)
    else:
        sns.countplot(x=votes)
    plt.title(f"Votes (Winner: {winner})")
    plt.xlabel("Option")
    plt.ylabel("Count")

    plt.subplot(1, 3, 2)
    if agent_names and satisfaction:
        sns.barplot(x=agent_names, y=satisfaction)
        plt.title("Per-Agent Satisfaction")
        plt.xlabel("Agent")
        plt.ylabel("Satisfaction")
        plt.ylim(0, 1)
        plt.xticks(rotation=30)
    else:
        plt.axis("off")

    plt.subplot(1, 3, 3)
    if history and rounds > 1:
        consensus = [
            h["votes"].count(h["winner"]) / len(h["votes"]) if h["votes"] else 0
            for h in history
        ]
        plt.plot(range(1, rounds + 1), consensus, marker="o")
        plt.title("Consensus Evolution")
        plt.xlabel("Round")
        plt.ylabel("Consensus Rate")
        plt.ylim(0, 1)
    else:
        plt.axis("off")

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path)
    plt.show()
    if winner is not None:
        print(f"Winner: {winner}")


def plot_method_comparison(batch_df, save_path=None):
    """
    Plot method comparison for batch results (requires pandas DataFrame with 'method' column).
    Optionally save the plot to a file.
    """
    import pandas as pd

    metrics = ["consensus_rate", "fairness", "efficiency", "satisfaction"]
    if batch_df.empty or "method" not in batch_df.columns:
        print("[plot_method_comparison] Invalid or empty DataFrame.")
        return
    means = batch_df.groupby("method")[metrics].mean().reset_index()
    means = means.melt(id_vars="method", var_name="metric", value_name="value")
    plt.figure(figsize=(10, 5))
    sns.barplot(data=means, x="method", y="value", hue="metric")
    plt.title("Governance Method Comparison")
    plt.ylabel("Score")
    plt.xlabel("Method")
    plt.legend(title="Metric")
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path)
    plt.show()


def plot_network(adjacency, agent_names, save_path=None):
    """
    Visualize the agent communication network as a graph.
    Optionally save the plot to a file.
    """
    if not HAS_NETWORKX:
        print("[plot_network] networkx is not installed.")
        return
    if adjacency is None or not agent_names:
        print("[plot_network] Invalid adjacency or agent_names.")
        return
    G = nx.Graph()
    for i, name in enumerate(agent_names):
        G.add_node(name)
    for i, row in enumerate(adjacency):
        for j, connected in enumerate(row):
            if connected and i < j:
                G.add_edge(agent_names[i], agent_names[j])
    plt.figure(figsize=(6, 6))
    nx.draw(G, with_labels=True, node_color="skyblue", node_size=800, font_size=10)
    plt.title("Agent Communication Network")
    if save_path:
        plt.savefig(save_path)
    plt.show()


def plot_coalitions(coalitions, save_path=None):
    """
    Visualize coalitions as colored groups in a graph.
    Optionally save the plot to a file.
    """
    if not HAS_NETWORKX:
        print("[plot_coalitions] networkx is not installed.")
        return
    if not coalitions:
        print("[plot_coalitions] No coalitions to plot.")
        return
    G = nx.Graph()
    color_map = []
    for idx, coalition in enumerate(coalitions):
        for agent in coalition:
            G.add_node(agent)
            color_map.append(idx)
        for i in range(len(coalition)):
            for j in range(i + 1, len(coalition)):
                G.add_edge(coalition[i], coalition[j])
    plt.figure(figsize=(6, 6))
    nx.draw(
        G,
        with_labels=True,
        node_color=color_map,
        cmap=plt.cm.Set3,
        node_size=800,
        font_size=10,
    )
    plt.title("Coalition Structure")
    if save_path:
        plt.savefig(save_path)
    plt.show()


def plot_manipulability_impact(
    results_list, metrics=("consensus_rate", "fairness", "satisfaction"), save_path=None
):
    """
    Plot the effect of manipulation/noise on consensus, fairness, and satisfaction.
    Optionally save the plot to a file.
    """
    import pandas as pd

    if not results_list:
        print("[plot_manipulability_impact] Empty results list.")
        return
    df = pd.DataFrame(results_list)
    if df.empty or "manipulation_type" not in df.columns:
        print("[plot_manipulability_impact] Invalid results for plotting.")
        return
    plt.figure(figsize=(12, 4))
    for i, metric in enumerate(metrics):
        if metric not in df.columns:
            continue
        plt.subplot(1, len(metrics), i + 1)
        sns.barplot(x="manipulation_type", y=metric, data=df)
        plt.title(f"Impact on {metric}")
        plt.xlabel("Manipulation Type")
        plt.ylabel(metric.capitalize())
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path)
    plt.show()
