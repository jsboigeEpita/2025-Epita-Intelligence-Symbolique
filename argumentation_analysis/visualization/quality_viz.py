"""
Quality evaluation visualization — radar/spider charts for 9 argumentative virtues.

Generates matplotlib figures showing per-argument quality scores across
the 9 virtues (clarity, relevance, sources, refutation, logical structure,
analogies, source reliability, exhaustiveness, low redundancy).
"""

import logging
import math
from io import BytesIO
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

VIRTUE_LABELS = [
    "Clarte",
    "Pertinence",
    "Sources",
    "Refutation",
    "Structure\nlogique",
    "Analogies",
    "Fiabilite\nsources",
    "Exhaustivite",
    "Faible\nredondance",
]

VIRTUE_KEYS = [
    "clarte",
    "pertinence",
    "sources",
    "refutation",
    "structure_logique",
    "analogies",
    "fiabilite_sources",
    "exhaustivite",
    "faible_redundance",
]


def render_quality_radar(
    scores: Dict[str, float],
    title: str = "Qualite argumentative",
    output_path: Optional[str] = None,
) -> Optional[bytes]:
    """Render a radar chart for argument quality scores.

    Args:
        scores: Dict mapping virtue keys to scores (0.0-1.0)
        title: Chart title
        output_path: If provided, saves to file. Otherwise returns PNG bytes.

    Returns:
        PNG bytes if output_path is None, else None (saves to file).
    """
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        logger.warning("matplotlib not available, skipping visualization")
        return None

    # Extract scores in order
    values = [scores.get(k, 0.0) for k in VIRTUE_KEYS]
    # Close the polygon
    values += [values[0]]

    n = len(VIRTUE_LABELS)
    angles = [i * 2 * math.pi / n for i in range(n)]
    angles += [angles[0]]

    fig, ax = plt.subplots(1, 1, figsize=(8, 8), subplot_kw={"polar": True})
    ax.plot(angles, values, "o-", linewidth=2, color="#2196F3")
    ax.fill(angles, values, alpha=0.25, color="#2196F3")
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(VIRTUE_LABELS, size=9)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"], size=7)
    ax.set_title(title, size=14, pad=20)

    # Add overall score
    overall = sum(values[:-1]) / max(n, 1)
    ax.text(
        0.5,
        -0.08,
        f"Score global: {overall:.2f}",
        transform=ax.transAxes,
        ha="center",
        size=12,
        weight="bold",
    )

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"Quality radar saved to {output_path}")
        return None

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
