#!/usr/bin/env python3
"""Build discourse pattern report from signature files.

Usage:
    python scripts/dataset/build_pattern_report.py [--signatures-dir .analysis_kb/signatures]

Reads ``signature_*.json`` files, runs pattern mining (C.3), and generates:
- ``docs/reports/discourse_patterns.md``
- ``docs/reports/discourse_patterns/*.svg`` (heatmap, radar, asymmetry)
"""
import argparse
import json
import pathlib
import sys
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

# Privacy: forbidden strings in any committed output
FORBIDDEN = ("raw_text", "full_text", "source_name", '"text":', "author")


# ---------------------------------------------------------------------------
# SVG generation helpers (no external dependencies)
# ---------------------------------------------------------------------------

def _svg_header(w: int, h: int) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">\n'


def _svg_text(x: int, y: int, text: str, size: int = 11, anchor: str = "start",
              color: str = "#333", angle: int = 0) -> str:
    transform = f' transform="rotate({angle},{x},{y})"' if angle else ""
    return (f'<text x="{x}" y="{y}" font-size="{size}" '
            f'fill="{color}" text-anchor="{anchor}"{transform}>{text}</text>\n')


def _svg_rect(x: int, y: int, w: int, h: int, fill: str, opacity: float = 1.0) -> str:
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'fill="{fill}" opacity="{opacity}"/>\n')


def _lerp_color(val: float, low: str = "#f0f0f0", high: str = "#2c3e50") -> str:
    """Interpolate between low and high hex colors based on val ∈ [0, 1]."""
    if val <= 0:
        return low
    if val >= 1:
        return high
    lr, lg, lb = int(low[1:3], 16), int(low[3:5], 16), int(low[5:7], 16)
    hr, hg, hb = int(high[1:3], 16), int(high[3:5], 16), int(high[5:7], 16)
    r = int(lr + (hr - lr) * val)
    g = int(lg + (hg - lg) * val)
    b = int(lb + (hb - lb) * val)
    return f"#{r:02x}{g:02x}{b:02x}"


def generate_heatmap_svg(pairs: List[Dict[str, Any]], top_n: int = 15) -> str:
    """Generate co-occurrence heatmap SVG from pattern_mining pairs."""
    if not pairs:
        return _svg_header(400, 200) + _svg_text(200, 100, "No co-occurrence data", 14, "middle") + "</svg>"

    types = sorted({p["a"] for p in pairs} | {p["b"] for p in pairs})[:top_n]
    n = len(types)
    cell = max(30, min(50, 500 // max(n, 1)))
    margin_l, margin_t = 120, 30
    w = margin_l + n * cell + 40
    h = margin_t + n * cell + 80

    pair_map = {}
    for p in pairs:
        pair_map[(p["a"], p["b"])] = p["lift"]
        pair_map[(p["b"], p["a"])] = p["lift"]

    max_lift = max((p["lift"] for p in pairs), default=1.0) or 1.0
    svg = _svg_header(w, h)

    # Column headers
    for i, t in enumerate(types):
        x = margin_l + i * cell + cell // 2
        svg += _svg_text(x, margin_t - 5, t[:12], 8, "middle", angle=-45)

    # Row headers + cells
    for j, tb in enumerate(types):
        y = margin_t + j * cell + cell // 2 + 4
        svg += _svg_text(margin_l - 5, y, tb[:12], 8, "end")
        for i, ta in enumerate(types):
            cx = margin_l + i * cell
            cy = margin_t + j * cell
            lift = pair_map.get((ta, tb), 0)
            norm = min(lift / max_lift, 1.0) if max_lift > 0 else 0
            fill = _lerp_color(norm)
            svg += _svg_rect(cx, cy, cell - 1, cell - 1, fill, 0.8)
            if lift > 0:
                svg += _svg_text(cx + cell // 2, cy + cell // 2 + 4,
                                 f"{lift:.1f}", 7, "middle", "white")

    svg += _svg_text(w // 2, h - 15, "Fallacy Co-occurrence Heatmap (lift)", 12, "middle", "#2c3e50")
    svg += "</svg>"
    return svg


def generate_radar_svg(spectrum: Dict[str, Dict[str, float]],
                       cluster_id: str) -> str:
    """Generate a simple radar-like bar chart for one cluster's fallacy spectrum."""
    fallacies = spectrum.get(cluster_id, {})
    if not fallacies:
        return _svg_header(400, 200) + _svg_text(200, 100, f"No data for {cluster_id}", 14, "middle") + "</svg>"

    items = sorted(fallacies.items(), key=lambda x: -x[1])[:12]
    n = len(items)
    bar_h = 18
    margin_l, margin_t = 130, 40
    w = 500
    h = margin_t + n * (bar_h + 4) + 40

    svg = _svg_header(w, h)
    svg += _svg_text(w // 2, 20, f"Fallacy Spectrum — {cluster_id}", 13, "middle", "#2c3e50")

    max_val = max((v for _, v in items), default=1.0) or 1.0
    for i, (ftype, freq) in enumerate(items):
        y = margin_t + i * (bar_h + 4)
        svg += _svg_text(margin_l - 5, y + bar_h - 3, ftype[:18], 9, "end")
        bar_w = int((freq / max_val) * (w - margin_l - 40))
        svg += _svg_rect(margin_l, y, bar_w, bar_h, "#2c3e50", 0.7)
        svg += _svg_text(margin_l + bar_w + 5, y + bar_h - 3, f"{freq:.2f}", 8)

    svg += "</svg>"
    return svg


def generate_asymmetry_svg(asymmetry: Dict[str, Dict[str, float]]) -> str:
    """Generate Tricherie vs Influence asymmetry bar chart."""
    if not asymmetry:
        return _svg_header(400, 200) + _svg_text(200, 100, "No asymmetry data", 14, "middle") + "</svg>"

    clusters = sorted(asymmetry.keys())
    n = len(clusters)
    bar_w = 60
    margin_l, margin_t = 100, 40
    gap = 40
    w = margin_l + n * (bar_w + gap) + 40
    h = 300

    svg = _svg_header(w, h)
    svg += _svg_text(w // 2, 20, "Tricherie vs Influence Asymmetry", 13, "middle", "#2c3e50")

    max_val = 1.0
    for i, cid in enumerate(clusters):
        x = margin_l + i * (bar_w + gap)
        d = asymmetry[cid]
        t_share = d.get("tricherie_share", 0)
        i_share = d.get("influence_share", 0)
        total = t_share + i_share

        # Tricherie bar (bottom, dark)
        t_h = int((t_share / max_val) * 180) if max_val > 0 else 0
        svg += _svg_rect(x, 240 - t_h - int((i_share / max_val) * 180),
                         bar_w, t_h, "#8b4513", 0.8)

        # Influence bar (top, blue)
        i_h = int((i_share / max_val) * 180) if max_val > 0 else 0
        svg += _svg_rect(x, 240 - i_h, bar_w, i_h, "#2c3e50", 0.8)

        svg += _svg_text(x + bar_w // 2, 258, cid[:10], 8, "middle")
        asym_val = d.get("asymmetry", 0)
        svg += _svg_text(x + bar_w // 2, 272, f"{asym_val:+.2f}", 8, "middle", "#666")

    svg += _svg_text(30, 80, "Influence", 9, "middle", "#2c3e50")
    svg += _svg_text(30, 200, "Tricherie", 9, "middle", "#8b4513")
    svg += "</svg>"
    return svg


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def load_signatures(signatures_dir: pathlib.Path) -> List[Dict[str, Any]]:
    """Load all signature_*.json files from directory."""
    sigs = []
    if not signatures_dir.is_dir():
        return sigs
    for p in sorted(signatures_dir.glob("signature_*.json")):
        try:
            sigs.append(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return sigs


def privacy_guard(content: str) -> None:
    """Exit with error if forbidden strings found in content."""
    lower = content.lower()
    for f in FORBIDDEN:
        if f.lower() in lower:
            print(f"PRIVACY GUARD: forbidden string '{f}' found in report", file=sys.stderr)
            sys.exit(1)


def build_report(signatures: List[Dict[str, Any]],
                 output_dir: pathlib.Path,
                 report_path: pathlib.Path) -> pathlib.Path:
    """Generate discourse_patterns.md + SVG charts."""
    from argumentation_analysis.evaluation.pattern_mining import (
        cooccurrence_matrix,
        cross_coverage,
        fallacy_spectrum,
        run_formal_detectors,
        trick_vs_influence_ratio,
        FORMAL_DETECTORS,
    )

    n_docs = len(signatures)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # 1. Spectral analysis
    spectrum = fallacy_spectrum(signatures)
    cluster_ids = sorted(spectrum.keys())

    # 2. Asymmetry
    asymmetry = trick_vs_influence_ratio(signatures)

    # 3. Co-occurrence
    coocc = cooccurrence_matrix(signatures, top_n=20)

    # 4. Formal detectors
    formal_results = {}
    for sig in signatures:
        cid = sig.get("metadata", {}).get("cluster_id", "unknown")
        if cid not in formal_results:
            formal_results[cid] = run_formal_detectors(sig)

    # 5. Cross-coverage
    xcov = cross_coverage(signatures)

    # --- Build markdown ---
    md = f"# Discourse Pattern Report\n\n"
    md += f"**Generated**: {now}\n"
    md += f"**Documents analyzed**: {n_docs}\n"
    md += f"**Clusters**: {len(cluster_ids)} ({', '.join(cluster_ids) or 'none'})\n"
    md += f"**Workflow**: spectacular 17 phases\n\n"
    md += "---\n\n"

    # Section 2: Spectra
    md += "## 1. Fallacy Spectra by Cluster\n\n"
    if spectrum:
        all_types = sorted({t for c in spectrum.values() for t in c})
        md += "| Cluster | " + " | ".join(all_types[:10]) + " |\n"
        md += "|" + "---------|" * (len(all_types[:10]) + 1) + "\n"
        for cid in cluster_ids:
            vals = [f"{spectrum[cid].get(t, 0):.2f}" for t in all_types[:10]]
            md += f"| {cid} | " + " | ".join(vals) + " |\n"
        md += "\n"
    else:
        md += "_No spectral data available._\n\n"

    # Section 3: Asymmetry
    md += "## 2. Tricherie ↔ Influence Asymmetry\n\n"
    if asymmetry:
        md += "| Cluster | Tricherie | Influence | Ratio | Asymmetry |\n"
        md += "|---------|-----------|-----------|-------|----------|\n"
        for cid in sorted(asymmetry.keys()):
            d = asymmetry[cid]
            md += (f"| {cid} | {d.get('tricherie_share', 0):.3f} | "
                   f"{d.get('influence_share', 0):.3f} | "
                   f"{d.get('ratio', 0):.2f} | "
                   f"{d.get('asymmetry', 0):+.3f} |\n")
        md += "\n"
    else:
        md += "_No asymmetry data._\n\n"

    # Section 4: Co-occurrences
    md += "## 3. Co-occurrence Top-20\n\n"
    if coocc.get("pairs"):
        md += "| Fallacy A | Fallacy B | Support | Confidence | Lift | Jaccard |\n"
        md += "|-----------|-----------|---------|------------|------|--------|\n"
        for p in coocc["pairs"][:20]:
            md += (f"| {p['a']} | {p['b']} | {p['support']} | "
                   f"{p['confidence']:.3f} | {p['lift']:.2f} | "
                   f"{p['jaccard']:.3f} |\n")
        md += f"\n_Units with co-occurrences: {coocc.get('unit_count', 0)}_\n\n"
    else:
        md += "_No co-occurrence data._\n\n"

    # Section 5: Formal patterns
    md += "## 4. Formal Pattern Detectors\n\n"
    for det in FORMAL_DETECTORS:
        md += f"### {det.name}\n\n"
        if formal_results:
            md += "| Cluster | " + " | ".join(k for k in next(iter(formal_results.values())).get(det.name, {}).keys()) + " |\n"
            header_cols = list(next(iter(formal_results.values())).get(det.name, {}).keys())
            md += "|" + "------|" * (len(header_cols) + 1) + "\n"
            for cid, results in sorted(formal_results.items()):
                vals = results.get(det.name, {})
                md += f"| {cid} | " + " | ".join(f"{vals.get(k, 0):.3f}" for k in header_cols) + " |\n"
        md += "\n"

    # Section 6: Cross-coverage
    md += "## 5. Cross-coverage: Informal ↔ Formal\n\n"
    if xcov:
        signals = ["fol_invalid", "dung_unsupported", "jtms_retraction"]
        md += "| Fallacy Type | " + " | ".join(s.title() for s in signals) + " |\n"
        md += "|" + "------|" * (len(signals) + 1) + "\n"
        for ftype in sorted(xcov.keys()):
            vals = [f"{xcov[ftype].get(s, 0):.2f}" for s in signals]
            md += f"| {ftype} | " + " | ".join(vals) + " |\n"
        md += "\n_Hypothesis: manipulation = camouflaging formal errors?_\n\n"
    else:
        md += "_No cross-coverage data._\n\n"

    # Section 7: Limitations
    md += "## 6. Limitations & Next Steps\n\n"
    md += "- Coverage limited to available corpus subset\n"
    md += "- Sampling bias toward represented discourse types\n"
    md += "- Formal detector registry is extensible (see `pattern_mining.FORMAL_DETECTORS`)\n"
    md += "- Future: temporal comparison, richer metadata, LLM-assisted narrative\n"

    # Privacy guard
    privacy_guard(md)

    # Write report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(md, encoding="utf-8")

    # Write SVGs
    svg_dir = output_dir / "discourse_patterns"
    svg_dir.mkdir(parents=True, exist_ok=True)

    (svg_dir / "heatmap_fallacies.svg").write_text(
        generate_heatmap_svg(coocc.get("pairs", [])), encoding="utf-8")
    (svg_dir / "asymmetry_chart.svg").write_text(
        generate_asymmetry_svg(asymmetry), encoding="utf-8")

    for cid in cluster_ids[:5]:
        (svg_dir / f"spectrum_radar_{cid}.svg").write_text(
            generate_radar_svg(spectrum, cid), encoding="utf-8")

    return report_path


def main():
    parser = argparse.ArgumentParser(
        description="Build discourse pattern report from signature files")
    parser.add_argument("--signatures-dir", type=pathlib.Path,
                        default=pathlib.Path(".analysis_kb/signatures"))
    args = parser.parse_args()

    signatures = load_signatures(args.signatures_dir)
    if not signatures:
        print("No signature files found. Generate them with pattern-rerun first.",
              file=sys.stderr)
        sys.exit(1)

    report_path = REPO_ROOT / "docs" / "reports" / "discourse_patterns.md"
    output_dir = REPO_ROOT / "docs" / "reports"

    result = build_report(signatures, output_dir, report_path)
    print(f"Report: {result}")
    print(f"SVGs:   {output_dir / 'discourse_patterns'}/")


if __name__ == "__main__":
    main()
