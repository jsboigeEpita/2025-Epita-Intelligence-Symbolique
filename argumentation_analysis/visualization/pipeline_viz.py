"""
Pipeline dashboard visualization — combines all analysis outputs.

Generates a multi-panel figure showing the key outputs from a unified
pipeline run: quality scores, fallacy counts, argument structure, etc.
"""

import logging
from io import BytesIO
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def render_pipeline_dashboard(
    state: Dict[str, Any],
    title: str = "Pipeline Analysis Dashboard",
    output_path: Optional[str] = None,
) -> Optional[bytes]:
    """Render a dashboard from pipeline state snapshot.

    Args:
        state: Pipeline state dict (from get_state_snapshot or iteration results)
        title: Dashboard title
        output_path: If provided, saves to file. Otherwise returns PNG bytes.

    Returns:
        PNG bytes if output_path is None, else None (saves to file).
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib not available, skipping visualization")
        return None

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(title, fontsize=14, fontweight="bold")

    # Panel 1: Arguments and claims count
    ax1 = axes[0, 0]
    _render_counts_panel(ax1, state)

    # Panel 2: Fallacy distribution
    ax2 = axes[0, 1]
    _render_fallacy_panel(ax2, state)

    # Panel 3: Quality scores (if available)
    ax3 = axes[1, 0]
    _render_quality_panel(ax3, state)

    # Panel 4: Pipeline phase status
    ax4 = axes[1, 1]
    _render_phase_status(ax4, state)

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"Dashboard saved to {output_path}")
        return None

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _render_counts_panel(ax, state: Dict[str, Any]) -> None:
    """Render argument/claim/fallacy counts bar chart."""
    categories = []
    values = []

    for key, label in [
        ("identified_arguments", "Arguments"),
        ("identified_claims", "Claims"),
        ("identified_fallacies", "Fallacies"),
        ("counter_arguments", "Counter-Args"),
        ("jtms_beliefs", "JTMS Beliefs"),
    ]:
        val = state.get(key)
        if isinstance(val, (list, dict)):
            categories.append(label)
            values.append(len(val))
        elif isinstance(val, (int, float)):
            categories.append(label)
            values.append(int(val))

    if not categories:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=12)
        ax.set_title("Extraction Results")
        return

    colors = ["#2196F3", "#4CAF50", "#F44336", "#FF9800", "#9C27B0"]
    bars = ax.barh(categories, values, color=colors[: len(categories)])
    ax.set_xlabel("Count")
    ax.set_title("Extraction Results")
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=10)


def _render_fallacy_panel(ax, state: Dict[str, Any]) -> None:
    """Render fallacy type distribution pie chart."""
    fallacies = state.get("identified_fallacies", {})
    if isinstance(fallacies, dict):
        items = fallacies
    elif isinstance(fallacies, list):
        items = {}
        for f in fallacies:
            ftype = f.get("fallacy_type", "unknown") if isinstance(f, dict) else str(f)
            items[ftype[:20]] = items.get(ftype[:20], 0) + 1
    else:
        items = {}

    if not items:
        ax.text(0.5, 0.5, "No fallacies\ndetected", ha="center", va="center", fontsize=12)
        ax.set_title("Fallacy Distribution")
        return

    labels = list(items.keys())[:8]
    sizes = [items[l] for l in labels]
    ax.pie(sizes, labels=labels, autopct="%1.0f%%", startangle=90, textprops={"fontsize": 8})
    ax.set_title(f"Fallacy Distribution ({sum(sizes)} total)")


def _render_quality_panel(ax, state: Dict[str, Any]) -> None:
    """Render quality scores bar chart."""
    quality = state.get("quality_scores", {})
    if not quality or not isinstance(quality, dict):
        ax.text(0.5, 0.5, "No quality\nscores", ha="center", va="center", fontsize=12)
        ax.set_title("Quality Scores")
        return

    # If nested (per-argument), aggregate
    if any(isinstance(v, dict) for v in quality.values()):
        # Average across arguments
        aggregated = {}
        count = 0
        for arg_id, scores in quality.items():
            if isinstance(scores, dict):
                count += 1
                for k, v in scores.items():
                    if isinstance(v, (int, float)):
                        aggregated[k] = aggregated.get(k, 0) + v
        if count > 0:
            quality = {k: v / count for k, v in aggregated.items()}

    labels = [k[:15] for k in quality.keys()][:9]
    values = [quality[list(quality.keys())[i]] for i in range(len(labels))]

    ax.barh(labels, values, color="#4CAF50")
    ax.set_xlim(0, 1)
    ax.set_xlabel("Score")
    ax.set_title("Quality Scores (avg)")


def _render_phase_status(ax, state: Dict[str, Any]) -> None:
    """Render pipeline phase completion status."""
    phases = []
    statuses = []

    for key in sorted(state.keys()):
        if key.startswith("phase_") and key.endswith("_output"):
            phase_name = key[6:-7]  # strip phase_ and _output
            val = state[key]
            phases.append(phase_name[:18])
            if isinstance(val, dict) and "error" in val:
                statuses.append(0)  # error
            elif val:
                statuses.append(1)  # success
            else:
                statuses.append(0.5)  # empty

    if not phases:
        # Try to count non-empty fields
        non_empty = sum(
            1 for k, v in state.items()
            if v and k not in ("raw_text", "source_info") and not k.startswith("phase_")
        )
        ax.text(
            0.5, 0.5,
            f"{non_empty} non-empty\noutput fields",
            ha="center", va="center", fontsize=16, fontweight="bold",
        )
        ax.set_title("Pipeline Output")
        return

    colors = ["#4CAF50" if s == 1 else "#F44336" if s == 0 else "#FFC107" for s in statuses]
    ax.barh(phases, statuses, color=colors)
    ax.set_xlim(0, 1.2)
    ax.set_xticks([0, 0.5, 1])
    ax.set_xticklabels(["Error", "Empty", "OK"])
    ax.set_title(f"Phase Status ({sum(1 for s in statuses if s == 1)}/{len(phases)} OK)")
