"""
Dung framework visualization — attack graphs with extension highlighting.

Generates networkx-based directed graphs showing arguments as nodes and
attack relations as edges, with optional highlighting of extensions.
"""

import logging
from io import BytesIO
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


def render_attack_graph(
    arguments: List[str],
    attacks: List[List[str]],
    extensions: Optional[Dict[str, List[List[str]]]] = None,
    highlight_extension: Optional[str] = None,
    title: str = "Argumentation Framework",
    output_path: Optional[str] = None,
) -> Optional[bytes]:
    """Render a Dung argumentation framework as a directed graph.

    Args:
        arguments: List of argument names
        attacks: List of [source, target] attack pairs
        extensions: Dict of semantics -> list of extensions (optional)
        highlight_extension: Semantics name to highlight (e.g., "grounded")
        title: Chart title
        output_path: If provided, saves to file. Otherwise returns PNG bytes.

    Returns:
        PNG bytes if output_path is None, else None (saves to file).
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import networkx as nx
    except ImportError:
        logger.warning("matplotlib/networkx not available, skipping visualization")
        return None

    G = nx.DiGraph()
    for arg in arguments:
        G.add_node(arg[:30])
    for attack in attacks:
        if len(attack) >= 2:
            G.add_edge(attack[0][:30], attack[1][:30])

    fig, ax = plt.subplots(1, 1, figsize=(10, 8))

    # Layout
    if len(G.nodes) <= 3:
        pos = nx.circular_layout(G)
    elif len(G.nodes) <= 8:
        pos = nx.spring_layout(G, seed=42, k=2)
    else:
        pos = nx.kamada_kawai_layout(G)

    # Determine node colors based on extension
    highlighted: Set[str] = set()
    if extensions and highlight_extension:
        ext_list = extensions.get(highlight_extension, [])
        if ext_list:
            highlighted = set(ext_list[0])  # Use first extension

    node_colors = []
    for n in G.nodes:
        if n in highlighted:
            node_colors.append("#4CAF50")  # Green = accepted
        elif any(n == a[1][:30] for a in attacks if a[0][:30] in highlighted):
            node_colors.append("#F44336")  # Red = attacked by accepted
        else:
            node_colors.append("#90CAF9")  # Light blue = undecided

    # Draw
    nx.draw_networkx_nodes(
        G, pos, ax=ax, node_color=node_colors, node_size=800, edgecolors="black"
    )
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=8, font_weight="bold")
    nx.draw_networkx_edges(
        G, pos, ax=ax, edge_color="#666",
        arrowsize=20, arrowstyle="-|>",
        connectionstyle="arc3,rad=0.1",
    )

    # Legend
    subtitle = title
    if highlight_extension and highlighted:
        subtitle += f" — {highlight_extension}: {{{', '.join(sorted(highlighted))}}}"
    ax.set_title(subtitle, size=13, pad=15)
    ax.set_axis_off()

    # Stats annotation
    stats_text = f"{len(arguments)} args, {len(attacks)} attacks"
    if extensions:
        for sem, exts in extensions.items():
            stats_text += f"\n{sem}: {len(exts)} ext(s)"
    ax.text(
        0.02, 0.02, stats_text, transform=ax.transAxes,
        fontsize=8, verticalalignment="bottom",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"Attack graph saved to {output_path}")
        return None

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
