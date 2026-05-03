"""
Visualization module for argumentation analysis outputs.

Provides chart and graph generation for pipeline results:
- Quality radar charts (9 virtues)
- Dung attack graphs with extension highlighting
- Pipeline dashboard combining all outputs
- HTML report renderer (self-contained interactive HTML)
"""

from argumentation_analysis.visualization.quality_viz import render_quality_radar
from argumentation_analysis.visualization.dung_viz import render_attack_graph
from argumentation_analysis.visualization.pipeline_viz import render_pipeline_dashboard
from argumentation_analysis.visualization.html_report import render_html_report

__all__ = [
    "render_quality_radar",
    "render_attack_graph",
    "render_pipeline_dashboard",
    "render_html_report",
]
