#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the showcase integrated report from live run results.

Reads all_results.json from outputs/showcase_ff/ and populates
the report template at docs/reports/SHOWCASE_INTEGRATED_ANALYSIS_2026-05-24.md.

Usage:
    python scripts/build_showcase_report.py
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_RESULTS_PATH = _PROJECT_ROOT / "outputs" / "showcase_ff" / "all_results.json"
_REPORT_PATH = _PROJECT_ROOT / "docs" / "reports" / "SHOWCASE_INTEGRATED_ANALYSIS_2026-05-24.md"


def _dash(val: Any) -> str:
    if val is None or val == 0:
        return "—"
    return str(val)


def _check_mark(val: Any) -> str:
    if val:
        return str(val)
    return "—"


def _format_fallacy_table(fallacy_details: List[Dict]) -> str:
    if not fallacy_details:
        return "None detected"
    rows = []
    for fd in fallacy_details:
        tp = fd.get("type", "?")
        pk = fd.get("taxonomy_pk") or "—"
        conf = fd.get("confidence")
        conf_str = f"{conf:.2f}" if conf else "—"
        target = fd.get("target_arg_id") or "—"
        rows.append(f"| {tp} | {pk} | {conf_str} | {target} |")
    header = "| Type | Taxonomy PK | Confidence | Target Arg |\n|------|-------------|------------|------------|"
    return header + "\n" + "\n".join(rows)


def build_corpus_section(corpus_id: str, data: Dict[str, Any]) -> str:
    """Build the per-corpus findings section."""
    label = data["label"]
    desc = data["desc"]
    text_len = data["text_length"]

    seq = data.get("sequential") or {}
    spec = data.get("spectacular") or {}

    has_error_seq = "error" in seq if seq else False
    has_error_spec = "error" in spec if spec else False

    # Arguments
    args_seq = seq.get("arguments_found", "—") if not has_error_seq else "ERROR"
    args_spec = spec.get("arguments_found", "—") if not has_error_spec else "ERROR"

    # Fallacies
    fall_seq = seq.get("fallacies_found", "—") if not has_error_seq else "ERROR"
    fall_spec = spec.get("fallacies_found", "—") if not has_error_spec else "ERROR"
    fall_seq_method = seq.get("extraction_method", "—") if not has_error_seq else "—"
    fall_spec_method = spec.get("extraction_method", "—") if not has_error_spec else "—"

    # Fallacy details
    fall_seq_details = _format_fallacy_table(seq.get("fallacy_details", [])) if not has_error_seq else "Run failed"
    fall_spec_details = _format_fallacy_table(spec.get("fallacy_details", [])) if not has_error_spec else "Run failed"

    # Formal categories
    form_seq = seq.get("unique_formal_categories", "—") if not has_error_seq else "—"
    form_spec = spec.get("unique_formal_categories", "—") if not has_error_spec else "—"
    form_seq_details = ", ".join(seq.get("formal_category_details", [])) or "—"

    # JTMS
    jtms_seq = seq.get("jtms_beliefs", "—") if not has_error_seq else "—"
    jtms_spec = spec.get("jtms_beliefs", "—") if not has_error_spec else "—"

    # Counter-args
    ctr_seq = seq.get("counter_arguments", "—") if not has_error_seq else "—"
    ctr_spec = spec.get("counter_arguments", "—") if not has_error_spec else "—"

    # Convergence
    conv_seq = seq.get("convergence_depth", 0) if not has_error_seq else "—"
    conv_spec = spec.get("convergence_depth", 0) if not has_error_spec else "—"

    signals_seq = seq.get("convergence_signals", {}) if not has_error_seq else {}
    signals_spec = spec.get("convergence_signals", {}) if not has_error_spec else {}

    # Duration
    dur_seq = f"{seq.get('duration_seconds', 0):.0f}s" if not has_error_seq else "—"
    dur_spec = f"{spec.get('duration_seconds', 0):.0f}s" if not has_error_spec else "—"

    section = f"""### Corpus {corpus_id}: {label} ({desc}, {text_len:,} chars)

#### Arguments Extracted

| Path | Count | Details |
|------|-------|---------|
| Sequential full | {args_seq} | Duration: {dur_seq} |
| Spectacular | {args_spec} | Duration: {dur_spec} |

#### Fallacies Detected

| Path | Count | Method |
|------|-------|--------|
| Sequential full | {fall_seq} | {fall_seq_method} |
| Spectacular | {fall_spec} | {fall_spec_method} |

<details>
<summary>Sequential fallacy details</summary>

{fall_seq_details}

</details>

<details>
<summary>Spectacular fallacy details</summary>

{fall_spec_details}

</details>

#### Formal Logic (Sequential path only)

| Metric | Value |
|--------|-------|
| Formal categories | {form_seq} ({form_seq_details}) |
| JTMS beliefs | {jtms_seq} |
| Counter-arguments | {ctr_seq} |

#### Convergence

| Signal | Sequential | Spectacular |
|--------|------------|-------------|
| Sophisme | {_check_mark(signals_seq.get('sophisme'))} | {_check_mark(signals_spec.get('sophisme'))} |
| Qualité faible | {_check_mark(signals_seq.get('qualite_faible'))} | {_check_mark(signals_spec.get('qualite_faible'))} |
| Contre-argument | {_check_mark(signals_seq.get('contre_argument'))} | {_check_mark(signals_spec.get('contre_argument'))} |
| JTMS rétracté | {_check_mark(signals_seq.get('jtms_retracte'))} | {_check_mark(signals_spec.get('jtms_retracte'))} |
| Rejet Dung | {_check_mark(signals_seq.get('rejet_dung'))} | {_check_mark(signals_spec.get('rejet_dung'))} |
| **Depth** | **{conv_seq}** | **{conv_spec}** |
"""
    return section


def build_dd_verify(data: Dict[str, Any]) -> str:
    """Build DD live-verify section for corpus C."""
    seq = data.get("sequential") or {}
    if "error" in seq:
        return f"| Metric | Value | DoD | Status |\n|--------|-------|-----|--------|\n| Sequential run | FAILED | — | ERROR: {seq['error'][:80]} |"

    fallacies = seq.get("fallacies_found", 0)
    targets = sum(1 for fd in seq.get("fallacy_details", []) if fd.get("target_arg_id"))
    dd_pass = fallacies >= 3 and targets >= 1

    return f"""| Metric | Value | DoD Threshold | Status |
|--------|-------|---------------|--------|
| Fallacies found | {fallacies} | ≥ 3 | {'PASS' if fallacies >= 3 else 'FAIL'} |
| target_argument_id resolved | {targets} | ≥ 1 | {'PASS' if targets >= 1 else 'FAIL'} |
| **DD DoD** | {'PASS' if dd_pass else 'FAIL'} | ≥3 fallacies AND ≥1 target | **{'CONFIRMED' if dd_pass else 'NOT MET'}** |"""


def build_cross_corpus_table(all_results: List[Dict]) -> str:
    """Build cross-corpus comparison table."""
    header = "| Metric | corpus_dense_A (seq/spec) | corpus_dense_B (seq/spec) | corpus_dense_C (seq/spec) |\n|--------|--------------------------|--------------------------|--------------------------|"

    def _pair(r: Dict, key: str) -> str:
        seq = r.get("sequential", {})
        spec = r.get("spectacular", {})
        sv = seq.get(key, "—") if "error" not in seq else "ERR"
        pv = spec.get(key, "—") if "error" not in spec else "ERR"
        return f"{_dash(sv)} / {_dash(pv)}"

    rows = []
    for key, label in [
        ("arguments_found", "Arguments"),
        ("fallacies_found", "Fallacies"),
        ("unique_formal_categories", "Formal categories"),
        ("jtms_beliefs", "JTMS beliefs"),
        ("counter_arguments", "Counter-args"),
        ("convergence_depth", "Convergence depth"),
    ]:
        cells = [_pair(r, key) for r in all_results]
        rows.append(f"| {label} | {' | '.join(cells)} |")

    # Duration row
    dur_cells = []
    for r in all_results:
        seq = r.get("sequential", {})
        spec = r.get("spectacular", {})
        sd = seq.get("duration_seconds")
        pd = spec.get("duration_seconds")
        sd_str = f"{sd:.0f}s" if sd and "error" not in seq else "ERR"
        pd_str = f"{pd:.0f}s" if pd and "error" not in spec else "ERR"
        dur_cells.append(f"{sd_str} / {pd_str}")
    rows.append(f"| Duration | {' | '.join(dur_cells)} |")

    return header + "\n" + "\n".join(rows)


def main() -> None:
    if not _RESULTS_PATH.exists():
        print(f"ERROR: {_RESULTS_PATH} not found. Run showcase_integrated_analysis.py first.")
        sys.exit(1)

    with open(_RESULTS_PATH, encoding="utf-8") as f:
        all_results = json.load(f)

    with open(_REPORT_PATH, encoding="utf-8") as f:
        template = f.read()

    # Build per-corpus sections
    corpus_sections = {}
    dd_section = ""
    for r in all_results:
        cid = r["corpus_id"]
        corpus_sections[cid] = build_corpus_section(cid, r)
        if cid == "C":
            dd_section = build_dd_verify(r)

    # Build cross-corpus table
    cross_table = build_cross_corpus_table(all_results)

    # Replace sections in template
    # Replace corpus A section
    pattern_a = r"(### Corpus A:.*?)(---\n\n### Corpus B)"
    if re.search(pattern_a, template, re.DOTALL):
        template = re.sub(pattern_a, corpus_sections.get("A", "") + "\n\n\\2", template, flags=re.DOTALL)

    # Replace corpus B section
    pattern_b = r"(### Corpus B:.*?)(---\n\n### Corpus C)"
    if re.search(pattern_b, template, re.DOTALL):
        template = re.sub(pattern_b, corpus_sections.get("B", "") + "\n\n\\2", template, flags=re.DOTALL)

    # Replace corpus C section
    pattern_c = r"(### Corpus C:.*?)(---\n\n## Cross-Corpus)"
    if re.search(pattern_c, template, re.DOTALL):
        template = re.sub(pattern_c, corpus_sections.get("C", "") + "\n\n\\2", template, flags=re.DOTALL)

    # Replace DD verify section
    dd_pattern = r"\| Metric \| Value \| DoD Threshold \| Status \|.*?(?=\n\n#### Arguments)"
    if re.search(dd_pattern, template, re.DOTALL):
        template = re.sub(dd_pattern, dd_section, template, flags=re.DOTALL)

    # Replace cross-corpus table
    cross_pattern = r"\| Metric \| corpus_dense_A.*?(?=\n\n---|\n\n## Tools)"
    if re.search(cross_pattern, template, re.DOTALL):
        template = re.sub(cross_pattern, cross_table + "\n", template, flags=re.DOTALL)

    with open(_REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(template)

    print(f"Report updated: {_REPORT_PATH}")


if __name__ == "__main__":
    main()
