"""
HTML report renderer — generates self-contained interactive HTML from spectacular state.

Produces a single HTML file with embedded JS/CSS (no external dependencies)
showing all 9 analysis sections with interactive visualizations:
- Dung graph (cytoscape.js via CDN)
- ATMS hypothesis tree (D3.js via CDN)
- Fallacy heatmap (CSS gradient)
"""

import json
import logging
import pathlib
from typing import Any, Dict, Optional, Union

from jinja2 import Environment, BaseLoader

logger = logging.getLogger(__name__)

JINJA_ENV = Environment(loader=BaseLoader(), autoescape=False)

TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Argumentation Report — {{ source_id }}</title>
<style>
:root {
  --bg: #0d1117; --surface: #161b22; --border: #30363d;
  --text: #e6edf3; --text-muted: #8b949e;
  --accent: #58a6ff; --green: #3fb950; --red: #f85149; --orange: #d29922;
  --purple: #bc8cff; --cyan: #39d2c0;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; padding: 2rem; max-width: 1200px; margin: 0 auto; }
h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
h2 { font-size: 1.4rem; color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; margin: 2rem 0 1rem; }
h3 { font-size: 1.1rem; color: var(--purple); margin: 1rem 0 0.5rem; }
.summary-bar { display: flex; gap: 1rem; flex-wrap: wrap; margin: 1rem 0; }
.summary-stat { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.5rem; text-align: center; min-width: 120px; }
.summary-stat .num { font-size: 2rem; font-weight: 700; color: var(--accent); }
.summary-stat .label { font-size: 0.85rem; color: var(--text-muted); }
.section { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; margin: 1rem 0; overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
th, td { padding: 0.6rem 0.8rem; text-align: left; border-bottom: 1px solid var(--border); }
th { color: var(--accent); font-weight: 600; white-space: nowrap; }
tr:hover { background: rgba(88,166,255,0.05); }
.badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
.badge-green { background: rgba(63,185,80,0.15); color: var(--green); }
.badge-red { background: rgba(248,81,73,0.15); color: var(--red); }
.badge-orange { background: rgba(210,153,34,0.15); color: var(--orange); }
.badge-blue { background: rgba(88,166,255,0.15); color: var(--accent); }
.badge-purple { background: rgba(188,140,255,0.15); color: var(--purple); }
.score-bar { height: 6px; border-radius: 3px; background: var(--border); min-width: 60px; display: inline-block; vertical-align: middle; }
.score-fill { height: 100%; border-radius: 3px; }
.heatmap-cell { padding: 0.4rem 0.8rem; text-align: center; font-weight: 600; font-size: 0.85rem; }
.viz-container { min-height: 350px; border: 1px solid var(--border); border-radius: 8px; margin: 1rem 0; position: relative; }
.collapsible { cursor: pointer; user-select: none; }
.collapsible::before { content: '\\25B6 '; color: var(--accent); display: inline-block; transition: transform 0.2s; }
.collapsible.open::before { transform: rotate(90deg); }
.collapsible-content { display: none; padding-left: 1.5rem; }
.collapsible-content.show { display: block; }
.narrative { background: rgba(88,166,255,0.05); border-left: 3px solid var(--accent); padding: 1rem 1.5rem; border-radius: 0 8px 8px 0; font-style: italic; }
.chip { display: inline-block; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 0.2rem 0.6rem; font-size: 0.75rem; margin: 0.15rem; }
.footer { text-align: center; color: var(--text-muted); font-size: 0.8rem; margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border); }
#dung-graph { width: 100%; height: 400px; }
#atms-tree { width: 100%; min-height: 350px; }
</style>
</head>
<body>

<h1>Argumentation Report</h1>
<p style="color: var(--text-muted);">Source: <strong>{{ source_id }}</strong> &middot; Workflow: {{ workflow_name }} &middot; {{ summary.completed }}/{{ summary.total }} phases completed</p>

{# ── Section 0: Executive Summary ── #}
<div class="summary-bar">
  <div class="summary-stat"><div class="num">{{ args_count }}</div><div class="label">Arguments</div></div>
  <div class="summary-stat"><div class="num">{{ fallacies_count }}</div><div class="label">Fallacies</div></div>
  <div class="summary-stat"><div class="num">{{ counter_count }}</div><div class="label">Counter-Args</div></div>
  <div class="summary-stat"><div class="num">{{ beliefs_count }}</div><div class="label">JTMS Beliefs</div></div>
  <div class="summary-stat"><div class="num">{{ atms_count }}</div><div class="label">ATMS Contexts</div></div>
  <div class="summary-stat"><div class="num">{{ capabilities|length }}</div><div class="label">Capabilities</div></div>
</div>
<div style="margin: 0.5rem 0;">
{% for cap in capabilities %}
  <span class="chip">{{ cap }}</span>
{% endfor %}
</div>

{# ── Section 1: Argument Extraction + Quality ── #}
<h2>1. Argument Extraction &amp; Quality Scores</h2>
<div class="section">
<table>
  <thead><tr><th>ID</th><th>Argument</th><th>Quality</th><th>Clarity</th><th>Coherence</th><th>Relevance</th><th>Completeness</th></tr></thead>
  <tbody>
  {% for arg_id, arg_text in arguments.items() %}
    {% set qs = quality_scores.get(arg_id, {}) %}
    {% set overall = qs.get('overall', '-') %}
    <tr>
      <td><code>{{ arg_id }}</code></td>
      <td>{{ arg_text|truncate(80, true) }}</td>
      <td>{{ _score_badge(overall) }}</td>
      <td>{{ _score_cell(qs.get('clarity', '-')) }}</td>
      <td>{{ _score_cell(qs.get('coherence', '-')) }}</td>
      <td>{{ _score_cell(qs.get('relevance', '-')) }}</td>
      <td>{{ _score_cell(qs.get('completeness', '-')) }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
</div>

{# ── Section 2: Fallacy Detection ── #}
<h2>2. Fallacy Detection</h2>
<div class="section">
  {# Heatmap table #}
  <h3>Family &times; Argument Heatmap</h3>
  <table>
    <thead><tr><th>Family / Fallacy</th>
    {% for arg_id in arg_ids %}
      <th>{{ arg_id }}</th>
    {% endfor %}
    </tr></thead>
    <tbody>
    {% for row in heatmap_rows %}
      <tr>
        <td><strong>{{ row.family }}</strong></td>
        {% for cell in row.cells %}
          <td class="heatmap-cell" {% if cell.conf %}style="background: {{ _heat_color(cell.conf) }}; color: #fff;"{% endif %}>
            {% if cell.conf %}{{ "%.0f"|format(cell.conf * 100) }}%{% endif %}
          </td>
        {% endfor %}
      </tr>
    {% endfor %}
    </tbody>
  </table>

  <h3>Detected Fallacies Detail</h3>
  <table>
    <thead><tr><th>ID</th><th>Type</th><th>Family</th><th>Target</th><th>Confidence</th><th>Justification</th></tr></thead>
    <tbody>
    {% for fid, fdata in fallacies.items() %}
      <tr>
        <td><code>{{ fid }}</code></td>
        <td>{{ fdata.type }}</td>
        <td><span class="badge badge-orange">{{ fdata.family }}</span></td>
        <td><code>{{ fdata.source_arg }}</code></td>
        <td>{{ _score_cell(fdata.confidence) }}</td>
        <td>{{ fdata.justification }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</div>

{# ── Section 3: Dung Argumentation Framework ── #}
<h2>3. Dung Argumentation Framework</h2>
<div class="section">
  <div id="dung-graph" class="viz-container"></div>
  <h3>Extensions</h3>
  {% for sem, exts in dung_extensions.items() %}
    <p><strong>{{ sem }}</strong>:
    {% for ext in exts %}
      <code>[{{ ext|join(', ') }}]</code>{% if not loop.last %}, {% endif %}
    {% endfor %}
    </p>
  {% endfor %}
  <h3>Status Assignment</h3>
  <table>
    <thead><tr><th>Argument</th><th>Status</th></tr></thead>
    <tbody>
    {% for arg_id, status in dung_status.items() %}
      <tr><td><code>{{ arg_id }}</code></td><td>{{ _status_badge(status) }}</td></tr>
    {% endfor %}
    </tbody>
  </table>
</div>

{# ── Section 4: ATMS Hypothesis Tree ── #}
<h2>4. ATMS Hypothesis Contexts</h2>
<div class="section">
  <div id="atms-tree" class="viz-container"></div>
  {% for ctx in atms_contexts %}
    <div style="margin: 0.5rem 0;">
      <h3 class="collapsible" onclick="toggleCollapse(this)">{{ ctx.label }} ({{ ctx.context_id }})
        {% if ctx.status == 'contradictory' %}
          <span class="badge badge-red">CONTRADICTORY</span>
        {% else %}
          <span class="badge badge-green">CONSISTENT</span>
        {% endif %}
      </h3>
      <div class="collapsible-content">
        <p><strong>Assumptions:</strong> {% for a in ctx.assumptions %}<span class="chip">{{ a }}</span>{% endfor %}</p>
        <p><strong>Environment:</strong> {% for e in ctx.environment %}<span class="chip">{{ e }}</span>{% endfor %}</p>
        {% if ctx.nogoods %}<p><strong>Nogoods:</strong> {% for n in ctx.nogoods %}<span class="chip" style="border-color: var(--red);">{{ n }}</span>{% endfor %}</p>{% endif %}
      </div>
    </div>
  {% endfor %}
</div>

{# ── Section 5: JTMS Justification Chains ── #}
<h2>5. JTMS Belief Network &amp; Retraction Chains</h2>
<div class="section">
  <h3>Belief Status</h3>
  <table>
    <thead><tr><th>Belief</th><th>Status</th><th>Confidence</th><th>Justification</th></tr></thead>
    <tbody>
    {% for bid, bdata in jtms_beliefs.items() %}
      <tr>
        <td><code>{{ bid }}</code></td>
        <td>{% if bdata.status == 'IN' %}<span class="badge badge-green">IN</span>{% else %}<span class="badge badge-red">OUT</span>{% endif %}</td>
        <td>{{ _score_cell(bdata.confidence) }}</td>
        <td>{{ bdata.justification }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% if jtms_retractions %}
  <h3>Retraction Cascades</h3>
  {% for cascade in jtms_retractions %}
    <div style="margin: 0.5rem 0; padding: 0.5rem 1rem; background: rgba(248,81,73,0.05); border-left: 3px solid var(--red); border-radius: 0 8px 8px 0;">
      <strong>{{ cascade.cascade_id }}</strong> — triggered by <code>{{ cascade.trigger }}</code><br>
      <span style="color: var(--text-muted);">{{ cascade.reason }}</span>
      {% for effect in cascade.downstream_effects %}
        <br><span class="badge badge-red">{{ effect.get('belief', '') }}: {{ effect.get('old_status', effect.get('old_confidence', '')) }} → {{ effect.get('new_status', effect.get('new_confidence', '')) }}</span>
      {% endfor %}
    </div>
  {% endfor %}
  {% endif %}
</div>

{# ── Section 6: Counter-Arguments ── #}
<h2>6. Counter-Arguments</h2>
<div class="section">
{% for ca in counter_arguments %}
  <div style="margin: 0.5rem 0; padding: 0.8rem 1rem; background: rgba(188,140,255,0.05); border-left: 3px solid var(--purple); border-radius: 0 8px 8px 0;">
    <strong>{{ ca.strategy }}</strong> → <code>{{ ca.target_arg }}</code>
    <span class="badge badge-purple" style="margin-left: 0.5rem;">Strength: {{ "%.0f"|format(ca.strength * 100) }}%</span>
    <p style="margin-top: 0.3rem;">{{ ca.counter_content }}</p>
  </div>
{% endfor %}
</div>

{# ── Section 7: Governance Vote ── #}
<h2>7. Governance Simulation</h2>
<div class="section">
{% for decision in governance_decisions %}
  <h3>{{ decision.method|capitalize }} Vote</h3>
  {% if decision.votes is defined %}
  <table>
    <thead><tr><th>Proposal</th><th>Votes</th></tr></thead>
    <tbody>
    {% for prop, count in decision.votes.items() %}
      <tr><td>{{ prop }}</td><td>{{ count }}</td></tr>
    {% endfor %}
    </tbody>
  </table>
  {% endif %}
  <p><strong>Winner:</strong> <span class="badge badge-green">{{ decision.result }}</span> &middot; Consensus: {{ "%.0f"|format((decision.consensus_score or 0) * 100) }}%</p>
{% endfor %}
</div>

{# ── Section 8: Ranking Results ── #}
<h2>8. Argument Ranking</h2>
<div class="section">
<table>
  <thead><tr><th>Rank</th><th>Argument</th><th>Score</th></tr></thead>
  <tbody>
  {% for r in ranking_results %}
    <tr><td>#{{ r.rank }}</td><td><code>{{ r.argument }}</code></td><td>{{ _score_cell(r.score) }}</td></tr>
  {% endfor %}
  </tbody>
</table>
</div>

{# ── Section 9: Narrative Synthesis ── #}
<h2>9. Narrative Synthesis</h2>
<div class="section">
  <div class="narrative">{{ narrative_synthesis }}</div>
</div>

{# ── Section 10: Discourse Pattern Mining (optional) ── #}
{% if pattern_data %}
<h2>10. Discourse Pattern Mining</h2>

{# 10a: Fallacy Spectra by Cluster #}
{% if pattern_data.spectrum %}
<div class="section">
  <h3>Fallacy Spectra by Cluster</h3>
  <table>
    <thead><tr><th>Cluster</th>
    {% for ftype in pattern_data.spectrum_types %}
      <th>{{ ftype }}</th>
    {% endfor %}
    </tr></thead>
    <tbody>
    {% for cid in pattern_data.cluster_ids %}
      <tr>
        <td><strong>{{ cid }}</strong></td>
        {% for ftype in pattern_data.spectrum_types %}
          <td class="heatmap-cell" style="background: {{ _pattern_heat_bg(pattern_data.spectrum[cid].get(ftype, 0)) }};">
            {{ "%.2f"|format(pattern_data.spectrum[cid].get(ftype, 0)) }}
          </td>
        {% endfor %}
      </tr>
    {% endfor %}
    </tbody>
  </table>
</div>
{% endif %}

{# 10b: Tricherie / Influence Asymmetry #}
{% if pattern_data.asymmetry %}
<div class="section">
  <h3>Tricherie &harr; Influence Asymmetry</h3>
  <table>
    <thead><tr><th>Cluster</th><th>Tricherie</th><th>Influence</th><th>Asymmetry</th></tr></thead>
    <tbody>
    {% for cid, d in pattern_data.asymmetry.items() %}
      <tr>
        <td><strong>{{ cid }}</strong></td>
        <td>{{ "%.3f"|format(d.tricherie_share) }}</td>
        <td>{{ "%.3f"|format(d.influence_share) }}</td>
        <td>{{ "%+.3f"|format(d.asymmetry) }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  <p style="color: var(--text-muted); margin-top: 0.5rem; font-size: 0.85rem;">Asymmetry &isin; [-1, +1]: positive = Influence-dominant, negative = Tricherie-dominant</p>
</div>
{% endif %}

{# 10c: Co-occurrence Top Pairs #}
{% if pattern_data.cooccurrence_pairs %}
<div class="section">
  <h3>Co-occurrence Top Pairs (by lift)</h3>
  <table>
    <thead><tr><th>Fallacy A</th><th>Fallacy B</th><th>Support</th><th>Lift</th><th>Jaccard</th></tr></thead>
    <tbody>
    {% for p in pattern_data.cooccurrence_pairs %}
      <tr>
        <td>{{ p.a }}</td>
        <td>{{ p.b }}</td>
        <td>{{ p.support }}</td>
        <td>{{ "%.2f"|format(p.lift) }}</td>
        <td>{{ "%.3f"|format(p.jaccard) }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</div>
{% endif %}

{# 10d: Cross-coverage Informal / Formal #}
{% if pattern_data.cross_coverage %}
<div class="section">
  <h3>Cross-coverage: Informal &harr; Formal</h3>
  <table>
    <thead><tr><th>Fallacy Type</th><th>FOL Invalid</th><th>Dung Unsupported</th><th>JTMS Retraction</th></tr></thead>
    <tbody>
    {% for ftype, signals in pattern_data.cross_coverage.items() %}
      <tr>
        <td>{{ ftype }}</td>
        <td>{{ "%.2f"|format(signals.get("fol_invalid", 0)) }}</td>
        <td>{{ "%.2f"|format(signals.get("dung_unsupported", 0)) }}</td>
        <td>{{ "%.2f"|format(signals.get("jtms_retraction", 0)) }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</div>
{% endif %}

{% endif %}

<div class="footer">
  Generated by argumentation_analysis.visualization.html_report &middot;
  {{ capabilities|length }} capabilities &middot; {{ summary.completed }} phases in {{ "%.1f"|format(duration_s) }}s
</div>

{# ── JavaScript: Interactive Visualizations ── #}
<script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
// ── Collapsible sections ──
function toggleCollapse(el) {
  el.classList.toggle('open');
  var content = el.nextElementSibling;
  content.classList.toggle('show');
}

// ── Dung Graph (cytoscape.js) ──
(function() {
  var container = document.getElementById('dung-graph');
  if (!container || !window.cytoscape) return;

  var elements = [];
  var nodeLabels = {{ dung_node_labels|safe }};
  var attacks = {{ dung_attacks|safe }};
  var grounded = {{ dung_grounded|safe }};
  var statusMap = {{ dung_status_json|safe }};

  nodeLabels.forEach(function(n) { elements.push({data: {id: n, label: n}}); });
  attacks.forEach(function(a, i) { elements.push({data: {id: 'e'+i, source: a[0], target: a[1]}}); });

  var cy = cytoscape({
    container: container,
    elements: elements,
    style: [
      {selector: 'node', style: {'label': 'data(label)', 'text-wrap': 'wrap', 'text-valign': 'center', 'font-size': '11px', 'width': 50, 'height': 50, 'color': '#e6edf3', 'background-color': '#58a6ff', 'text-outline-color': '#0d1117', 'text-outline-width': 2}},
      {selector: 'node[status="accepted"]', style: {'background-color': '#3fb950'}},
      {selector: 'node[status="rejected"]', style: {'background-color': '#f85149'}},
      {selector: 'edge', style: {'width': 2, 'line-color': '#f85149', 'target-arrow-color': '#f85149', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', 'arrow-scale': 1.2}},
    ],
    layout: {name: 'cose', animate: true, padding: 30}
  });

  // Apply status colors
  Object.keys(statusMap).forEach(function(id) {
    var s = statusMap[id];
    var cls = s.includes('accepted') ? 'accepted' : (s === 'rejected' ? 'rejected' : '');
    if (cls) cy.$('#' + id).addClass(cls);
  });
})();

// ── ATMS Context Tree (D3.js) ──
(function() {
  var container = document.getElementById('atms-tree');
  if (!container || !window.d3) return;

  var data = {{ atms_tree_data|safe }};

  var width = container.clientWidth;
  var height = 350;
  var svg = d3.select(container).append('svg').attr('width', width).attr('height', height);
  var g = svg.append('g').attr('transform', 'translate(40, 30)');

  var root = d3.hierarchy(data);
  var treeLayout = d3.tree().size([width - 80, height - 60]);
  treeLayout(root);

  // Links
  g.selectAll('.link').data(root.links()).join('line')
    .attr('class', 'link')
    .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
    .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
    .attr('stroke', '#30363d').attr('stroke-width', 1.5);

  // Nodes
  var nodes = g.selectAll('.node').data(root.descendants()).join('g')
    .attr('class', 'node').attr('transform', d => 'translate(' + d.x + ',' + d.y + ')');

  nodes.append('circle').attr('r', 8)
    .attr('fill', d => d.data.status === 'contradictory' ? '#f85149' : '#3fb950')
    .attr('stroke', '#0d1117').attr('stroke-width', 2);

  nodes.append('text').attr('dy', '-12').attr('text-anchor', 'middle')
    .attr('fill', '#e6edf3').attr('font-size', '10px')
    .text(d => d.data.name.length > 25 ? d.data.name.substring(0, 22) + '...' : d.data.name);
})();
</script>
</body>
</html>
"""


def _score_color(value: float) -> str:
    if value >= 0.8:
        return "var(--green)"
    if value >= 0.6:
        return "var(--orange)"
    return "var(--red)"


def _heat_color(value: float) -> str:
    r = int(248 * value)
    g = int(180 * (1 - value))
    return f"rgba({r}, {g}, 40, 0.7)"


def render_html_report(
    state: Dict[str, Any],
    output_path: Optional[Union[str, pathlib.Path]] = None,
    pattern_data: Optional[Dict[str, Any]] = None,
) -> str:
    """Render a self-contained HTML report from a spectacular analysis state.

    Args:
        state: Dict matching the golden fixture schema (top-level keys:
            workflow_name, source_id, summary, capabilities_used, state_snapshot).
        output_path: If provided, writes HTML to this path.
        pattern_data: Optional dict with discourse pattern mining results.
            Expected keys: spectrum, asymmetry, cooccurrence_pairs, cross_coverage.

    Returns:
        The HTML string.
    """
    snapshot = state.get("state_snapshot", state)
    arguments = snapshot.get("identified_arguments", {})
    fallacies = snapshot.get("identified_fallacies", {})
    quality_scores = snapshot.get("argument_quality_scores", {})
    counter_arguments = snapshot.get("counter_arguments", [])
    jtms_beliefs = snapshot.get("jtms_beliefs", {})
    jtms_retractions = snapshot.get("jtms_retraction_chain", [])
    atms_contexts = snapshot.get("atms_contexts", [])
    governance_decisions = snapshot.get("governance_decisions", [])
    ranking_results = snapshot.get("ranking_results", [])
    dung_frameworks = snapshot.get("dung_frameworks", {})
    narrative_synthesis = snapshot.get("narrative_synthesis", "")

    # Build fallacy-by-family mapping for heatmap
    fallacy_by_family: Dict[str, list] = {}
    for fid, fdata in fallacies.items():
        family = fdata.get("family", "unknown")
        fallacy_by_family.setdefault(family, []).append({
            "id": fid,
            "type": fdata.get("type", ""),
            "source_arg": fdata.get("source_arg", ""),
            "confidence": fdata.get("confidence", 0),
        })

    # Precompute heatmap grid: list of {family, cells: [{conf: float|None}]}
    arg_ids = list(arguments.keys())
    heatmap_rows = []
    for family, flist in fallacy_by_family.items():
        cells = []
        for arg_id in arg_ids:
            conf = None
            for f in flist:
                if f["source_arg"] == arg_id:
                    conf = f["confidence"]
                    break
            cells.append({"conf": conf})
        heatmap_rows.append({"family": family, "cells": cells})

    # Extract Dung framework data (use first framework)
    dung_fw = {}
    for fw_data in dung_frameworks.values():
        dung_fw = fw_data
        break
    dung_nodes = dung_fw.get("arguments", [])
    dung_attacks = [[a["from"], a["to"]] for a in dung_fw.get("attacks", [])]
    dung_extensions = dung_fw.get("extensions", {})
    dung_status = dung_fw.get("status_assignment", {})

    # Build ATMS tree data for D3
    atms_root = {
        "name": state.get("source_id", "Analysis"),
        "status": "root",
        "children": [
            {
                "name": ctx.get("label", ctx.get("context_id", "")),
                "status": ctx.get("status", "unknown"),
                "children": [
                    {"name": a, "status": "assumption"}
                    for a in ctx.get("assumptions", [])
                ],
            }
            for ctx in atms_contexts
        ],
    }

    workflow_results = snapshot.get("workflow_results", {})
    duration_s = workflow_results.get("total_duration_ms", 0) / 1000.0

    # Prepare optional pattern mining data for template
    pattern_ctx = None
    if pattern_data:
        spectrum = pattern_data.get("spectrum", {})
        spectrum_types = sorted({t for c in spectrum.values() for t in c}) if spectrum else []
        cluster_ids = sorted(spectrum.keys()) if spectrum else []
        pattern_ctx = {
            "spectrum": spectrum,
            "spectrum_types": spectrum_types,
            "cluster_ids": cluster_ids,
            "asymmetry": pattern_data.get("asymmetry", None),
            "cooccurrence_pairs": pattern_data.get("cooccurrence_pairs", [])[:10],
            "cross_coverage": pattern_data.get("cross_coverage", None),
        }

    template = JINJA_ENV.from_string(TEMPLATE)
    html = template.render(
        source_id=state.get("source_id", "unknown"),
        workflow_name=state.get("workflow_name", "unknown"),
        summary=state.get("summary", {"completed": 0, "total": 0, "failed": 0, "skipped": 0}),
        capabilities=state.get("capabilities_used", []),
        arguments=arguments,
        arg_ids=arg_ids,
        fallacies=fallacies,
        heatmap_rows=heatmap_rows,
        fallacy_by_family=fallacy_by_family,
        quality_scores=quality_scores,
        counter_arguments=counter_arguments,
        jtms_beliefs=jtms_beliefs,
        jtms_retractions=jtms_retractions,
        atms_contexts=atms_contexts,
        governance_decisions=governance_decisions,
        ranking_results=ranking_results,
        dung_extensions=dung_extensions,
        narrative_synthesis=narrative_synthesis,
        args_count=len(arguments),
        fallacies_count=len(fallacies),
        counter_count=len(counter_arguments),
        beliefs_count=len(jtms_beliefs),
        atms_count=len(atms_contexts),
        duration_s=duration_s,
        pattern_data=pattern_ctx,
        # JSON-encoded data for JS
        dung_node_labels=json.dumps(dung_nodes),
        dung_attacks=json.dumps(dung_attacks),
        dung_grounded=json.dumps(dung_extensions.get("grounded", [])),
        dung_status_json=json.dumps(dung_status),
        dung_status=dung_status,
        atms_tree_data=json.dumps(atms_root),
        # Helper functions
        _score_badge=lambda v: f'<span class="badge {"badge-green" if float(v) >= 0.8 else "badge-orange" if float(v) >= 0.6 else "badge-red"}">{v:.0%}</span>' if isinstance(v, (int, float)) else v,
        _score_cell=lambda v: f'<span style="color:{_score_color(float(v))};font-weight:600;">{v:.2f}</span>' if isinstance(v, (int, float)) else str(v),
        _heat_color=_heat_color,
        _pattern_heat_bg=lambda v: f"rgba(88,166,255,{min(v * 0.8, 0.6):.2f})" if v > 0 else "transparent",
        _status_badge=lambda s: f'<span class="badge {"badge-green" if "accepted" in s else "badge-red" if s == "rejected" else "badge-blue"}">{s.replace("_", " ")}</span>',
    )

    if output_path:
        pathlib.Path(output_path).write_text(html, encoding="utf-8")
        logger.info(f"HTML report written to {output_path}")

    return html


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Render HTML report from spectacular state JSON")
    parser.add_argument("state_json", help="Path to state JSON file (golden fixture format)")
    parser.add_argument("output_html", help="Output HTML file path")
    parser.add_argument("--pattern-json", help="Optional path to pattern mining JSON for section 10")
    parser.add_argument("--indent", action="store_true", help="Pretty-print HTML output")
    args = parser.parse_args()

    state_path = pathlib.Path(args.state_json)
    if not state_path.exists():
        print(f"Error: {state_path} not found", file=sys.stderr)
        sys.exit(1)

    state = json.loads(state_path.read_text(encoding="utf-8"))
    pattern_data = None
    if args.pattern_json:
        ppath = pathlib.Path(args.pattern_json)
        if ppath.exists():
            pattern_data = json.loads(ppath.read_text(encoding="utf-8"))

    render_html_report(state, output_path=args.output_html, pattern_data=pattern_data)
    print(f"Report generated: {args.output_html}")
