"""
Visualization module for argumentation analysis outputs.

Provides the HTML report renderer (self-contained interactive HTML) for
pipeline results. The matplotlib chart trio (quality radar, Dung attack
graph, pipeline dashboard) was withdrawn in #2116: zero production
importers, zero tests — html_report is the only visualization surface
the production tree ever mounts.
"""

from argumentation_analysis.visualization.html_report import render_html_report

__all__ = [
    "render_html_report",
]
